"""Getting from a dashboard to the public website and back without signing out."""
from tests.conftest import login, make_user


def test_signed_in_person_can_open_the_website_and_stays_signed_in(app, client):
    make_user("a@x.io")
    login(client, "a@x.io")
    r = client.get("/")
    assert r.status_code == 200                                   # the landing page no longer bounces to the dashboard
    html = r.get_data(as_text=True)
    assert "Go to my dashboard" in html and "Sign in as evaluator" not in html
    assert client.get("/claims/").status_code == 200              # still signed in afterwards


def test_logo_and_account_menu_link_to_the_website(app, client):
    make_user("a@x.io")
    login(client, "a@x.io")
    html = client.get("/claims/").get_data(as_text=True)
    assert 'class="brand" href="/"' in html
    for href in ('href="/home"', 'href="/model-card"', 'href="/blog"'):
        assert href in html


def test_signed_out_landing_still_offers_sign_in(app, client):
    html = client.get("/").get_data(as_text=True)
    assert "Sign in as evaluator" in html and "Go to my dashboard" not in html
