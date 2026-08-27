import re

import pytest

from app import create_app


@pytest.fixture
def app():
    return create_app("testing")


@pytest.fixture
def client(app):
    return app.test_client()


def test_home_lists_all_ten_tools(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    for path in (
        "/user-rights", "/recent-logs", "/available-rights", "/last-revision",
        "/rights-changes", "/rights-log-search", "/rights-statistics",
        "/steward-activity", "/sysop-inactivity", "/checkusers",
    ):
        assert path in body


def test_user_rights_blank_form_does_not_touch_db(client):
    resp = client.get("/user-rights")
    assert resp.status_code == 200
    assert "Username" in resp.get_data(as_text=True)


def test_recent_logs_blank_form_does_not_touch_db(client):
    resp = client.get("/recent-logs")
    assert resp.status_code == 200


def test_rights_log_search_blank_form_does_not_touch_db(client):
    resp = client.get("/rights-log-search")
    assert resp.status_code == 200


@pytest.mark.parametrize(
    "old,new",
    [
        ("/cgi-bin/userrights", "/user-rights"),
        ("/cgi-bin/recentlogs", "/recent-logs"),
        ("/cgi-bin/availrights", "/available-rights"),
        ("/cgi-bin/lastrevision", "/last-revision"),
        ("/cgi-bin/rightschanges", "/rights-changes"),
        ("/cgi-bin/rightslogsearch", "/rights-log-search"),
        ("/cgi-bin/rightsstats", "/rights-statistics"),
        ("/cgi-bin/stewctivity", "/steward-activity"),
        ("/cgi-bin/sysopinactivity", "/sysop-inactivity"),
        ("/cgi-bin/checkusers", "/checkusers"),
    ],
)
def test_cgi_bin_redirects_to_new_route(client, old, new):
    resp = client.get(old + "?foo=bar", follow_redirects=False)
    assert resp.status_code == 301
    assert resp.headers["Location"].endswith(new + "?foo=bar")


def test_cgi_bin_unknown_tool_404s(client):
    resp = client.get("/cgi-bin/checkuser")
    assert resp.status_code == 404


def test_steward_activity_header_matches_data_row_column_count(app):
    """Regression test: the header row was missing a leading <th> for the
    username column every data row has, so headers were off-by-one against
    the data underneath them."""
    with app.test_request_context():
        from flask import render_template

        results = [("SomeSteward", {"rights": None, "gblrights": None, "globalauth": None, "gblblock": None})]
        html = render_template("steward_activity.html", results=results)
    header_cells = re.search(r"<thead>(.*?)</thead>", html, re.DOTALL).group(1).count("<th")
    data_cells = re.search(r"<tbody>(.*?)</tbody>", html, re.DOTALL).group(1).count("<td")
    assert header_cells == data_cells == 5
