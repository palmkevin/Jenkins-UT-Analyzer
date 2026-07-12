// Long-text ergonomics for error details / stack traces (issue #145). Vanilla JS, vendored.
//
// Generic, driven by data- attributes:
//   - clamp:  <code data-clamp="15">…</code> — when the element's text exceeds N lines, show only
//     the first N (plus an ellipsis line) and add a "Show full trace (M lines)" toggle after the
//     enclosing <pre>/<p>. Progressive enhancement: the full text always ships in the HTML, so
//     without JS nothing is hidden.
//   - copy:   <button data-copy-target="<element-id>">…</button> — copies the target element's
//     FULL text (the pre-clamp original) to the clipboard, with a transient "Copied" confirmation.
(function () {
  "use strict";

  var DEFAULT_LINES = 15;
  var fullText = new WeakMap(); // element -> its original, un-clamped text

  document.querySelectorAll("[data-clamp]").forEach(function (el) {
    var limit = parseInt(el.getAttribute("data-clamp"), 10) || DEFAULT_LINES;
    var full = el.textContent;
    fullText.set(el, full);
    var lines = full.split("\n");
    if (lines.length <= limit) return;

    var clamped = lines.slice(0, limit).join("\n") + "\n…";
    var expanded = false;
    var toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "btn btn-sm btn-outline-secondary trace-toggle";

    function render() {
      el.textContent = expanded ? full : clamped;
      toggle.textContent = expanded
        ? "Collapse trace"
        : "Show full trace (" + lines.length + " lines)";
    }
    toggle.addEventListener("click", function () {
      expanded = !expanded;
      render();
    });

    // Prefer the sibling .trace-actions bar (next to the copy button); else drop the toggle
    // straight after the clamped block.
    var host = el.closest("pre, p") || el;
    var actions = host.nextElementSibling;
    if (actions && actions.classList.contains("trace-actions")) {
      actions.insertBefore(toggle, actions.firstChild);
    } else {
      host.insertAdjacentElement("afterend", toggle);
    }
    render();
  });

  document.querySelectorAll("[data-copy-target]").forEach(function (btn) {
    var target = document.getElementById(btn.getAttribute("data-copy-target"));
    if (!target) return;
    var label = btn.textContent;
    var timer = null;

    function done(ok) {
      btn.textContent = ok ? "Copied ✓" : "Copy failed";
      clearTimeout(timer);
      timer = setTimeout(function () {
        btn.textContent = label;
      }, 1500);
    }

    btn.addEventListener("click", function () {
      var text = fullText.get(target) || target.textContent;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(
          function () { done(true); },
          function () { done(false); }
        );
        return;
      }
      // Fallback for non-secure contexts (plain-HTTP deployments): hidden textarea + execCommand.
      var area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.left = "-9999px";
      document.body.appendChild(area);
      area.select();
      var ok = false;
      try {
        ok = document.execCommand("copy");
      } catch (e) {
        ok = false;
      }
      document.body.removeChild(area);
      done(ok);
    });
  });
})();
