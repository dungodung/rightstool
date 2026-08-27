import re

from .. import db

_GROUP_ITEM_RE = re.compile(r'i:\d+;s:\d+:"([^"]*)"')
_OLDGROUPS_RE = re.compile(r'"4::oldgroups";(a:\d+:\{.*?\})s:\d+:"5::newgroups"')
_NEWGROUPS_RE = re.compile(r'"5::newgroups";(a:\d+:\{.*?\})\}$')


def search(term: str, search_users: bool, search_titles: bool, metawiki_db_host: str):
    """Rows of ('rights'-type log entries on Meta-Wiki matching `term`,
    either against the acting user's name or the affected page title (or
    both). Returns (actor_name, log_title, log_params, comment, timestamp).

    Fixes three things versus the original: (1) `log_user`/`log_comment`
    don't exist anymore (see rights_changes.py for the same actor/comment
    migration); (2) the "search titles only" branch built a malformed SQL
    string (`'%%%s%%%'` -- an unterminated literal with a mismatched `%`
    count); (3) every branch interpolated the search term directly into the
    query text -- LIKE wildcards now live in the bound parameter instead.
    """
    pattern = f"%{term.strip().replace(' ', '_')}%"
    conditions = []
    params = []
    if search_users:
        conditions.append("actor_name LIKE %s")
        params.append(pattern)
    if search_titles:
        conditions.append("log_title LIKE %s")
        params.append(pattern)
    if not conditions:
        return []

    sql = f"""
        SELECT actor_name, log_title, log_params, comment_text, log_timestamp
        FROM logging
        JOIN actor ON log_actor = actor_id
        LEFT JOIN comment ON log_comment_id = comment_id
        WHERE log_type = 'rights' AND ({' OR '.join(conditions)})
        ORDER BY log_timestamp DESC
    """
    with db.connect(metawiki_db_host, db="metawiki_p") as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            return [db.decode_row(row) for row in cur.fetchall()]


def format_params(log_params) -> str:
    """A 'rights' log entry's params, rendered as "from OLD groups to NEW
    groups" when recognized, or returned as-is otherwise.

    Modern log_params for this log type is a PHP-serialized array keyed
    "4::oldgroups"/"5::newgroups" (confirmed live -- e.g.
    `a:2:{s:12:"4::oldgroups";a:1:{i:0;s:13:"autopatrolled";}...}`), not the
    plain newline-separated old/new pair the original tool's `split("\n")`
    assumed (that format predates this schema). This is a small targeted
    extraction of just those two keys, not a general PHP deserializer.
    """
    if not log_params:
        return "(none)"
    text = log_params.decode("utf-8") if isinstance(log_params, bytes) else log_params

    old_match = _OLDGROUPS_RE.search(text)
    new_match = _NEWGROUPS_RE.search(text)
    if old_match and new_match:
        old_groups = _GROUP_ITEM_RE.findall(old_match.group(1))
        new_groups = _GROUP_ITEM_RE.findall(new_match.group(1))
        return f"from {', '.join(old_groups) or '(none)'} to {', '.join(new_groups) or '(none)'}"

    # Legacy newline-separated old/new pair, from before params were
    # PHP-serialized.
    parts = [p if p else "(none)" for p in text.split("\n")]
    if len(parts) == 2:
        return f"from {parts[0]} to {parts[1]}"
    return text
