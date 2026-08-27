from .. import db
from ..wikis import for_each_wiki, wiki_db_host

DEFAULT_RIGHTS = {
    "bot", "sysop", "bureaucrat", "checkuser", "steward", "boardvote", "import",
    "transwiki", "developer", "oversight", "ipblock-exempt", "confirmed", "",
}


def non_default_rights_by_wiki(meta_host: str):
    """(dbname, url, [group, ...]) for every wiki that has at least one
    user group beyond the standard/global ones.
    """
    def query_one(dbname, url):
        with db.connect(wiki_db_host(dbname), db=f"{dbname}_p") as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT ug_group FROM user_groups")
                groups = {db.decode(row[0]) for row in cur.fetchall()}
        extra = sorted(groups - DEFAULT_RIGHTS)
        return (dbname, url, extra) if extra else None

    return for_each_wiki(meta_host, query_one)
