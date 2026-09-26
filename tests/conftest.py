"""Shared fixtures: an isolated app (in-memory DB, temp upload dir), factories and model stubs."""
from __future__ import annotations

import io
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config.config import TestConfig  # noqa: E402
from database.db import db  # noqa: E402
from src.app import create_app  # noqa: E402
from src.core import gtm_classifier_v2  # noqa: E402
from src.core.vocab import coverage_days  # noqa: E402
from src.models.entities import (Claim, ClaimStatusHistory, Product, ProductWarranty, RepairHistory,  # noqa: E402
                                 ServiceCenter, User)

PASSWORD = "Passw0rd!xyz"


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(TestConfig, "UPLOAD_DIR", tmp_path / "uploads")
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


# ------------------------------------------------------------------ factories
def make_user(email, role="customer", center=None, **kw):
    u = User(email=email, full_name=kw.pop("full_name", email.split("@")[0].title()), role=role,
             service_center_id=center.id if center else None, **kw)
    u.set_password(PASSWORD)
    db.session.add(u)
    db.session.commit()
    return u


def make_center(name="Metro Center", city="Lahore"):
    c = ServiceCenter(name=name, city=city)
    db.session.add(c)
    db.session.commit()
    return c


def make_product(owner, *, category="Consumer Electronics", days_ago=200, months=24, serial="SN-TST-1000001",
                 invoice="INV-2025-11111", center=None, name="Test Laptop", model="TL-1", extended=False):
    purchased = date.today() - timedelta(days=days_ago)
    p = Product(owner=owner, service_center=center, product_name=name, category=category, brand="TestBrand",
                model_number=model, serial_number=serial, purchase_date=purchased, purchase_price=999.0,
                retailer="Test Store", invoice_number=invoice)
    db.session.add(p)
    db.session.add(ProductWarranty(product=p, warranty_provider="TestBrand", start_date=purchased,
                                   expiry_date=purchased + timedelta(days=coverage_days(months)),
                                   duration_months=months, is_extended=extended))
    db.session.commit()
    return p


def make_claim(product, actor=None, *, fault=None, damage="Manufacturing Defect", fault_days_ago=3, conf=0.8,
               status="Draft", description="The device stopped working during normal use at home.", **kw):
    from src.core.vocab import FAULTS
    c = Claim(user_id=product.user_id, created_by_id=(actor or product.owner).id, product=product,
              warranty=product.warranty, service_center_id=product.service_center_id,
              fault_category=fault or FAULTS[product.category][0], damage_type=damage,
              fault_occurrence_date=date.today() - timedelta(days=fault_days_ago), fault_description=description,
              diagnostic_confidence=conf, diagnosis_source="Service-center technician", status=status, **kw)
    db.session.add(c)
    db.session.flush()
    db.session.add(ClaimStatusHistory(claim=c, new_status=status, reason_comment="created"))
    db.session.commit()
    return c


def add_repair(product, *, authorised=True, days_ago=30, serial=None):
    db.session.add(RepairHistory(product=product, repair_date=date.today() - timedelta(days=days_ago),
                                 repair_center="Somewhere", outcome="Repaired", is_authorized_center=authorised,
                                 serial_number_seen=serial))
    db.session.commit()


# ------------------------------------------------------------------ files
def png_bytes(color=(200, 30, 30), size=(64, 64)) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def receipt_pdf(lines) -> bytes:
    from reportlab.lib.pagesizes import A5
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A5)
    y = 540
    for line in lines:
        c.drawString(40, y, line)
        y -= 18
    c.save()
    return buf.getvalue()


def standard_receipt(product, serial=None) -> bytes:
    return receipt_pdf([f"Invoice No: {product.invoice_number}", f"Date: {product.purchase_date:%d/%m/%Y}",
                        f"Product: {product.product_name}", f"Model: {product.model_number}",
                        f"Serial No: {serial or product.serial_number}", "Grand Total: 999.00",
                        f"Retailer: {product.retailer}"])


def upload(data: bytes, name: str):
    from werkzeug.datastructures import FileStorage
    return FileStorage(stream=io.BytesIO(data), filename=name)


def attach_docs(claim, kinds=("receipt", "warranty_card", "serial_photo", "damage_photo")):
    from src.services import documents
    for i, k in enumerate(kinds):
        data = standard_receipt(claim.product) if k == "receipt" else png_bytes((i * 40, 90, 150))
        documents.store(upload(data, f"{k}.{'pdf' if k == 'receipt' else 'png'}"), k, claim=claim,
                        uploader=claim.product.owner)
    db.session.commit()


def login(client, email, password=PASSWORD):
    return client.post("/login", data={"email": email, "password": password})


# ------------------------------------------------------------------ model stubs
class FakeGTM:
    """Stands in for the Teachable Machine export in tests (the real one is trained in the browser)."""
    version = "gtm-testdouble"

    def __init__(self, cls="Valid Claim", conf=0.9):
        self.cls, self.conf = cls, conf

    def predict(self, image):
        rest = (1 - self.conf) / 2
        scores = {c: (self.conf if c == self.cls else rest) for c in ("Valid Claim", "Invalid Claim", "Manual Review")}
        return {"model_type": "stub", "model_version": self.version, "predicted_class": self.cls,
                "top_confidence": self.conf, "confidence_scores": scores}


@pytest.fixture()
def gtm(monkeypatch):
    """Install a controllable fake GTM: gtm.set('Invalid Claim', 0.8)."""
    fake = FakeGTM()

    class Handle:
        def set(self, cls, conf=0.9):
            fake.cls, fake.conf = cls, conf
            return fake

        def mirror_python(self):
            """Make the image model echo the Python model's class and confidence (Strong Match)."""
            from src.core.python_classifier import get_python_classifier
            real = get_python_classifier().predict
            import src.core.pipeline as pl

            def run_py(features):
                r = real(features)
                fake.cls, fake.conf = r["predicted_class"], r["top_confidence"]
                return r, None
            monkeypatch.setattr(pl, "_run_python", run_py)
    monkeypatch.setattr("src.core.pipeline.get_gtm_classifier", lambda: fake)
    monkeypatch.setattr("src.core.offline_eval.get_gtm_classifier", lambda: fake)
    return Handle()


@pytest.fixture(autouse=True)
def _no_real_gtm(monkeypatch):
    """Tests never depend on a Teachable Machine file being present on the machine running them."""
    def unavailable():
        raise gtm_classifier_v2.GTMUnavailable("not installed (test)")
    monkeypatch.setattr("src.core.pipeline.get_gtm_classifier", unavailable)
