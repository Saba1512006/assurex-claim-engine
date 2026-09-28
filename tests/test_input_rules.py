"""Field rules: names of people, places and organisations take no digits; phone numbers take no letters; emails
are well formed; a paused sign-in says how long it lasts.

The browser filters keystrokes, but these are the checks that hold when a request skips the page."""
from __future__ import annotations

import pytest

from src.models.entities import ServiceCenter, User
from src.rules.validator import email_problem, person_name_problem, phone_problem, product_form, words_problem
from tests.conftest import login, make_center, make_user


@pytest.mark.parametrize("name", ["Areeba Khan", "Muhammad Ali Jr.", "O'Brien", "Anne-Marie Lee", "José Núñez", "Zoë Brontë"])
def test_real_names_pass(name):
    assert person_name_problem(name) is None


@pytest.mark.parametrize("name", ["Areeba123", "Ali 2", "12345", "Ali_Khan", "Ali@Khan", "A", "-Ali", "x" * 101])
def test_names_with_digits_symbols_or_bad_length_fail(name):
    assert person_name_problem(name)


@pytest.mark.parametrize("value", ["", "Karachi", "Metro Fix & Care (Pvt.) Ltd", "Saddar/Clifton", "Hi-Tech"])
def test_word_fields_accept_letters_and_punctuation(value):
    assert words_problem(value, "City") is None


@pytest.mark.parametrize("value", ["Karachi 75", "Store 1", "4U Mobiles", "Shop#", "-Store"])
def test_word_fields_refuse_digits_and_symbols(value):
    assert words_problem(value, "City")


@pytest.mark.parametrize("phone", ["", "+92 300 1234567", "0300-1234567", "(042) 3576 1234"])
def test_phones_pass(phone):
    assert phone_problem(phone) is None


@pytest.mark.parametrize("phone", ["0300-12ab567", "call me", "+92 300 1234567 ext", "123", "1" * 16])
def test_phones_with_letters_or_wrong_length_fail(phone):
    assert phone_problem(phone)


def test_product_form_refuses_digits_in_brand_retailer_and_provider():
    form = {"product_name": "Galaxy S23", "brand": "Sams2ng", "model_number": "SM-S911", "serial_number": "SN-12345",
            "retailer": "Store 9", "warranty_provider": "Care 24", "category": "Consumer Electronics",
            "purchase_date": "2025-01-10", "purchase_price": "999", "warranty_months": "12"}
    _, errors, _ = product_form(form)
    joined = " ".join(errors)
    assert "Brand" in joined and "Retailer" in joined and "Warranty provider" in joined
    assert not any("Product name" in e or "Model number" in e for e in errors)   # codes and product names mix digits


def test_register_rejects_a_name_with_digits(client):
    r = client.post("/register", data={"full_name": "Areeba 123", "email": "a@x.io", "password": "Passw0rd!xyz",
                                       "confirm_password": "Passw0rd!xyz", "phone": "0300-12ab567"})
    body = r.get_data(as_text=True)
    assert r.status_code == 400 and "no numbers" in body and "no letters" in body
    assert User.query.filter_by(email="a@x.io").first() is None


def test_profile_keeps_old_name_when_new_one_has_digits(client):
    u = make_user("p@x.io", full_name="Pat Lee")
    login(client, "p@x.io")
    client.post("/profile", data={"action": "details", "full_name": "Pat 007", "phone": ""})
    assert User.query.get(u.id).full_name == "Pat Lee"


def test_invite_and_service_center_refuse_digits(client):
    make_user("ad@x.io", "administrator")
    make_center()
    login(client, "ad@x.io")
    client.post("/admin/access/invite", data={"full_name": "Staff 2", "email": "s2@x.io", "role": "customer"})
    assert User.query.filter_by(email="s2@x.io").first() is None
    client.post("/admin/access/service-centers", data={"name": "Fix Hub", "city": "Lahore 54000", "phone": ""})
    client.post("/admin/access/service-centers", data={"name": "Care Point", "city": "Lahore", "phone": "04x-123"})
    assert ServiceCenter.query.filter(ServiceCenter.name.in_(["Fix Hub", "Care Point"])).count() == 0
    client.post("/admin/access/service-centers", data={"name": "Care Point", "city": "Lahore", "phone": "042 3576 1234"})
    assert ServiceCenter.query.filter_by(name="Care Point").count() == 1


# ------------------------------------------------------------------ email and sign-in pauses
@pytest.mark.parametrize("email", ["name@example.com", "a.b+tag@mail.co.uk", "x_y-z@sub.domain.pk", "USER@EXAMPLE.ORG"])
def test_good_emails_pass(email):
    assert email_problem(email) is None


@pytest.mark.parametrize("email", ["", "plain", "a@b", "a@b.c", "a b@x.io", "a@@x.io", "a@x..io", ".a@x.io", "a.@x.io",
                                   "a..b@x.io", "a@-x.io", "a@x-.io", "a@x.io.", "a@x.1o", "a,b@x.io", "a@x.io;b@y.io",
                                   "a" * 65 + "@x.io", "a@" + "b" * 120 + ".io"])
def test_bad_emails_fail(email):
    assert email_problem(email)


def test_login_with_a_malformed_email_is_refused_without_counting(client):
    r = client.post("/login", data={"email": "abc@x", "password": "whatever"})
    assert r.status_code == 400 and b"valid email address" in r.data


def test_lockout_lasts_a_minute_and_the_page_counts_down(app, client):
    from database.db import db
    u = make_user("t@x.io")
    for _ in range(5):
        r = client.post("/login", data={"email": "t@x.io", "password": "wrong"})
    body = r.get_data(as_text=True)
    assert r.status_code == 401 and "data-retry=" in body and "data-retry-lock" in body
    assert "pause the account for 1 minute" in body
    left = db.session.get(User, u.id).lock_seconds_left
    assert 55 <= left <= 60


def test_rate_limit_page_shows_a_countdown(tmp_path, monkeypatch):
    from config.config import TestConfig
    from database.db import db
    from src.app import create_app

    class Limited(TestConfig):
        RATELIMIT_ENABLED = True
    monkeypatch.setattr(Limited, "UPLOAD_DIR", tmp_path / "uploads")
    app = create_app(Limited)
    with app.app_context():
        db.create_all()
        c = app.test_client()
        codes = [c.post("/login", data={"email": f"n{i}@x.io", "password": "x"}).status_code for i in range(11)]
        assert codes[:10] == [401] * 10 and codes[10] == 429
        r = c.post("/login", data={"email": "n@x.io", "password": "x"})
        assert r.status_code == 429 and b"data-retry=" in r.data
        db.session.remove()
        db.drop_all()
