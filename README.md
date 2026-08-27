# rightstool

Filip's cross-wiki user-rights tools for the broader Wikimedia community,
rebuilt as a Flask app for Toolforge Build Service. There is nothing else in
this Toolforge tool besides the ten pages listed below.

## Why this rewrite happened

Every one of the original ten tools was completely broken -- not "some
pages," all of them. The Toolforge webservice type had drifted to `php5.6`
(confirmed via `service.manifest`/`webservice status`), so PHP was trying to
serve `.py` CGI scripts as static files: every page just returned raw
Python source as `text/html` instead of running it.

Porting off the CGI scripts to Python 3/Flask surfaced several more bugs
that were real even before the webservice broke, found by comparing the
recovered source against the *current* wikireplica schema (confirmed live,
via `DESCRIBE` on the actual tables):

- `logging.log_user` and `revision.rev_user` don't exist anymore -- actions
  are attributed via `log_actor`/`rev_actor` -> `actor.actor_id` now. This
  affected **recent-logs, rights-changes, rights-log-search,
  steward-activity, and sysop-inactivity**.
- `logging.log_comment` doesn't exist anymore either -- comments live in a
  separate `comment` table referenced by `log_comment_id`. Affected
  **recent-logs** and **rights-log-search**.
- Every `*.labsdb` wikireplica hostname (`metawiki.labsdb`, and the
  `meta_p.wiki.slice` column every tool used to pick a host) is retired;
  every wiki is reachable directly at
  `<dbname>.analytics.db.svc.wikimedia.cloud` now (confirmed straight from
  the Toolforge `sql` CLI's own source, which special-cases `meta_p` itself
  onto a fixed shard, `s7.<cluster>.db.svc.wikimedia.cloud` -- see
  `app/config.py`).
- **rights-log-search**'s "search titles only" branch built a malformed SQL
  string (`'%%%s%%%'`) that would have errored if it had ever run.
- **recent-logs** had a dead-code bug independent of all of the above: it
  unconditionally reset its own `results` variable to empty right before
  checking whether it was empty, so it never rendered a single row, even
  back when the CGI itself worked.
- The client-side table sorting (`sortable` class) hot-linked
  `http://www.kryogenix.org/.../sorttable.js` over plain HTTP from an HTTPS
  page -- blocked as mixed content by every modern browser, and that URL now
  404s outright regardless. Replaced with a small local `static/sortable.js`.

## Tools

`/user-rights`, `/recent-logs`, `/available-rights`, `/last-revision`,
`/rights-changes`, `/rights-log-search`, `/rights-statistics`,
`/steward-activity`, `/sysop-inactivity`, `/checkusers` -- see each one's
docstring in `app/tools/` for what it does and, where relevant, exactly what
was fixed. Old `/cgi-bin/<name>` URLs still work as 301 redirects.

Several of these (`available-rights`, `last-revision`, `rights-statistics`,
`checkusers`, `user-rights`, `recent-logs`) loop over all ~1,000 Wikimedia
wikis -- expect those pages to take some seconds to load (confirmed live:
~13s for a full sweep with per-connection `connect`/`read`/`write` timeouts
in place; without those timeouts, one slow replica can stall the whole loop
indefinitely, which is why `app/db.py` sets all three).

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
```

Every tool here is a read-only wikireplica query -- no database of this
app's own. Point `REPLICA_MY_CNF` at a `replica.my.cnf`-formatted file with
real Toolforge wikireplica credentials to exercise them locally; without
one, only the blank-form pages work.

```bash
make test    # or: pytest tests -v
flask --app wsgi run
```

## Deployment

See `docs/deployment-toolforge.md`.

## Licence

MIT, see `LICENSE`.
