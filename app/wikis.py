from concurrent.futures import ThreadPoolExecutor

from . import db

# How many per-wiki queries to run at once. Sequential execution turned out
# to be unworkable: `logging.log_actor` has no usable index on the large
# wikis (confirmed live -- a bare `SELECT COUNT(*) FROM logging WHERE
# log_actor = <id>` on enwiki, no joins or sorting, took 25.5s for 100
# matching rows out of a huge table), so a handful of the ~1,000 wikis cost
# 15-45s+ each. With this many workers, those all fit in roughly one round
# instead of two-plus (confirmed live: recent-logs for a very active account
# went from 90s at 20 workers to well under that at 40 -- there just aren't
# many wikis that land on the slow path for any single user). Chosen as a
# balance against the wikireplica connection-count limit per tool, not
# tuned for raw throughput -- no connection-limit errors observed live at
# this level, but don't keep raising it blindly.
MAX_CONCURRENT_WIKI_QUERIES = 40


def list_wikis(meta_host):
    """(dbname, url) for every public Wikimedia wiki, per meta_p.wiki.

    The original scripts also selected `slice` and used it as the MySQL
    host to connect to, reconnecting only when it changed between wikis (an
    optimization for the old shared-host-per-slice replica topology). That
    column still exists but its values are stale retired hostnames like
    "s3.labsdb" -- confirmed live via `SELECT slice FROM wiki`. Every wiki
    is directly reachable today at wiki_db_host(dbname), so there's no
    grouping to do; this only selects dbname/url.
    """
    with db.connect(meta_host, db="meta_p") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT dbname, url FROM wiki WHERE url IS NOT NULL ORDER BY dbname")
            return cur.fetchall()


def wiki_db_host(dbname, cluster="analytics"):
    return f"{dbname}.{cluster}.db.svc.wikimedia.cloud"


def for_each_wiki(meta_host, fn):
    """Calls fn(dbname, url) for every public wiki, concurrently (see
    MAX_CONCURRENT_WIKI_QUERIES), and collects the non-None results. A wiki
    whose replica is unreachable, times out, or raises for any other reason
    (a closed/private wiki that slips through the `url IS NOT NULL` filter,
    a query that doesn't match some wiki's schema variant) is silently
    skipped -- mirroring the original scripts' bare `except: pass` per-wiki
    fault tolerance rather than failing the whole page over one wiki.

    `results` stays in wiki (dbname) order despite the concurrent
    execution -- `Executor.map` yields in input order, not completion
    order, so display order is unchanged from the old sequential version.
    """
    def run_one(wiki):
        dbname, url = wiki
        try:
            return fn(dbname, url)
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WIKI_QUERIES) as pool:
        return [
            value
            for value in pool.map(run_one, list_wikis(meta_host))
            if value is not None
        ]
