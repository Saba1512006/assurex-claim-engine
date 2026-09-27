"""Create the database and demo data.

    python database/seed.py            # drop + recreate everything (asks nothing - demo data only)
    python database/seed.py --if-empty # only seed when there are no users (used by render.yaml)

Every demo claim is submitted through the real pipeline (rules, Python model,
Claim Summary Card, Teachable Machine when installed, decision table), so the
outcomes you see are computed, not written here. Receipts are generated as
text PDFs so the OCR step genuinely reads them. All people, products and
documents are fictitious.
"""
from __future__ import annotations

import argparse
import io
import os
import secrets
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def ensure_secret_key() -> None:
    """Write a random SECRET_KEY to .env on first run so `python src/app.py` works out of the box."""
    if os.environ.get("SECRET_KEY"):
        return
    env = ROOT / ".env"
    lines = env.read_text().splitlines() if env.exists() else []
    if not any(line.startswith("SECRET_KEY=") for line in lines):
        lines.append(f"SECRET_KEY={secrets.token_hex(32)}")
        env.write_text("\n".join(lines) + "\n")
        print("-> wrote a random SECRET_KEY to .env")
    for line in lines:
        if line.startswith("SECRET_KEY="):
            os.environ["SECRET_KEY"] = line.split("=", 1)[1]


ensure_secret_key()

from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from reportlab.lib.pagesizes import A5  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402
from werkzeug.datastructures import FileStorage  # noqa: E402

from config.config import Config  # noqa: E402
from database.db import db  # noqa: E402
from src.app import create_app  # noqa: E402
from src.core.vocab import coverage_days  # noqa: E402
from src.models.entities import (Claim, ClaimStatusHistory, Product, ProductWarranty, RepairHistory,  # noqa: E402
                                 ServiceCenter, User, WarrantyPolicy)
from src.rules.policy_store import get_policy  # noqa: E402
from src.services import claim_service, documents  # noqa: E402

TODAY = date.today()
FONT = ROOT / "static" / "fonts" / "DejaVuSans.ttf"

USERS = [
    ("admin@assurex.local", "AdminPass123!", "Areeba Khan", Config.ROLE_ADMIN, None),
    ("reviewer@assurex.local", "ReviewerPass123!", "Bilal Ahmed", Config.ROLE_REVIEWER, None),
    ("reviewer2@assurex.local", "ReviewerPass123!", "Nadia Qureshi", Config.ROLE_REVIEWER, None),
    ("staff@assurex.local", "StaffPass123!", "Sana Malik", Config.ROLE_STAFF, 0),
    ("customer@assurex.local", "CustomerPass123!", "Usman Tariq", Config.ROLE_CUSTOMER, None),
    ("hira@example.com", "CustomerPass123!", "Hira Siddiqui", Config.ROLE_CUSTOMER, None),
    ("kamran@example.com", "CustomerPass123!", "Kamran Ali", Config.ROLE_CUSTOMER, None),
]
CENTERS = [("Metro Authorised Service Center", "Lahore", "+92 42 3555 0100"),
           ("Harbor Tech Repairs", "Karachi", "+92 21 3555 0200")]


# ------------------------------------------------------------------ synthetic evidence files
def receipt_pdf(*, invoice, purchased, product, model, serial, retailer, amount, months) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A5)
    y = 540
    for line in (retailer.upper(), "TAX INVOICE", "", f"Invoice No: {invoice}", f"Date: {purchased:%d/%m/%Y}",
                 f"Product: {product}", f"Model: {model}", f"Serial No: {serial}", f"Warranty: {months} months",
                 f"Grand Total: {amount:,.2f}", f"Retailer: {retailer}", "", "Thank you for your purchase."):
        c.setFont("Helvetica-Bold" if y == 540 else "Helvetica", 11)
        c.drawString(40, y, line)
        y -= 20
    c.save()
    return buf.getvalue()


def photo_png(title: str, subtitle: str, tone=(71, 85, 105)) -> bytes:
    img = Image.new("RGB", (640, 420), (241, 245, 249))
    g = ImageDraw.Draw(img)
    g.rounded_rectangle([40, 40, 600, 380], radius=24, fill=(226, 232, 240), outline=tone, width=4)
    big, small = ImageFont.truetype(str(FONT), 30), ImageFont.truetype(str(FONT), 16)
    g.text((70, 150), title, font=big, fill=tone)
    g.text((70, 200), subtitle, font=small, fill=(100, 116, 139))
    g.text((70, 330), "Synthetic demo image", font=small, fill=(148, 163, 184))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def as_upload(data: bytes, name: str) -> FileStorage:
    return FileStorage(stream=io.BytesIO(data), filename=name)


# ------------------------------------------------------------------ builders
def make_product(owner, *, name, category, brand, model, serial, days_ago, price, retailer, months,
                 center=None, extended=False, invoice=None, receipt_serial=None, receipt=True):
    purchased = TODAY - timedelta(days=days_ago)
    p = Product(owner=owner, service_center=center, product_name=name, category=category, brand=brand,
                model_number=model, serial_number=serial, purchase_date=purchased, purchase_price=price,
                retailer=retailer, invoice_number=invoice)
    db.session.add(p)
    pol = get_policy(category)
    row = WarrantyPolicy.query.filter_by(category=category).first() or WarrantyPolicy(
        category=category, policy_name=pol["policy_name"], coverage_duration_months=pol["coverage_duration_months"],
        grace_period_days=pol["grace_period_days"], claim_reporting_period_days=pol["claim_reporting_period_days"])
    db.session.add(row)
    db.session.add(ProductWarranty(
        product=p, policy=row, warranty_provider=f"{brand} manufacturer warranty", start_date=purchased,
        expiry_date=purchased + timedelta(days=coverage_days(months)), duration_months=months, is_extended=extended,
        extended_months=12 if extended else 0, coverage_conditions=f"Covered faults: {', '.join(pol['covered_faults'])}.",
        exclusions="; ".join(pol["exclusions"]), service_center_name=center.name if center else None))
    db.session.flush()
    if receipt and invoice:
        pdf = receipt_pdf(invoice=invoice, purchased=purchased, product=name, model=model,
                          serial=receipt_serial or serial, retailer=retailer, amount=price, months=months)
        documents.store(as_upload(pdf, f"receipt_{invoice}.pdf"), "receipt", product=p, uploader=owner)
    return p


def attach(claim, kind, uploader, label=None):
    data = photo_png({"damage_photo": "Damage photo", "serial_photo": f"S/N {claim.product.serial_number}",
                      "warranty_card": "Warranty card", "product_photo": "Product photo"}[kind],
                     label or f"{claim.product.brand} {claim.product.product_name}")
    documents.store(as_upload(data, f"{kind}.png"), kind, claim=claim, uploader=uploader)


def make_claim(product, actor, *, fault, damage, days_ago_fault, description, conf=None, docs=("warranty_card",
               "damage_photo", "serial_photo"), submit=True, replacement=None, submitted_days_ago=0):
    claim = Claim(user_id=product.user_id, created_by_id=actor.id, product=product, warranty=product.warranty,
                  service_center_id=product.service_center_id, fault_category=fault, damage_type=damage,
                  fault_occurrence_date=TODAY - timedelta(days=days_ago_fault), fault_description=description,
                  diagnostic_confidence=0.5 if conf is None else conf,
                  diagnosis_source="Not assessed" if conf is None else "Service-center technician",
                  previous_replacement_details=replacement)
    db.session.add(claim)
    db.session.flush()
    db.session.add(ClaimStatusHistory(claim=claim, new_status="Draft", changed_by_user_id=actor.id,
                                      reason_comment="Claim created"))
    for kind in docs:
        attach(claim, kind, actor)
    db.session.flush()
    if submit:
        claim.claim_submission_date = TODAY - timedelta(days=submitted_days_ago)
        claim_service.submit(claim, actor)
    db.session.flush()
    return claim


def seed(reset: bool = True) -> None:
    app = create_app()
    with app.app_context():
        if not reset and User.query.first():
            print("-> database already has users; nothing to do (--if-empty)")
            return
        db.drop_all()
        db.create_all()
        up = Path(app.config["UPLOAD_DIR"])
        for sub in ("docs", "cards"):
            for f in (up / sub).glob("*"):
                f.unlink()

        centers = [ServiceCenter(name=n, city=c, phone=ph) for n, c, ph in CENTERS]
        db.session.add_all(centers)
        db.session.flush()
        users = {}
        for email, pw, name, role, center in USERS:
            u = User(email=email, full_name=name, role=role, phone_number="+92 300 5550" + str(len(users)).zfill(3),
                     service_center_id=centers[center].id if center is not None else None)
            u.set_password(pw)
            db.session.add(u)
            users[email] = u
        db.session.flush()
        usman, hira, kamran = users["customer@assurex.local"], users["hira@example.com"], users["kamran@example.com"]
        staff, reviewer = users["staff@assurex.local"], users["reviewer@assurex.local"]
        metro = centers[0]

        # 1 valid: covered manufacturing defect, complete evidence, technician-confirmed
        laptop = make_product(usman, name="ApexBook Pro 16", category="Consumer Electronics", brand="ApexTech",
                              model="ABP-16", serial="SN-APX-4471823", days_ago=210, price=1899.0,
                              retailer="City Electronics Mall", months=24, center=metro, invoice="INV-2025-48213")
        make_claim(laptop, staff, fault="Motherboard failure", damage="Manufacturing Defect", days_ago_fault=4, conf=0.86,
                   description="Laptop shuts down within minutes of starting; the technician traced it to the motherboard.")
        # 2 invalid: excluded damage confirmed by diagnosis
        fridge = make_product(usman, name="FrostGuard 450L", category="Home Appliances", brand="FrostGuard",
                              model="FG-450", serial="SN-FRO-2209381", days_ago=400, price=1250.0,
                              retailer="National Appliance Depot", months=24, center=metro, invoice="INV-2025-11872")
        make_claim(fridge, staff, fault="PCB failure", damage="Water Ingress", days_ago_fault=6, conf=0.81,
                   description="Control board corroded after water from a burst pipe entered the rear panel.")
        # 3 manual review: cause unknown and diagnosis inconclusive
        saw = make_product(usman, name="VoltEdge Saw 18V", category="Industrial Tools", brand="VoltEdge",
                           model="VE-18S", serial="SN-VOL-7781204", days_ago=300, price=420.0,
                           retailer="Metro Hardware Centre", months=24, invoice="INV-2025-50931")
        make_claim(saw, usman, fault="Trigger switch failure", damage="Unknown / Not Sure", days_ago_fault=5, conf=0.3,
                   description="Trigger stopped responding intermittently; no obvious cause, the saw was stored indoors.")
        # 4 expired warranty
        phone = make_product(usman, name="NovaPhone 12", category="Consumer Electronics", brand="NovaSound",
                             model="NP-12", serial="SN-NOV-5520913", days_ago=560, price=699.0,
                             retailer="MegaMart Online", months=12, invoice="INV-2024-77410")
        make_claim(phone, usman, fault="Battery not charging", damage="Manufacturing Defect", days_ago_fault=3,
                   description="Battery no longer charges past 10 percent with the original charger.")
        # 5 missing mandatory document (no receipt anywhere)
        washer = make_product(hira, name="CleanCycle 8kg", category="Home Appliances", brand="CleanCycle",
                              model="CC-8FL", serial="SN-CLE-6612045", days_ago=180, price=780.0,
                              retailer="Brand Flagship Store", months=24, invoice=None, receipt=False)
        make_claim(washer, hira, fault="Drum spin malfunction", damage="Manufacturing Defect", days_ago_fault=2,
                   docs=("damage_photo",), description="Drum does not spin on any programme; motor hums but nothing turns.")
        # 6 duplicate: the laptop's receipt and invoice reused for a second registration
        dup = make_product(kamran, name="ApexBook Pro 16", category="Consumer Electronics", brand="ApexTech",
                           model="ABP-16", serial="SN-APX-4471823", days_ago=210, price=1899.0,
                           retailer="City Electronics Mall", months=24, invoice="INV-2025-48213")
        make_claim(dup, kamran, fault="Motherboard failure", damage="Manufacturing Defect", days_ago_fault=3,
                   description="Laptop shuts down within minutes of starting; the technician traced it to the motherboard.")
        # 7 contradictory: fault dated before purchase
        tv = make_product(hira, name="VividTab 11", category="Consumer Electronics", brand="VividDisplay",
                          model="VT-11", serial="SN-VIV-3390117", days_ago=90, price=540.0,
                          retailer="City Electronics Mall", months=12, invoice="INV-2026-20455")
        make_claim(tv, hira, fault="Touch panel unresponsive", damage="Manufacturing Defect", days_ago_fault=120,
                   description="Touch input stops working in the lower third of the screen.")
        # 8 serial mismatch: receipt shows a different serial than the registered unit
        grinder = make_product(kamran, name="IronForge Grinder 9", category="Industrial Tools", brand="IronForge",
                               model="IF-G9", serial="SN-IRO-1184420", days_ago=250, price=310.0,
                               retailer="Industrial Supply Direct", months=24, invoice="INV-2025-63310",
                               receipt_serial="SN-IRO-9901772")
        make_claim(grinder, kamran, fault="Armature burnout", damage="Mechanical Stress", days_ago_fault=6,
                   description="Burning smell then the grinder stopped; armature windings look scorched.")
        # 9 unauthorised repair recorded by staff
        ac = make_product(usman, name="AeroBreeze 1.5T", category="Home Appliances", brand="AeroBreeze",
                          model="AB-15I", serial="SN-AER-4410297", days_ago=330, price=980.0,
                          retailer="National Appliance Depot", months=24, center=metro, invoice="INV-2025-33018")
        db.session.add(RepairHistory(product=ac, recorded_by_id=staff.id, repair_date=TODAY - timedelta(days=60),
                                     repair_center="Street Fix Workshop", replaced_parts="Capacitor",
                                     outcome="Repaired", repair_cost=35.0, is_authorized_center=False,
                                     notes="Customer had the unit opened at a local shop."))
        make_claim(ac, staff, fault="Compressor failure", damage="Manufacturing Defect", days_ago_fault=5, conf=0.7,
                   description="Compressor starts and trips after a few seconds; no cooling.")
        # 10 tricky boundary date: warranty ended 4 days ago, inside the 7-day grace period
        pods = make_product(hira, name="NovaPods Max", category="Consumer Electronics", brand="NovaSound",
                            model="NPM-2", serial="SN-NOV-8830154", days_ago=coverage_days(12) + 4, price=329.0,
                            retailer="MegaMart Online", months=12, invoice="INV-2025-90126")
        make_claim(pods, hira, fault="Speaker malfunction", damage="Manufacturing Defect", days_ago_fault=6, conf=0.75,
                   description="Left speaker crackles at any volume; started a few days before the warranty end date.")
        # 11 model disagreement: reported 35 days after the fault. Home Appliances allow 45 days, so the claim is
        # covered; the Teachable Machine card shows "Reported in time" and says Valid, while the Python model -
        # which mostly saw 30-day limits - says Invalid. Neither model decides alone: D04 sends it to a reviewer.
        oven = make_product(kamran, name="KitchenPro Oven 45L", category="Home Appliances", brand="KitchenPro",
                            model="KP-45X", serial="SN-KIT-6630195", days_ago=200, price=560.0,
                            retailer="National Appliance Depot", months=24, invoice="INV-2026-41876")
        make_claim(oven, kamran, fault="Thermostat failure", damage="Manufacturing Defect", days_ago_fault=35, conf=0.62,
                   description="Oven overheats and the thermostat no longer cuts out; noticed after a family event "
                               "and reported once the technician had inspected it.")
        # extras: a draft and a reviewed claim
        make_claim(make_product(usman, name="KitchenPro 30L", category="Home Appliances", brand="KitchenPro",
                                model="KP-30C", serial="SN-KIT-2201984", days_ago=120, price=210.0,
                                retailer="MegaMart Online", months=24, invoice="INV-2026-10822"),
                   usman, fault="Thermostat failure", damage="Manufacturing Defect", days_ago_fault=1, submit=False,
                   docs=("damage_photo",), description="Oven does not hold temperature; food burns at low settings.")
        manual = Claim.query.filter_by(product=saw).first()
        claim_service.assign(manual, reviewer, reviewer)
        claim_service.decide(manual, reviewer, "request_info",
                             "Please upload a diagnostic report from an authorised center confirming the cause.", None)
        db.session.commit()
        counts = {s: Claim.query.filter_by(status=s).count() for s in Config.ALL_CLAIM_STATUSES}
        print("-> seeded", User.query.count(), "users,", Product.query.count(), "products,", Claim.query.count(), "claims")
        print("   status mix:", {k: v for k, v in counts.items() if v})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--if-empty", action="store_true", help="seed only when the database has no users")
    seed(reset=not ap.parse_args().if_empty)
