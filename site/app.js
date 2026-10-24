/*
 * The logic of index.html: the map and its seven views, the guided tour, route cards with
 * their shorter paths and overlaps, reach from a stop, the data issues and the checklist
 * tables. Everything shown comes from site/data.js, which site/build.py writes from
 * output/. Text that comes from the data (stop names, carriers) goes into the page with
 * textContent only.
 */
(function () {
  "use strict";

  var D = window.SITE_DATA;
  var S = D.summary;
  S.uncovered = S.population - S.covered;

  // ---------------------------------------------------------------- text

  var T = {
    million: "million",
    routeN: "Route {n}",
    noMatch: "No route or stop matches.",
    stopsFound: "Stops",
    routesHere: "Routes here",
    stopRoutes: "{n} routes stop here",
    stopRoute: "1 route stops here",
    scrollHint: "Click the map first to zoom with the wheel",
    close: "Close",
    copyLink: "Copy link",
    copied: "Copied",
    show: "On map",
    open: "Open",
    compare: "Compare",
    shapes: { direct: "Direct", indirect: "Indirect", "very indirect": "Very indirect", loop: "Loop" },
    ranges: { direct: "at most 1.4 times the straight line", indirect: "1.4 to 2 times", "very indirect": "2 to 3 times", loop: "over 3 times, or ends close together" },
    routesCount: "{n} routes",
    stopsCount: "{n} stops",
    views: {
      directness: {
        name: "Directness",
        text: "Each route is coloured by how many times longer its path is than the straight line between its end stops (the more roundabout of its two directions). Darker means more roundabout.",
        fact: "Together the routes run {route_km} km of route over only {street_km} km of distinct links between stops: {per_link} routes on each link on average."
      },
      detours: {
        name: "Detours",
        text: "Stretches where the bus travels at least 2.5 times the straight line between two of its stops, and at least 1.5 km more. Hover a detour: the dashed line is the straight way, the green one a path along streets buses already use.",
        fact: "Together the detours add {km} km to one trip each way on every route. {with} of them have a path along today's bus streets at least 0.5 km shorter. The longest is on route {route}: about {minutes} minutes per trip.",
        nobody: "Everyone inside has another route within 400 m",
        some: "Some residents are reached only by this route",
        fix: "Shorter path along streets buses already use"
      },
      duplication: {
        name: "Overlap",
        text: "At least 85% of the stops of each orange route are also served by another route (express routes are left out). Blue routes are the ones that contain them. Open a route and press Compare to see the shared stops.",
        fact: "There are {pairs} such pairs; in {two} of them the two routes have different carriers.",
        inside: "Mostly inside another route",
        host: "Contains such a route"
      },
      corridors: {
        name: "Corridors",
        text: "Stretches of at least 1 km where every link between stops carries 8 or more routes. Line width shows the average number of routes per link.",
        fact: "The most routes on a single link: {max}.",
        width: "{n} routes per link"
      },
      coverage: {
        name: "Coverage",
        text: "Residents who live more than {radius} m in a straight line from the nearest stop, per hexagon (about 0.74 km²). The darker the hexagon, the more such residents.",
        fact: "{covered} of {population} residents ({share}) live within {radius} m of a stop. Population: Kontur, November 2023.",
        legend: "Such residents per hexagon",
        bins: ["fewer than 100", "100 to 500", "500 to 2,000", "more than 2,000"],
        people: "{n} residents"
      },
      spacing: {
        name: "Stop spacing",
        text: "Orange stops are less than {gap} m along the route from a neighbouring stop on every route that uses them, and removing them would leave no gap longer than {max} m. Terminals and interchange hubs are kept.",
        close: "Could go",
        other: "Other stops",
        fact: "Removing all {n} would take {visits} stops off one trip each way on every route: about {hours} hours of running time at an assumed {loss} seconds per stop. {lost} residents would no longer have a stop within {radius} m."
      },
      reach: {
        name: "Reach",
        text: "Click any stop, or search for one, to see how far its buses go. Until then, stops are coloured by how many routes serve them.",
        legend: "Routes serving each stop",
        bins: ["1 route", "2 or 3", "4 to 7", "8 or more"],
        fact: "The best-served stop, {name}, has {n} routes; {single} stops have only one.",
        title: "From {stop}",
        routes: "Routes that stop here",
        none: "Without changing buses",
        noneNote: "on the routes that stop here",
        one: "With one change",
        oneNote: "walking up to {walk} m between stops",
        of: "{n} stops",
        share: "{p} of all {total}",
        keys: ["Reachable without changing", "With one change", "Out of reach with one change"],
        clear: "Pick another stop"
      }
    },
    tip: {
      detour: "+{min} min per trip · {km} km extra",
      alt: "a path along bus streets is {km} km shorter",
      corridor: "{mean} routes per link on average · {km} km",
      hex: "{n} residents farther than {radius} m",
      inside: "{share} of its stops are on route {r}",
      gap: "{gap} m to its nearest neighbour · could go"
    },
    popup: {
      hex: "{n} residents live more than {radius} m from the nearest stop.",
      hexTotal: "{n} residents live in this hexagon.",
      corridor: "{km} km · {stops} stops · {mean} routes per link on average, {max} at most",
      corridorRoutes: "Routes on this corridor:",
      gap: "{gap} m along the route from its nearest neighbour; it could go without leaving a gap over {max} m.",
      reach: "Show its reach"
    },
    card: {
      shape: "Its path is {x} times the straight line between its end stops.",
      loop: "Its ends are less than 1 km apart, or its path is more than 3 times the straight line.",
      measures: "Measurements",
      length: "Length, one way",
      stops: "Stops",
      stopsValue: "{a} and {b}",
      spacing: "Stop spacing, median",
      short: "Gaps under 200 m",
      shared: "Path shared with other routes",
      residents: "Residents within {radius} m",
      only: "Residents only this route reaches",
      boardings: "Weekday boardings per day",
      boardingsNote: "BakuBus, {month}",
      notPublished: "Not published",
      notPublishedNote: "only BakuBus publishes counts",
      closeStops: "Stops that could go",
      closeNote: "orange on the map",
      detours: "Detours",
      noDetours: "This route has no detours.",
      detourMeta: "+{min} min per trip (estimate) · {km} km extra",
      nobody: "everyone inside has another route",
      some: "{n} residents reached only by this route",
      alt: "Shorter path: {km} km instead of {along} km, about {min} min less per trip (estimate), skipping {dropped} stops",
      altNone: "No path along today's bus streets is 0.5 km shorter.",
      overlap: "Overlap",
      inside: "Most of its stops are also served by:",
      contains: "It contains most of the stops of:",
      noOverlap: "No other route serves 85% of its stops.",
      compareNote: "Orange stops are on both routes: {shared} of its {n}.",
      fixes: "In the map data",
      straight: "Direction {d} has no usable line on the map; here its stops are joined by straight lines.",
      direction: "Direction {d}"
    },
    fix: {
      wrong_direction: "A direction's line is stored under the other direction",
      backwards: "The line of direction {d} is stored backwards",
      swapped: "The line of direction {d} has latitude and longitude swapped",
      lat_equals_lon: "The line of direction {d} has latitude equal to longitude",
      scrambled: "The line of direction {d} does not follow the order of its stops",
      far: "The line of direction {d} lies far from its stops",
      repeated_stops: "The stop list of direction {d} is repeated twice",
      no_shape: "The route has no line"
    },
    groups: { lines: "Route lines", table: "Route table", stops: "Stops", fresh: "Up to date" },
    units: { routes: "routes", directions: "directions", names: "names", stops: "stops", changes: "changes", of: "/ {n}" },
    issues: {
      wrong_direction: ["Lines under the wrong direction", "A direction's line is stored under the other direction, so a map showing one direction draws the other one's streets."],
      backwards: ["Line stored backwards", "The line's points run from the last stop to the first, while the stops run from the first to the last."],
      swapped: ["Latitude and longitude swapped", "This line is drawn more than a thousand kilometres from Baku."],
      lat_equals_lon: ["Latitude equal to longitude", "Both coordinates are the same at every point, so the line is unusable."],
      scrambled: ["Line does not follow the stops", "The line has straight jumps of {min} to {max} km; this page draws those directions with straight lines between stops."],
      far: ["Line far from the stops", "The line lies far from the route's stops."],
      repeated_stops: ["Stop list repeated", "The list of stops is written out twice in a row."],
      other: ["Other defect", "Another defect from the list of automatic repairs."],
      no_shape: ["No line", "The route has stops but no line; this page draws it with straight lines between stops."],
      no_stops: ["Routes without stops", "These routes are listed, but have no stops and no line."],
      cutoff: " 150A and 446 connect Pirallahı with the city, so route 180 looks cut off on the map.",
      length: ["route_length_km is the round trip", "The field is a median {x} times the one-way line, so it is the round-trip length. Its name or description should say so."],
      duration: ["duration_min is not a real time", "On all {n} routes the field equals floor(route_length_km / 0.6): a fixed 36 km/h over the round trip."],
      api: ["One route does not come through", "For one of its 209 route ids (id 96, route 144) the API returns an error instead of data."],
      cyrillic: ["Names with Cyrillic letters", "In {n} stop names the letter ə, Ə or X is the Cyrillic look-alike, not the Latin one. It looks the same, but a text search can miss these names."],
      shared: ["Shared stop names", "{n} names are used by more than one stop; {far} of them by stops more than 1 km apart."],
      unnamed: ["Unnamed stops", "{n} stops have coordinates but no name and no route."],
      unchanged: ["The map does not show the new network", "On {scraped} the API returned exactly the data of {same_as}, while the new network has been launching in stages since January 2026."],
      missing: ["Counted, but not on the map", "BakuBus publishes boardings for these routes for {month}, but AYNA's map does not carry them."]
    },
    tables: {
      detours: {
        title: "The longest detours where everyone inside has another route",
        note: "The extra time is an estimate from speeds assumed by type of service. The shorter path runs along streets buses already use.",
        cols: ["Route", "From → to", "Extra distance", "Extra per trip", "Shorter path saves"]
      },
      duplicates: {
        title: "The most overlapping routes",
        note: "The share of the first route's stops that the second also serves.",
        cols: ["Route", "Mostly inside", "Shared stops", "Carriers"],
        same: "same", different: "different", of: "{b} of {a} stops"
      },
      corridors: {
        title: "The busiest corridors",
        note: "Ranked by length times the number of routes per link.",
        cols: ["Corridor", "Length", "Routes per link", "Routes"]
      }
    },
    tour: {
      label: "Guided tour",
      step: "{i} of {n}",
      back: "Back",
      next: "Next",
      done: "Finish",
      issues: "See the data issues",
      checklist: "Download the checklist",
      overview: ["{routes} routes, {direct} of them direct", "Each line is a bus route, coloured by how roundabout it is. Only {direct} of {routes} routes run at most 1.4 times the straight line between their end stops; {loops} are loops."],
      detour: ["A {min}-minute detour", "Between {from} and {to}, route {r} travels {along} km where the straight line is {straight} km: about {min} extra minutes on every trip (an estimate). Everyone who lives along it has another route within 400 m."],
      detourFix: " The green dashed line runs along streets buses already use: {alt} km instead of {along} km.",
      overlap: ["Two routes, one set of stops", "{all} stops of route {a} are also served by route {b}{carrier}. Orange stops are on both."],
      overlapAll: "All {n}",
      overlapShare: "{share} of the {n}",
      sameCarrier: ", run by the same carrier, {c}",
      otherCarrier: ", run by a different carrier",
      corridor: ["{routes} routes along one corridor","Between {from} and {to}, {routes} routes share {km} km of street, {mean} on every link on average. Stretches like this are the usual candidates for bus lanes or a single frequent trunk line."],
      spacing: ["{n} stops too close together", "Orange stops sit less than {gap} m from the next stop on every route that uses them. Removing them would leave no gap over {max} m and save about {hours} hours on one trip each way of every route (an estimate)."],
      coverage: ["{people} people, no stop within {radius} m", "In this hexagon {people} residents live more than {radius} m in a straight line from the nearest stop. Across the city, {uncovered} of {population} residents do."],
      reach: ["From {stop}", "{k} routes stop here. Without changing buses they reach {n0} stops; with one change, walking up to {walk} m between stops, {n1} of all {total}."],
      fixes: ["Fixable at the source", "AYNA's own map data has {defects} defects, from route lines filed under the wrong direction to {missing} counted routes missing from the map. They are listed below with the routes they affect."]
    }
  };

  // ---------------------------------------------------------------- state

  var VIEWS = ["directness", "detours", "duplication", "corridors", "coverage", "spacing", "reach"];
  var SHAPES = ["direct", "indirect", "very indirect", "loop"];
  var HEX_BINS = [100, 500, 2000];
  var ROUTE_BINS = [2, 4, 8];
  var CORRIDOR_WIDTHS = [8, 12, 16];
  var motionQuery = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;

  var view = "directness";
  var selected = null;        // the route whose card is open
  var compareWith = null;     // the route compared with it
  var reachFrom = null;       // the stop the reach view starts from
  var map = null;
  var R = {};
  var layers = {};

  var C = {
    ramp: { direct: "#86b6ef", indirect: "#3987e5", "very indirect": "#1c5cab", loop: "#0d366b" },
    hex: ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab"],
    stopRamp: ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"],
    base: "#bdbcb4", one: "#2a78d6", two: "#eb6834", fix: "#1baf7a", ink: "#0b0b0b", casing: "#ffffff",
    stop: "#52514e", faint: "#a9b1bf", near: "#9ec5f4"
  };

  function reduceMotion() { return !!(motionQuery && motionQuery.matches); }

  // ---------------------------------------------------------------- formatting

  var MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  function fmt(x, digits) {
    if (x === null || x === undefined || isNaN(x)) return "–";
    digits = digits || 0;
    var parts = Math.abs(x).toFixed(digits).split(".");
    var whole = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    return (x < 0 ? "−" : "") + whole + (digits ? "." + parts[1] : "");
  }
  function pct(x) { return fmt(Math.round(100 * x)) + "%"; }
  function millions(x) { return fmt(x / 1e6, 2) + " " + T.million; }
  function dayText(iso) { var p = iso.split("-"); return +p[2] + " " + MONTHS[+p[1] - 1] + " " + p[0]; }
  function monthText(ym) { var p = ym.split("-"); return MONTHS[+p[1] - 1] + " " + p[0]; }
  function fill(template, vals) {
    return template.replace(/\{(\w+)\}/g, function (all, k) { return k in vals ? vals[k] : all; });
  }
  // The template as nodes, each {key} a <b> holding its value; values are text, never HTML.
  function rich(template, vals) {
    var frag = document.createDocumentFragment();
    template.split(/(\{\w+\})/).forEach(function (part) {
      var m = part.match(/^\{(\w+)\}$/);
      if (m && m[1] in vals) frag.appendChild(el("b", { text: String(vals[m[1]]) }));
      else if (part) frag.appendChild(document.createTextNode(part));
    });
    return frag;
  }

  function el(tag, props, children) {
    var n = document.createElement(tag);
    if (props) {
      Object.keys(props).forEach(function (k) {
        var v = props[k];
        if (v === null || v === undefined || v === false) return;
        if (k === "class") n.className = v;
        else if (k === "text") n.textContent = v;
        else if (k === "style") n.setAttribute("style", v);
        else if (k.slice(0, 2) === "on") n.addEventListener(k.slice(2), v);
        else n.setAttribute(k, v === true ? "" : v);
      });
    }
    (children || []).forEach(function (c) {
      if (c === null || c === undefined || c === false) return;
      n.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return n;
  }
  function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); return n; }
  var ARROW = "M3 8h10m0 0-4-4m4 4-4 4";
  function icon(path) {
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 16 16");
    svg.setAttribute("aria-hidden", "true");
    var p = document.createElementNS("http://www.w3.org/2000/svg", "path");
    p.setAttribute("d", path);
    svg.appendChild(p);
    return svg;
  }
  // Lower case without Azerbaijani accents, and the Cyrillic look-alikes some stop names use,
  // so that "neftciler" finds "Neftçilər".
  var FOLD = { "ə": "e", "ә": "e", "ç": "c", "ş": "s", "ğ": "g", "ı": "i", "i̇": "i", "ö": "o", "ü": "u", "х": "x" };
  function fold(s) {
    return (s || "").toLocaleLowerCase("en").replace(/i̇|[əәçşğıöüх]/g, function (c) { return FOLD[c] || c; });
  }

  // ---------------------------------------------------------------- the data

  function decode(str) {
    var pts = [], i = 0, lat = 0, lon = 0;
    while (i < str.length) {
      var r = 0, s = 0, b;
      do { b = str.charCodeAt(i++) - 63; r |= (b & 0x1f) << s; s += 5; } while (b >= 0x20);
      lat += (r & 1) ? ~(r >> 1) : (r >> 1);
      r = 0; s = 0;
      do { b = str.charCodeAt(i++) - 63; r |= (b & 0x1f) << s; s += 5; } while (b >= 0x20);
      lon += (r & 1) ? ~(r >> 1) : (r >> 1);
      pts.push([lat / 1e5, lon / 1e5]);
    }
    return pts;
  }
  function bbox(ll) {
    var b = [Infinity, -Infinity, Infinity, -Infinity];
    ll.forEach(function (p) {
      if (p[0] < b[0]) b[0] = p[0];
      if (p[0] > b[1]) b[1] = p[0];
      if (p[1] < b[2]) b[2] = p[1];
      if (p[1] > b[3]) b[3] = p[1];
    });
    return b;
  }
  function joinBoxes(boxes) {
    return boxes.reduce(function (a, b) {
      return [Math.min(a[0], b[0]), Math.max(a[1], b[1]), Math.min(a[2], b[2]), Math.max(a[3], b[3])];
    }, [Infinity, -Infinity, Infinity, -Infinity]);
  }
  function pointBox(lat, lon, m) {
    var dLat = m / 111320, dLon = m / (111320 * Math.cos(lat * Math.PI / 180));
    return [lat - dLat, lat + dLat, lon - dLon, lon + dLon];
  }

  var stops = D.stops;                     // [lat, lon, name, AYNA id]
  var routes = D.routes;
  var byNumber = {};
  var stopById = {};
  stops.forEach(function (s, i) { stopById[s[3]] = i; });
  routes.forEach(function (r) {
    byNumber[r.n] = r;
    var seen = {};
    r.dirs.forEach(function (d) {
      d.ll = decode(d.line);
      d.box = bbox(d.ll);
      d.stops.forEach(function (s) { seen[s] = true; });
    });
    r.stopList = Object.keys(seen).map(Number);
    r.box = joinBoxes(r.dirs.map(function (d) { return d.box; }));
    r.detourList = [];
    r.inside = [];
    r.contains = [];
    r.fixes = [];
  });
  D.detours.forEach(function (d) {
    d.ll = decode(d.line);
    d.box = bbox(d.ll);
    if (d.alt) { d.alt.ll = decode(d.alt.line); d.box = joinBoxes([d.box, bbox(d.alt.ll)]); }
    byNumber[d.r].detourList.push(d);
  });
  D.duplicates.forEach(function (p) { byNumber[p.r].inside.push(p); byNumber[p["in"]].contains.push(p); });
  D.corridors.forEach(function (c) { c.ll = decode(c.line); c.box = bbox(c.ll); });
  D.hexes.forEach(function (h) { h.ll = decode(h[0]); h.box = bbox(h.ll); h.people = h[1]; h.total = h[2]; });
  D.issues.repairs.forEach(function (f) { if (byNumber[f.route]) byNumber[f.route].fixes.push(f); });
  D.issues.no_shape.forEach(function (n) { if (byNumber[n]) byNumber[n].fixes.push({ kind: "no_shape", direction: null }); });
  var NETWORK_BOX = joinBoxes(routes.map(function (r) { return r.box; }));
  var atStop = stops.map(function () { return []; });
  routes.forEach(function (r) {
    r.stopList.forEach(function (s) { atStop[s].push(r.n); });
  });
  var closeGap = {};
  D.spacing.stops.forEach(function (x) { closeGap[x[0]] = x[1]; });
  var foldedNames = stops.map(function (s) { return fold(s[2]); });
  var longest = D.detours.reduce(function (a, b) { return b.minutes > a.minutes ? b : a; });

  // Stops within walking distance of each other, for changes between routes.
  var GRID_M = 300;
  var grid = null;
  function gridKey(lat, lon) {
    return Math.floor(lat * 111320 / GRID_M) + ":" + Math.floor(lon * 111320 * Math.cos(40.4 * Math.PI / 180) / GRID_M);
  }
  function nearStops(i, m) {
    if (!grid) {
      grid = {};
      stops.forEach(function (s, k) { var key = gridKey(s[0], s[1]); (grid[key] = grid[key] || []).push(k); });
    }
    var s = stops[i], out = [];
    var gy = Math.floor(s[0] * 111320 / GRID_M), gx = Math.floor(s[1] * 111320 * Math.cos(40.4 * Math.PI / 180) / GRID_M);
    var kx = 111320 * Math.cos(s[0] * Math.PI / 180);
    for (var dy = -1; dy <= 1; dy++) {
      for (var dx = -1; dx <= 1; dx++) {
        (grid[(gy + dy) + ":" + (gx + dx)] || []).forEach(function (k) {
          var t = stops[k], ax = (t[1] - s[1]) * kx, ay = (t[0] - s[0]) * 111320;
          if (ax * ax + ay * ay <= m * m) out.push(k);
        });
      }
    }
    return out;
  }

  // Every stop reachable from stop i on the routes that stop there, and with one change.
  function reachOf(i) {
    var walk = D.meta.transfer_walk_m;
    var r0 = atStop[i], s0 = {}, r1 = {}, s1 = {};
    r0.forEach(function (n) { r1[n] = true; byNumber[n].stopList.forEach(function (s) { s0[s] = true; }); });
    Object.keys(s0).forEach(function (s) {
      nearStops(+s, walk).forEach(function (t) { atStop[t].forEach(function (n) { r1[n] = true; }); });
    });
    Object.keys(r1).forEach(function (n) { byNumber[n].stopList.forEach(function (s) { s1[s] = true; }); });
    return { routes: r0, none: s0, one: s1, nNone: Object.keys(s0).length, nOne: Object.keys(s1).length };
  }

  // ---------------------------------------------------------------- static text

  function get(path) {
    return path.split(".").reduce(function (o, k) { return o === null || o === undefined ? undefined : o[k]; }, D);
  }
  function renderStatic() {
    document.querySelectorAll("[data-v]").forEach(function (n) {
      var v = get(n.getAttribute("data-v"));
      var f = n.getAttribute("data-f");
      n.textContent = f === "share" ? pct(v / S.population) : f === "millions" ? millions(v) : fmt(v);
    });
    document.querySelectorAll("[data-date]").forEach(function (n) { n.textContent = dayText(get(n.getAttribute("data-date"))); });
    document.querySelectorAll("[data-month]").forEach(function (n) { n.textContent = monthText(get(n.getAttribute("data-month"))); });
  }

  // ---------------------------------------------------------------- map

  // OpenStreetMap's own tiles: no key needed, names in Azerbaijani. style.css greys them so
  // the routes carry the colour.
  var TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
  var ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · AYNA · Kontur';

  function toBounds(b) { return L.latLngBounds([b[0], b[2]], [b[1], b[3]]); }

  // Where most stops are: the view the map opens on, without the few far-out routes.
  function coreBox() {
    var lats = stops.map(function (s) { return s[0]; }).sort(function (a, b) { return a - b; });
    var lons = stops.map(function (s) { return s[1]; }).sort(function (a, b) { return a - b; });
    function q(a, p) { return a[Math.floor(p * (a.length - 1))]; }
    return [q(lats, 0.03), q(lats, 0.97), q(lons, 0.03), q(lons, 0.97)];
  }

  function initMap() {
    if (!window.L) {
      document.querySelector(".map-fallback").hidden = false;
      return;
    }
    map = L.map("leaflet", { zoomControl: false, scrollWheelZoom: false, minZoom: 9, maxZoom: 18, zoomSnap: 0.5, wheelPxPerZoomLevel: 90 });
    L.control.zoom({ position: "topright" }).addTo(map);
    map.attributionControl.setPrefix(false);
    ["routes", "overlay", "select", "hover"].forEach(function (name, i) {
      var pane = map.createPane(name);
      pane.style.zIndex = String(410 + 10 * i);
      pane.style.pointerEvents = "none";
    });
    R.routes = L.canvas({ pane: "routes", padding: 0.4 });
    R.overlay = L.canvas({ pane: "overlay", padding: 0.4 });
    R.select = L.canvas({ pane: "select", padding: 0.4 });
    R.hover = L.canvas({ pane: "hover", padding: 0.4 });
    layers.base = L.tileLayer(TILES, { maxZoom: 19, attribution: ATTRIBUTION }).addTo(map);

    // Route lines, least roundabout first, so the most roundabout are drawn on top.
    layers.routes = [];
    SHAPES.forEach(function (cls) {
      routes.forEach(function (r) {
        if (r.shape !== cls) return;
        r.dirs.forEach(function (d) {
          var line = L.polyline(d.ll, { renderer: R.routes, interactive: false, lineCap: "round", lineJoin: "round" });
          line.route = r;
          layers.routes.push(line);
          line.addTo(map);
        });
      });
    });
    layers.focus = L.layerGroup().addTo(map);
    layers.sel = L.layerGroup().addTo(map);
    layers.hover = L.layerGroup().addTo(map);

    map.fitBounds(toBounds(coreBox()), { padding: [8, 8] });
    map.setMaxBounds(toBounds(NETWORK_BOX).pad(0.5));
    map.on("zoomend", styleRoutes);
    map.on("mousemove", onMove);
    map.on("mouseout", hideTip);
    map.on("click", onClick);
    map.on("click", function () { map.scrollWheelZoom.enable(); });
    map.on("popupclose", function () { layers.hover.clearLayers(); });
    var container = map.getContainer();
    container.addEventListener("mouseleave", function () { map.scrollWheelZoom.disable(); });
    container.addEventListener("wheel", function () {
      if (!map.scrollWheelZoom.enabled()) flashHint(T.scrollHint);
    }, { passive: true });
  }

  var hintTimer = null;
  function flashHint(text) {
    var frame = document.querySelector(".map-frame");
    var hint = frame.querySelector(".map-hint");
    if (!hint) { hint = el("div", { class: "map-hint", "aria-hidden": "true" }); frame.appendChild(hint); }
    hint.textContent = text;
    hint.classList.add("on");
    clearTimeout(hintTimer);
    hintTimer = setTimeout(function () { hint.classList.remove("on"); }, 1400);
  }

  function fly(box, maxZoom, pad) {
    if (!map) return;
    var b = toBounds(box), p = pad || 48;
    // During the tour the card covers the bottom of the map: keep what it describes above it.
    var below = tour.on && tour.box && !tour.box.hidden ? tour.box.offsetHeight + 24 : 0;
    var opts = { paddingTopLeft: [p, p], paddingBottomRight: [p, p + below], maxZoom: maxZoom || 15 };
    if (reduceMotion()) map.fitBounds(b, opts);
    else map.flyToBounds(b, Object.assign(opts, { duration: 1.1 }));
  }

  // Bring the whole map into view, under the sticky top bar; if it is taller than the
  // window, show its bottom, where the tour card sits.
  function scrollToMap() {
    var frame = document.querySelector(".map-frame").getBoundingClientRect();
    var bar = document.querySelector(".topbar").getBoundingClientRect().height + 14;
    var top = window.scrollY + frame.top - bar;
    if (frame.height + bar > window.innerHeight) top = window.scrollY + frame.bottom - window.innerHeight + 12;
    window.scrollTo({ top: Math.max(0, top), behavior: reduceMotion() ? "auto" : "smooth" });
  }

  function routeWeight() {
    var z = map.getZoom();
    return z >= 15 ? 3.4 : z >= 13 ? 2.6 : z >= 11.5 ? 2 : 1.6;
  }

  function styleRoutes() {
    if (!map) return;
    var w = routeWeight(), dim = selected || reachFrom !== null ? 0.55 : 1;
    // A view's own layer steps back while a route is open, except the reach it draws.
    map.getPane("overlay").style.opacity = selected && view !== "reach" ? "0.4" : "1";
    layers.routes.forEach(function (line) {
      if (view === "directness") {
        line.setStyle({ color: C.ramp[line.route.shape], weight: w, opacity: 0.92 * dim });
      } else {
        var quiet = view === "coverage" || view === "spacing" || view === "reach";
        line.setStyle({ color: C.base, weight: Math.max(1.2, w - 0.6), opacity: (quiet ? 0.55 : 0.85) * dim });
      }
    });
  }

  function corridorWidth(mean) { return 3 + (Math.min(mean, 18) - 6) * 0.75; }
  function bin(n, edges) { var i = 0; while (i < edges.length && n >= edges[i]) i++; return i; }

  function dot(i, opts) {
    return L.circleMarker([stops[i][0], stops[i][1]], Object.assign({ renderer: R.overlay, interactive: false }, opts));
  }

  function buildOverlay(name) {
    var g = L.layerGroup();
    if (name === "detours") {
      D.detours.forEach(function (d) {
        g.addLayer(L.polyline(d.ll, { renderer: R.overlay, interactive: false, lineCap: "round", lineJoin: "round",
          color: d.pop_only === 0 ? C.two : C.one, weight: 4, opacity: 0.95 }));
      });
    } else if (name === "duplication") {
      var inside = {}, host = {};
      D.duplicates.forEach(function (p) { inside[p.r] = true; host[p["in"]] = true; });
      [["one", 2.6], ["two", 3.6]].forEach(function (kind) {
        routes.forEach(function (r) {
          var k = inside[r.n] ? "two" : host[r.n] ? "one" : null;
          if (k !== kind[0]) return;
          r.dirs.forEach(function (d) {
            g.addLayer(L.polyline(d.ll, { renderer: R.overlay, interactive: false, lineCap: "round", lineJoin: "round",
              color: C[k], weight: kind[1], opacity: 0.92 }));
          });
        });
      });
    } else if (name === "corridors") {
      D.corridors.forEach(function (k) {
        g.addLayer(L.polyline(k.ll, { renderer: R.overlay, interactive: false, lineCap: "round", lineJoin: "round",
          color: C.two, weight: corridorWidth(k.mean), opacity: 0.88 }));
      });
    } else if (name === "coverage") {
      // The lowest bin recedes: those hexagons are mostly sparse outskirts.
      var opacity = [0.22, 0.5, 0.68, 0.8];
      D.hexes.forEach(function (h) {
        var i = bin(h.people, HEX_BINS);
        g.addLayer(L.polygon(h.ll, { renderer: R.overlay, interactive: false, stroke: false,
          fillColor: C.hex[i], fillOpacity: opacity[i] }));
      });
      stops.forEach(function (s, i) {
        g.addLayer(dot(i, { radius: 1.4, stroke: false, fillColor: C.stop, fillOpacity: 0.65 }));
      });
    } else if (name === "spacing") {
      stops.forEach(function (s, i) {
        if (!(i in closeGap)) g.addLayer(dot(i, { radius: 1.7, stroke: false, fillColor: C.faint, fillOpacity: 0.9 }));
      });
      D.spacing.stops.forEach(function (x) {
        g.addLayer(dot(x[0], { radius: 4.4, color: C.casing, weight: 1.5, fillColor: C.two, fillOpacity: 1 }));
      });
    } else if (name === "reach") {
      if (reachFrom === null) {
        var order = stops.map(function (s, i) { return i; }).sort(function (a, b) { return atStop[a].length - atStop[b].length; });
        order.forEach(function (i) {
          var k = bin(atStop[i].length, ROUTE_BINS);
          g.addLayer(dot(i, { radius: [1.8, 2.3, 3, 3.8][k], stroke: false, fillColor: C.stopRamp[k], fillOpacity: 0.95 }));
        });
      } else {
        var reach = reachOf(reachFrom);
        reach.routes.forEach(function (n) {
          byNumber[n].dirs.forEach(function (d) {
            g.addLayer(L.polyline(d.ll, { renderer: R.overlay, interactive: false, color: C.one, weight: 2.4, opacity: 0.75, lineCap: "round" }));
          });
        });
        stops.forEach(function (s, i) {
          if (reach.none[i]) return;
          g.addLayer(dot(i, reach.one[i] ? { radius: 2.4, stroke: false, fillColor: C.near, fillOpacity: 1 }
                                          : { radius: 1.5, stroke: false, fillColor: C.faint, fillOpacity: 0.8 }));
        });
        Object.keys(reach.none).forEach(function (i) {
          g.addLayer(dot(+i, { radius: 3, stroke: false, fillColor: C.one, fillOpacity: 1 }));
        });
        g.addLayer(dot(reachFrom, { radius: 8, color: C.casing, weight: 3, fillColor: C.ink, fillOpacity: 1 }));
      }
    }
    return g;
  }

  function refreshOverlay() {
    if (!map) return;
    if (layers.overlay) layers.overlay.remove();
    layers.overlay = view === "directness" ? null : buildOverlay(view).addTo(map);
  }

  function showView(name, keepHash) {
    var next = VIEWS.indexOf(name) >= 0 ? name : "directness";
    if (next !== "reach") reachFrom = null;
    view = next;
    document.querySelectorAll("[data-view]").forEach(function (b) {
      b.setAttribute("aria-selected", String(b.getAttribute("data-view") === view));
    });
    if (map) {
      refreshOverlay();
      layers.hover.clearLayers();
      layers.focus.clearLayers();
      map.closePopup();
      styleRoutes();
    }
    renderPanel();
    if (!keepHash) updateHash();
  }

  // ---------------------------------------------------------------- selection

  function select(n, opts) {
    opts = opts || {};
    var r = byNumber[n] || null;
    selected = r;
    compareWith = r && opts.compare && byNumber[opts.compare] ? opts.compare : null;
    if (!opts.keepFocus && layers.focus) layers.focus.clearLayers();
    drawSelection();
    renderCard();
    renderChips();
    renderPanel();
    setSelectedChip();
    updateHash();
    if (r && map && !opts.noZoom) {
      var b = opts.box || (compareWith ? joinBoxes([r.box, byNumber[compareWith].box]) : r.box);
      fly(b, opts.box ? 15 : 14.5);
    }
    if (r && opts.scroll) scrollToMap();
  }

  function setCompare(n) {
    compareWith = compareWith === n ? null : n;
    drawSelection();
    renderCard();
    updateHash();
    if (compareWith && selected) fly(joinBoxes([selected.box, byNumber[compareWith].box]), 14.5);
  }

  function lineOpts(color, weight, extra) {
    return Object.assign({ renderer: R.select, interactive: false, color: color, weight: weight, opacity: 1,
      lineCap: "round", lineJoin: "round" }, extra || {});
  }

  function drawSelection() {
    if (!map) return;
    layers.sel.clearLayers();
    styleRoutes();
    if (!selected) return;
    var partner = compareWith ? byNumber[compareWith] : null;
    var shared = {};
    if (partner) {
      partner.stopList.forEach(function (s) { shared[s] = true; });
      partner.dirs.forEach(function (d) {
        layers.sel.addLayer(L.polyline(d.ll, lineOpts(C.casing, 8)));
        layers.sel.addLayer(L.polyline(d.ll, lineOpts(C.one, 3.6)));
      });
    }
    selected.dirs.forEach(function (d) { layers.sel.addLayer(L.polyline(d.ll, lineOpts(C.casing, 9))); });
    selected.dirs.forEach(function (d) { layers.sel.addLayer(L.polyline(d.ll, lineOpts(C.ink, 3.6))); });
    selected.detourList.forEach(function (d) {
      layers.sel.addLayer(L.polyline(d.ll, lineOpts(C.casing, 8.5)));
      layers.sel.addLayer(L.polyline(d.ll, lineOpts(d.pop_only === 0 ? C.two : C.one, 4.4)));
      if (d.alt) {
        layers.sel.addLayer(L.polyline(d.alt.ll, lineOpts(C.casing, 7)));
        layers.sel.addLayer(L.polyline(d.alt.ll, lineOpts(C.fix, 3.4, { dashArray: "8 7", lineCap: "butt" })));
      }
    });
    var seen = {};
    selected.dirs.forEach(function (d) {
      d.stops.forEach(function (s) {
        if (seen[s]) return;
        seen[s] = true;
        var hot = partner ? shared[s] : (s in closeGap);
        layers.sel.addLayer(L.circleMarker([stops[s][0], stops[s][1]], { renderer: R.select, interactive: false,
          radius: hot ? 4.6 : 3.6, color: hot ? C.casing : C.ink, weight: hot ? 1.8 : 1.6,
          fillColor: hot ? C.two : C.casing, fillOpacity: 1 }));
      });
    });
  }

  function setSelectedChip() {
    var box = document.querySelector(".map-selected");
    if (!box) return;
    clear(box);
    if (!selected || !map) { box.hidden = true; return; }
    box.appendChild(el("span", { text: fill(T.routeN, { n: selected.n }) }));
    box.appendChild(el("button", { type: "button", "aria-label": T.close, text: "×", onclick: function () { select(null); } }));
    box.hidden = false;
  }

  function setReach(i, opts) {
    opts = opts || {};
    if (view !== "reach") showView("reach", true);
    reachFrom = i;
    if (selected && !opts.keepRoute) { selected = null; compareWith = null; drawSelection(); renderCard(); setSelectedChip(); renderChips(); }
    refreshOverlay();
    styleRoutes();
    renderPanel();
    updateHash();
    if (map && i !== null && opts.zoom) fly(pointBox(stops[i][0], stops[i][1], 1500), 15);
  }

  // A detour, corridor or hexagon drawn on top until something else is chosen.
  function focusDetour(d) {
    layers.focus.clearLayers();
    layers.focus.addLayer(L.polyline([[stops[d.a][0], stops[d.a][1]], [stops[d.b][0], stops[d.b][1]]],
      lineOpts(C.ink, 2, { dashArray: "5 6", renderer: R.hover })));
  }
  function focusCorridor(k) {
    layers.focus.clearLayers();
    layers.focus.addLayer(L.polyline(k.ll, lineOpts(C.ink, corridorWidth(k.mean) + 3, { opacity: 0.3, renderer: R.hover })));
  }
  function focusHex(h) {
    layers.focus.clearLayers();
    layers.focus.addLayer(L.polygon(h.ll, { renderer: R.hover, interactive: false, color: C.ink, weight: 2.5, fill: false }));
  }

  // ---------------------------------------------------------------- pointing at the map

  function distanceTo(ll, lat, lon, kx, ky, dLat, dLon) {
    var best = Infinity;
    for (var i = 0; i < ll.length - 1; i++) {
      var a = ll[i], b = ll[i + 1];
      if ((a[0] < lat - dLat && b[0] < lat - dLat) || (a[0] > lat + dLat && b[0] > lat + dLat) ||
          (a[1] < lon - dLon && b[1] < lon - dLon) || (a[1] > lon + dLon && b[1] > lon + dLon)) continue;
      var ax = (a[1] - lon) * kx, ay = (a[0] - lat) * ky, bx = (b[1] - lon) * kx, by = (b[0] - lat) * ky;
      var dx = bx - ax, dy = by - ay, len2 = dx * dx + dy * dy;
      var t = len2 ? Math.max(0, Math.min(1, -(ax * dx + ay * dy) / len2)) : 0;
      var px = ax + t * dx, py = ay + t * dy;
      var d = Math.sqrt(px * px + py * py);
      if (d < best) best = d;
    }
    return best;
  }
  function insideRing(ll, lat, lon) {
    var inside = false;
    for (var i = 0, j = ll.length - 1; i < ll.length; j = i++) {
      var a = ll[i], b = ll[j];
      if ((a[0] > lat) !== (b[0] > lat) && lon < (b[1] - a[1]) * (lat - a[0]) / (b[0] - a[0]) + a[1]) inside = !inside;
    }
    return inside;
  }

  var PRIORITY = { stop: 0, detour: 1, corridor: 1, route: 2, hex: 3 };

  // Everything within px pixels of a point, nearest first within each kind.
  function hitsAt(latlng, px) {
    var lat = latlng.lat, lon = latlng.lng;
    var cos = Math.cos(lat * Math.PI / 180);
    var ky = 111320, kx = 111320 * cos;
    var tol = px * 40075016.686 * cos / Math.pow(2, map.getZoom() + 8);
    var dLat = tol / ky, dLon = tol / kx;
    function near(b) { return !(b[1] < lat - dLat || b[0] > lat + dLat || b[3] < lon - dLon || b[2] > lon + dLon); }
    var out = [];
    function stopHit(s, limit) {
      var dx = (stops[s][1] - lon) * kx, dy = (stops[s][0] - lat) * ky, m = Math.sqrt(dx * dx + dy * dy);
      if (m <= limit) out.push({ type: "stop", item: s, d: m });
    }
    if (view === "spacing" || view === "reach") {
      var best = null;
      for (var i = 0; i < stops.length; i++) {
        var s = stops[i];
        if (s[0] < lat - dLat || s[0] > lat + dLat || s[1] < lon - dLon || s[1] > lon + dLon) continue;
        var dx = (s[1] - lon) * kx, dy = (s[0] - lat) * ky, m = Math.sqrt(dx * dx + dy * dy);
        if (m <= tol && (!best || m < best.d)) best = { type: "stop", item: i, d: m };
      }
      if (best) out.push(best);
    } else if (selected) {
      selected.stopList.forEach(function (s) { stopHit(s, tol * 0.8); });
    }
    if (view === "detours") {
      D.detours.forEach(function (d) {
        if (!near(d.box)) return;
        var m = distanceTo(d.ll, lat, lon, kx, ky, dLat, dLon);
        if (m <= tol) out.push({ type: "detour", item: d, d: m });
      });
    }
    if (view === "corridors") {
      D.corridors.forEach(function (c) {
        if (!near(c.box)) return;
        var m = distanceTo(c.ll, lat, lon, kx, ky, dLat, dLon);
        if (m <= tol * 1.4) out.push({ type: "corridor", item: c, d: m });
      });
    }
    routes.forEach(function (r) {
      if (!near(r.box)) return;
      var best = Infinity;
      r.dirs.forEach(function (d) { if (near(d.box)) best = Math.min(best, distanceTo(d.ll, lat, lon, kx, ky, dLat, dLon)); });
      if (best <= tol) out.push({ type: "route", item: r, d: best });
    });
    if (view === "coverage") {
      for (var k = 0; k < D.hexes.length; k++) {
        var h = D.hexes[k];
        if (lat < h.box[0] || lat > h.box[1] || lon < h.box[2] || lon > h.box[3]) continue;
        if (insideRing(h.ll, lat, lon)) { out.push({ type: "hex", item: h, d: tol }); break; }
      }
    }
    out.sort(function (a, b) { return (PRIORITY[a.type] - PRIORITY[b.type]) || (a.d - b.d); });
    return out;
  }

  var pending = null;
  function onMove(e) {
    pending = e;
    if (onMove.busy) return;
    onMove.busy = true;
    window.requestAnimationFrame(function () {
      onMove.busy = false;
      var ev = pending;
      if (!ev || !map) return;
      showTip(ev, hitsAt(ev.latlng, 10));
    });
  }

  function hideTip() {
    var tip = document.querySelector(".map-tip");
    tip.hidden = true;
    if (layers.hover) layers.hover.clearLayers();
    if (map) map.getContainer().style.cursor = "";
  }

  function stopLine(i) {
    var n = atStop[i].length;
    return n === 1 ? T.stopRoute : fill(T.stopRoutes, { n: fmt(n) });
  }

  function showTip(e, hits) {
    var tip = document.querySelector(".map-tip");
    layers.hover.clearLayers();
    if (!hits.length) { hideTip(); return; }
    var h = hits[0], title = "", sub = "";
    map.getContainer().style.cursor = h.type === "hex" ? "" : "pointer";
    if (h.type === "stop") {
      title = stops[h.item][2] || "–";
      sub = view === "spacing" && h.item in closeGap ? fill(T.tip.gap, { gap: fmt(closeGap[h.item]) }) : stopLine(h.item);
    } else if (h.type === "detour") {
      var d = h.item;
      title = fill(T.routeN, { n: d.r }) + " · " + stops[d.a][2] + " → " + stops[d.b][2];
      sub = fill(T.tip.detour, { min: fmt(d.minutes, 1), km: fmt(d.excess, 1) }) +
        (d.alt ? " · " + fill(T.tip.alt, { km: fmt(d.alt.saved_km, 1) }) : "");
      layers.hover.addLayer(L.polyline(d.ll, lineOpts(C.ink, 5, { opacity: 0.85, renderer: R.hover })));
      layers.hover.addLayer(L.polyline([[stops[d.a][0], stops[d.a][1]], [stops[d.b][0], stops[d.b][1]]],
        lineOpts(C.ink, 2, { dashArray: "5 6", opacity: 0.9, renderer: R.hover })));
      if (d.alt) {
        layers.hover.addLayer(L.polyline(d.alt.ll, lineOpts(C.casing, 7, { renderer: R.hover })));
        layers.hover.addLayer(L.polyline(d.alt.ll, lineOpts(C.fix, 3.4, { dashArray: "8 7", lineCap: "butt", renderer: R.hover })));
      }
    } else if (h.type === "corridor") {
      var k = h.item;
      title = k.from + " → " + (k.via ? k.via + " → " : "") + k.to;
      sub = fill(T.tip.corridor, { mean: fmt(k.mean, 1), km: fmt(k.km, 1) });
      layers.hover.addLayer(L.polyline(k.ll, lineOpts(C.ink, corridorWidth(k.mean) + 2, { opacity: 0.35, renderer: R.hover })));
    } else if (h.type === "route") {
      var numbers = [];
      hits.forEach(function (x) { if (x.type === "route" && numbers.indexOf(x.item.n) < 0) numbers.push(x.item.n); });
      var r = h.item;
      title = numbers.length > 1 ? numbers.slice(0, 8).join(", ") + (numbers.length > 8 ? " +" + (numbers.length - 8) : "")
                                 : fill(T.routeN, { n: r.n });
      if (numbers.length === 1) {
        if (view === "duplication" && r.inside.length) {
          var p = r.inside[0];
          sub = fill(T.tip.inside, { share: pct(p.share), r: p["in"] });
        } else {
          sub = T.shapes[r.shape];
        }
        r.dirs.forEach(function (dd) {
          layers.hover.addLayer(L.polyline(dd.ll, lineOpts(C.ink, 3.2, { opacity: 0.75, renderer: R.hover })));
        });
      }
    } else if (h.type === "hex") {
      title = fill(T.tip.hex, { n: fmt(h.item.people), radius: fmt(D.meta.radius_m) });
    }
    clear(tip);
    tip.appendChild(el("b", { text: title }));
    if (sub) tip.appendChild(el("span", { text: sub }));
    var frame = document.querySelector(".map-frame").getBoundingClientRect();
    var x = e.containerPoint.x + 14, y = e.containerPoint.y + 14;
    tip.hidden = false;
    var w = tip.offsetWidth, hgt = tip.offsetHeight;
    if (x + w > frame.width - 8) x = e.containerPoint.x - w - 14;
    if (y + hgt > frame.height - 8) y = e.containerPoint.y - hgt - 14;
    tip.style.left = Math.max(6, x) + "px";
    tip.style.top = Math.max(6, y) + "px";
  }

  function routeChips(numbers, onPick) {
    return el("div", { class: "chips" }, numbers.map(function (n) {
      return byNumber[n]
        ? el("button", { type: "button", class: "chip", text: n, onclick: function () { onPick(n); } })
        : el("span", { class: "chip", text: n });
    }));
  }

  function openPopup(latlng, nodes) {
    L.popup({ maxWidth: 320, autoPanPadding: [24, 24] }).setLatLng(latlng)
      .setContent(el("div", null, nodes)).openOn(map);
  }

  function onClick(e) {
    if (tour.on) endTour();
    var hits = hitsAt(e.latlng, 12);
    hideTip();
    if (!hits.length) return;
    var h = hits[0];
    function pick(n) { map.closePopup(); select(n); }
    if (h.type === "stop") {
      if (view === "reach") { setReach(h.item); return; }
      var nodes = [el("div", { class: "popup-title", text: stops[h.item][2] || "–" }),
        el("div", { class: "popup-meta", text: stopLine(h.item) })];
      if (h.item in closeGap) {
        nodes.push(el("div", { class: "popup-meta", text: fill(T.popup.gap, { gap: fmt(closeGap[h.item]), max: fmt(D.spacing.max_gap_after_m) }) }));
      }
      nodes.push(routeChips(atStop[h.item], pick));
      nodes.push(el("button", { type: "button", class: "popup-link", text: T.popup.reach, onclick: function () {
        map.closePopup();
        setReach(h.item);
      } }));
      openPopup(e.latlng, nodes);
    } else if (h.type === "detour") {
      select(h.item.r, { box: h.item.box });
      focusDetour(h.item);
    } else if (h.type === "corridor") {
      var k = h.item;
      focusCorridor(k);
      openPopup(e.latlng, [el("div", { class: "popup-title", text: k.from + " → " + (k.via ? k.via + " → " : "") + k.to }),
        el("div", { class: "popup-meta", text: fill(T.popup.corridor, { km: fmt(k.km, 1), stops: fmt(k.stops), mean: fmt(k.mean, 1), max: fmt(k.max) }) }),
        el("div", { class: "popup-meta", text: T.popup.corridorRoutes }),
        routeChips(k.routes, pick)]);
    } else if (h.type === "route") {
      var numbers = [];
      hits.forEach(function (x) { if (x.type === "route" && numbers.indexOf(x.item.n) < 0) numbers.push(x.item.n); });
      if (numbers.length === 1) select(numbers[0], { noZoom: true });
      else openPopup(e.latlng, [el("div", { class: "popup-title", text: T.routesHere }), routeChips(numbers, pick)]);
    } else if (h.type === "hex") {
      focusHex(h.item);
      openPopup(e.latlng, [el("div", { class: "popup-title", text: fill(T.popup.hex, { n: fmt(h.item.people), radius: fmt(D.meta.radius_m) }) }),
        el("div", { class: "popup-meta", text: fill(T.popup.hexTotal, { n: fmt(h.item.total) }) })]);
    }
  }

  // ---------------------------------------------------------------- the panel: view, finder, card

  function legendItem(swatch, label, count, note) {
    return el("li", null, [swatch, el("span", null, [label, note ? el("small", { text: note }) : null]), el("span", { class: "count", text: count || "" })]);
  }
  function keyLine(color, extra) { return el("span", { class: "key-line" + (extra ? " " + extra : ""), style: "--key:" + color }); }
  function keyDot(color, size) { return el("span", { class: "key-dot", style: "--key:" + color + ";--size:" + (size || 10) + "px" }); }

  function renderPanel() {
    var box = document.querySelector(".panel-view");
    clear(box);
    box.hidden = !!selected;
    if (selected) return;
    var v = T.views[view], list = el("ul", { class: "legend" }), radius = fmt(D.meta.radius_m);
    if (view === "reach" && reachFrom !== null) { renderReachPanel(box); return; }
    box.appendChild(el("h3", { text: v.name }));
    if (view === "directness") {
      box.appendChild(el("p", { text: v.text }));
      SHAPES.forEach(function (s) { list.appendChild(legendItem(keyLine(C.ramp[s]), T.shapes[s], fill(T.routesCount, { n: fmt(S.shapes[s]) }), T.ranges[s])); });
      box.appendChild(list);
      box.appendChild(el("p", { class: "fact" }, [rich(v.fact, { route_km: fmt(S.route_km), street_km: fmt(S.street_km), per_link: fmt(S.routes_per_link, 2) })]));
    } else if (view === "detours") {
      box.appendChild(el("p", { text: v.text }));
      var nobody = S.detours_nobody_only;
      list.appendChild(legendItem(keyLine(C.two), v.nobody, fmt(nobody)));
      list.appendChild(legendItem(keyLine(C.one), v.some, fmt(S.detours - nobody)));
      list.appendChild(legendItem(keyLine(C.fix, "dashed"), v.fix, fmt(S.detours_with_shorter_path)));
      box.appendChild(list);
      box.appendChild(el("p", { class: "fact" }, [rich(v.fact, { km: fmt(S.detour_km), with: fmt(S.detours_with_shorter_path), route: longest.r, minutes: fmt(longest.minutes, 1) })]));
    } else if (view === "duplication") {
      box.appendChild(el("p", { text: v.text }));
      var inside = {}, host = {};
      D.duplicates.forEach(function (p) { inside[p.r] = true; host[p["in"]] = true; });
      var hosts = Object.keys(host).filter(function (n) { return !inside[n]; }).length;
      list.appendChild(legendItem(keyLine(C.two), v.inside, fill(T.routesCount, { n: fmt(Object.keys(inside).length) })));
      list.appendChild(legendItem(keyLine(C.one), v.host, fill(T.routesCount, { n: fmt(hosts) })));
      box.appendChild(list);
      box.appendChild(el("p", { class: "fact" }, [rich(v.fact, { pairs: fmt(S.duplicate_pairs), two: fmt(S.duplicate_pairs_two_carriers) })]));
    } else if (view === "corridors") {
      box.appendChild(el("p", { text: v.text }));
      CORRIDOR_WIDTHS.forEach(function (n) {
        list.appendChild(legendItem(el("span", { class: "key-line", style: "--key:" + C.two + ";height:" + corridorWidth(n).toFixed(1) + "px" }),
          fill(v.width, { n: fmt(n) })));
      });
      box.appendChild(list);
      box.appendChild(el("p", { class: "fact" }, [rich(v.fact, { max: fmt(S.most_routes_on_a_link) })]));
    } else if (view === "coverage") {
      box.appendChild(el("p", { text: fill(v.text, { radius: radius }) }));
      var sums = [0, 0, 0, 0];
      D.hexes.forEach(function (h) { sums[bin(h.people, HEX_BINS)] += h.people; });
      box.appendChild(el("p", { class: "legend-title", text: v.legend }));
      v.bins.forEach(function (label, i) {
        list.appendChild(legendItem(el("span", { class: "key-box", style: "--key:" + C.hex[i] }), label, fill(v.people, { n: fmt(sums[i]) })));
      });
      box.appendChild(list);
      box.appendChild(el("p", { class: "fact" }, [rich(v.fact, { population: millions(S.population), covered: millions(S.covered), share: pct(S.covered / S.population), radius: radius })]));
    } else if (view === "spacing") {
      var sp = D.spacing;
      box.appendChild(el("p", { text: fill(v.text, { gap: fmt(sp.min_gap_m), max: fmt(sp.max_gap_after_m) }) }));
      list.appendChild(legendItem(keyDot(C.two, 11), v.close, fill(T.stopsCount, { n: fmt(sp.stops.length) })));
      list.appendChild(legendItem(keyDot(C.faint, 6), v.other, fill(T.stopsCount, { n: fmt(stops.length - sp.stops.length) })));
      box.appendChild(list);
      box.appendChild(el("p", { class: "fact" }, [rich(v.fact, { n: fmt(sp.stops.length), visits: fmt(sp.visits), hours: fmt(sp.hours_saved, 1),
        loss: fmt(D.meta.stop_loss_s), lost: fmt(sp.residents_losing), radius: radius })]));
    } else if (view === "reach") {
      box.appendChild(el("p", { text: v.text }));
      var counts = [0, 0, 0, 0], single = 0, hub = 0;
      atStop.forEach(function (rs, i) {
        counts[bin(rs.length, ROUTE_BINS)]++;
        if (rs.length === 1) single++;
        if (rs.length > atStop[hub].length) hub = i;
      });
      box.appendChild(el("p", { class: "legend-title", text: v.legend }));
      v.bins.forEach(function (label, i) {
        list.appendChild(legendItem(keyDot(C.stopRamp[i], [7, 8, 10, 12][i]), label, fill(T.stopsCount, { n: fmt(counts[i]) })));
      });
      box.appendChild(list);
      var fact = el("p", { class: "fact" }, [rich(v.fact, { name: stops[hub][2], n: fmt(atStop[hub].length), single: fmt(single) })]);
      box.appendChild(fact);
      box.appendChild(el("button", { type: "button", class: "btn btn-small", text: fill(v.title, { stop: stops[hub][2] }), onclick: function () { setReach(hub, { zoom: true }); } }));
    }
  }

  function renderReachPanel(box) {
    var v = T.views.reach, i = reachFrom, reach = reachOf(i), total = stops.length, walk = fmt(D.meta.transfer_walk_m);
    box.appendChild(el("p", { class: "eyebrow-small", text: v.name }));
    box.appendChild(el("h3", { text: fill(v.title, { stop: stops[i][2] || "–" }) }));
    box.appendChild(el("dl", { class: "reach-stats" }, [
      el("div", null, [el("dt", { text: v.none }), el("dd", null, [fill(v.of, { n: fmt(reach.nNone) }), el("small", { text: fill(v.share, { p: pct(reach.nNone / total), total: fmt(total) }) + " · " + v.noneNote })])]),
      el("div", null, [el("dt", { text: v.one }), el("dd", null, [fill(v.of, { n: fmt(reach.nOne) }), el("small", { text: fill(v.share, { p: pct(reach.nOne / total), total: fmt(total) }) + " · " + fill(v.oneNote, { walk: walk }) })])])
    ]));
    var list = el("ul", { class: "legend" });
    list.appendChild(legendItem(keyDot(C.one, 10), v.keys[0]));
    list.appendChild(legendItem(keyDot(C.near, 8), v.keys[1]));
    list.appendChild(legendItem(keyDot(C.faint, 6), v.keys[2]));
    box.appendChild(list);
    box.appendChild(el("p", { class: "legend-title", text: v.routes + " · " + fmt(reach.routes.length) }));
    box.appendChild(routeChips(reach.routes, function (n) { select(n); }));
    box.appendChild(el("div", { class: "card-actions" }, [
      el("button", { type: "button", class: "btn btn-small", text: v.clear, onclick: function () { setReach(null); } }),
      copyButton()
    ]));
  }

  function renderChips() {
    var box = document.querySelector(".route-chips");
    var results = document.querySelector(".stop-results");
    var raw = document.getElementById("route-search").value.trim();
    var q = raw.toLowerCase(), f = fold(raw);
    clear(box);
    clear(results);
    var shown = routes.filter(function (r) { return !q || r.n.toLowerCase().indexOf(q) === 0; });
    shown.forEach(function (r) {
      box.appendChild(el("button", { type: "button", class: "chip", role: "listitem", text: r.n,
        "aria-current": selected === r ? "true" : null, onclick: function () { select(r.n); } }));
    });
    box.hidden = !shown.length;
    var found = [];
    if (f.length >= 2) {
      for (var i = 0; i < stops.length && found.length < 8; i++) {
        if (foldedNames[i].indexOf(f) >= 0) found.push(i);
      }
    }
    results.hidden = !found.length;
    if (found.length) {
      results.appendChild(el("p", { class: "legend-title", text: T.stopsFound }));
      results.appendChild(el("ul", { class: "items" }, found.map(function (i) {
        // Several stops share a name (one on each side of a street): the routes tell them apart.
        var rs = atStop[i].slice().sort(function (a, b) { return a.localeCompare(b, "en", { numeric: true }); });
        var which = rs.slice(0, 5).join(", ") + (rs.length > 5 ? " +" + (rs.length - 5) : "");
        return el("li", null, [el("button", { type: "button", class: "item", onclick: function () {
          document.getElementById("route-search").value = "";
          renderChips();
          setReach(i, { zoom: true });
        } }, [
          el("div", { class: "item-title", text: stops[i][2] }),
          el("div", { class: "item-meta", text: stopLine(i) + ": " + which })
        ])]);
      })));
    }
    if (!shown.length && !found.length) {
      results.appendChild(el("p", { class: "finder-empty", text: T.noMatch }));
      results.hidden = false;
    }
  }

  function fact(label, value, note) {
    return el("div", null, [el("dt", { text: label }), el("dd", null, [value, note ? el("small", { text: note }) : null])]);
  }

  function fixText(f) {
    var template = T.fix[f.kind];
    if (!template) return f.text || "";
    return fill(template, { d: f.direction || "" });
  }

  function copyButton() {
    var copy = el("button", { type: "button", class: "btn btn-small", text: T.copyLink, onclick: function () {
      var url = window.location.href;
      var done = function () { copy.textContent = T.copied; setTimeout(function () { copy.textContent = T.copyLink; }, 1600); };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(done, function () { window.prompt("", url); });
      else window.prompt("", url);
    } });
    return copy;
  }

  function renderCard() {
    var box = document.querySelector(".card");
    clear(box);
    if (!selected) { box.hidden = true; return; }
    box.hidden = false;
    var r = selected, k = T.card;
    box.appendChild(el("div", { class: "card-head" }, [
      el("div", { class: "card-num", text: r.n }),
      el("div", null, [
        el("div", { class: "card-ends", text: (r.from || "–") + " — " + (r.to || "–") }),
        el("div", { class: "card-meta", text: [r.carrier, r.zone, r.region, fmt(r.fare, 2) + " AZN"].filter(Boolean).join(" · ") })
      ]),
      el("button", { type: "button", class: "card-close", "aria-label": T.close, text: "×", onclick: function () { select(null); } })
    ]));
    box.appendChild(el("div", { class: "badge" }, [el("i", { style: "background:" + C.ramp[r.shape] }), T.shapes[r.shape]]));
    var shapeText = r.shape === "loop" && !(r.circuity > 3) ? k.loop : fill(k.shape, { x: fmt(r.circuity, 2) });
    box.appendChild(el("p", { class: "card-shape", text: shapeText }));

    box.appendChild(el("h4", { text: k.measures }));
    var counts = r.dirs.map(function (d) { return d.stops.length; });
    var closeHere = r.stopList.filter(function (s) { return s in closeGap; }).length;
    box.appendChild(el("dl", { class: "facts" }, [
      fact(k.length, fmt(r.km, 1) + " km"),
      fact(k.stops, counts.length === 2 ? fill(k.stopsValue, { a: fmt(counts[0]), b: fmt(counts[1]) }) : fmt(counts[0])),
      fact(k.spacing, fmt(r.gap) + " m"),
      fact(k.short, fmt(r.gaps200)),
      fact(k.shared, pct(r.shared)),
      fact(k.closeStops, fmt(closeHere), closeHere ? k.closeNote : null),
      fact(fill(k.residents, { radius: fmt(D.meta.radius_m) }), fmt(r.pop)),
      fact(k.only, fmt(r.pop_only)),
      r.boardings === null
        ? fact(k.boardings, k.notPublished, k.notPublishedNote)
        : fact(k.boardings, fmt(r.boardings), fill(k.boardingsNote, { month: monthText(D.meta.counts_month) }))
    ]));

    box.appendChild(el("h4", { text: k.detours + (r.detourList.length ? " · " + fmt(r.detourList.length) : "") }));
    if (!r.detourList.length) {
      box.appendChild(el("p", { class: "card-note", text: k.noDetours }));
    } else {
      box.appendChild(el("ul", { class: "items" }, r.detourList.slice().sort(function (a, b) { return b.minutes - a.minutes; }).map(function (d) {
        return el("li", null, [el("button", { type: "button", class: "item", onclick: function () {
          focusDetour(d);
          fly(d.box, 16, 60);
        } }, [
          el("div", { class: "item-title", text: stops[d.a][2] + " → " + stops[d.b][2] }),
          el("div", { class: "item-meta" }, [
            el("span", { class: "tag", style: "background:" + (d.pop_only === 0 ? C.two : C.one) }),
            fill(k.detourMeta, { min: fmt(d.minutes, 1), km: fmt(d.excess, 1) }) + " · " + fill(k.direction, { d: d.d })
          ]),
          el("div", { class: "item-meta", text: d.pop_only === 0 ? k.nobody : fill(k.some, { n: fmt(d.pop_only) }) }),
          el("div", { class: "item-meta item-fix" }, [
            d.alt ? el("span", { class: "tag tag-fix" }) : null,
            d.alt ? fill(k.alt, { km: fmt(d.alt.km, 1), along: fmt(d.along, 1), min: fmt(d.alt.saved_min), dropped: fmt(d.alt.dropped) }) : k.altNone
          ])
        ])]);
      })));
    }

    box.appendChild(el("h4", { text: k.overlap }));
    if (!r.inside.length && !r.contains.length) box.appendChild(el("p", { class: "card-note", text: k.noOverlap }));
    function pairRow(p, key) {
      var n = p[key];
      return el("div", { class: "pair" }, [
        el("button", { type: "button", class: "chip", "aria-pressed": String(compareWith === n), onclick: function () { setCompare(n); } },
          [T.compare + " " + n, el("small", { text: pct(p.share) })]),
        el("button", { type: "button", class: "pair-open", "aria-label": T.open + " " + n, onclick: function () { select(n); } }, [icon(ARROW)])
      ]);
    }
    if (r.inside.length) {
      box.appendChild(el("p", { class: "card-note", text: k.inside }));
      box.appendChild(el("div", { class: "pairs" }, r.inside.map(function (p) { return pairRow(p, "in"); })));
    }
    if (r.contains.length) {
      box.appendChild(el("p", { class: "card-note", text: k.contains, style: r.inside.length ? "margin-top:12px" : null }));
      box.appendChild(el("div", { class: "pairs" }, r.contains.map(function (p) { return pairRow(p, "r"); })));
    }
    if (compareWith) {
      var other = {};
      byNumber[compareWith].stopList.forEach(function (s) { other[s] = true; });
      var sharedN = r.stopList.filter(function (s) { return other[s]; }).length;
      box.appendChild(el("p", { class: "card-note compare-note", text: fill(k.compareNote, { shared: fmt(sharedN), n: fmt(r.stopList.length) }) }));
    }

    var notes = r.fixes.map(fixText);
    r.straight.forEach(function (d) { notes.push(fill(k.straight, { d: d })); });
    if (notes.length) {
      box.appendChild(el("h4", { text: k.fixes }));
      box.appendChild(el("ul", { class: "items" }, notes.filter(function (x, i) { return notes.indexOf(x) === i; }).map(function (text) {
        return el("li", { class: "card-note", text: "• " + text });
      })));
    }
    box.appendChild(el("div", { class: "card-actions" }, [copyButton()]));
  }

  // ---------------------------------------------------------------- data issues

  function issueCard(kind, count, unit, body, chips) {
    return el("article", { class: "issue" }, [
      el("div", { class: "issue-count" }, [count, unit ? el("small", { text: unit }) : null]),
      el("h4", { text: T.issues[kind][0] }),
      el("p", null, [body]),
      chips || null
    ]);
  }

  function renderIssues() {
    var box = document.querySelector(".issues");
    clear(box);
    var u = T.units, I = D.issues;
    function goTo(n) { select(n, { scroll: true }); }
    var byKind = {};
    I.repairs.forEach(function (f) { (byKind[f.kind] = byKind[f.kind] || []).push(f); });
    function repairChips(list) {
      return el("div", { class: "chips" }, list.map(function (f) {
        var label = f.direction ? [f.route, el("small", { text: "· " + f.direction })] : [f.route];
        return el("button", { type: "button", class: "chip", onclick: function () { goTo(f.route); } }, label);
      }));
    }
    function routeSet(list) { var s = {}; list.forEach(function (f) { s[f.route] = true; }); return Object.keys(s).length; }

    var lines = [];
    ["wrong_direction", "backwards", "swapped", "lat_equals_lon", "scrambled", "far", "repeated_stops", "other"].forEach(function (kind) {
      var list = byKind[kind];
      if (!list) return;
      var perRoute = list.every(function (f) { return !f.direction; }) || kind === "repeated_stops";
      var count = perRoute ? routeSet(list) : list.length;
      var vals = {};
      if (kind === "scrambled") {
        var jumps = list.map(function (f) { return f.jump_km; }).filter(function (x) { return x; });
        vals = { min: fmt(Math.floor(Math.min.apply(null, jumps))), max: fmt(Math.ceil(Math.max.apply(null, jumps))) };
      }
      var shown = kind === "repeated_stops" ? list.filter(function (f, i) { return list.findIndex(function (g) { return g.route === f.route; }) === i; })
        .map(function (f) { return { route: f.route, direction: null }; }) : list;
      lines.push(issueCard(kind, fmt(count), perRoute ? u.routes : u.directions, fill(T.issues[kind][1], vals), repairChips(shown)));
    });
    if (I.no_shape.length) lines.push(issueCard("no_shape", fmt(I.no_shape.length), u.routes, T.issues.no_shape[1], routeChips(I.no_shape, goTo)));

    var table = [];
    var cut = I.no_stops.indexOf("150A") >= 0 && I.no_stops.indexOf("446") >= 0 && byNumber["180"];
    table.push(issueCard("no_stops", fmt(I.no_stops.length), u.routes, T.issues.no_stops[1] + (cut ? T.issues.cutoff : ""), routeChips(I.no_stops, goTo)));
    table.push(issueCard("length", fmt(I.length_round_trip_median, 2) + "×", null, fill(T.issues.length[1], { x: fmt(I.length_round_trip_median, 2) })));
    table.push(issueCard("duration", fmt(I.duration_formula), fill(u.of, { n: fmt(I.routes_in_table) }), fill(T.issues.duration[1], { n: fmt(I.routes_in_table) })));

    var stopsGroup = [
      issueCard("cyrillic", fmt(I.cyrillic_names), u.names, fill(T.issues.cyrillic[1], { n: fmt(I.cyrillic_names) })),
      issueCard("shared", fmt(I.shared_names), u.names, fill(T.issues.shared[1], { n: fmt(I.shared_names), far: fmt(I.shared_names_far_apart) })),
      issueCard("unnamed", fmt(I.unnamed_unused_stops), u.stops, fill(T.issues.unnamed[1], { n: fmt(I.unnamed_unused_stops) }))
    ];

    var fresh = [
      issueCard("unchanged", "0", u.changes, fill(T.issues.unchanged[1], { scraped: dayText(D.meta.scraped), same_as: dayText(D.meta.same_as) })),
      issueCard("missing", fmt(I.missing_from_map.length), u.routes, fill(T.issues.missing[1], { month: monthText(I.counts_month) }), routeChips(I.missing_from_map, goTo)),
      issueCard("api", "1", u.routes, T.issues.api[1])
    ];

    [["lines", lines], ["table", table], ["fresh", fresh], ["stops", stopsGroup]].forEach(function (g) {
      box.appendChild(el("section", { class: "issue-group" }, [el("h3", { text: T.groups[g[0]] }), el("div", { class: "issue-grid" }, g[1])]));
    });
  }

  function defectCount() {
    var I = D.issues;
    return I.repairs.length + I.no_shape.length + I.no_stops.length + I.missing_from_map.length;
  }

  // ---------------------------------------------------------------- checklist tables

  function goButton(onclick) {
    return el("button", { type: "button", class: "go", onclick: onclick }, [T.show, icon(ARROW)]);
  }

  function table(spec, head, rows) {
    var numeric = head.map(function (h) { return h.num; });
    return el("article", { class: "table-card" }, [
      el("h3", { text: spec.title }),
      el("p", { class: "table-note", text: spec.note }),
      el("div", { class: "table-scroll" }, [el("table", null, [
        el("thead", null, [el("tr", null, head.map(function (h) { return el("th", { class: h.num ? "num" : null, text: h.label }); }).concat([el("th")]))]),
        el("tbody", null, rows.map(function (row) {
          return el("tr", null, row.cells.map(function (cell, i) {
            return el("td", { class: (numeric[i] ? "num" : "") + (head[i].route ? " route" : "") }, Array.isArray(cell) ? cell : [cell]);
          }).concat([el("td", { class: "num" }, [goButton(row.go)])]));
        }))
      ])])
    ]);
  }

  function renderTables() {
    var box = document.querySelector(".tables");
    clear(box);
    var t = T.tables, c;

    c = t.detours.cols;
    var detours = D.detours.filter(function (d) { return d.pop_only === 0; }).sort(function (a, b) { return b.minutes - a.minutes; }).slice(0, 10);
    box.appendChild(table(t.detours, [{ label: c[0], route: true }, { label: c[1] }, { label: c[2], num: true }, { label: c[3], num: true }, { label: c[4], num: true }],
      detours.map(function (d) {
        return {
          cells: [d.r, [stops[d.a][2] + " → " + stops[d.b][2], el("span", { class: "sub", text: fill(T.card.direction, { d: d.d }) })],
            fmt(d.excess, 1) + " km", "+" + fmt(d.minutes, 1) + " min", d.alt ? fmt(d.alt.saved_km, 1) + " km" : "–"],
          go: function () { showView("detours"); select(d.r, { box: d.box, scroll: true }); focusDetour(d); }
        };
      })));

    c = t.duplicates.cols;
    var carrier = {};
    routes.forEach(function (r) { carrier[r.n] = r.carrier; });
    box.appendChild(table(t.duplicates, [{ label: c[0], route: true }, { label: c[1], route: true }, { label: c[2], num: true }, { label: c[3] }],
      D.duplicates.slice(0, 10).map(function (p) {
        return {
          cells: [p.r, p["in"], [pct(p.share), el("span", { class: "sub", text: fill(t.duplicates.of, { a: fmt(p.stops), b: fmt(Math.round(p.share * p.stops)) }) })],
            [p.same ? t.duplicates.same : t.duplicates.different, el("span", { class: "sub", text: carrier[p.r] + (p.same ? "" : " · " + carrier[p["in"]]) })]],
          go: function () { showView("duplication"); select(p.r, { scroll: true, compare: p["in"] }); }
        };
      })));

    c = t.corridors.cols;
    box.appendChild(table(t.corridors, [{ label: c[0] }, { label: c[1], num: true }, { label: c[2], num: true }, { label: c[3], num: true }],
      D.corridors.slice(0, 10).map(function (k) {
        return {
          cells: [k.from + " → " + (k.via ? k.via + " → " : "") + k.to, fmt(k.km, 1) + " km", fmt(k.mean, 1), fmt(k.routes.length)],
          go: function () {
            select(null);
            showView("corridors");
            focusCorridor(k);
            scrollToMap();
            fly(k.box, 15, 60);
          }
        };
      })));
  }

  // ---------------------------------------------------------------- the guided tour

  var tour = { on: false, i: 0, steps: [], box: null };

  function buildTour() {
    var t = T.tour, steps = [];
    steps.push({
      title: fill(t.overview[0], { routes: fmt(S.routes), direct: fmt(S.shapes.direct) }),
      text: fill(t.overview[1], { routes: fmt(S.routes), direct: fmt(S.shapes.direct), loops: fmt(S.shapes.loop) }),
      run: function () { select(null); showView("directness", true); fly(coreBox(), 12, 8); }
    });
    var d = D.detours.filter(function (x) { return x.pop_only === 0; }).sort(function (a, b) { return b.minutes - a.minutes; })[0];
    if (d) {
      steps.push({
        title: fill(t.detour[0], { min: fmt(d.minutes) }),
        text: fill(t.detour[1], { from: stops[d.a][2], to: stops[d.b][2], r: d.r, along: fmt(d.along, 1), straight: fmt(d.straight, 1), min: fmt(d.minutes) }) +
          (d.alt ? fill(t.detourFix, { alt: fmt(d.alt.km, 1), along: fmt(d.along, 1) }) : ""),
        run: function () { showView("detours", true); select(d.r, { noZoom: true }); focusDetour(d); fly(d.box, 15, 70); }
      });
    }
    var p = D.duplicates[0];
    if (p) {
      var a = byNumber[p.r], b = byNumber[p["in"]];
      var all = p.share >= 0.9995 ? fill(t.overlapAll, { n: fmt(p.stops) }) : fill(t.overlapShare, { share: pct(p.share), n: fmt(p.stops) });
      steps.push({
        title: t.overlap[0],
        text: fill(t.overlap[1], { all: all, a: p.r, b: p["in"], carrier: p.same ? fill(t.sameCarrier, { c: a.carrier }) : t.otherCarrier }),
        run: function () { showView("duplication", true); select(p.r, { noZoom: true, compare: p["in"] }); fly(joinBoxes([a.box, b.box]), 14.5); }
      });
    }
    var k = D.corridors[0];
    if (k) {
      steps.push({
        title: fill(t.corridor[0], { routes: fmt(k.routes.length) }),
        text: fill(t.corridor[1], { from: k.from, to: k.to, routes: fmt(k.routes.length), km: fmt(k.km, 1), mean: fmt(k.mean, 1) }),
        run: function () { select(null); showView("corridors", true); focusCorridor(k); fly(k.box, 15, 60); }
      });
    }
    if (D.spacing.stops.length) {
      // Fly to the square kilometre with the most stops that could go.
      var cells = {}, best = null;
      D.spacing.stops.forEach(function (x) {
        var s = stops[x[0]], key = Math.floor(s[0] / 0.01) + ":" + Math.floor(s[1] / 0.012);
        cells[key] = (cells[key] || 0) + 1;
        if (!best || cells[key] > cells[best]) best = key;
      });
      var parts = best.split(":"), lat = (+parts[0] + 0.5) * 0.01, lon = (+parts[1] + 0.5) * 0.012;
      steps.push({
        title: fill(t.spacing[0], { n: fmt(D.spacing.stops.length) }),
        text: fill(t.spacing[1], { gap: fmt(D.spacing.min_gap_m), max: fmt(D.spacing.max_gap_after_m), hours: fmt(D.spacing.hours_saved, 1) }),
        run: function () { select(null); showView("spacing", true); fly(pointBox(lat, lon, 1600), 15.5, 30); }
      });
    }
    var h = D.hexes.reduce(function (x, y) { return y.people > x.people ? y : x; });
    steps.push({
      title: fill(t.coverage[0], { people: fmt(h.people), radius: fmt(D.meta.radius_m) }),
      text: fill(t.coverage[1], { people: fmt(h.people), radius: fmt(D.meta.radius_m), uncovered: millions(S.uncovered), population: millions(S.population) }),
      run: function () { select(null); showView("coverage", true); focusHex(h); fly(pointBox((h.box[0] + h.box[1]) / 2, (h.box[2] + h.box[3]) / 2, 2600), 13.5, 20); }
    });
    var hub = 0;
    atStop.forEach(function (rs, i) { if (rs.length > atStop[hub].length) hub = i; });
    var reach = reachOf(hub);
    steps.push({
      title: fill(t.reach[0], { stop: stops[hub][2] }),
      text: fill(t.reach[1], { k: fmt(reach.routes.length), n0: fmt(reach.nNone), walk: fmt(D.meta.transfer_walk_m), n1: fmt(reach.nOne), total: fmt(stops.length) }),
      run: function () { select(null); setReach(hub); fly(coreBox(), 12, 8); }
    });
    steps.push({
      title: t.fixes[0],
      text: fill(t.fixes[1], { defects: fmt(defectCount()), missing: fmt(D.issues.missing_from_map.length) }),
      last: true,
      run: function () { select(null); showView("directness", true); fly(coreBox(), 12, 8); }
    });
    return steps;
  }

  function startTour() {
    if (!map) return;
    tour.steps = buildTour();
    tour.on = true;
    scrollToMap();
    goStep(0);
  }

  function endTour() {
    tour.on = false;
    if (tour.box) tour.box.hidden = true;
    document.removeEventListener("keydown", tourKeys);
    updateHash();
  }

  function tourKeys(e) {
    if (!tour.on) return;
    if (e.key === "ArrowRight") { e.preventDefault(); goStep(tour.i + 1); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); goStep(tour.i - 1); }
    else if (e.key === "Escape") endTour();
  }

  function goStep(i) {
    if (i >= tour.steps.length) { endTour(); return; }
    tour.i = Math.max(0, i);
    renderTour();
    tour.steps[tour.i].run();
    document.removeEventListener("keydown", tourKeys);
    document.addEventListener("keydown", tourKeys);
  }

  function renderTour() {
    var t = T.tour, step = tour.steps[tour.i], n = tour.steps.length;
    if (!tour.box) {
      tour.box = el("div", { class: "tour", role: "dialog", "aria-label": t.label });
      document.querySelector(".map-frame").appendChild(tour.box);
    }
    var box = clear(tour.box);
    box.hidden = false;
    box.appendChild(el("div", { class: "tour-top" }, [
      el("span", { class: "tour-step", text: t.label + " · " + fill(t.step, { i: tour.i + 1, n: n }) }),
      el("button", { type: "button", class: "tour-close", "aria-label": T.close, text: "×", onclick: endTour })
    ]));
    box.appendChild(el("h3", { class: "tour-title", text: step.title }));
    box.appendChild(el("p", { class: "tour-text", text: step.text }));
    var actions = [];
    if (step.last) {
      actions.push(el("button", { type: "button", class: "btn btn-small", text: t.issues, onclick: function () {
        endTour();
        document.getElementById("issues").scrollIntoView({ behavior: reduceMotion() ? "auto" : "smooth" });
      } }));
      actions.push(el("a", { class: "btn btn-small btn-primary", href: "site/checklist.xlsx", download: true, text: t.checklist, onclick: endTour }));
    } else {
      if (tour.i > 0) actions.push(el("button", { type: "button", class: "btn btn-small", text: t.back, onclick: function () { goStep(tour.i - 1); } }));
      actions.push(el("button", { type: "button", class: "btn btn-small btn-primary tour-next", text: t.next, onclick: function () { goStep(tour.i + 1); } }));
    }
    box.appendChild(el("div", { class: "tour-bottom" }, [
      el("div", { class: "tour-dots", "aria-hidden": "true" }, tour.steps.map(function (s, k) {
        return el("button", { type: "button", tabindex: "-1", class: "tour-dot" + (k === tour.i ? " on" : ""), onclick: function () { goStep(k); } });
      })),
      el("div", { class: "tour-actions" }, actions)
    ]));
    var focusable = box.querySelector(".tour-next") || box.querySelector(".tour-actions .btn");
    if (focusable) focusable.focus({ preventScroll: true });
  }

  // ---------------------------------------------------------------- the network behind the title

  function drawHeroNetwork() {
    var canvas = document.querySelector(".hero-net");
    if (!canvas || !canvas.getContext) return;
    var rect = canvas.getBoundingClientRect(), ratio = Math.min(2, window.devicePixelRatio || 1);
    if (!rect.width || !rect.height) return;
    canvas.width = Math.round(rect.width * ratio);
    canvas.height = Math.round(rect.height * ratio);
    var ctx = canvas.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, rect.width, rect.height);
    // Fit the whole network above the figures, against the right edge.
    var b = NETWORK_BOX, kx = Math.cos((b[0] + b[1]) / 2 * Math.PI / 180);
    var w = (b[3] - b[2]) * kx, h = b[1] - b[0];
    var narrow = rect.width < 700;
    var statsEl = document.querySelector(".stats");
    var bottom = statsEl ? statsEl.getBoundingClientRect().top - rect.top - 16 : rect.height;
    var areaW = rect.width * (narrow ? 1.05 : 0.66), areaH = Math.max(120, bottom - 24);
    var scale = Math.min(areaW / w, areaH / h);
    var x0 = rect.width - w * scale - (narrow ? -rect.width * 0.04 : rect.width * 0.03), y0 = 12 + (areaH - h * scale) / 2;
    ctx.lineWidth = 1;
    ctx.lineJoin = "round";
    ctx.globalAlpha = 0.5;
    SHAPES.forEach(function (cls) {
      ctx.strokeStyle = C.ramp[cls];
      ctx.beginPath();
      routes.forEach(function (r) {
        if (r.shape !== cls) return;
        r.dirs.forEach(function (d) {
          d.ll.forEach(function (p, i) {
            var x = x0 + (p[1] - b[2]) * kx * scale, y = y0 + (b[1] - p[0]) * scale;
            if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y);
          });
        });
      });
      ctx.stroke();
    });
  }

  // ---------------------------------------------------------------- the address bar

  function updateHash() {
    if (tour.on) return;
    var parts = [];
    if (view !== "directness") parts.push("view=" + view);
    if (selected) parts.push("route=" + encodeURIComponent(selected.n));
    if (compareWith) parts.push("compare=" + encodeURIComponent(compareWith));
    if (view === "reach" && reachFrom !== null) parts.push("stop=" + stops[reachFrom][3]);
    var url = window.location.pathname + window.location.search + (parts.length ? "#" + parts.join("&") : "");
    try { window.history.replaceState(null, "", url); } catch (e) { /* file:// in some browsers */ }
  }
  function readHash() {
    var out = {};
    window.location.hash.slice(1).split("&").forEach(function (kv) {
      var p = kv.split("=");
      if (p.length === 2) out[p[0]] = decodeURIComponent(p[1]);
      else if (p[0]) out[p[0]] = "";                       // #tour, or a section anchor
    });
    return out;
  }
  function applyHash() {
    var h = readHash();
    if (h.tour !== undefined) { startTour(); return true; }
    if (!h.view && !h.route && !h.stop) return false;
    showView(h.view || view, true);
    if (h.stop && stopById[h.stop] !== undefined) setReach(stopById[h.stop], { zoom: true });
    if (h.route && byNumber[h.route]) select(h.route, { compare: h.compare });
    return true;
  }

  // ---------------------------------------------------------------- start

  document.querySelectorAll("[data-view]").forEach(function (b) {
    b.addEventListener("click", function () { if (tour.on) endTour(); showView(b.getAttribute("data-view")); });
  });
  document.querySelectorAll("[data-tour]").forEach(function (b) {
    b.addEventListener("click", function (e) { e.preventDefault(); startTour(); });
  });
  var search = document.getElementById("route-search");
  search.addEventListener("input", renderChips);
  search.addEventListener("keydown", function (e) {
    if (e.key !== "Enter") return;
    var raw = search.value.trim(), q = raw.toLowerCase(), f = fold(raw);
    var exact = routes.filter(function (r) { return r.n.toLowerCase() === q; })[0];
    var first = exact || routes.filter(function (r) { return r.n.toLowerCase().indexOf(q) === 0; })[0];
    if (first) { select(first.n); return; }
    var stop = f.length >= 2 ? foldedNames.findIndex(function (n) { return n.indexOf(f) >= 0; }) : -1;
    if (stop >= 0) setReach(stop, { zoom: true });
  });

  initMap();
  renderStatic();
  renderChips();
  renderIssues();
  renderTables();
  showView(view, true);
  if (applyHash()) {
    setTimeout(scrollToMap, 0);
  }
  window.addEventListener("hashchange", function () { if (!tour.on) applyHash(); });
  drawHeroNetwork();
  var resizeTimer = null;
  window.addEventListener("resize", function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(drawHeroNetwork, 150);
  });
})();
