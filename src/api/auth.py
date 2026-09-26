"""Sign-in, registration, profile (SRS i, ii)."""
from __future__ import annotations

import re

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from config.config import Config
from database.db import db
from src.app_security import limiter
from src.models.entities import AuditLog, Claim, Notification, Product, User
from src.security import rbac
from src.security.guards import (LOCKED_MESSAGE, invalidate_sessions, login_user, registration_role, require,
                                 safe_next)
from src.services.audit import audit

auth_bp = Blueprint("auth", __name__)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
HOME = {Config.ROLE_ADMIN: "admin.dashboard", Config.ROLE_REVIEWER: "reviewer.queue",
        Config.ROLE_STAFF: "claims.dashboard", Config.ROLE_CUSTOMER: "claims.dashboard"}


def password_problem(password: str, confirm: str | None = None) -> str | None:
    if len(password) < 10:
        return "Use at least 10 characters for your password."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Your password needs at least one letter and one number."
    if confirm is not None and password != confirm:
        return "The two passwords don't match."
    return None


def phone_problem(phone: str) -> str | None:
    digits = re.sub(r"\D", "", phone or "")
    if phone and not 7 <= len(digits) <= 15:
        return "Phone numbers need between 7 and 15 digits."
    return None


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10/minute;60/hour", methods=["POST"])
def login():
    if g.get("user"):
        return redirect(url_for("auth.home"))
    email = request.form.get("email", "").strip().lower()
    if request.method == "POST":
        user = User.query.filter_by(email=email).first()
        was_locked = bool(user and user.is_locked)
        ok, message = login_user(user, request.form.get("password", ""))
        if ok:
            audit("LOGIN_SUCCESS", "User", user.user_id, user=user)
            db.session.commit()
            flash(f"Welcome back, {user.first_name}.", "success")
            return redirect(safe_next(request.args.get("next"), url_for("auth.home")))
        reason = "locked" if message == LOCKED_MESSAGE else ("unknown_email" if user is None else
                                                             "disabled" if not user.is_active else "bad_password")
        audit("LOGIN_LOCKED" if user and user.is_locked and not was_locked else "LOGIN_FAILED", "User",
              user.user_id if user else None, user=None, email=email, reason=reason)
        db.session.commit()
        flash(message, "danger")
    return render_template("auth/login.html", email=email), (401 if request.method == "POST" else 200)


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10/hour", methods=["POST"])
def register():
    if g.get("user"):
        return redirect(url_for("auth.home"))
    form = request.form
    if request.method == "POST":
        name = form.get("full_name", "").strip()
        email = form.get("email", "").strip().lower()
        password = form.get("password", "")
        problem = (None if 2 <= len(name) <= 100 else "Enter your full name.") or \
            (None if EMAIL_RE.match(email) else "Enter a valid email address.") or \
            password_problem(password, form.get("confirm_password", "")) or phone_problem(form.get("phone", ""))
        if problem is None and User.query.filter_by(email=email).first():
            problem = "An account with this email already exists. Sign in instead."
        if problem:
            flash(problem, "warning")
            return render_template("auth/register.html", form=form), 400
        user = User(full_name=name, email=email, role=registration_role(form.get("role")),
                    phone_number=form.get("phone", "").strip() or None, address=form.get("address", "").strip() or None)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        audit("ACCOUNT_CREATED", "User", user.user_id, user=user, role=user.role, self_registered=True)
        db.session.commit()
        flash("Your account is ready. Sign in to register your first product.", "success")
        return redirect(url_for("auth.login", email=email))
    return render_template("auth/register.html", form={})


@auth_bp.post("/logout")
def logout():
    if g.get("user"):
        audit("LOGOUT", "User", g.user.user_id)
        db.session.commit()
    session.clear()
    flash("You're signed out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.get("/home")
@require()
def home():
    return redirect(url_for(HOME.get(g.user.role, "claims.dashboard")))


@auth_bp.route("/profile", methods=["GET", "POST"])
@require("profile.manage")
def profile():
    user = g.user
    if request.method == "POST":
        action = request.form.get("action")
        if action == "details":
            name = request.form.get("full_name", "").strip()
            phone = request.form.get("phone", "").strip()
            problem = (None if 2 <= len(name) <= 100 else "Enter your full name.") or phone_problem(phone)
            if problem:
                flash(problem, "warning")
            else:
                user.full_name, user.phone_number = name, phone or None
                user.address = request.form.get("address", "").strip() or None
                audit("PROFILE_UPDATED", "User", user.user_id)
                db.session.commit()
                flash("Profile saved.", "success")
        elif action == "password":
            new = request.form.get("new_password", "")
            if not user.check_password(request.form.get("current_password", "")):
                flash("Your current password is not correct.", "danger")
            elif (problem := password_problem(new, request.form.get("confirm_password", ""))):
                flash(problem, "warning")
            elif user.check_password(new):
                flash("Choose a password you haven't used for this account.", "warning")
            else:
                user.set_password(new)
                user.must_change_password = False
                invalidate_sessions(user)                   # sign out every other device
                audit("PASSWORD_CHANGED", "User", user.user_id)
                db.session.commit()
                session["ver"] = user.session_version       # keep this session alive
                flash("Password changed. Other devices were signed out.", "success")
        return redirect(url_for("auth.profile"))
    stats = {"products": Product.query.filter_by(user_id=user.id).count(),
             "claims": Claim.query.filter_by(user_id=user.id).count(),
             "unread": Notification.query.filter_by(user_id=user.id, is_read=False).count()}
    activity = AuditLog.query.filter_by(user_id=user.id).order_by(AuditLog.id.desc()).limit(8).all()
    permissions = sorted(rbac.policy()["roles"].get(user.role, {}).get("permissions", {}).items())
    return render_template("auth/profile.html", user=user, stats=stats, activity=activity, permissions=permissions)
