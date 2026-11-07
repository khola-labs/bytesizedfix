/* Byte-Sized Fix course hub: progress (localStorage), filters, click-to-load video.
   No tracking, no cookies, no dependencies. Everything degrades gracefully. */
(function () {
  "use strict";
  var KEY = "bsf-course-progress-v1";
  var mem = {};          // fallback store when localStorage is unavailable
  var persistent = true;

  function load() {
    try {
      var raw = window.localStorage.getItem(KEY);
      mem = raw ? JSON.parse(raw) || {} : {};
    } catch (e) { persistent = false; }
  }
  function save() {
    if (!persistent) return;
    try { window.localStorage.setItem(KEY, JSON.stringify(mem)); }
    catch (e) { persistent = false; showStorageNote(); }
  }
  function isDone(k) { return mem[k] === 1; }
  function setDone(k, v) { if (v) mem[k] = 1; else delete mem[k]; save(); }

  function showStorageNote() {
    document.querySelectorAll("[data-storage-note]").forEach(function (el) { el.hidden = false; });
  }

  function refreshMeters() {
    document.querySelectorAll("[data-meter]").forEach(function (el) {
      var ids = (el.getAttribute("data-meter") || "").split(" ").filter(Boolean);
      var n = 0;
      ids.forEach(function (id) { if (isDone("L:" + id)) n++; });
      var pct = ids.length ? Math.round((n / ids.length) * 100) : 0;
      var bar = el.querySelector(".meter > span");
      var label = el.querySelector("[data-meter-label]");
      var meter = el.querySelector(".meter");
      if (bar) bar.style.width = pct + "%";
      if (meter) { meter.setAttribute("aria-valuenow", String(n)); meter.setAttribute("aria-valuetext", n + " of " + ids.length + " lessons done"); }
      if (label) label.textContent = n + " / " + ids.length + " lessons done (" + pct + "%)";
    });
    document.querySelectorAll("[data-pmeter]").forEach(function (el) {
      var boxes = document.querySelectorAll("input[data-progress^='P:" + el.getAttribute("data-pmeter") + "|']");
      var n = 0;
      boxes.forEach(function (b) { if (b.checked) n++; });
      el.textContent = n + " / " + boxes.length + " solved";
    });
  }

  function wireChecks() {
    document.querySelectorAll("input[data-progress]").forEach(function (box) {
      var k = box.getAttribute("data-progress");
      box.checked = isDone(k);
      mark(box);
      box.addEventListener("change", function () {
        setDone(k, box.checked);
        // keep duplicates of the same key on one page in sync
        document.querySelectorAll("input[data-progress]").forEach(function (o) {
          if (o !== box && o.getAttribute("data-progress") === k) { o.checked = box.checked; mark(o); }
        });
        mark(box);
        refreshMeters();
        if (typeof applyFilters === "function") applyFilters();
      });
    });
  }
  function mark(box) {
    var row = box.closest("[data-row]");
    if (row) row.classList.toggle("done", box.checked);
  }

  function wireReset() {
    var btn = document.getElementById("reset-progress");
    if (!btn) return;
    btn.hidden = false;
    btn.addEventListener("click", function () {
      if (!window.confirm("Clear all your ticked lessons and problems on this device?")) return;
      mem = {}; save();
      document.querySelectorAll("input[data-progress]").forEach(function (b) { b.checked = false; mark(b); });
      refreshMeters();
    });
  }

  /* Catalogue filters (lessons.html) */
  var applyFilters = null;
  function wireFilters() {
    var form = document.getElementById("filters");
    if (!form) return;
    var q = document.getElementById("f-q"), tr = document.getElementById("f-track"),
        mo = document.getElementById("f-module"), st = document.getElementById("f-status"),
        count = document.getElementById("count");
    var rows = Array.prototype.slice.call(document.querySelectorAll("[data-lesson]"));
    var groups = Array.prototype.slice.call(document.querySelectorAll("[data-group]"));
    var params = new URLSearchParams(window.location.search);
    if (params.get("q")) q.value = params.get("q");
    if (params.get("track")) tr.value = params.get("track");
    if (params.get("module")) mo.value = params.get("module");

    function syncModules() {
      Array.prototype.forEach.call(mo.options, function (o) {
        var t = o.getAttribute("data-track");
        o.hidden = !!(t && tr.value && t !== tr.value);
        o.disabled = o.hidden;
      });
      var sel = mo.options[mo.selectedIndex];
      if (sel && sel.disabled) mo.value = "";
    }
    applyFilters = function () {
      var terms = q.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
      var shown = 0;
      rows.forEach(function (r) {
        var hay = r.getAttribute("data-search");
        var ok = (!tr.value || r.getAttribute("data-track") === tr.value) &&
                 (!mo.value || r.getAttribute("data-module") === mo.value) &&
                 terms.every(function (t) { return hay.indexOf(t) !== -1; });
        if (ok && st.value) {
          var id = r.getAttribute("data-lesson");
          if (st.value === "out") ok = r.getAttribute("data-out") === "1";
          else if (st.value === "coming") ok = r.getAttribute("data-out") !== "1";
          else if (st.value === "todo") ok = !isDone("L:" + id);
          else if (st.value === "done") ok = isDone("L:" + id);
        }
        r.hidden = !ok;
        if (ok) shown++;
      });
      groups.forEach(function (g) { g.hidden = !g.querySelector("[data-lesson]:not([hidden])"); });
      count.textContent = shown === 1 ? "1 lesson" : shown + " lessons";
      var p = new URLSearchParams();
      if (q.value.trim()) p.set("q", q.value.trim());
      if (tr.value) p.set("track", tr.value);
      if (mo.value) p.set("module", mo.value);
      try { history.replaceState(null, "", p.toString() ? "?" + p.toString() : window.location.pathname); } catch (e) {}
    };
    form.addEventListener("submit", function (e) { e.preventDefault(); applyFilters(); });
    q.addEventListener("input", applyFilters);
    tr.addEventListener("change", function () { syncModules(); applyFilters(); });
    mo.addEventListener("change", applyFilters);
    st.addEventListener("change", applyFilters);
    syncModules();
    applyFilters();
  }

  /* Click-to-load YouTube (privacy-enhanced domain; nothing loads until the visitor asks) */
  function wireVideos() {
    document.querySelectorAll("button[data-yt]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-yt");
        var f = document.createElement("iframe");
        f.src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(id) + "?autoplay=1&rel=0";
        f.title = btn.getAttribute("data-title") || "YouTube video";
        f.allow = "accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture; fullscreen";
        f.allowFullscreen = true;
        f.referrerPolicy = "strict-origin-when-cross-origin";
        btn.parentNode.replaceChild(f, btn);
        f.focus();
      });
    });
  }

  load();
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".js-only").forEach(function (el) { el.hidden = false; });
    if (!persistent) showStorageNote();
    wireChecks();
    wireFilters();
    wireReset();
    wireVideos();
    refreshMeters();
  });
})();
