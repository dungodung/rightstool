// Click-to-sort for any <table class="sortable">. Replaces the original
// tool's dependency on http://www.kryogenix.org/.../sorttable.js, which was
// (a) loaded over plain http:// from an https:// page -- silently blocked
// by every modern browser as mixed content, so sorting has never actually
// worked in years -- and (b) now 404s outright; the URL doesn't serve
// anything anymore. This is a small from-scratch replacement, not a port.
(function () {
  function cellText(cell) {
    return cell.textContent.trim();
  }

  function compareRows(a, b, colIndex, numeric) {
    const av = cellText(a.cells[colIndex]);
    const bv = cellText(b.cells[colIndex]);
    if (numeric) {
      const an = parseFloat(av.replace(/[^0-9.-]/g, ""));
      const bn = parseFloat(bv.replace(/[^0-9.-]/g, ""));
      if (!isNaN(an) && !isNaN(bn)) return an - bn;
    }
    return av.localeCompare(bv, undefined, { sensitivity: "base" });
  }

  function sortTableByColumn(table, colIndex, ascending) {
    const tbody = table.tBodies[0];
    if (!tbody) return;
    const numeric = Array.from(tbody.rows).every((row) => {
      const text = cellText(row.cells[colIndex]);
      return text === "" || !isNaN(parseFloat(text.replace(/[^0-9.-]/g, "")));
    });
    const rows = Array.from(tbody.rows).sort((a, b) => compareRows(a, b, colIndex, numeric));
    if (!ascending) rows.reverse();
    rows.forEach((row) => tbody.appendChild(row));
  }

  document.querySelectorAll("table.sortable").forEach((table) => {
    const headerRow = table.tHead && table.tHead.rows[0];
    if (!headerRow) return;
    Array.from(headerRow.cells).forEach((th, colIndex) => {
      th.style.cursor = "pointer";
      th.title = "Click to sort";
      let ascending = true;
      th.addEventListener("click", () => {
        sortTableByColumn(table, colIndex, ascending);
        ascending = !ascending;
      });
    });
  });
})();
