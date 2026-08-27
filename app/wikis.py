from . import db


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
    """Calls fn(dbname, url) for every public wiki and collects the non-None
    results. A wiki whose replica is unreachable, or that raises for any
    other reason (a closed/private wiki that slips through the `url IS NOT
    NULL` filter, a query that doesn't match some wiki's schema variant),
    is silently skipped -- mirroring the original scripts' bare `except:
    pass` per-wiki fault tolerance rather than failing the whole page over
    one wiki.
    """
    results = []
    for dbname, url in list_wikis(meta_host):
        try:
            value = fn(dbname, url)
        except Exception:
            continue
        if value is not None:
            results.append(value)
    return results
