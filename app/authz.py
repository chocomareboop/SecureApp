"""Central object-level authorization for posts (FIX-3, CWE-639).

Every route that touches a post goes through get_post_or_404(), so the rules
live in exactly one place:

    view     published posts: anyone; drafts: only the author
    comment  published posts, any logged-in user
    edit / publish / inspect   only the author
    delete   the author, or an admin (published posts)

Posts a user is not allowed to *see* return 404 so that draft IDs cannot be
discovered by enumeration; posts they can see but not change return 403.
"""
from flask import abort, g

from .models import Post, db

OWNER_ACTIONS = {"edit", "publish", "inspect"}


def can(user, post, action):
    is_owner = user is not None and user.id == post.author_id
    if action == "view":
        return post.is_published or is_owner
    if user is None:
        return False
    if action == "comment":
        return post.is_published
    if action in OWNER_ACTIONS:
        return is_owner
    if action == "delete":
        return is_owner or user.is_admin
    return False


def get_post_or_404(post_id, action):
    post = db.session.get(Post, post_id)
    if post is None or not can(g.user, post, "view"):
        abort(404)
    if not can(g.user, post, action):
        abort(403)
    return post
