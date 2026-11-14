/* Clickable prototype. All data comes from data.js (generated from the fictional
   sample and from real engine output). State lives in the URL hash so every
   screen can be linked to. */
(function () {
  "use strict";
  var D = window.SSA_DATA;
  var view = document.getElementById("view");
  var drawer = document.getElementById("drawer");
  var drawerBody = document.getElementById("drawer-body");
  var scrim = document.getElementById("scrim");
  var portName = {};
  D.ports.forEach(function (p) { portName[p.code] = p.name; });
  var rowById = {};
  D.rows.forEach(function (r) { rowById[r.sailing_id] = r; });
  var faqById = {};
  D.faq.forEach(function (f) { faqById[f.id] = f; });
  document.getElementById("asof").textContent = D.meta.as_of;

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function port(code) { return esc(portName[code]) + " (" + esc(code) + ")"; }
  function parseHash() {
    var h = location.hash.replace(/^#\/?/, "") || "search";
    var bits = h.split("?");
    var params = {};
    (bits[1] || "").split("&").forEach(function (kv) {
      if (!kv) { return; }
      var i = kv.indexOf("=");
      params[decodeURIComponent(kv.slice(0, i))] = decodeURIComponent(kv.slice(i + 1));
    });
    return { path: bits[0].split("/"), params: params };
  }
  function setNav(name) {
    document.querySelectorAll("nav a").forEach(function (a) {
      a.classList.toggle("active", a.getAttribute("data-nav") === name);
    });
  }

  /* ---------- schedule search ---------- */
  function options(list, selected, value, label) {
    return list.map(function (x, i) {
      var v = value(x, i);
      return '<option value="' + esc(v) + '"' + (String(v) === String(selected) ? " selected" : "") +
        ">" + esc(label(x)) + "</option>";
    }).join("");
  }
  function renderSearch(q) {
    setNav("search");
    var o = q.o || "SGSIN", d = q.d || "NLRTM", w = q.w || "0", direct = q.direct === "1";
    var win = D.windows[Number(w)] || D.windows[0];
    var rows = D.rows.filter(function (r) {
      return r.origin_code === o && r.dest_code === d && r.etd >= win.from && r.etd <= win.to &&
        r.etd >= D.meta.as_of && (!direct || r.routing === "direct");
    });
    var html = "<h1>Find sailings</h1><p class='sub'>Point-to-point search over the fictional sample schedule.</p>" +
      "<form class='card' id='search-form'><div class='form'>" +
      "<div><label for='o'>From</label><select id='o'>" + options(D.ports, o, function (p) { return p.code; }, function (p) { return p.name + " (" + p.code + ")"; }) + "</select></div>" +
      "<div><label for='d'>To</label><select id='d'>" + options(D.ports, d, function (p) { return p.code; }, function (p) { return p.name + " (" + p.code + ")"; }) + "</select></div>" +
      "<div><label for='w'>Departure</label><select id='w'>" + options(D.windows, w, function (x, i) { return i; }, function (x) { return x.label; }) + "</select></div>" +
      "<div><button type='submit'>Search</button></div></div>" +
      "<label class='check'><input type='checkbox' id='direct'" + (direct ? " checked" : "") + "> Direct sailings only</label></form>";
    html += "<p class='small' id='result-count'>" + rows.length + " sailing(s) from " + port(o) + " to " + port(d) + " &middot; " + esc(win.label) + "</p>";
    if (!rows.length) {
      html += "<div class='card empty' id='no-results'>No sailing in the sample schedule matches this search. " +
        "Nothing is estimated or guessed. <a href='#/ask'>Ask a question instead</a></div>";
    }
    rows.forEach(function (r) {
      var ts = r.routing !== "direct";
      html += "<a class='card result' href='#/sailing/" + esc(r.sailing_id) + "'>" +
        "<div><div class='when'>ETD " + esc(r.etd) + "</div><div class='small'>ETA " + esc(r.eta) + "</div></div>" +
        "<div><div class='route'><span>" + esc(r.origin_code) + "</span><span class='bar" + (ts ? " ts" : "") + "'></span><span>" + esc(r.dest_code) + "</span></div>" +
        "<div class='small'>" + esc(r.carrier) + " &middot; " + esc(r.vessel) + " " + esc(r.voyage) + "</div></div>" +
        "<div><strong>" + esc(r.transit_days) + " days</strong><br><span class='pill" + (ts ? " ts" : "") + "'>" +
        (ts ? "via " + esc(portName[r.via_code]) : "direct") + "</span></div>" +
        "<div class='small'>CY cut-off<br>" + esc(r.cy_cutoff) + "</div></a>";
    });
    view.innerHTML = html;
    document.getElementById("search-form").addEventListener("submit", function (e) {
      e.preventDefault();
      location.hash = "#/search?o=" + document.getElementById("o").value + "&d=" + document.getElementById("d").value +
        "&w=" + document.getElementById("w").value + "&direct=" + (document.getElementById("direct").checked ? "1" : "0");
    });
  }

  /* ---------- sailing detail ---------- */
  function renderSailing(id) {
    setNav("search");
    var r = rowById[id];
    if (!r) {
      view.innerHTML = "<div class='card empty'>No sailing " + esc(id) + " in the sample schedule. <a href='#/search'>Back to search</a></div>";
      return;
    }
    var ts = r.routing !== "direct";
    view.innerHTML = "<p><a href='#/search?o=" + esc(r.origin_code) + "&d=" + esc(r.dest_code) + "'>&larr; Back to results</a></p>" +
      "<h1>" + port(r.origin_code) + " to " + port(r.dest_code) + "</h1>" +
      "<p class='sub'>" + esc(r.sailing_id) + " &middot; " + esc(r.carrier) + " &middot; " + esc(r.vessel) + " " + esc(r.voyage) + " &middot; service " + esc(r.service) + "</p>" +
      "<div class='grid2'><div class='card'><h2>Deadlines and voyage</h2><ul class='timeline' id='timeline'>" +
      [["Documentation cut-off", r.doc_cutoff], ["VGM cut-off", r.vgm_cutoff], ["CY cut-off", r.cy_cutoff]]
        .sort(function (a, b) { return a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0; })
        .map(function (x) { return "<li><span>" + x[0] + "</span><strong>" + esc(x[1]) + "</strong></li>"; }).join("") +
      "<li class='dep'><span>Departure (ETD)</span><strong>" + esc(r.etd) + " " + esc(portName[r.origin_code]) + "</strong></li>" +
      (ts ? "<li><span>Transshipment</span><strong>" + port(r.via_code) + "</strong></li>" : "") +
      "<li class='arr'><span>Arrival (ETA)</span><strong>" + esc(r.eta) + " " + esc(portName[r.dest_code]) + "</strong></li></ul>" +
      "<p class='small'>Deadlines are shown in time order. Cut-offs are local time at the origin port.</p></div>" +
      "<div class='card'><h2>Summary</h2><dl class='kv' style='margin-top:10px'>" +
      "<dt>Transit time</dt><dd>" + esc(r.transit_days) + " days</dd>" +
      "<dt>Routing</dt><dd><span class='pill" + (ts ? " ts" : "") + "'>" + (ts ? "transshipment" : "direct") + "</span></dd>" +
      "<dt>Data status</dt><dd>Fictional sample, as of " + esc(D.meta.as_of) + "</dd></dl>" +
      "<p style='margin-top:14px'><button class='ghost' id='show-source'>Show source record</button></p>" +
      "<p class='small'>Booking is out of scope for this prototype: the next step would hand over to the carrier's booking channel.</p>" +
      "<p><a href='#/ask'>Ask a question about schedules or documents</a></p></div></div>";
    document.getElementById("show-source").addEventListener("click", function () { openDrawer([r.sailing_id], r.sailing_id, null); });
  }

  /* ---------- ask a question ---------- */
  function partHtml(p, exIndex) {
    var text = esc(p.text).replace(/\[(DL-\d{4}|FAQ-\d{2})\]/g, function (_m, id) {
      return "<button class='cite' data-ex='" + exIndex + "' data-id='" + id + "' title='Show the source record'>" + id + "</button>";
    });
    var label = p.op === "refuse" ? "<span class='label refuse'>Not answered &middot; " + esc(p.reason.replace(/_/g, " ")) + "</span>"
      : "<span class='label ok'>Answered from " + p.ids.length + " retrieved record(s)</span>";
    return "<div class='part'>" + label + "\n" + text + "</div>";
  }
  function renderAsk(q) {
    setNav("ask");
    var html = "<h1>Ask a question</h1><p class='sub'>Answers are built only from retrieved sample records and the FAQ, with citations. " +
      "If the data is missing or the question is out of scope, the assistant says so.</p>" +
      "<div class='card'><div class='label'>Try one of these</div><div class='chips'>" +
      D.examples.map(function (ex, i) { return "<button class='chip' data-q='" + i + "'>" + esc(ex.q) + "</button>"; }).join("") +
      "</div><div class='chat' id='chat'>";
    var ex = D.examples[Number(q.q)];
    if (q.q !== undefined && ex) {
      html += "<div class='msg user'>" + esc(ex.q) + "</div>" +
        "<div class='msg bot" + (ex.refused ? " refused" : "") + "' id='answer'>" +
        ex.parts.map(function (p) { return partHtml(p, q.q); }).join("") +
        "<div class='meta'>" + (ex.refused ? "" : "<button class='ghost small' id='why' data-ex='" + q.q + "'>Show the source of this answer</button>") +
        "<button class='ghost small' data-fb='up'>Helpful</button><button class='ghost small' data-fb='down'>Not helpful</button>" +
        "<span id='fb-note'></span></div><div class='meta'>" + esc(ex.notice) + "</div></div>";
    } else if (q.free) {
      html += "<div class='msg user'>" + esc(q.free) + "</div><div class='msg bot refused' id='answer'>" +
        "<span class='label refuse'>Prototype limit</span>\nThis static prototype only replays the sample questions above. " +
        "Free-text questions are answered by the working demo: python scripts/ask.py \"your question\"</div>";
    }
    html += "</div><form class='askbar' id='ask-form'><input type='text' id='ask-input' placeholder='Type a question about sailings, cut-offs or documents' aria-label='Question'>" +
      "<button type='submit'>Ask</button></form></div>";
    view.innerHTML = html;
    view.querySelectorAll(".chip").forEach(function (b) {
      b.addEventListener("click", function () { location.hash = "#/ask?q=" + b.getAttribute("data-q"); });
    });
    view.querySelectorAll(".cite").forEach(function (b) {
      b.addEventListener("click", function () { openSource(Number(b.getAttribute("data-ex")), b.getAttribute("data-id")); });
    });
    var why = document.getElementById("why");
    if (why) { why.addEventListener("click", function () { openSource(Number(why.getAttribute("data-ex")), null); }); }
    view.querySelectorAll("[data-fb]").forEach(function (b) {
      b.addEventListener("click", function () {
        document.getElementById("fb-note").textContent = "Feedback recorded (prototype only: nothing is sent).";
      });
    });
    document.getElementById("ask-form").addEventListener("submit", function (e) {
      e.preventDefault();
      var text = document.getElementById("ask-input").value.trim();
      if (!text) { return; }
      var hit = -1;
      D.examples.forEach(function (x, i) { if (x.q.toLowerCase() === text.toLowerCase()) { hit = i; } });
      location.hash = hit >= 0 ? "#/ask?q=" + hit : "#/ask?free=" + encodeURIComponent(text);
    });
    if (q.src !== undefined && ex) { openSource(Number(q.q), q.src || null); }
  }

  /* ---------- source drawer ---------- */
  function openSource(exIndex, focusId) {
    var ex = D.examples[exIndex];
    var ids = [];
    ex.parts.forEach(function (p) { ids = ids.concat(p.ids); });
    openDrawer(ids, focusId, ex.parts.map(function (p) { return p.query; }));
  }
  function openDrawer(ids, focusId, queries) {
    var html = "<p class='small'>Every date, number and port in the answer is checked against these records before it is shown. " +
      "Source file: fictional sample schedule and authored FAQ, as of " + esc(D.meta.as_of) + ".</p>";
    if (queries) {
      html += "<div class='label'>How the question was read</div><pre id='query'>" + esc(JSON.stringify(queries, null, 1)) + "</pre>";
    }
    html += "<div class='label'>Retrieved records (" + ids.length + ")</div>";
    ids.forEach(function (id) {
      var rec = rowById[id] || faqById[id];
      html += "<div class='record" + (id === focusId ? " hit" : "") + "' data-rec='" + esc(id) + "'><h3>" + esc(id) + "</h3>";
      if (rowById[id]) {
        html += "<dl class='kv'>" + Object.keys(rec).map(function (k) {
          return "<dt>" + esc(k) + "</dt><dd>" + esc(rec[k] === "" ? "-" : rec[k]) + "</dd>";
        }).join("") + "</dl><p><a href='#/sailing/" + esc(id) + "'>Open sailing detail</a></p>";
      } else {
        html += "<p><strong>" + esc(rec.topic) + "</strong></p><p>" + esc(rec.answer) + "</p>";
      }
      html += "</div>";
    });
    drawerBody.innerHTML = html;
    drawer.classList.add("open");
    scrim.classList.add("open");
    drawer.setAttribute("aria-hidden", "false");
    var hit = drawerBody.querySelector(".record.hit");
    if (hit && hit.scrollIntoView) { hit.scrollIntoView({ block: "nearest" }); }
  }
  function closeDrawer() {
    drawer.classList.remove("open");
    scrim.classList.remove("open");
    drawer.setAttribute("aria-hidden", "true");
  }
  document.getElementById("drawer-close").addEventListener("click", closeDrawer);
  scrim.addEventListener("click", closeDrawer);

  function route() {
    closeDrawer();
    var r = parseHash();
    if (r.path[0] === "sailing") { renderSailing(r.path[1]); }
    else if (r.path[0] === "ask") { renderAsk(r.params); }
    else { renderSearch(r.params); }
    window.scrollTo(0, 0);
  }
  window.addEventListener("hashchange", route);
  route();
})();
