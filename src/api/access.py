"""Administrator > Access control: users, invitations, roles, sessions, permission matrix."""
import re
import secrets

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from sqlalchemy import func

from database.db import db
from src.models.entities import AuditLog, ServiceCenter, User
from src.security import rbac
from src.security.guards import invalidate_sessions, require
from src.services.audit import audit

access_bp = Blueprint("access", __name__, url_prefix="/admin/access")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


def _active_admins() -> int:
    return User.query.filter_by(role="administrator", is_active=True).count()


def _center(raw: str | None):
    return db.session.get(ServiceCenter, int(raw)) if raw and raw.isdigit() else None


@access_bp.get("/")
@require("user.manage")
def index():
    q = User.query
    if request.args.get("role") in rbac.roles():
        q = q.filter_by(role=request.args["role"])
    if request.args.get("status") in {"active", "disabled"}:
        q = q.filter_by(is_active=request.args["status"] == "active")
    if (term := request.args.get("q", "").strip()):
        like = f"%{term.lower()}%"
        q = q.filter(func.lower(User.email).like(like) | func.lower(User.full_name).like(like))
    users = q.order_by(User.role, User.full_name).limit(200).all()
    denials = AuditLog.query.filter_by(action="ACCESS_DENIED").order_by(AuditLog.id.desc()).limit(12).all()
    perms = sorted({p for r in rbac.policy()["roles"].values() for p in r["permissions"]})
    counts = dict(db.session.query(User.role, func.count()).group_by(User.role).all())
    return render_template("admin/access_control.html", users=users, denials=denials, perms=perms,
                           policy=rbac.policy(), counts=counts, filters=request.args,
                           centers=ServiceCenter.query.order_by(ServiceCenter.name).all())


@access_bp.post("/invite")
@require("user.manage")
def invite():
    email = request.form.get("email", "").strip().lower()
    name = request.form.get("full_name", "").strip()
    role = request.form.get("role", "")
    center = _center(request.form.get("service_center_id"))
    if role not in rbac.roles() or not EMAIL_RE.match(email) or not 2 <= len(name) <= 100:
        flash("Enter a name, a valid email and a role.", "warning")
        return redirect(url_for(".index"))
    if User.query.filter_by(email=email).first():
        flash("That email already has an account.", "warning")
        return redirect(url_for(".index"))
    if role == "service_center_staff" and center is None:
        flash("Staff accounts need a service center.", "warning")
        return redirect(url_for(".index"))
    temp = secrets.token_urlsafe(9) + "7a"             # meets the password policy (letter + digit)
    u = User(email=email, full_name=name, role=role, must_change_password=True,
             service_center_id=center.id if role == "service_center_staff" else None)
    u.set_password(temp)
    db.session.add(u)
    db.session.flush()
    audit("USER_INVITED", "User", u.user_id, role=role, service_center=center.center_id if center else None)
    db.session.commit()
    flash(f"Invited {email}. One-time password: {temp} — it's shown only once. They must change it at first sign-in.",
          "success")
    return redirect(url_for(".index"))


@access_bp.post("/<string:user_code>/role")
@require("user.manage")
def change_role(user_code):
    target = User.query.filter_by(user_id=user_code).first_or_404()
    new_role = request.form.get("role")
    decision = rbac.authorize(g.user, "user.manage", target_user=target, new_role=new_role,
                              active_admin_count=_active_admins())
    if not decision:
        flash(rbac.MESSAGES[decision.code], "danger")
        return redirect(url_for(".index"))
    if new_role == target.role:
        return redirect(url_for(".index"))
    if new_role == "service_center_staff":
        center = _center(request.form.get("service_center_id")) or target.service_center or \
            ServiceCenter.query.order_by(ServiceCenter.id).first()
        if center is None:
            flash("Create a service center before assigning staff.", "warning")
            return redirect(url_for(".index"))
        target.service_center_id = center.id
    else:
        target.service_center_id = None
    old = target.role
    target.role = new_role
    invalidate_sessions(target)                    # old privileges end immediately
    audit("ROLE_CHANGED", "User", target.user_id, old=old, new=new_role)
    db.session.commit()
    flash(f"{target.full_name} is now {rbac.policy()['roles'][new_role]['label']}. Their open sessions were signed out.",
          "success")
    return redirect(url_for(".index"))


@access_bp.post("/<string:user_code>/status")
@require("user.manage")
def toggle_status(user_code):
    target = User.query.filter_by(user_id=user_code).first_or_404()
    deactivate = target.is_active
    decision = rbac.authorize(g.user, "user.manage", target_user=target, deactivate=deactivate,
                              active_admin_count=_active_admins())
    if not decision:
        flash(rbac.MESSAGES[decision.code], "danger")
        return redirect(url_for(".index"))
    target.is_active = not deactivate
    invalidate_sessions(target)
    audit("USER_DISABLED" if deactivate else "USER_ENABLED", "User", target.user_id)
    db.session.commit()
    flash(f"{target.full_name} {'disabled' if deactivate else 'enabled'}.", "success")
    return redirect(url_for(".index"))


@access_bp.post("/<string:user_code>/sign-out")
@require("user.manage")
def force_sign_out(user_code):
    target = User.query.filter_by(user_id=user_code).first_or_404()
    invalidate_sessions(target)
    target.failed_logins, target.locked_until = 0, None
    audit("SESSIONS_REVOKED", "User", target.user_id)
    db.session.commit()
    flash(f"Signed {target.full_name} out everywhere and cleared any lockout.", "success")
    return redirect(url_for(".index"))


@access_bp.post("/service-centers")
@require("user.manage")
def add_center():
    name, city = request.form.get("name", "").strip(), request.form.get("city", "").strip()
    if not 3 <= len(name) <= 120 or not 2 <= len(city) <= 80:
        flash("Enter the service center's name and city.", "warning")
    elif ServiceCenter.query.filter(func.lower(ServiceCenter.name) == name.lower()).first():
        flash("A service center with that name already exists.", "warning")
    else:
        c = ServiceCenter(name=name, city=city, phone=request.form.get("phone", "").strip() or None)
        db.session.add(c)
        db.session.flush()
        audit("SERVICE_CENTER_CREATED", "ServiceCenter", c.center_id, name=name)
        db.session.commit()
        flash(f"{name} added.", "success")
    return redirect(url_for(".index", _anchor="centers"))
