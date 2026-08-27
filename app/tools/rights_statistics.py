from collections import defaultdict

from .. import db
from ..wikis import list_wikis, wiki_db_host


def user_counts_by_right(meta_host: str):
    """{right: [(dbname, url, count), ...]} across every wiki, sorted by
    right name.
    """
    data = defaultdict(list)
    for dbname, url in list_wikis(meta_host):
        try:
            with db.connect(wiki_db_host(dbname), db=f"{dbname}_p") as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT ug_group, COUNT(ug_user) FROM user_groups GROUP BY ug_group")
                    rows = cur.fetchall()
        except Exception:
            continue
        for right, count in rows:
            data[db.decode(right)].append((dbname, url, count))
    return dict(sorted(data.items()))
