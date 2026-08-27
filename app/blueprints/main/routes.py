from flask import Blueprint, current_app, redirect, render_template, request, url_for

from ...tools import available_rights, checkusers, last_revision, recent_logs
from ...tools import rights_changes, rights_log_search, rights_statistics
from ...tools import steward_activity, sysop_inactivity, user_rights
from ...wikis import list_wikis, wiki_db_host

main_bp = Blueprint("main", __name__)


def _capitalize(value: str) -> str:
    return value[0].upper() + value[1:] if len(value) > 1 else value


@main_bp.get("/")
def home():
    return render_template("index.html")


@main_bp.get("/user-rights")
def user_rights_route():
    user = _capitalize(request.args.get("user", ""))
    steward = request.args.get("steward", "").lower() == "true"
    results = []
    if user:
        results = user_rights.rights_by_wiki(user, current_app.config["META_DB_HOST"])
    return render_template("user_rights.html", user=user, steward=steward, results=results)


@main_bp.get("/recent-logs")
def recent_logs_route():
    user = _capitalize(request.args.get("user", ""))
    hide_patrol = request.args.get("patrol", "").lower() == "false"
    hide_newusers = request.args.get("newusers", "").lower() == "false"
    results = []
    if user:
        results = recent_logs.logs_by_wiki(
            user, hide_patrol, hide_newusers, current_app.config["META_DB_HOST"]
        )
    total_count = sum(count for _dbname, _url, count, _rows in results)
    return render_template(
        "recent_logs.html",
        user=user,
        hide_patrol=hide_patrol,
        hide_newusers=hide_newusers,
        results=results,
        total_count=total_count,
    )


@main_bp.get("/available-rights")
def available_rights_route():
    results = available_rights.non_default_rights_by_wiki(current_app.config["META_DB_HOST"])
    return render_template("available_rights.html", results=results)


@main_bp.get("/last-revision")
def last_revision_route():
    results = last_revision.last_revision_by_wiki(current_app.config["META_DB_HOST"])
    return render_template("last_revision.html", results=results)


@main_bp.get("/rights-changes")
def rights_changes_route():
    results = rights_changes.changes_by_user(wiki_db_host("metawiki"))
    return render_template("rights_changes.html", results=results)


@main_bp.get("/rights-log-search")
def rights_log_search_route():
    user = request.args.get("user", "")
    search_users = request.args.get("who") is None
    search_titles = request.args.get("whom") is None
    results = []
    if user and (search_users or search_titles):
        results = rights_log_search.search(user, search_users, search_titles, wiki_db_host("metawiki"))
    return render_template(
        "rights_log_search.html",
        user=user,
        search_users=search_users,
        search_titles=search_titles,
        results=results,
    )


@main_bp.get("/rights-statistics")
def rights_statistics_route():
    data = rights_statistics.user_counts_by_right(current_app.config["META_DB_HOST"])
    return render_template("rights_statistics.html", data=data)


@main_bp.get("/steward-activity")
def steward_activity_route():
    results = steward_activity.steward_activity(wiki_db_host("metawiki"))
    return render_template("steward_activity.html", results=results)


@main_bp.get("/sysop-inactivity")
def sysop_inactivity_route():
    # Unlike every other tool here, even the bare form needs a DB round
    # trip -- the wiki <select> is populated from meta_p.wiki, same as the
    # original.
    wiki = request.args.get("wiki", "")
    timestamp = request.args.get("timestamp", "")
    wikis = list_wikis(current_app.config["META_DB_HOST"])
    all_wikis = [dbname for dbname, _url in wikis]

    results = []
    site = ""
    if wiki and wiki in all_wikis:
        site = dict(wikis).get(wiki, "").replace("http://", "https://")
        results = sysop_inactivity.inactive_sysops(wiki, timestamp or None)

    return render_template(
        "sysop_inactivity.html",
        wiki=wiki,
        timestamp=timestamp,
        all_wikis=all_wikis,
        site=site,
        results=results,
    )


@main_bp.get("/checkusers")
def checkusers_route():
    results = checkusers.checkusers_by_wiki(current_app.config["META_DB_HOST"])
    return render_template("checkusers.html", results=results)


# --- Old /cgi-bin/<name> URLs: redirect to the new routes, keep the query --

_CGI_BIN_REDIRECTS = {
    "userrights": "main.user_rights_route",
    "recentlogs": "main.recent_logs_route",
    "availrights": "main.available_rights_route",
    "lastrevision": "main.last_revision_route",
    "rightschanges": "main.rights_changes_route",
    "rightslogsearch": "main.rights_log_search_route",
    "rightsstats": "main.rights_statistics_route",
    "stewctivity": "main.steward_activity_route",
    "sysopinactivity": "main.sysop_inactivity_route",
    "checkusers": "main.checkusers_route",
}


@main_bp.get("/cgi-bin/<name>")
def cgi_bin_redirect(name):
    endpoint = _CGI_BIN_REDIRECTS.get(name)
    if endpoint is None:
        return render_template("404.html"), 404
    target = url_for(endpoint)
    query = request.query_string.decode("utf-8")
    if query:
        target = f"{target}?{query}"
    return redirect(target, code=301)
