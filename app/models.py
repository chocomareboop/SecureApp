"""Database models for InkPost."""
import re
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="user")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    posts = db.relationship("Post", backref="author", lazy=True, cascade="all, delete-orphan")
    comments = db.relationship("Comment", backref="author", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def initial(self):
        return self.username[:1].upper()


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False, default="")
    tags = db.Column(db.String(200), nullable=False, default="")
    cover_filename = db.Column(db.String(255))
    cover_original_name = db.Column(db.String(255))
    is_published = db.Column(db.Boolean, nullable=False, default=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    comments = db.relationship(
        "Comment", backref="post", lazy=True, cascade="all, delete-orphan", order_by="Comment.created_at"
    )

    @property
    def tag_list(self):
        return [t.strip() for t in (self.tags or "").split(",") if t.strip()]

    @property
    def reading_minutes(self):
        return max(1, round(len((self.body or "").split()) / 200))

    @property
    def excerpt(self):
        text = re.sub(r"^\s*([-*]|\d+\.)\s+", "", self.body or "", flags=re.M)
        text = re.sub(r"[#*_>`\[\]()!]", "", text)
        text = " ".join(text.split())
        return text[:160] + ("…" if len(text) > 160 else "")

    @property
    def tone(self):
        return self.id % 6 if self.id else 0

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "tags": self.tag_list,
            "is_published": self.is_published,
            "author": self.author.username if self.author else None,
            "author_id": self.author_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
