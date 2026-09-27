"""Field rules: names of people, places and organisations take no digits; phone numbers take no letters.

The browser filters keystrokes, but these are the checks that hold when a request skips the page."""
from __future__ import annotations

import pytest

from src.models.entities import ServiceCenter, User
from src.rules.validator import person_name_problem, phone_problem, product_form, words_problem
from tests.conftest import login, make_center, make_user


@pytest.mark.parametrize("name", ["Areeba Khan", "Muhammad Ali Jr.", "O'Brien", "Anne-Marie Lee", "José Núñez", "عائشہ خان"])
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
