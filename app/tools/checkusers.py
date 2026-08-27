from .. import db
from ..wikis import for_each_wiki, wiki_db_host


def checkusers_by_wiki(meta_host: str):
    """(dbname, url, [(username, group), ...]) for every wiki that has at
    least one checkuser or steward.
    """
    def query_one(dbname, url):
        with db.connect(wiki_db_host(dbname), db=f"{dbname}_p") as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT user_name, ug_group FROM user, user_groups
                    WHERE ug_user = user_id AND (ug_group = 'checkuser' OR ug_group = 'steward')
                    ORDER BY user_name ASC
                    """
                )
                rows = [db.decode_row(row) for row in cur.fetchall()]
        return (dbname, url, rows) if rows else None

    return for_each_wiki(meta_host, query_one)
