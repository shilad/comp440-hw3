// The results viewer's few bits of behaviour. Every page works without this file: the
// filters are a plain form, prev/next are links, and every result can be opened by hand.
(function () {
  "use strict";

  // Filters: a change to a list or the checkbox applies at once. The text search applies
  // when you press Enter or the button.
  document.querySelectorAll("form.filters [data-auto]").forEach(function (el) {
    el.addEventListener("change", function () {
      if (el.form) el.form.submit();
    });
  });

  // Open or fold every long result in a trace.
  document.querySelectorAll("[data-open-all], [data-close-all]").forEach(function (button) {
    button.addEventListener("click", function () {
      var open = button.hasAttribute("data-open-all");
      var trace = button.closest(".trace") || document;
      trace.querySelectorAll("details.result").forEach(function (d) { d.open = open; });
    });
  });

  // Following a link to a call opens its result if it is folded.
  function openTarget() {
    if (!location.hash || location.hash.indexOf(":~:") >= 0) return;
    var el;
    try { el = document.querySelector(location.hash); } catch (err) { return; }
    if (!el) return;
    el.querySelectorAll("details.result").forEach(function (d) { d.open = true; });
  }
  window.addEventListener("hashchange", openTarget);
  openTarget();

  // Left and right arrow keys move to the previous and next claim, unless you are typing.
  document.addEventListener("keydown", function (ev) {
    if (ev.altKey || ev.ctrlKey || ev.metaKey || ev.shiftKey) return;
    var t = ev.target;
    if (t && (t.isContentEditable || /^(INPUT|SELECT|TEXTAREA|BUTTON|SUMMARY)$/.test(t.tagName))) return;
    var rel = ev.key === "ArrowLeft" ? "prev" : ev.key === "ArrowRight" ? "next" : null;
    if (!rel) return;
    var a = document.querySelector('a[rel="' + rel + '"]');
    if (a) { location.href = a.href; ev.preventDefault(); }
  });
})();
