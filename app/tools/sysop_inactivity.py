from .. import db
from ..wikis import wiki_db_host

ADMIN_LOG_TYPES = ("block", "delete", "protect", "import")
MEDIAWIKI_NAMESPACE = 8


def inactive_sysops(dbname: str, since_timestamp: str | None):
    """(username, last_activity_or_None) for every sysop on `dbname`,
    ordered by last activity (NULLs -- i.e. never active at all by either
    measure -- first). "Activity" is the later of: their last
    block/delete/protect/import log action, or their last edit to a
    MediaWiki: namespace (system message) page. When `since_timestamp` is
    given, only sysops whose activity is entirely before it are returned
    (matches the original tool's "inactive since" filter).

    Rewritten off `user_id`/`rev_user`/`log_user` joins, none of which
    exist anymore -- both `logging` and `revision` now attribute actions
    via `log_actor`/`rev_actor` -> `actor.actor_id`, bridged back to
    `user_groups`/`user` via `actor.actor_user` (confirmed live against
    srwiki_p, see docs/deployment-toolforge.md).
    """
    log_type_list = ", ".join(f"'{t}'" for t in ADMIN_LOG_TYPES)  # fixed, trusted constants
    having = "HAVING latest < %(ts)s" if since_timestamp else ""
    params = {"ts": since_timestamp} if since_timestamp else {}

    sql = f"""
        SELECT A.username, CASE
            WHEN A.latest IS NULL AND B.latest IS NULL THEN NULL
            WHEN A.latest IS NULL THEN B.latest
            WHEN B.latest IS NULL THEN A.latest
            WHEN A.latest > B.latest THEN A.latest ELSE B.latest END AS latest
        FROM (
            (SELECT user_name AS username, MAX(log_timestamp) AS latest
             FROM user
             JOIN user_groups ON user_id = ug_user
             JOIN actor ON actor_user = user_id
             JOIN logging ON log_actor = actor_id
             WHERE ug_group = 'sysop' AND log_type IN ({log_type_list})
             GROUP BY username {having})
            UNION
            (SELECT user_name AS username, NULL AS latest
             FROM user JOIN user_groups ON user_id = ug_user
             WHERE ug_group = 'sysop'
             AND user_id NOT IN (
                 SELECT actor_user FROM actor JOIN logging ON log_actor = actor_id
                 WHERE log_type IN ({log_type_list}) AND actor_user IS NOT NULL))
        ) AS A
        INNER JOIN (
            (SELECT user_name AS username, MAX(rev_timestamp) AS latest
             FROM user
             JOIN user_groups ON user_id = ug_user
             JOIN actor ON actor_user = user_id
             JOIN revision ON rev_actor = actor_id
             JOIN page ON rev_page = page_id
             WHERE ug_group = 'sysop' AND page_namespace = {MEDIAWIKI_NAMESPACE}
             GROUP BY username {having})
            UNION
            (SELECT user_name AS username, NULL AS latest
             FROM user JOIN user_groups ON user_id = ug_user
             WHERE ug_group = 'sysop'
             AND user_id NOT IN (
                 SELECT actor_user FROM actor JOIN revision ON rev_actor = actor_id
                 JOIN page ON rev_page = page_id
                 WHERE page_namespace = {MEDIAWIKI_NAMESPACE} AND actor_user IS NOT NULL))
        ) AS B ON A.username = B.username
        ORDER BY latest
    """
    with db.connect(wiki_db_host(dbname), db=f"{dbname}_p") as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [db.decode_row(row) for row in cur.fetchall()]
