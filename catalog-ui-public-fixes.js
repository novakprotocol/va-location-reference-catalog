(function () {
  "use strict";

  function textHasVcl(node) {
    if (!node || !node.textContent) return false;
    return node.textContent.indexOf("Veterans Crisis Line") !== -1;
  }

  function removeOldVclBanners() {
    var candidates = Array.prototype.slice.call(document.body.querySelectorAll("div, header, section, aside"));
    candidates.forEach(function (el) {
      if (el.id === "vcl-fixed-banner") return;
      if (!textHasVcl(el)) return;

      var text = (el.textContent || "").trim();
      if (text.length > 0 && text.length < 500) {
        el.remove();
      }
    });
  }

  function ensureVclBanner() {
    removeOldVclBanners();

    var banner = document.getElementById("vcl-fixed-banner");
    if (!banner) {
      banner = document.createElement("div");
      banner.id = "vcl-fixed-banner";
      banner.setAttribute("role", "banner");
      banner.setAttribute("aria-label", "Veterans Crisis Line");
      banner.innerHTML =
        '<strong>Veterans Crisis Line:</strong> Call <a href="tel:988">988</a> then press 1 | ' +
        'Text <a href="sms:838255">838255</a> | Chat <a href="https://www.veteranscrisisline.net/" rel="noopener">VeteransCrisisLine.net</a> | ' +
        'TTY <a href="tel:18007994889">1-800-799-4889</a>' +
        '<span class="vcl-subline">Public-site safety notice. Remove this banner for internal-only deployments where the public emergency-resource banner is not required.</span>';
      document.body.insertBefore(banner, document.body.firstChild);
    }
    measureVclBanner();
  }

  function measureVclBanner() {
    var banner = document.getElementById("vcl-fixed-banner");
    var h = banner ? Math.ceil(banner.getBoundingClientRect().height) : 0;
    if (!h || h < 34) h = 44;
    document.documentElement.style.setProperty("--vcl-fixed-banner-height", h + "px");
    document.documentElement.style.setProperty("--catalog-sticky-header-top", h + "px");
    document.body.style.paddingTop = h + "px";
  }

  function repairTables() {
    var tables = Array.prototype.slice.call(document.querySelectorAll("table"));
    tables.forEach(function (table) {
      var thead = table.querySelector("thead");
      if (thead && table.firstElementChild !== thead) {
        table.insertBefore(thead, table.firstElementChild);
      }

      if (!thead) return;
      Array.prototype.slice.call(thead.querySelectorAll("th")).forEach(function (th) {
        th.setAttribute("scope", th.getAttribute("scope") || "col");
      });
    });
  }

  function addDayBoxes() {
    var days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
    var selectors = [
      ".hours-candidate",
      ".hours-candidates",
      "[data-hours-candidate]",
      "td",
      "li",
      "p"
    ];

    var nodes = [];
    selectors.forEach(function (sel) {
      Array.prototype.slice.call(document.querySelectorAll(sel)).forEach(function (n) {
        if (nodes.indexOf(n) === -1) nodes.push(n);
      });
    });

    nodes.forEach(function (node) {
      if (node.querySelector && node.querySelector(".hours-day-boxes, .hours-247-badge")) return;

      var text = (node.textContent || "").toLowerCase();
      if (!text) return;
      if (
        text.indexOf("hours") === -1 &&
        text.indexOf("open daily") === -1 &&
        text.indexOf("monday") === -1 &&
        text.indexOf("tuesday") === -1 &&
        text.indexOf("wednesday") === -1 &&
        text.indexOf("thursday") === -1 &&
        text.indexOf("friday") === -1 &&
        text.indexOf("saturday") === -1 &&
        text.indexOf("sunday") === -1 &&
        text.indexOf("24/7") === -1 &&
        text.indexOf("24 hours") === -1
      ) return;

      if (text.indexOf("24/7") !== -1 || text.indexOf("24 hours") !== -1 || text.indexOf("24-hour") !== -1) {
        var badge = document.createElement("span");
        badge.className = "hours-247-badge";
        badge.textContent = "24/7";
        node.appendChild(document.createTextNode(" "));
        node.appendChild(badge);
        return;
      }

      var open = {};
      if (text.indexOf("open daily") !== -1 || text.indexOf("daily from") !== -1) {
        days.forEach(function (d) { open[d] = true; });
      }
      if (text.indexOf("monday") !== -1 || text.indexOf("mon") !== -1) open.MON = true;
      if (text.indexOf("tuesday") !== -1 || text.indexOf("tue") !== -1) open.TUE = true;
      if (text.indexOf("wednesday") !== -1 || text.indexOf("wed") !== -1) open.WED = true;
      if (text.indexOf("thursday") !== -1 || text.indexOf("thu") !== -1) open.THU = true;
      if (text.indexOf("friday") !== -1 || text.indexOf("fri") !== -1) open.FRI = true;
      if (text.indexOf("saturday") !== -1 || text.indexOf("sat") !== -1) open.SAT = true;
      if (text.indexOf("sunday") !== -1 || text.indexOf("sun") !== -1) open.SUN = true;
      if (text.indexOf("monday through friday") !== -1 || text.indexOf("monday thru friday") !== -1 || text.indexOf("mon-fri") !== -1 || text.indexOf("mon through fri") !== -1) {
        ["MON", "TUE", "WED", "THU", "FRI"].forEach(function (d) { open[d] = true; });
      }

      var any = Object.keys(open).length > 0;
      if (!any) return;

      var wrap = document.createElement("div");
      wrap.className = "hours-day-boxes";
      days.forEach(function (d) {
        var b = document.createElement("span");
        b.className = "hours-day-box " + (open[d] ? "open" : "closed");
        b.textContent = d;
        wrap.appendChild(b);
      });
      node.appendChild(wrap);
    });
  }

  function init() {
    ensureVclBanner();
    repairTables();
    addDayBoxes();
    window.addEventListener("resize", measureVclBanner);
    setTimeout(measureVclBanner, 250);
    setTimeout(repairTables, 250);
    setTimeout(addDayBoxes, 500);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();