// InkPost UI behaviour. Kept in an external file (no inline scripts) so a
// strict Content-Security-Policy can be applied.
(function () {
  "use strict";

  // ---- Theme toggle ----
  function currentTheme() {
    var set = document.documentElement.getAttribute("data-theme");
    if (set) return set;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("inkpost-theme", next); } catch (e) { /* ignore */ }
    });
  });

  // ---- Toasts ----
  document.querySelectorAll(".toast").forEach(function (toast, i) {
    setTimeout(function () {
      toast.classList.add("leaving");
      setTimeout(function () { toast.remove(); }, 350);
    }, 4200 + i * 400);
  });

  // ---- Confirm dialogs ----
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm(form.getAttribute("data-confirm"))) e.preventDefault();
    });
  });

  // ---- Editor: Write / Preview tabs with a tiny, escaping Markdown renderer ----
  function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function inline(s) {
    return s
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>")
      .replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" rel="noopener">$1</a>');
  }
  function renderMarkdown(src) {
    var lines = esc(src).split(/\r?\n/), out = [], list = null, para = [];
    function flushPara() { if (para.length) { out.push("<p>" + inline(para.join(" ")) + "</p>"); para = []; } }
    function flushList() { if (list) { out.push("</" + list + ">"); list = null; } }
    lines.forEach(function (line) {
      var m;
      if (!line.trim()) { flushPara(); flushList(); return; }
      if ((m = line.match(/^(#{1,3})\s+(.*)/))) {
        flushPara(); flushList();
        var level = Math.min(m[1].length + 1, 3);
        out.push("<h" + level + ">" + inline(m[2]) + "</h" + level + ">");
      } else if ((m = line.match(/^&gt;\s?(.*)/))) {
        flushPara(); flushList(); out.push("<blockquote>" + inline(m[1]) + "</blockquote>");
      } else if ((m = line.match(/^\s*[-*]\s+(.*)/)) || (m = line.match(/^\s*\d+\.\s+(.*)/))) {
        flushPara();
        var type = /^\s*\d+\./.test(line) ? "ol" : "ul";
        if (list !== type) { flushList(); out.push("<" + type + ">"); list = type; }
        out.push("<li>" + inline(m[1]) + "</li>");
      } else { flushList(); para.push(line); }
    });
    flushPara(); flushList();
    return out.join("\n") || '<p class="muted">Nothing to preview yet.</p>';
  }

  var tabs = document.querySelectorAll("[data-tab]");
  var source = document.getElementById("body");
  var preview = document.getElementById("preview");
  if (tabs.length && source && preview) {
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        tabs.forEach(function (t) { t.classList.toggle("active", t === tab); });
        var showPreview = tab.getAttribute("data-tab") === "preview";
        if (showPreview) preview.innerHTML = renderMarkdown(source.value);
        source.classList.toggle("hidden", showPreview);
        preview.classList.toggle("hidden", !showPreview);
      });
    });
  }
})();
