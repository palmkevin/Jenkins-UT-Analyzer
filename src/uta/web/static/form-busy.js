// Disable-on-submit feedback for every form (issue #150).
//
// A slow action (a bulk attribute, an ingest trigger, a cold demo instance) leaves the submit
// button looking idle — inviting a double click that acts twice. On submit, the button that fired
// it is disabled and swapped to a Bootstrap spinner + "Working…" until the PRG navigation lands.
// The original label rides in data-busy-label so a back/forward-cache restore can put it back
// (browsers resurrect the disabled busy state from bfcache; pageshow undoes it). Buttons rendered
// disabled server-side (the zero-selection bulk buttons) never submit, so they are never touched.
(function () {
  "use strict";

  document.addEventListener("submit", function (event) {
    var button = event.submitter;
    if (!button || button.tagName !== "BUTTON") return;
    // Deferred a tick: disabling the submitter inside the submit event itself would drop its
    // name/value (formaction routing) from the submitted data in some browsers, and a later
    // handler may still cancel the submission (re-checked before going busy).
    setTimeout(function () {
      if (event.defaultPrevented) return;
      button.setAttribute("data-busy-label", button.innerHTML);
      button.disabled = true;
      button.innerHTML =
        '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Working…';
    }, 0);
  });

  window.addEventListener("pageshow", function () {
    document.querySelectorAll("button[data-busy-label]").forEach(function (button) {
      button.innerHTML = button.getAttribute("data-busy-label");
      button.removeAttribute("data-busy-label");
      button.disabled = false;
    });
  });
})();
