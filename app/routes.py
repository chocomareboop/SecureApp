"""All InkPost routes.

LAB BUILD: intentional vulnerabilities are marked VULN-n.
"""
import functools
import os
import re
import subprocess

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from . import native
from .models import Comment, Post, User, db

bp = Blueprint("main", __name__)

ALLOWED_COVER_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,120}\.[A-Za-z]{2,}$")


# --------------------------------------------------------------------------- #
# Session / auth helpers
# --------------------------------------------------------------------------- #
@bp.before_app_request
def load_user():
    uid = session.get("user_id")
    g.user = db.session.get(User, uid) if uid else None
    if g.user is not None and not g.user.is_active:
        session.clear()
        g.user = None


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            if request.path.startswith("/api/"):
                return jsonify(error="authentication required"), 401
            flash("Please log in first.", "info")
            return redirect(url_for("main.login"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @functools.wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not g.user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


# --------------------------------------------------------------------------- #
# Public pages
# --------------------------------------------------------------------------- #
@bp.route("/")
def feed():
    tag = (request.args.get("tag") or "").strip()
    query = Post.query.filter_by(is_published=True)
    if tag:
        query = query.filter(Post.tags.ilike(f"%{tag}%"))
    posts = query.order_by(Post.created_at.desc()).all()
    all_tags = sorted({t for p in Post.query.filter_by(is_published=True) for t in p.tag_list})
    return render_template("feed.html", posts=posts, tag=tag, all_tags=all_tags)


@bp.route("/post/<int:post_id>")
def view_post(post_id):
    post = db.get_or_404(Post, post_id)
    if not post.is_published and (g.user is None or g.user.id != post.author_id):
        abort(404)
    return render_template("post.html", post=post)


@bp.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(current_app.config["UPLOAD_DIR"], filename)


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        error = None
        if not USERNAME_RE.match(username):
            error = "Username must be 3–30 letters, numbers or underscores."
        elif not EMAIL_RE.match(email):
            error = "Please enter a valid email address."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif User.query.filter((User.username == username) | (User.email == email)).first():
            error = "That username or email is already taken."
        if error:
            flash(error, "error")
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            session.clear()
            session["user_id"] = user.id
            flash("Welcome to InkPost!", "success")
            return redirect(url_for("main.feed"))
    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash("Incorrect username or password.", "error")
        elif not user.is_active:
            flash("This account has been disabled.", "error")
        else:
            session.clear()
            session["user_id"] = user.id
            flash(f"Welcome back, {user.username}.", "success")
            return redirect(url_for("main.feed"))
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.feed"))


# --------------------------------------------------------------------------- #
# Writing
# --------------------------------------------------------------------------- #
@bp.route("/me")
@login_required
def my_posts():
    posts = Post.query.filter_by(author_id=g.user.id).order_by(Post.updated_at.desc()).all()
    return render_template("my_posts.html", posts=posts)


def _save_cover(post, file):
    name = file.filename or ""
    if not name.lower().endswith(ALLOWED_COVER_EXT):
        raise ValueError("Cover must be a .png, .jpg, .gif or .webp image.")
    # VULN-2 (part 1) / CWE-22: the client-supplied filename is used as the
    # on-disk name without sanitization.
    path = os.path.join(current_app.config["UPLOAD_DIR"], name)
    file.save(path)
    post.cover_filename = name
    post.cover_original_name = name


def _apply_form(post):
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "")
    tags = request.form.get("tags", "").strip()
    if not title or len(title) > 200:
        raise ValueError("Title is required (max 200 characters).")
    if len(tags) > 200:
        raise ValueError("Tags are too long.")
    post.title = title
    post.body = body
    post.tags = tags
    post.is_published = request.form.get("publish") == "on"
    cover = request.files.get("cover")
    if cover and cover.filename:
        _save_cover(post, cover)


@bp.route("/write", methods=["GET", "POST"])
@login_required
def write():
    post = Post(author_id=g.user.id)
    if request.method == "POST":
        try:
            _apply_form(post)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("editor.html", post=post, is_new=True)
        db.session.add(post)
        db.session.commit()
        flash("Story saved.", "success")
        return redirect(url_for("main.view_post", post_id=post.id))
    return render_template("editor.html", post=post, is_new=True)


@bp.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    # VULN-3 (CWE-639): IDOR — the post is looked up by ID only. Any logged-in
    # user can open (and read) or modify anyone's post, including drafts.
    post = db.get_or_404(Post, post_id)
    if request.method == "POST":
        try:
            _apply_form(post)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("editor.html", post=post, is_new=False)
        db.session.commit()
        flash("Changes saved.", "success")
        return redirect(url_for("main.view_post", post_id=post.id))
    return render_template("editor.html", post=post, is_new=False)


@bp.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = db.get_or_404(Post, post_id)  # VULN-3: no ownership check
    db.session.delete(post)
    db.session.commit()
    flash("Story deleted.", "success")
    return redirect(url_for("main.my_posts"))


@bp.route("/post/<int:post_id>/publish", methods=["POST"])
@login_required
def toggle_publish(post_id):
    post = db.get_or_404(Post, post_id)  # VULN-3: no ownership check
    post.is_published = not post.is_published
    db.session.commit()
    flash("Story published." if post.is_published else "Story moved back to drafts.", "success")
    return redirect(url_for("main.view_post", post_id=post.id))


@bp.route("/post/<int:post_id>/cover-info", methods=["POST"])
@login_required
def cover_info(post_id):
    post = db.get_or_404(Post, post_id)  # VULN-3: no ownership check
    if not post.cover_filename:
        flash("This story has no cover image yet.", "info")
        return redirect(url_for("main.edit_post", post_id=post.id))
    path = os.path.join(current_app.config["UPLOAD_DIR"], post.cover_filename)
    # VULN-2 (CWE-78): OS command injection — the user-controlled filename is
    # interpolated into a string that is run by /bin/sh.
    result = subprocess.run(f"file {path}", shell=True, capture_output=True, text=True, timeout=10)
    info = (result.stdout + result.stderr).strip()
    return render_template("editor.html", post=post, is_new=False, cover_info=info)


@bp.route("/post/<int:post_id>/comment", methods=["POST"])
@login_required
def add_comment(post_id):
    post = db.get_or_404(Post, post_id)
    if not post.is_published:
        abort(404)
    body = request.form.get("body", "").strip()
    if not body or len(body) > 2000:
        flash("Comments must be 1–2000 characters.", "error")
    else:
        db.session.add(Comment(body=body, post_id=post.id, author_id=g.user.id))
        db.session.commit()
        flash("Comment posted.", "success")
    return redirect(url_for("main.view_post", post_id=post.id) + "#comments")


# --------------------------------------------------------------------------- #
# Import (.ink files, parsed by native C code)
# --------------------------------------------------------------------------- #
@bp.route("/import", methods=["GET", "POST"])
@login_required
def import_post():
    if request.method == "POST":
        file = request.files.get("ink_file")
        if not file or not file.filename:
            flash("Choose a .ink file to import.", "error")
            return render_template("import.html")
        data = file.read()
        try:
            meta, body = native.parse_ink(data, uploader_id=g.user.id)
        except native.InkError as exc:
            flash(f"Import rejected: {exc}", "error")
            return render_template("import.html")
        # FIX-1 (defense in depth): ownership and visibility are decided by the
        # server, never by values coming back from native code.
        post = Post(
            title=meta["title"][:200] or "Untitled import",
            tags=meta["tags"][:200],
            body=body,
            is_published=False,
            author_id=g.user.id,
        )
        db.session.add(post)
        db.session.commit()
        flash("Imported as a draft.", "success")
        return redirect(url_for("main.view_post", post_id=post.id))
    return render_template("import.html")


# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #
@bp.route("/settings")
@login_required
def settings():
    return render_template("settings.html")


@bp.route("/settings/email", methods=["POST"])
@login_required
def change_email():
    # VULN-4 (CWE-352): state-changing POST with no anti-CSRF token.
    email = request.form.get("email", "").strip().lower()
    if not EMAIL_RE.match(email):
        flash("Please enter a valid email address.", "error")
    elif User.query.filter(User.email == email, User.id != g.user.id).first():
        flash("That email is already in use.", "error")
    else:
        g.user.email = email
        db.session.commit()
        flash("Email updated.", "success")
    return redirect(url_for("main.settings"))


@bp.route("/settings/password", methods=["POST"])
@login_required
def change_password():
    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    if not g.user.check_password(current):
        flash("Current password is incorrect.", "error")
    elif len(new) < 8:
        flash("New password must be at least 8 characters.", "error")
    else:
        g.user.set_password(new)
        db.session.commit()
        flash("Password changed.", "success")
    return redirect(url_for("main.settings"))


@bp.route("/settings/delete", methods=["POST"])
@login_required
def delete_account():
    if request.form.get("confirm", "") != g.user.username:
        flash("Type your username to confirm.", "error")
        return redirect(url_for("main.settings"))
    db.session.delete(g.user)
    db.session.commit()
    session.clear()
    flash("Your account has been deleted.", "info")
    return redirect(url_for("main.feed"))


# --------------------------------------------------------------------------- #
# Admin
# --------------------------------------------------------------------------- #
@bp.route("/admin")
@admin_required
def admin():
    users = User.query.order_by(User.id).all()
    return render_template("admin.html", users=users)


@bp.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def admin_toggle_user(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == g.user.id:
        flash("You cannot disable your own account.", "error")
    else:
        user.is_active = not user.is_active
        db.session.commit()
        flash(f"{user.username} is now {'active' if user.is_active else 'disabled'}.", "success")
    return redirect(url_for("main.admin"))


# --------------------------------------------------------------------------- #
# JSON API
# --------------------------------------------------------------------------- #
@bp.route("/api/posts/<int:post_id>")
@login_required
def api_post(post_id):
    post = db.get_or_404(Post, post_id)  # VULN-3: returns other users' drafts
    return jsonify(post.to_dict())


@bp.route("/api/me/posts")
@login_required
def api_my_posts():
    posts = Post.query.filter_by(author_id=g.user.id).all()
    return jsonify([p.to_dict() for p in posts])


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #
@bp.app_errorhandler(400)
@bp.app_errorhandler(403)
@bp.app_errorhandler(404)
@bp.app_errorhandler(413)
@bp.app_errorhandler(429)
def handle_error(err):
    if request.path.startswith("/api/"):
        return jsonify(error=err.name), err.code
    return render_template("error.html", error=err), err.code
