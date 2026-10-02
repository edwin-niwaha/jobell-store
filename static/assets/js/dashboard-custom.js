(function () {
  function closeOtherDropdowns(event) {
    var openMenus = document.querySelectorAll('.navbar .dropdown-menu.show');
    openMenus.forEach(function (menu) {
      if (!menu.parentElement || menu.parentElement.contains(event.target)) {
        return;
      }
      menu.classList.remove('show');
      var toggle = menu.parentElement.querySelector('[data-toggle="dropdown"], [data-bs-toggle="dropdown"]');
      if (toggle) {
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  function markEmptyTables() {
    document.querySelectorAll('.content-wrapper table').forEach(function (table) {
      var body = table.tBodies && table.tBodies[0];
      if (!body || body.rows.length !== 0) {
        return;
      }
      var columns = table.tHead && table.tHead.rows[0] ? table.tHead.rows[0].cells.length : 1;
      var row = body.insertRow();
      var cell = row.insertCell();
      cell.colSpan = columns;
      cell.className = 'empty-state';
      cell.textContent = 'No records found.';
    });
  }

  function bindDangerousConfirmations() {
    var emailForm = document.getElementById('emailForm');
    if (emailForm) {
      emailForm.addEventListener('submit', function (event) {
        if (!window.confirm('Send this email to all selected subscribers?')) {
          event.preventDefault();
        }
      });
    }
  }

  document.addEventListener('click', closeOtherDropdowns);
  document.addEventListener('DOMContentLoaded', function () {
    markEmptyTables();
    bindDangerousConfirmations();
  });
})();
