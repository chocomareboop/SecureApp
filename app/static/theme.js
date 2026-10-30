// Applies the saved theme before first paint (loaded synchronously in <head>).
(function () {
  var t = null;
  try { t = localStorage.getItem("inkpost-theme"); } catch (e) { /* storage blocked */ }
  if (t === "dark" || t === "light") document.documentElement.setAttribute("data-theme", t);
})();
