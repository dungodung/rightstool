import time

from .. import db
from ..wikis import for_each_wiki, wiki_db_host

WORRYING_AFTER_SECONDS = 4_000_000
CRITICAL_AFTER_SECONDS = 10_000_000


def last_revision_by_wiki(meta_host: str):
    """(dbname, url, timestamp, severity) for every wiki, ordered by dbname.
    severity is one of "ok", "worrying", "critical" based on how long ago
    the last edit landed.
    """
    now = int(time.strftime("%Y%m%d%H%M%S"))

    def query_one(dbname, url):
        with db.connect(wiki_db_host(dbname), db=f"{dbname}_p") as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT rev_timestamp FROM revision ORDER BY rev_id DESC LIMIT 1")
                row = cur.fetchone()
        if row is None:
            return None
        ts = db.decode(row[0])
        age = now - int(ts)
        if age > CRITICAL_AFTER_SECONDS:
            severity = "critical"
        elif age > WORRYING_AFTER_SECONDS:
            severity = "worrying"
        else:
            severity = "ok"
        return (dbname, url, ts, severity)

    return for_each_wiki(meta_host, query_one)
