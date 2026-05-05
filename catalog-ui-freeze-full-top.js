(function () {
  "use strict";

  var STATE = {
    initialized: false,
    lastTop: null,
    attempts: 0
  };

  function textOf(el) {
    return (el && el.textContent ? el.textContent : "").replace(/\s+/g, " ").trim();
  }

  function findVclBanner() {
    var bodyChildren = Array.prototype.slice.call(document.body.children || []);
    for (var i = 0; i < bodyChildren.length; i += 1) {
      if (/Veterans Crisis Line/i.test(textOf(bodyChildren[i]))) {
        return bodyChildren[i];
      }
    }

    var all = Array.prototype.slice.call(document.querySelectorAll("body *"));
    for (var j = 0; j < all.length; j += 1) {
      var txt = textOf(all[j]);
      if (/Veterans Crisis Line/i.test(txt) && txt.length < 500) {
        return all[j];
      }
    }

    return null;
  }

  function findPrimaryTable() {
    var tables = Array.prototype.slice.call(document.querySelectorAll("table"));
    if (!tables.length) {
      return null;
    }

    var best = null;
    var bestScore = -1;

    tables.forEach(function (table) {
      var rows = table.querySelectorAll("tbody tr").length;
      var heads = table.querySelectorAll("thead th, thead td, tr:first-child th").length;
      var rect = table.getBoundingClientRect();
      var score = rows * 10 + heads + Math.round(rect.width / 100);
      if (score > bestScore) {
        bestScore = score;
        best = table;
      }
    });

    return best;
  }

  function findScrollPane(table) {
    if (!table) {
      return null;
    }

    var node = table.parentElement;
    var chosen = node;

    while (node && node !== document.body && node !== document.documentElement) {
      var rect = node.getBoundingClientRect();
      var style = window.getComputedStyle(node);
      var hasUsefulBox = rect.width > 300 && rect.height > 80;
      var hasBorderOrRadius = style.borderTopWidth !== "0px" || style.borderRadius !== "0px";
      if (hasUsefulBox && hasBorderOrRadius) {
        chosen = node;
        break;
      }
      chosen = node;
      node = node.parentElement;
    }

    return chosen || table.parentElement;
  }

  function ensureCssLoaded() {
    var href = "catalog-ui-freeze-full-top.css";
    var found = Array.prototype.slice.call(document.querySelectorAll('link[rel="stylesheet"]'))
      .some(function (link) { return (link.getAttribute("href") || "").indexOf(href) !== -1; });
    if (!found) {
      var link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = href;
      document.head.appendChild(link);
    }
  }

  function lockVclBanner() {
    var banner = findVclBanner();
    if (!banner) {
      document.documentElement.style.setProperty("--catalog-vcl-banner-height", "0px");
      return 0;
    }

    banner.classList.add("catalog-vcl-fixed-top");

    var height = Math.ceil(banner.getBoundingClientRect().height || 0);
    if (height < 1) {
      height = Math.ceil(banner.scrollHeight || 0);
    }

    document.documentElement.style.setProperty("--catalog-vcl-banner-height", height + "px");
    return height;
  }

  function hasHeader(table) {
    if (!table) {
      return false;
    }
    return !!(table.querySelector("thead th, thead td, tr:first-child th"));
  }

  function ensureThead(table) {
    if (!table || table.tHead || !table.rows || !table.rows.length) {
      return;
    }

    var first = table.rows[0];
    if (!first || !first.querySelector("th")) {
      return;
    }

    var thead = document.createElement("thead");
    table.insertBefore(thead, table.firstChild);
    thead.appendChild(first);
  }

  function lockTablePane() {
    var table = findPrimaryTable();
    if (!table) {
      return false;
    }

    ensureThead(table);
    if (!hasHeader(table)) {
      return false;
    }

    var pane = findScrollPane(table);
    if (!pane) {
      return false;
    }

    document.documentElement.classList.add("catalog-freeze-full-top");
    table.classList.add("catalog-sticky-real-header-table");
    pane.classList.add("catalog-table-scrollpane-lock");

    var rect = pane.getBoundingClientRect();
    var top = Math.max(0, Math.ceil(rect.top));

    // A too-small top usually means layout has not settled yet. Recompute shortly.
    if (top < 10 && STATE.attempts < 20) {
      return false;
    }

    STATE.lastTop = top;
    pane.style.setProperty("--catalog-table-scrollpane-top", top + "px");
    pane.style.height = "calc(100vh - " + top + "px - 12px)";
    pane.style.maxHeight = "calc(100vh - " + top + "px - 12px)";
    pane.style.overflow = "auto";
    pane.style.position = "relative";

    var headerCells = table.querySelectorAll("thead th, thead td");
    Array.prototype.forEach.call(headerCells, function (cell) {
      cell.style.position = "sticky";
      cell.style.top = "0px";
      cell.style.zIndex = "1000";
    });

    return true;
  }

  function apply() {
    STATE.attempts += 1;
    ensureCssLoaded();
    lockVclBanner();
    return lockTablePane();
  }

  function scheduleApply() {
    window.requestAnimationFrame(function () {
      try {
        apply();
      } catch (err) {
        console.warn("catalog full-top freeze failed", err);
      }
    });
  }

  function boot() {
    if (STATE.initialized) {
      return;
    }
    STATE.initialized = true;

    var timer = window.setInterval(function () {
      var ok = apply();
      if (ok || STATE.attempts > 60) {
        window.clearInterval(timer);
      }
    }, 100);

    window.addEventListener("resize", scheduleApply);
    window.addEventListener("orientationchange", scheduleApply);

    var observer = new MutationObserver(function () {
      scheduleApply();
    });
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();