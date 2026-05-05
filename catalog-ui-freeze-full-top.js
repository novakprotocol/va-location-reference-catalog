(function () {
  "use strict";

  var STATE = { initialized: false, attempts: 0 };

  function textOf(el) {
    return (el && el.textContent ? el.textContent : "").replace(/\s+/g, " ").trim();
  }

  function isCandidateReviewPage() {
    return /contact-hours-candidates\.html/i.test(window.location.pathname);
  }

  function findVclBanner() {
    var bodyChildren = Array.prototype.slice.call(document.body.children || []);
    for (var i = 0; i < bodyChildren.length; i += 1) {
      if (/Veterans Crisis Line/i.test(textOf(bodyChildren[i]))) return bodyChildren[i];
    }
    var all = Array.prototype.slice.call(document.querySelectorAll("body *"));
    for (var j = 0; j < all.length; j += 1) {
      var txt = textOf(all[j]);
      if (/Veterans Crisis Line/i.test(txt) && txt.length < 500) return all[j];
    }
    return null;
  }

  function lockVclBanner() {
    var banner = findVclBanner();
    if (!banner) {
      document.documentElement.style.setProperty("--catalog-vcl-banner-height", "0px");
      return 0;
    }
    banner.classList.add("catalog-vcl-fixed-top");
    var height = Math.ceil(banner.getBoundingClientRect().height || banner.scrollHeight || 0);
    document.documentElement.style.setProperty("--catalog-vcl-banner-height", height + "px");
    return height;
  }

  function cleanupGenericTableLock() {
    document.documentElement.classList.remove("catalog-freeze-full-top");
    document.documentElement.classList.add("catalog-candidate-review-safe");

    Array.prototype.forEach.call(document.querySelectorAll(".catalog-table-scrollpane-lock"), function (pane) {
      pane.classList.remove("catalog-table-scrollpane-lock");
      pane.style.height = "";
      pane.style.maxHeight = "";
      pane.style.minHeight = "";
      pane.style.overflow = "";
      pane.style.position = "";
      pane.style.width = "";
    });

    Array.prototype.forEach.call(document.querySelectorAll("thead th, thead td"), function (cell) {
      cell.style.position = "";
      cell.style.top = "";
      cell.style.zIndex = "";
    });

    document.documentElement.style.removeProperty("--catalog-table-scrollpane-top");
    document.body.style.overflow = "";
    document.body.style.height = "";
    document.documentElement.style.overflow = "";
    document.documentElement.style.height = "";
  }

  function tableHeaderText(table) {
    var cells = table.querySelectorAll("thead th, thead td, tr:first-child th");
    return Array.prototype.map.call(cells, textOf).join(" ").toLowerCase();
  }

  function looksLikeMainCatalogTable(table) {
    if (!table) return false;

    var rows = table.querySelectorAll("tbody tr").length || table.querySelectorAll("tr").length;
    var header = tableHeaderText(table);

    var hasCoreCatalogHeaders =
      header.indexOf("facility id") !== -1 &&
      (header.indexOf("station") !== -1 || header.indexOf("site code") !== -1) &&
      header.indexOf("name") !== -1 &&
      header.indexOf("city") !== -1 &&
      header.indexOf("state") !== -1;

    var hasLargeCatalogShape = rows >= 20 && header.indexOf("facility") !== -1 && header.indexOf("source") !== -1;

    return hasCoreCatalogHeaders || hasLargeCatalogShape;
  }

  function findPrimaryCatalogTable() {
    var tables = Array.prototype.slice.call(document.querySelectorAll("table"));
    var candidates = tables.filter(looksLikeMainCatalogTable);
    if (!candidates.length) return null;

    candidates.sort(function (a, b) {
      return b.querySelectorAll("tbody tr, tr").length - a.querySelectorAll("tbody tr, tr").length;
    });
    return candidates[0];
  }

  function ensureThead(table) {
    if (!table || table.tHead || !table.rows || !table.rows.length) return;
    var first = table.rows[0];
    if (!first || !first.querySelector("th")) return;
    var thead = document.createElement("thead");
    table.insertBefore(thead, table.firstChild);
    thead.appendChild(first);
  }

  function findScrollPane(table) {
    if (!table) return null;
    var node = table.parentElement;
    var chosen = node;
    while (node && node !== document.body && node !== document.documentElement) {
      var rect = node.getBoundingClientRect();
      var hasUsefulBox = rect.width > 300 && rect.height > 80;
      if (hasUsefulBox && node.scrollWidth >= table.scrollWidth) {
        chosen = node;
        break;
      }
      chosen = node;
      node = node.parentElement;
    }
    return chosen || table.parentElement;
  }

  function applyCandidateReviewMode() {
    lockVclBanner();
    cleanupGenericTableLock();
    return true;
  }

  function applyCatalogTableMode() {
    document.documentElement.classList.remove("catalog-candidate-review-safe");

    lockVclBanner();

    var table = findPrimaryCatalogTable();
    if (!table) {
      // No true catalog table. Do not force body/table scroll locking.
      cleanupGenericTableLock();
      return false;
    }

    ensureThead(table);
    var pane = findScrollPane(table);
    if (!pane) return false;

    document.documentElement.classList.add("catalog-freeze-full-top");
    table.classList.add("catalog-sticky-real-header-table");
    pane.classList.add("catalog-table-scrollpane-lock");

    var top = Math.max(0, Math.ceil(pane.getBoundingClientRect().top));
    if (top < 10 && STATE.attempts < 20) return false;

    document.documentElement.style.setProperty("--catalog-table-scrollpane-top", top + "px");
    pane.style.height = "calc(100vh - " + top + "px - 12px)";
    pane.style.maxHeight = "calc(100vh - " + top + "px - 12px)";
    pane.style.overflow = "auto";
    pane.style.position = "relative";

    Array.prototype.forEach.call(table.querySelectorAll("thead th, thead td"), function (cell) {
      cell.style.position = "sticky";
      cell.style.top = "0px";
      cell.style.zIndex = "1000";
    });

    return true;
  }

  function apply() {
    STATE.attempts += 1;
    if (isCandidateReviewPage()) return applyCandidateReviewMode();
    return applyCatalogTableMode();
  }

  function scheduleApply() {
    window.requestAnimationFrame(function () {
      try { apply(); }
      catch (err) { console.warn("catalog page-scoped freeze failed", err); }
    });
  }

  function boot() {
    if (STATE.initialized) return;
    STATE.initialized = true;

    var timer = window.setInterval(function () {
      var ok = apply();
      if (ok || STATE.attempts > 60) window.clearInterval(timer);
    }, 100);

    window.addEventListener("resize", scheduleApply);
    window.addEventListener("orientationchange", scheduleApply);

    var observer = new MutationObserver(scheduleApply);
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();