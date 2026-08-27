from .. import db


def changes_by_user(metawiki_db_host: str):
    """(username, count) for every meta-wiki user who has performed at
    least one 'rights' log action, ordered by username.

    Original joined `logging` to `user` via `log_user=user_id`; `log_user`
    no longer exists (confirmed live) -- log actions are attributed via
    `log_actor` -> `actor.actor_id` now.
    """
    with db.connect(metawiki_db_host, db="metawiki_p") as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT actor_name AS username, COUNT(*) AS number
                FROM logging JOIN actor ON log_actor = actor_id
                WHERE log_type = 'rights'
                GROUP BY username ORDER BY username
                """
            )
            return [db.decode_row(row) for row in cur.fetchall()]
