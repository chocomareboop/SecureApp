"""Jinja filters."""
import markdown
from markupsafe import Markup


def render_markdown(text):
    # VULN-6 (CWE-79): Markdown is converted to HTML and marked safe without
    # sanitization, so raw HTML/JS in a post body is rendered as-is.
    return Markup(markdown.markdown(text or "", extensions=["fenced_code", "tables"]))


def nice_date(value):
    return value.strftime("%b %d, %Y") if value else ""


def register_filters(app):
    app.jinja_env.filters["markdown"] = render_markdown
    app.jinja_env.filters["nice_date"] = nice_date
