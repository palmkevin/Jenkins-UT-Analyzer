// Bulk-selection ergonomics for tables whose rows feed a bulk-action form (issue #76).
//
// Generic, driven by data- attributes keyed on the bulk form's id:
//   - header checkbox:  <input type="checkbox" data-bulk-select-all="<form-id>">
//   - row checkboxes:   <input type="checkbox" data-bulk-item="<form-id>">
//   - action button:    <button data-bulk-button="<form-id>" data-bulk-label="Acknowledge selected">
//
// Behaviour: the header checkbox selects/deselects all row checkboxes of its own table only and
// shows the indeterminate state on partial selection; the button carries a live selected-count
// ("Acknowledge selected (3)") and is disabled while nothing is selected. Buttons are rendered
// disabled server-side, so the zero-selection state holds even before this script runs.
(function () {
  "use strict";

  document.querySelectorAll("[data-bulk-select-all]").forEach(function (master) {
    var formId = master.getAttribute("data-bulk-select-all");
    var rows = Array.prototype.slice.call(
      document.querySelectorAll('input[type="checkbox"][data-bulk-item="' + formId + '"]')
    );
    var button = document.querySelector('[data-bulk-button="' + formId + '"]');
    var label = button
      ? button.getAttribute("data-bulk-label") || button.textContent.trim()
      : "";

    function refresh() {
      var checked = rows.filter(function (cb) { return cb.checked; }).length;
      master.checked = rows.length > 0 && checked === rows.length;
      master.indeterminate = checked > 0 && checked < rows.length;
      if (button) {
        button.disabled = checked === 0;
        button.textContent = label + " (" + checked + ")";
      }
    }

    master.addEventListener("change", function () {
      rows.forEach(function (cb) { cb.checked = master.checked; });
      refresh();
    });
    rows.forEach(function (cb) { cb.addEventListener("change", refresh); });
    refresh();
  });
})();
