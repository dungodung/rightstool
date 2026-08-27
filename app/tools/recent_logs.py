from .. import db
from ..wikis import for_each_wiki, wiki_db_host

NAMESPACES = {
    -2: "Media:", -1: "Special:", 0: "", 1: "Talk:", 2: "User:", 3: "User talk:",
    4: "Project:", 5: "Project talk:", 6: "Image:", 7: "Image talk:", 8: "MediaWiki:",
    9: "MediaWiki talk:", 10: "Template:", 11: "Template talk:", 12: "Help:",
    13: "Help talk:", 14: "Category:", 15: "Category talk:", 100: "Portal:", 101: "Portal talk:",
}


def namespace_prefix(ns: int) -> str:
    return NAMESPACES.get(ns, f"Namespace_{ns}:")


def logs_by_wiki(username: str, hide_patrol: bool, hide_newusers: bool, meta_host: str):
    """(dbname, url, total_count, [row, ...]) per wiki with at least one
    matching log entry; each row is (log_type, timestamp, title, comment).

    The original query joined `logging` to `user` via `log_user=user_id` and
    selected `log_comment` directly -- both gone from the current schema
    (confirmed live via `DESCRIBE logging` on metawiki_p): log actions are
    now attributed via `log_actor` -> `actor.actor_id`, and comments live in
    a separate `comment` table referenced by `log_comment_id`.
    """
    conditions = []
    if hide_patrol:
        conditions.append("log_type != 'patrol'")
    if hide_newusers:
        conditions.append("log_type != 'newusers'")
    conditions.append("log_type != 'suppress'")
    where = " AND ".join(conditions)

    def query_one(dbname, url):
        # One round trip per wiki, not two: the total-count subquery rides
        # along in the same SELECT instead of a separate query afterwards.
        # This mattered in practice -- with a second query per wiki, a full
        # ~1,000-wiki sweep took long enough to trip gunicorn's worker
        # timeout and 500 (confirmed live), where the other all-wikis tools
        # here (one query per wiki) finish in ~15s.
        with db.connect(wiki_db_host(dbname), db=f"{dbname}_p") as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT log_type, log_namespace, log_title, comment_text, log_timestamp,
                        (SELECT COUNT(*) FROM logging l2 JOIN actor a2 ON l2.log_actor = a2.actor_id
                         WHERE a2.actor_name = %s) AS total_count
                    FROM logging
                    JOIN actor ON log_actor = actor_id
                    LEFT JOIN comment ON log_comment_id = comment_id
                    WHERE actor_name = %s AND {where}
                    ORDER BY log_timestamp DESC LIMIT 10
                    """,
                    (username, username),
                )
                fetched = [db.decode_row(row) for row in cur.fetchall()]
        if not fetched:
            return None
        count = fetched[0][-1]
        rows = [row[:-1] for row in fetched]
        return (dbname, url, count, rows)

    return for_each_wiki(meta_host, query_one)
