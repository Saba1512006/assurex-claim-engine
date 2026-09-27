"""Notifications page: the account menu's "Notifications" opens it (not the profile), it lists only the signed-in
person's notifications, unread by default, and marking read works from it."""
from database.db import db
from src.models.entities import Notification
from tests.conftest import login, make_user


def _note(user, title, read=False, claim=None):
    n = Notification(user_id=user.id, notification_type="status_change", title=title, message=f"{title} message",
                     related_claim_id=claim, is_read=read)
    db.session.add(n)
    db.session.commit()
    return n


def test_menu_link_opens_the_notifications_page(app, client):
    make_user("a@x.io")
    login(client, "a@x.io")
    html = client.get("/claims/").get_data(as_text=True)
    assert 'href="/claims/notifications"' in html
    assert "/profile#notifications" not in html
    r = client.get("/claims/notifications")
    assert r.status_code == 200 and b"<h1>Notifications</h1>" in r.data


def test_lists_only_own_notifications_unread_first(app, client):
    me, other = make_user("me@x.io"), make_user("other@x.io")
    _note(me, "Fresh update")
    _note(me, "Old update", read=True)
    _note(other, "Someone else's update")
    login(client, "me@x.io")
    unread = client.get("/claims/notifications").get_data(as_text=True)
    assert "Fresh update" in unread and "Old update" not in unread and "Someone else" not in unread
    everything = client.get("/claims/notifications?show=all").get_data(as_text=True)
    assert "Fresh update" in everything and "Old update" in everything and "Someone else" not in everything


def test_mark_read_from_the_page(app, client):
    me = make_user("me@x.io")
    n = _note(me, "Needs a look")
    login(client, "me@x.io")
    r = client.post(f"/claims/notifications/{n.notification_id}/read", headers={"Referer": "/claims/notifications"})
    assert r.status_code == 302
    assert db.session.get(Notification, n.id).is_read
    assert "Needs a look" not in client.get("/claims/notifications").get_data(as_text=True)
