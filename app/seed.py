"""Demo data. Creates admin (id 1), alice (id 2) and bob (id 3)."""
import click

from .models import Comment, Post, User, db

DEMO_USERS = [
    # username, email, password, role
    ("admin", "admin@inkpost.local", "admin-pass-123", "admin"),
    ("alice", "alice@inkpost.local", "alice-pass-123", "user"),
    ("bob", "bob@inkpost.local", "bob-pass-123", "user"),
]


def seed_if_empty():
    if User.query.first() is not None:
        return
    users = {}
    for username, email, password, role in DEMO_USERS:
        u = User(username=username, email=email, role=role)
        u.set_password(password)
        db.session.add(u)
        users[username] = u
    db.session.flush()

    posts = [
        Post(
            title="Welcome to the Robotics Society blog",
            tags="robotics, announcements",
            is_published=True,
            author_id=users["alice"].id,
            body=(
                "## Hello, builders\n\nThis is where the **Robotics Society** shares build logs, "
                "event recaps and tutorials.\n\n- Weekly lab nights on Thursdays\n"
                "- Line-follower workshop next month\n- Bring your own Arduino\n\n"
                "Leave a comment if you want to join the competition team."
            ),
        ),
        Post(
            title="Budget 2026 — confidential draft",
            tags="finance, internal",
            is_published=False,
            author_id=users["alice"].id,
            body=(
                "CONFIDENTIAL — society executives only.\n\n"
                "Sponsor contract: PKR 450,000 from the robotics sponsor. "
                "Do not share before the general body meeting."
            ),
        ),
        Post(
            title="Notes from the 24-hour hackathon",
            tags="hackathon, recap",
            is_published=True,
            author_id=users["bob"].id,
            body=(
                "We shipped a campus lost-and-found app in 24 hours.\n\n"
                "### What worked\n\n1. Small team, clear roles\n2. Deploying early\n\n"
                "### What didn't\n\nSleep. Sleep did not work."
            ),
        ),
        Post(
            title="Draft: elections timeline",
            tags="elections",
            is_published=False,
            author_id=users["bob"].id,
            body="Nominations open on the 3rd, voting on the 10th. Still waiting on the faculty advisor.",
        ),
        Post(
            title="Inside the CS Society's new mentorship program",
            tags="mentorship, community",
            is_published=True,
            author_id=users["admin"].id,
            body=(
                "Senior students are pairing with first-years this semester.\n\n"
                "> The best way to learn is to teach.\n\nSign-ups close Friday."
            ),
        ),
    ]
    db.session.add_all(posts)
    db.session.flush()
    db.session.add(Comment(body="Count me in for the line-follower workshop!", post_id=posts[0].id, author_id=users["bob"].id))
    db.session.commit()


def register_cli(app):
    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, help="Drop all data first.")
    def seed_command(reset):
        """Load demo users and posts."""
        if reset:
            db.drop_all()
            db.create_all()
        seed_if_empty()
        click.echo("Demo data ready: admin / alice / bob")
