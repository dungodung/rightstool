from .. import db
from ..wikis import for_each_wiki, wiki_db_host


def rights_by_wiki(username: str, meta_host: str):
    """(dbname, url, [group, ...]) for every wiki where the user holds at
    least one non-default group. `user`/`user_groups` are unaffected by the
    actor/comment normalization that broke several of the other tools here
    (verified live), so this query is unchanged from the original besides
    parameterization.
    """
    def query_one(dbname, url):
        with db.connect(wiki_db_host(dbname), db=f"{dbname}_p") as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT ug_group FROM user, user_groups WHERE user_name=%s AND user_id=ug_user",
                    (username,),
                )
                rights = [db.decode(row[0]) for row in cur.fetchall()]
        return (dbname, url, rights) if rights else None

    return for_each_wiki(meta_host, query_one)
