from concurrent.futures import ThreadPoolExecutor

from . import db

# How many per-wiki queries to run at once. Sequential execution turned out
# to be unworkable (see for_each_wiki's docstring), but so did overshooting
# this: the wikireplica MySQL user has a hard server-side cap, confirmed
# live via the actual error --
#   OperationalError: (1226, "User 's...' has exceeded the
#   'max_user_connections' resource (current value: 10)")
# -- hit at 40 (and would hit at 20 too), which silently dropped ~1/3 of
# wikis at random from every "all wikis" tool's results (each dropped wiki
# just looks like it has nothing to report, since for_each_wiki treats a
# connection failure the same as "no data for this wiki" -- this is what
# was actually behind wikidatawiki/wikifunctionswiki/etc. intermittently
# vanishing from results, not anything specific to those wikis). Kept a
# couple of connections under that hard 10 rather than exactly at it, since
# list_wikis() itself briefly holds one more.
#
# This is a real speed tradeoff, not a free fix: at this concurrency,
# recent-logs for a very globally active account took ~190s live (vs ~48s
# at the too-high 40 that was silently dropping wikis) -- see Procfile's
# gunicorn --timeout, sized with that in mind. There's no further easy win
# here short of Wikimedia raising the per-user connection cap; the slowness
# is inherent to combining "no usable index for this query on large wikis"
# with "only 8-ish requests can be in flight against the replicas at once".
MAX_CONCURRENT_WIKI_QUERIES = 8


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
