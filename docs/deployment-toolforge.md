# GitHub → GitLab → Toolforge deployment runbook

rightstool deploys to Wikimedia Toolforge via **Build Service** (a git push,
mirrored to GitLab, triggers an automatic container build) -- the same
pipeline `wikiwhiz`/`duga`/`srwiki` use, replacing the tool's previous
`php5.6` webservice type. That misconfiguration (a Python CGI tool running
under a PHP webservice) is the entire reason every page here was broken --
see `README.md`.

This app needs the webservice's **NFS mount kept on** (`--mount=all`, not
`--mount=none`): every tool reads
`/data/project/rightstool/replica.my.cnf` for wikireplica credentials at
request time. There's nothing else on NFS this app needs -- no ToolsDB, no
other files to serve live.

The rightstool Toolforge tool already exists (this is a rewrite, not a new
tool), so skip `toolforge tools create`.

## One-time setup

1. **Create the GitLab repo** at
   `gitlab.wikimedia.org/toolforge-repos/rightstool` (via the Toolforge tool
   dashboard, which provisions this automatically) and add it as a remote.

## The `deploy` branch

This app has no separate frontend build step (server-rendered Flask/Jinja
only), so `.gitlab-ci.yml` just fast-forwards `main` onto `deploy` on every
push -- that branch is what Toolforge actually builds from. To do this
manually instead of relying on CI:
```
git checkout -B deploy
git push origin deploy -f
```

## Deploying / redeploying

```
become rightstool

# build & start (first time)
toolforge build start https://gitlab.wikimedia.org/toolforge-repos/rightstool --ref deploy
toolforge build show   # wait for "ok (Succeeded)"
toolforge webservice buildservice start --mount=all

# stop the old php5.6 webservice first if it's still running
toolforge webservice php5.6 stop
```

Redeploy after a code change: push `main`, let CI (or the manual steps
above) update `deploy`, then re-run `toolforge build start` +
`toolforge webservice buildservice restart`.

## Verify

- `https://rightstool.toolforge.org/` loads the tool list.
- Every one of the ten tools returns real HTML, not raw Python source (the
  original symptom). `/user-rights?user=<a real username>` and
  `/checkusers` are good quick checks.
- `/cgi-bin/<name>` (all ten old names) 301-redirects to the new route.
- The all-wikis tools (`/available-rights`, `/last-revision`,
  `/rights-statistics`, `/checkusers`, `/user-rights?user=...`,
  `/recent-logs?user=...`) each finish loading within well under a minute
  (confirmed live at ~13s for a full ~1,000-wiki sweep on one such tool) --
  if a page hangs far longer than that, check that `--mount=all` was
  actually passed to `webservice buildservice start`; without it,
  `replica.my.cnf` isn't readable and every per-wiki query fails silently
  (each wiki is skipped, not a page-level error) until the timeout in
  `app/db.py` trips for every single wiki in sequence.
