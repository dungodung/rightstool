from .. import db

LOG_TYPES = ("rights", "gblrights", "globalauth", "gblblock")


def steward_activity(metawiki_db_host: str):
    """(username, {log_type: last_timestamp_or_None}) for every user in
    metawiki's local 'steward' group, ordered by username.

    Rewritten as two simple queries instead of the original's four
    self-joined subqueries pivoted via SQL, both to fix the actor migration
    (`log_user` -> `log_actor`, which is an actor_id, not a user_id -- the
    original's `ug_user=log_user` comparison would now compare a user_id to
    an actor_id, matching nothing) and because pivoting the four
    max-timestamps-per-type in Python is far easier to verify correct than
    a 4-way self join.
    """
    with db.connect(metawiki_db_host, db="metawiki_p") as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT actor_id, actor_name FROM actor
                JOIN user_groups ON ug_user = actor_user
                WHERE ug_group = 'steward'
                """
            )
            stewards = [(actor_id, db.decode(name)) for actor_id, name in cur.fetchall()]
            if not stewards:
                return []
            actor_ids = [row[0] for row in stewards]
            placeholders = ", ".join(["%s"] * len(actor_ids))
            cur.execute(
                f"""
                SELECT log_actor, log_type, MAX(log_timestamp)
                FROM logging
                WHERE log_actor IN ({placeholders}) AND log_type IN ({", ".join(["%s"] * len(LOG_TYPES))})
                GROUP BY log_actor, log_type
                """,
                (*actor_ids, *LOG_TYPES),
            )
            latest = {}
            for actor_id, log_type, ts in cur.fetchall():
                # log_type comes back as bytes (varbinary); decode it before
                # using it as a dict key, or it won't match the plain-str
                # LOG_TYPES keys looked up below.
                latest.setdefault(actor_id, {})[db.decode(log_type)] = db.decode(ts)

    results = [
        (name, {log_type: latest.get(actor_id, {}).get(log_type) for log_type in LOG_TYPES})
        for actor_id, name in stewards
    ]
    results.sort(key=lambda row: row[0])
    return results
