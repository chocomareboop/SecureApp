"""Jinja filters."""
import bleach
import markdown
from markupsafe import Markup

# FIX-6 (CWE-79): only formatting tags survive; scripts, event handlers and
# javascript: URLs are stripped after Markdown is rendered.
ALLOWED_TAGS = {
    "p", "br", "hr", "h1", "h2", "h3", "h4", "strong", "em", "b", "i", "del",
    "a", "ul", "ol", "li", "blockquote", "code", "pre",
    "table", "thead", "tbody", "tr", "th", "td", "img",
}
ALLOWED_ATTRIBUTES = {"a": ["href", "title", "rel"], "img": ["src", "alt", "title"]}
ALLOWED_PROTOCOLS = {"http", "https", "mailto"}


def render_markdown(text):
    html = markdown.markdown(text or "", extensions=["fenced_code", "tables"])
    clean = bleach.clean(
        html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, protocols=ALLOWED_PROTOCOLS, strip=True
    )
    # Safe: the HTML was sanitized by bleach on the line above.
    return Markup(clean)  # nosec B704


def nice_date(value):
    return value.strftime("%b %d, %Y") if value else ""


def register_filters(app):
    app.jinja_env.filters["markdown"] = render_markdown
    app.jinja_env.filters["nice_date"] = nice_date
