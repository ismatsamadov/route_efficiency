/*
 * The logic of index.html: the language switch, the map and its five views, the route
 * cards, the data issues and the checklist tables. Everything shown comes from
 * site/data.js, which site/build.py writes from output/. Text that comes from the data
 * (stop names, carriers) goes into the page with textContent only.
 */
(function () {
  "use strict";

  var D = window.SITE_DATA;
  var S = D.summary;
  S.uncovered = S.population - S.covered;

  // ---------------------------------------------------------------- text

  var T = {
    az: {
      title: "Bakı avtobus şəbəkəsi",
      million: "milyon",
      routeN: "Marşrut {n}",
      placeholder: "177, 120A, M8",
      noMatch: "Belə marşrut yoxdur.",
      routesHere: "Bu yerdən keçən marşrutlar",
      stopRoutes: "{n} marşrut dayanır",
      scrollHint: "Təkərlə böyütmək üçün əvvəlcə xəritəyə klikləyin",
      close: "Bağla",
      copyLink: "Linki kopyala",
      copied: "Kopyalandı",
      show: "Xəritədə",
      shapes: { direct: "Birbaşa", indirect: "Dolayı", "very indirect": "Çox dolayı", loop: "Dairəvi" },
      ranges: { direct: "düz xəttin ən çoxu 1,4 qatı", indirect: "1,4–2 qatı", "very indirect": "2–3 qatı", loop: "3 qatından çox və ya ucları yaxın" },
      routesCount: "{n} marşrut",
      views: {
        directness: {
          name: "Birbaşalıq",
          text: "Hər marşrut yolunun uc dayanacaqları arasındakı düz xəttdən neçə dəfə uzun olduğuna görə rənglənib (iki istiqamətindən daha dolayısına görə). Tünd rəng daha dolayı deməkdir.",
          fact: "Marşrutların ümumi uzunluğu {route_km} km-dir, amma onlar yalnız {street_km} km fərqli dayanacaqlararası hissədən keçir: hər hissədən orta hesabla {per_link} marşrut."
        },
        detours: {
          name: "Dolamalar",
          text: "Avtobusun iki dayanacağı arasında düz xəttin ən azı 2,5 qatı və ən azı 1,5 km artıq yol getdiyi hissələr. Dolamanın üzərinə gəlin: qırıq xətt düz yolu göstərir.",
          fact: "Dolamalar birlikdə hər marşrutun hər istiqamətdə bir reysinə {km} km artıq yol əlavə edir. Ən uzunu {route} nömrəli marşrutdadır: hər reysə təxminən {minutes} dəqiqə.",
          nobody: "İçindəki hər kəsin 400 m-də başqa marşrutu var",
          some: "Bəzi sakinlərə yalnız bu marşrut çatır"
        },
        duplication: {
          name: "Təkrarlanma",
          text: "Narıncı marşrutların dayanacaqlarının ən azı 85%-i başqa bir marşrutda da var (ekspres marşrutlar daxil deyil). Mavi marşrutlar onları içinə alanlardır.",
          fact: "Belə {pairs} cüt var; {two} cütdə iki marşrutu fərqli daşıyıcılar işlədir.",
          inside: "Başqa marşrutun içindədir",
          host: "Belə marşrutu içinə alır"
        },
        corridors: {
          name: "Dəhlizlər",
          text: "Hər dayanacaqlararası hissəsindən ən azı 8 marşrutun keçdiyi, ən azı 1 km uzunluğunda küçə hissələri. Xəttin qalınlığı hər hissədən keçən orta marşrut sayını göstərir.",
          fact: "Bir küçə hissəsindən keçən ən çox marşrut: {max}.",
          width: "hər hissədə {n} marşrut"
        },
        coverage: {
          name: "Əhatə",
          text: "Ən yaxın dayanacaqdan düz xətlə {radius} m-dən uzaqda yaşayan sakinlər, hər altıbucaqlıda (təxminən 0,74 km²). Altıbucaqlı nə qədər tünddürsə, orada belə sakin bir o qədər çoxdur.",
          fact: "{population} sakindən {covered} nəfərin ({share}) {radius} m-də dayanacağı var. Əhali: Kontur, noyabr 2023.",
          legend: "Altıbucaqlıda belə sakinlər",
          bins: ["100-dən az", "100–500", "500–2.000", "2.000-dən çox"],
          people: "{n} sakin"
        }
      },
      tip: {
        detour: "+{min} dəq hər reysə · {km} km artıq",
        corridor: "hər hissədə orta hesabla {mean} marşrut · {km} km",
        hex: "{n} sakin {radius} m-dən uzaqda",
        inside: "dayanacaqlarının {share}-i {r} nömrəli marşrutda da var"
      },
      popup: {
        hex: "{n} sakin ən yaxın dayanacaqdan {radius} m-dən uzaqda yaşayır.",
        hexTotal: "Bu altıbucaqlıda cəmi {n} sakin var.",
        corridor: "{km} km · {stops} dayanacaq · hər hissədə orta hesabla {mean}, ən çox {max} marşrut",
        corridorRoutes: "Bu dəhlizdən keçən marşrutlar:"
      },
      card: {
        shape: "Yolu uc dayanacaqları arasındakı düz xəttdən {x} dəfə uzundur.",
        loop: "Ucları bir-birinə 1 km-dən yaxındır və ya yolu düz xəttin 3 qatından uzundur.",
        measures: "Ölçülər",
        length: "Uzunluq, bir istiqamət",
        stops: "Dayanacaqlar",
        stopsValue: "{a} və {b}",
        spacing: "Dayanacaqlar arası, median",
        short: "200 m-dən qısa aralıqlar",
        shared: "Başqa marşrutlarla ortaq yol",
        residents: "{radius} m-də yaşayan sakinlər",
        only: "Yalnız bu marşrutun çatdığı sakinlər",
        boardings: "Həftəiçi sərnişin, gündə",
        boardingsNote: "BakuBus, {month}",
        notPublished: "Dərc olunmayıb",
        notPublishedNote: "yalnız BakuBus dərc edir",
        detours: "Dolamalar",
        noDetours: "Bu marşrutda dolama yoxdur.",
        detourMeta: "+{min} dəq hər reysə (təxmini) · {km} km artıq",
        nobody: "içindəki hər kəsin başqa marşrutu var",
        some: "{n} sakinə yalnız bu marşrut çatır",
        overlap: "Təkrarlanma",
        inside: "Dayanacaqlarının çoxu bu marşrutlarda da var:",
        contains: "Bu marşrutların dayanacaqlarının çoxu onda var:",
        noOverlap: "Dayanacaqlarının 85%-i başqa heç bir marşrutda yoxdur.",
        fixes: "Xəritə məlumatında",
        straight: "{d}. istiqamətin xəritədə yararlı xətti yoxdur; burada dayanacaqlar düz xətlərlə birləşdirilib.",
        direction: "{d}. istiqamət"
      },
      fix: {
        wrong_direction: "İstiqamətlərin xətti səhv istiqamətə yazılıb",
        backwards: "{d}. istiqamətin xətti tərs ardıcıllıqla saxlanılıb",
        swapped: "{d}. istiqamətin xəttində enlik və uzunluq yerini dəyişib",
        lat_equals_lon: "{d}. istiqamətin xəttində enlik uzunluğa bərabərdir",
        scrambled: "{d}. istiqamətin xətti dayanacaqların ardıcıllığına uyğun gəlmir",
        far: "{d}. istiqamətin xətti dayanacaqlardan çox uzaqdadır",
        repeated_stops: "{d}. istiqamətin dayanacaq siyahısı iki dəfə təkrarlanır",
        no_shape: "Marşrutun xətti yoxdur"
      },
      groups: { lines: "Marşrut xətləri", table: "Marşrut cədvəli", stops: "Dayanacaqlar", fresh: "Aktuallıq" },
      units: { routes: "marşrut", directions: "istiqamət", names: "ad", stops: "dayanacaq", changes: "dəyişiklik", of: "/ {n}" },
      issues: {
        wrong_direction: ["Xətlər səhv istiqamətə yazılıb", "Bir istiqamətin xətti digər istiqamətin adı altında saxlanılıb, ona görə bir istiqaməti göstərən xəritə digərinin küçələrini çəkir."],
        backwards: ["Xətt tərs saxlanılıb", "Xəttin nöqtələri sonuncu dayanacaqdan birinciyə doğru düzülüb, dayanacaqlar isə birincidən sonuncuya."],
        swapped: ["Enlik və uzunluq yerini dəyişib", "Bu xətt Bakıdan min kilometrdən çox uzaqda çəkilir."],
        lat_equals_lon: ["Enlik uzunluğa bərabərdir", "Xəttin hər nöqtəsində iki koordinat eynidir, ona görə xətt yararsızdır."],
        scrambled: ["Xətt dayanacaqlara uyğun gəlmir", "Xəttin içində {min}–{max} km-lik düz sıçrayışlar var; bu səhifə həmin istiqamətləri dayanacaqlar arasında düz xətlərlə çəkir."],
        far: ["Xətt dayanacaqlardan uzaqdadır", "Xətt marşrutun dayanacaqlarından çox uzaqda çəkilir."],
        repeated_stops: ["Dayanacaq siyahısı təkrarlanır", "Dayanacaqların siyahısı ardıcıl iki dəfə yazılıb."],
        other: ["Başqa xəta", "Avtomatik düzəlişlərin siyahısında olan başqa bir xəta."],
        no_shape: ["Xətt yoxdur", "Marşrutun dayanacaqları var, amma xətti yoxdur; bu səhifə onu dayanacaqlar arasında düz xətlərlə çəkir."],
        no_stops: ["Dayanacaqsız marşrutlar", "Bu marşrutlar cədvəldə var, amma nə dayanacağı, nə xətti var."],
        cutoff: " 150A və 446 Pirallahını şəhərlə birləşdirir, ona görə 180 nömrəli marşrut xəritədə təcrid olunmuş görünür.",
        length: ["route_length_km gediş-dönüş uzunluğudur", "Bu sahə bir istiqamətin xəttindən median hesabla {x} dəfə uzundur, yəni gediş-dönüş uzunluğudur. Sahənin adı və ya təsviri bunu deməlidir."],
        duration: ["duration_min real vaxt deyil", "Bütün {n} marşrutda bu sahə floor(route_length_km / 0,6) düsturuna bərabərdir: gediş-dönüş boyu saatda 36 km sabit sürət."],
        api: ["Bir marşrut API-dən gəlmir", "API-nin 209 marşrut identifikatorundan biri (id 96, marşrut 144) məlumat əvəzinə xəta qaytarır."],
        cyrillic: ["Kiril hərfli adlar", "{n} dayanacağın adında ə, Ə və ya X hərfi latın deyil, kiril əlifbasındandır. Görünüşü eynidir, amma mətn axtarışı bu adları tapmaya bilər."],
        shared: ["Eyni adlı dayanacaqlar", "{n} ad birdən çox dayanacaqda işlənir; onlardan {far} ad bir-birindən 1 km-dən uzaq dayanacaqlara verilib."],
        unnamed: ["Adsız dayanacaqlar", "{n} dayanacağın koordinatı var, amma nə adı, nə də marşrutu."],
        unchanged: ["Xəritə yeni şəbəkəni göstərmir", "{scraped} tarixində API {same_as} tarixindəki məlumatı sətir-sətir eyni qaytarırdı, halbuki yeni şəbəkə 2026-cı ilin yanvarından mərhələlərlə işə salınır."],
        missing: ["Sərnişin saylarında var, xəritədə yoxdur", "BakuBus {month} üçün bu marşrutların sərnişin saylarını dərc edir, amma AYNA-nın xəritəsində onlar yoxdur."]
      },
      tables: {
        detours: {
          title: "Ən uzun dolamalar: içindəki hər kəsin başqa marşrutu var",
          note: "Əlavə vaxt xidmət növünə görə güman edilən sürətlə hesablanmış təxmindir.",
          cols: ["Marşrut", "Haradan → haraya", "Artıq yol", "Hər reysə əlavə"]
        },
        duplicates: {
          title: "Ən çox üst-üstə düşən marşrutlar",
          note: "Birinci marşrutun dayanacaqlarının neçə faizi ikincidə də var.",
          cols: ["Marşrut", "Əsasən bunun içində", "Ortaq dayanacaqlar", "Daşıyıcılar"],
          same: "eyni", different: "fərqli", of: "{a} dayanacaqdan {b}"
        },
        corridors: {
          title: "Ən sıx dəhlizlər",
          note: "Uzunluğa və hər hissədən keçən marşrut sayına görə sıralanıb.",
          cols: ["Dəhliz", "Uzunluq", "Hissədə orta", "Marşrutlar"]
        }
      }
    },

    en: {
      title: "Baku bus network",
      million: "million",
      routeN: "Route {n}",
      placeholder: "177, 120A, M8",
      noMatch: "No such route.",
      routesHere: "Routes here",
      stopRoutes: "{n} routes stop here",
      scrollHint: "Click the map first to zoom with the wheel",
      close: "Close",
      copyLink: "Copy link",
      copied: "Copied",
      show: "On map",
      shapes: { direct: "Direct", indirect: "Indirect", "very indirect": "Very indirect", loop: "Loop" },
      ranges: { direct: "at most 1.4 times the straight line", indirect: "1.4 to 2 times", "very indirect": "2 to 3 times", loop: "over 3 times, or ends close together" },
      routesCount: "{n} routes",
      views: {
        directness: {
          name: "Directness",
          text: "Each route is coloured by how many times longer its path is than the straight line between its end stops (the more roundabout of its two directions). Darker means more roundabout.",
          fact: "Together the routes run {route_km} km of route over only {street_km} km of distinct links between stops: {per_link} routes on each link on average."
        },
        detours: {
          name: "Detours",
          text: "Stretches where the bus travels at least 2.5 times the straight line between two of its stops, and at least 1.5 km more. Hover a detour: the dashed line shows the straight way.",
          fact: "Together the detours add {km} km to one trip each way on every route. The longest is on route {route}: about {minutes} minutes per trip.",
          nobody: "Everyone inside has another route within 400 m",
          some: "Some residents are reached only by this route"
        },
        duplication: {
          name: "Overlap",
          text: "At least 85% of the stops of each orange route are also served by another route (express routes are left out). Blue routes are the ones that contain them.",
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
        }
      },
      tip: {
        detour: "+{min} min per trip · {km} km extra",
        corridor: "{mean} routes per link on average · {km} km",
        hex: "{n} residents farther than {radius} m",
        inside: "{share} of its stops are on route {r}"
      },
      popup: {
        hex: "{n} residents live more than {radius} m from the nearest stop.",
        hexTotal: "{n} residents live in this hexagon.",
        corridor: "{km} km · {stops} stops · {mean} routes per link on average, {max} at most",
        corridorRoutes: "Routes on this corridor:"
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
        detours: "Detours",
        noDetours: "This route has no detours.",
        detourMeta: "+{min} min per trip (estimate) · {km} km extra",
        nobody: "everyone inside has another route",
        some: "{n} residents reached only by this route",
        overlap: "Overlap",
        inside: "Most of its stops are also served by:",
        contains: "It contains most of the stops of:",
        noOverlap: "No other route serves 85% of its stops.",
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
          note: "The extra time is an estimate from speeds assumed by type of service.",
          cols: ["Route", "From → to", "Extra distance", "Extra per trip"]
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
      }
    }
  };

  // ---------------------------------------------------------------- state

  var LANGS = ["az", "en"];
  var VIEWS = ["directness", "detours", "duplication", "corridors", "coverage"];
  var SHAPES = ["direct", "indirect", "very indirect", "loop"];
  var HEX_BINS = [100, 500, 2000];
  var CORRIDOR_WIDTHS = [8, 12, 16];
  var darkQuery = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  var motionQuery = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;

  var lang = initialLang();
  var theme = currentTheme();
  var view = "directness";
  var selected = null;
  var map = null;
  var R = {};
  var layers = {};

  var COLORS = {
    light: {
      ramp: { direct: "#86b6ef", indirect: "#3987e5", "very indirect": "#1c5cab", loop: "#0d366b" },
      hex: ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab"],
      base: "#bdbcb4", one: "#2a78d6", two: "#eb6834", ink: "#0b0b0b", casing: "#ffffff", stop: "#52514e"
    },
    dark: {
      ramp: { direct: "#1c5cab", indirect: "#2a78d6", "very indirect": "#6da7ec", loop: "#b7d3f6" },
      hex: ["#184f95", "#2a78d6", "#6da7ec", "#b7d3f6"],
      base: "#55544f", one: "#3987e5", two: "#d95926", ink: "#f0efec", casing: "#1a1a19", stop: "#c3c2b7"
    }
  };

  function C() { return COLORS[theme]; }
  function tr() { return T[lang]; }
  function currentTheme() { return darkQuery && darkQuery.matches ? "dark" : "light"; }
  function reduceMotion() { return !!(motionQuery && motionQuery.matches); }

  function initialLang() {
    var q = null;
    try { q = new URLSearchParams(window.location.search).get("lang"); } catch (e) { q = null; }
    if (LANGS.indexOf(q) >= 0) return q;
    try {
      var saved = window.localStorage.getItem("lang");
      if (LANGS.indexOf(saved) >= 0) return saved;
    } catch (e) { /* storage blocked: use the default */ }
    return "az";
  }

  // ---------------------------------------------------------------- formatting

  // Written out rather than left to Intl: browsers without Azerbaijani locale data
  // would fall back to English separators and month numbers.
  var MONTHS = {
    az: ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr"],
    en: ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
  };
  function fmt(x, digits) {
    if (x === null || x === undefined || isNaN(x)) return "–";
    digits = digits || 0;
    var parts = Math.abs(x).toFixed(digits).split(".");
    var whole = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, lang === "az" ? "." : ",");
    return (x < 0 ? "−" : "") + whole + (digits ? (lang === "az" ? "," : ".") + parts[1] : "");
  }
  function pct(x) { return fmt(Math.round(100 * x)) + "%"; }
  function millions(x) { return fmt(x / 1e6, 2) + " " + tr().million; }
  function dayText(iso) {
    var p = iso.split("-");
    return +p[2] + " " + MONTHS[lang][+p[1] - 1] + " " + p[0];
  }
  function monthText(ym) {
    var p = ym.split("-");
    return MONTHS[lang][+p[1] - 1] + " " + p[0];
  }
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

  var stops = D.stops;
  var routes = D.routes;
  var byNumber = {};
  routes.forEach(function (r) {
    byNumber[r.n] = r;
    r.dirs.forEach(function (d) { d.ll = decode(d.line); d.box = bbox(d.ll); });
    r.box = joinBoxes(r.dirs.map(function (d) { return d.box; }));
    r.detourList = [];
    r.inside = [];
    r.contains = [];
    r.fixes = [];
  });
  D.detours.forEach(function (d) { d.ll = decode(d.line); d.box = bbox(d.ll); byNumber[d.r].detourList.push(d); });
  D.duplicates.forEach(function (p) { byNumber[p.r].inside.push(p); byNumber[p["in"]].contains.push(p); });
  D.corridors.forEach(function (c) { c.ll = decode(c.line); c.box = bbox(c.ll); });
  D.hexes.forEach(function (h) { h.ll = decode(h[0]); h.box = bbox(h.ll); h.people = h[1]; h.total = h[2]; });
  D.issues.repairs.forEach(function (f) { if (byNumber[f.route]) byNumber[f.route].fixes.push(f); });
  D.issues.no_shape.forEach(function (n) { if (byNumber[n]) byNumber[n].fixes.push({ kind: "no_shape", direction: null }); });
  var NETWORK_BOX = joinBoxes(routes.map(function (r) { return r.box; }));
  var atStop = stops.map(function () { return []; });
  routes.forEach(function (r) {
    r.dirs.forEach(function (d) {
      d.stops.forEach(function (s) { if (atStop[s].indexOf(r.n) < 0) atStop[s].push(r.n); });
    });
  });
  var longest = D.detours.reduce(function (a, b) { return b.minutes > a.minutes ? b : a; });

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
    document.querySelectorAll("[data-download]").forEach(function (a) { a.setAttribute("href", "site/checklist-" + lang + ".xlsx"); });
    document.getElementById("route-search").setAttribute("placeholder", tr().placeholder);
    document.title = tr().title;
  }

  function setLang(l, save) {
    lang = l;
    document.documentElement.lang = l;
    document.querySelectorAll("[data-set-lang]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-set-lang") === l));
    });
    if (save) {
      try { window.localStorage.setItem("lang", l); } catch (e) { /* not remembered: fine */ }
    }
    renderStatic();
    renderPanel();
    renderChips();
    renderCard();
    renderIssues();
    renderTables();
    setSelectedChip();
    if (map) map.closePopup();
  }

  // ---------------------------------------------------------------- map

  // OpenStreetMap's own tiles: no key needed, names in Azerbaijani. style.css greys them
  // (and inverts them in dark mode) so the routes carry the colour.
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
    layers.hover = L.layerGroup().addTo(map);
    layers.sel = L.layerGroup().addTo(map);

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
      if (!map.scrollWheelZoom.enabled()) flashHint(tr().scrollHint);
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

  function routeWeight() {
    var z = map.getZoom();
    return z >= 15 ? 3.4 : z >= 13 ? 2.6 : z >= 11.5 ? 2 : 1.6;
  }

  function styleRoutes() {
    if (!map) return;
    var c = C(), w = routeWeight(), dim = selected ? 0.55 : 1;
    layers.routes.forEach(function (line) {
      if (view === "directness") {
        line.setStyle({ color: c.ramp[line.route.shape], weight: w, opacity: 0.92 * dim });
      } else {
        line.setStyle({ color: c.base, weight: Math.max(1.2, w - 0.6), opacity: (view === "coverage" ? 0.6 : 0.85) * dim });
      }
    });
  }

  function corridorWidth(mean) { return 3 + (Math.min(mean, 18) - 6) * 0.75; }
  function hexBin(n) { var i = 0; while (i < HEX_BINS.length && n >= HEX_BINS[i]) i++; return i; }

  function buildOverlay(name) {
    var c = C(), g = L.layerGroup();
    if (name === "detours") {
      D.detours.forEach(function (d) {
        g.addLayer(L.polyline(d.ll, { renderer: R.overlay, interactive: false, lineCap: "round", lineJoin: "round",
          color: d.pop_only === 0 ? c.two : c.one, weight: 4, opacity: 0.95 }));
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
              color: c[k], weight: kind[1], opacity: 0.92 }));
          });
        });
      });
    } else if (name === "corridors") {
      D.corridors.forEach(function (k) {
        g.addLayer(L.polyline(k.ll, { renderer: R.overlay, interactive: false, lineCap: "round", lineJoin: "round",
          color: c.two, weight: corridorWidth(k.mean), opacity: 0.88 }));
      });
    } else if (name === "coverage") {
      // The lowest bin recedes: those hexagons are mostly sparse outskirts.
      var opacity = [0.22, 0.5, 0.68, 0.8];
      D.hexes.forEach(function (h) {
        var i = hexBin(h.people);
        g.addLayer(L.polygon(h.ll, { renderer: R.overlay, interactive: false, stroke: false,
          fillColor: c.hex[i], fillOpacity: opacity[i] }));
      });
      stops.forEach(function (s) {
        g.addLayer(L.circleMarker([s[0], s[1]], { renderer: R.overlay, interactive: false, radius: 1.4,
          stroke: false, fillColor: c.stop, fillOpacity: 0.65 }));
      });
    }
    return g;
  }

  function showView(name, keepHash) {
    view = VIEWS.indexOf(name) >= 0 ? name : "directness";
    document.querySelectorAll("[data-view]").forEach(function (b) {
      b.setAttribute("aria-selected", String(b.getAttribute("data-view") === view));
    });
    if (map) {
      if (layers.overlay) layers.overlay.remove();
      layers.overlay = view === "directness" ? null : buildOverlay(view).addTo(map);
      layers.hover.clearLayers();
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
    drawSelection();
    renderCard();
    renderChips();
    renderPanel();
    setSelectedChip();
    updateHash();
    if (r && map && !opts.noZoom) {
      var b = opts.box || r.box;
      map.fitBounds(toBounds(b), { padding: [48, 48], maxZoom: opts.box ? 15 : 14.5, animate: !reduceMotion() });
    }
    if (r && opts.scroll) document.getElementById("map").scrollIntoView({ behavior: reduceMotion() ? "auto" : "smooth" });
  }

  function drawSelection() {
    if (!map) return;
    layers.sel.clearLayers();
    styleRoutes();
    if (!selected) return;
    var c = C();
    selected.dirs.forEach(function (d) {
      layers.sel.addLayer(L.polyline(d.ll, { renderer: R.select, interactive: false, color: c.casing, weight: 9, opacity: 1, lineCap: "round", lineJoin: "round" }));
    });
    selected.dirs.forEach(function (d) {
      layers.sel.addLayer(L.polyline(d.ll, { renderer: R.select, interactive: false, color: c.ink, weight: 3.6, opacity: 1, lineCap: "round", lineJoin: "round" }));
    });
    selected.detourList.forEach(function (d) {
      layers.sel.addLayer(L.polyline(d.ll, { renderer: R.select, interactive: false, color: d.pop_only === 0 ? c.two : c.one,
        weight: 4.2, opacity: 1, lineCap: "round", lineJoin: "round" }));
    });
    var seen = {};
    selected.dirs.forEach(function (d) {
      d.stops.forEach(function (s) {
        if (seen[s]) return;
        seen[s] = true;
        layers.sel.addLayer(L.circleMarker([stops[s][0], stops[s][1]], { renderer: R.select, interactive: false,
          radius: 3.6, color: c.ink, weight: 1.6, fillColor: c.casing, fillOpacity: 1 }));
      });
    });
  }

  function setSelectedChip() {
    var box = document.querySelector(".map-selected");
    if (!box) return;
    clear(box);
    if (!selected || !map) { box.hidden = true; return; }
    box.appendChild(el("span", { text: fill(tr().routeN, { n: selected.n }) }));
    box.appendChild(el("button", { type: "button", "aria-label": tr().close, text: "×", onclick: function () { select(null); } }));
    box.hidden = false;
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
    if (selected) {
      var seen = {};
      selected.dirs.forEach(function (d) {
        d.stops.forEach(function (s) {
          if (seen[s]) return;
          seen[s] = true;
          var dx = (stops[s][1] - lon) * kx, dy = (stops[s][0] - lat) * ky, m = Math.sqrt(dx * dx + dy * dy);
          if (m <= tol * 0.8) out.push({ type: "stop", item: s, d: m });
        });
      });
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
      for (var i = 0; i < D.hexes.length; i++) {
        var h = D.hexes[i];
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
    layers.hover && layers.hover.clearLayers();
    if (map) map.getContainer().style.cursor = "";
  }

  function showTip(e, hits) {
    var tip = document.querySelector(".map-tip");
    layers.hover.clearLayers();
    if (!hits.length) { hideTip(); return; }
    var h = hits[0], c = C(), t = tr(), title = "", sub = "";
    map.getContainer().style.cursor = h.type === "hex" ? "" : "pointer";
    if (h.type === "stop") {
      title = stops[h.item][2] || "–";
      sub = fill(t.stopRoutes, { n: fmt(atStop[h.item].length) });
    } else if (h.type === "detour") {
      var d = h.item;
      title = fill(t.routeN, { n: d.r }) + " · " + stops[d.a][2] + " → " + stops[d.b][2];
      sub = fill(t.tip.detour, { min: fmt(d.minutes, 1), km: fmt(d.excess, 1) });
      layers.hover.addLayer(L.polyline(d.ll, { renderer: R.hover, interactive: false, color: c.ink, weight: 5, opacity: 0.85, lineCap: "round" }));
      layers.hover.addLayer(L.polyline([[stops[d.a][0], stops[d.a][1]], [stops[d.b][0], stops[d.b][1]]],
        { renderer: R.hover, interactive: false, color: c.ink, weight: 2, dashArray: "5 6", opacity: 0.9 }));
    } else if (h.type === "corridor") {
      var k = h.item;
      title = k.from + " → " + (k.via ? k.via + " → " : "") + k.to;
      sub = fill(t.tip.corridor, { mean: fmt(k.mean, 1), km: fmt(k.km, 1) });
      layers.hover.addLayer(L.polyline(k.ll, { renderer: R.hover, interactive: false, color: c.ink, weight: corridorWidth(k.mean) + 2, opacity: 0.35, lineCap: "round" }));
    } else if (h.type === "route") {
      var numbers = [];
      hits.forEach(function (x) { if (x.type === "route" && numbers.indexOf(x.item.n) < 0) numbers.push(x.item.n); });
      var r = h.item;
      title = numbers.length > 1 ? numbers.slice(0, 8).join(", ") + (numbers.length > 8 ? " +" + (numbers.length - 8) : "")
                                 : fill(t.routeN, { n: r.n });
      if (numbers.length === 1) {
        if (view === "duplication" && r.inside.length) {
          var p = r.inside[0];
          sub = fill(t.tip.inside, { share: pct(p.share), r: p["in"] });
        } else {
          sub = t.shapes[r.shape];
        }
        r.dirs.forEach(function (dd) {
          layers.hover.addLayer(L.polyline(dd.ll, { renderer: R.hover, interactive: false, color: c.ink, weight: 3.2, opacity: 0.75, lineCap: "round" }));
        });
      }
    } else if (h.type === "hex") {
      title = fill(t.tip.hex, { n: fmt(h.item.people), radius: fmt(D.meta.radius_m) });
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
    var hits = hitsAt(e.latlng, 12), t = tr();
    hideTip();
    if (!hits.length) return;
    var h = hits[0];
    function pick(n) { map.closePopup(); select(n); }
    if (h.type === "stop") {
      openPopup(e.latlng, [el("div", { class: "popup-title", text: stops[h.item][2] || "–" }),
        el("div", { class: "popup-meta", text: fill(t.stopRoutes, { n: fmt(atStop[h.item].length) }) }),
        routeChips(atStop[h.item], pick)]);
    } else if (h.type === "detour") {
      select(h.item.r, { box: h.item.box });
    } else if (h.type === "corridor") {
      var k = h.item;
      openPopup(e.latlng, [el("div", { class: "popup-title", text: k.from + " → " + (k.via ? k.via + " → " : "") + k.to }),
        el("div", { class: "popup-meta", text: fill(t.popup.corridor, { km: fmt(k.km, 1), stops: fmt(k.stops), mean: fmt(k.mean, 1), max: fmt(k.max) }) }),
        el("div", { class: "popup-meta", text: t.popup.corridorRoutes }),
        routeChips(k.routes, pick)]);
    } else if (h.type === "route") {
      var numbers = [];
      hits.forEach(function (x) { if (x.type === "route" && numbers.indexOf(x.item.n) < 0) numbers.push(x.item.n); });
      if (numbers.length === 1) select(numbers[0], { noZoom: true });
      else openPopup(e.latlng, [el("div", { class: "popup-title", text: t.routesHere }), routeChips(numbers, pick)]);
    } else if (h.type === "hex") {
      openPopup(e.latlng, [el("div", { class: "popup-title", text: fill(t.popup.hex, { n: fmt(h.item.people), radius: fmt(D.meta.radius_m) }) }),
        el("div", { class: "popup-meta", text: fill(t.popup.hexTotal, { n: fmt(h.item.total) }) })]);
    }
  }

  // ---------------------------------------------------------------- the panel: view, finder, card

  function legendLine(color, label, count, note) {
    return el("li", null, [
      el("span", { class: "key-line", style: "background:" + color }),
      el("span", null, [label, note ? el("small", { text: note }) : null]),
      el("span", { class: "count", text: count })
    ]);
  }

  function renderPanel() {
    var box = document.querySelector(".panel-view");
    clear(box);
    box.hidden = !!selected;
    if (selected) return;
    var t = tr(), v = t.views[view], c = C(), list = el("ul", { class: "legend" });
    box.appendChild(el("h3", { text: v.name }));
    var radius = fmt(D.meta.radius_m);
    box.appendChild(el("p", { text: fill(v.text, { radius: radius }) }));
    if (view === "directness") {
      SHAPES.forEach(function (s) { list.appendChild(legendLine(c.ramp[s], t.shapes[s], fill(t.routesCount, { n: fmt(S.shapes[s]) }), t.ranges[s])); });
      box.appendChild(list);
      box.appendChild(el("p", { class: "fact" }, [rich(v.fact, { route_km: fmt(S.route_km), street_km: fmt(S.street_km), per_link: fmt(S.routes_per_link, 2) })]));
    } else if (view === "detours") {
      var nobody = S.detours_nobody_only;
      list.appendChild(legendLine(c.two, v.nobody, fmt(nobody)));
      list.appendChild(legendLine(c.one, v.some, fmt(S.detours - nobody)));
      box.appendChild(list);
      box.appendChild(el("p", { class: "fact" }, [rich(v.fact, { km: fmt(S.detour_km), route: longest.r, minutes: fmt(longest.minutes, 1) })]));
    } else if (view === "duplication") {
      var inside = {}, host = {};
      D.duplicates.forEach(function (p) { inside[p.r] = true; host[p["in"]] = true; });
      var hosts = Object.keys(host).filter(function (n) { return !inside[n]; }).length;
      list.appendChild(legendLine(c.two, v.inside, fill(t.routesCount, { n: fmt(Object.keys(inside).length) })));
      list.appendChild(legendLine(c.one, v.host, fill(t.routesCount, { n: fmt(hosts) })));
      box.appendChild(list);
      box.appendChild(el("p", { class: "fact" }, [rich(v.fact, { pairs: fmt(S.duplicate_pairs), two: fmt(S.duplicate_pairs_two_carriers) })]));
    } else if (view === "corridors") {
      CORRIDOR_WIDTHS.forEach(function (n) {
        list.appendChild(el("li", null, [
          el("span", { class: "key-line", style: "background:" + c.two + ";height:" + corridorWidth(n).toFixed(1) + "px" }),
          el("span", { text: fill(v.width, { n: fmt(n) }) }), el("span")
        ]));
      });
      box.appendChild(list);
      box.appendChild(el("p", { class: "fact" }, [rich(v.fact, { max: fmt(S.most_routes_on_a_link) })]));
    } else if (view === "coverage") {
      var sums = [0, 0, 0, 0];
      D.hexes.forEach(function (h) { sums[hexBin(h.people)] += h.people; });
      box.appendChild(el("p", { class: "legend-title", text: v.legend }));
      v.bins.forEach(function (label, i) {
        list.appendChild(el("li", null, [
          el("span", { class: "key-box", style: "background:" + c.hex[i] }),
          el("span", { text: label }),
          el("span", { class: "count", text: fill(v.people, { n: fmt(sums[i]) }) })
        ]));
      });
      list.style.marginTop = "8px";
      box.appendChild(list);
      box.appendChild(el("p", { class: "fact" }, [rich(v.fact, { population: millions(S.population), covered: millions(S.covered), share: pct(S.covered / S.population), radius: radius })]));
    }
  }

  function renderChips() {
    var box = document.querySelector(".route-chips");
    var q = document.getElementById("route-search").value.trim().toLowerCase();
    clear(box);
    var shown = routes.filter(function (r) { return !q || r.n.toLowerCase().indexOf(q) === 0; });
    if (!shown.length) { box.appendChild(el("p", { class: "finder-empty", text: tr().noMatch })); return; }
    shown.forEach(function (r) {
      box.appendChild(el("button", { type: "button", class: "chip", role: "listitem", text: r.n,
        "aria-current": selected === r ? "true" : null, onclick: function () { select(r.n); } }));
    });
  }

  function fact(label, value, note) {
    return el("div", null, [el("dt", { text: label }), el("dd", null, [value, note ? el("small", { text: note }) : null])]);
  }

  function fixText(f) {
    var t = tr();
    var template = t.fix[f.kind];
    if (!template) return f.text || "";
    return fill(template, { d: f.direction || "" });
  }

  function renderCard() {
    var box = document.querySelector(".card");
    clear(box);
    if (!selected) { box.hidden = true; return; }
    box.hidden = false;
    var r = selected, t = tr(), k = t.card, c = C();
    var zone = lang === "az" ? r.zone : r.zone_en, region = lang === "az" ? r.region : r.region_en;
    box.appendChild(el("div", { class: "card-head" }, [
      el("div", { class: "card-num", text: r.n }),
      el("div", null, [
        el("div", { class: "card-ends", text: (r.from || "–") + " — " + (r.to || "–") }),
        el("div", { class: "card-meta", text: [r.carrier, zone, region, fmt(r.fare, 2) + " AZN"].filter(Boolean).join(" · ") })
      ]),
      el("button", { type: "button", class: "card-close", "aria-label": t.close, text: "×", onclick: function () { select(null); } })
    ]));
    box.appendChild(el("div", { class: "badge" }, [el("i", { style: "background:" + c.ramp[r.shape] }), t.shapes[r.shape]]));
    var shapeText = r.shape === "loop" && !(r.circuity > 3) ? k.loop : fill(k.shape, { x: fmt(r.circuity, 2) });
    box.appendChild(el("p", { class: "card-shape", text: shapeText }));

    box.appendChild(el("h4", { text: k.measures }));
    var counts = r.dirs.map(function (d) { return d.stops.length; });
    var radius = fmt(D.meta.radius_m);
    box.appendChild(el("dl", { class: "facts" }, [
      fact(k.length, fmt(r.km, 1) + " km"),
      fact(k.stops, counts.length === 2 ? fill(k.stopsValue, { a: fmt(counts[0]), b: fmt(counts[1]) }) : fmt(counts[0])),
      fact(k.spacing, fmt(r.gap) + " m"),
      fact(k.short, fmt(r.gaps200)),
      fact(k.shared, pct(r.shared)),
      fact(fill(k.residents, { radius: radius }), fmt(r.pop)),
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
          if (map) map.fitBounds(toBounds(d.box), { padding: [60, 60], maxZoom: 16, animate: !reduceMotion() });
        } }, [
          el("div", { class: "item-title", text: stops[d.a][2] + " → " + stops[d.b][2] }),
          el("div", { class: "item-meta" }, [
            el("span", { class: "tag", style: "background:" + (d.pop_only === 0 ? c.two : c.one) }),
            fill(k.detourMeta, { min: fmt(d.minutes, 1), km: fmt(d.excess, 1) }) + " · " + fill(k.direction, { d: d.d })
          ]),
          el("div", { class: "item-meta", text: d.pop_only === 0 ? k.nobody : fill(k.some, { n: fmt(d.pop_only) }) })
        ])]);
      })));
    }

    box.appendChild(el("h4", { text: k.overlap }));
    if (!r.inside.length && !r.contains.length) box.appendChild(el("p", { class: "card-note", text: k.noOverlap }));
    function pairChips(pairs, key) {
      return el("div", { class: "chips" }, pairs.map(function (p) {
        var n = p[key];
        return el("button", { type: "button", class: "chip", onclick: function () { select(n); } }, [n, el("small", { text: pct(p.share) })]);
      }));
    }
    if (r.inside.length) { box.appendChild(el("p", { class: "card-note", text: k.inside })); box.appendChild(pairChips(r.inside, "in")); }
    if (r.contains.length) {
      box.appendChild(el("p", { class: "card-note", text: k.contains, style: r.inside.length ? "margin-top:12px" : null }));
      box.appendChild(pairChips(r.contains, "r"));
    }

    var notes = r.fixes.map(fixText);
    r.straight.forEach(function (d) { notes.push(fill(k.straight, { d: d })); });
    if (notes.length) {
      box.appendChild(el("h4", { text: k.fixes }));
      box.appendChild(el("ul", { class: "items" }, notes.filter(function (x, i) { return notes.indexOf(x) === i; }).map(function (text) {
        return el("li", { class: "card-note", text: "• " + text });
      })));
    }

    var copy = el("button", { type: "button", class: "btn", text: t.copyLink, onclick: function () {
      var url = window.location.href;
      var done = function () { copy.textContent = t.copied; setTimeout(function () { copy.textContent = t.copyLink; }, 1600); };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(done, function () { window.prompt("", url); });
      else window.prompt("", url);
    } });
    box.appendChild(el("div", { class: "card-actions" }, [copy]));
  }

  // ---------------------------------------------------------------- data issues

  function issueCard(kind, count, unit, body, chips) {
    var t = tr();
    return el("article", { class: "issue" }, [
      el("div", { class: "issue-count" }, [count, unit ? el("small", { text: unit }) : null]),
      el("h4", { text: t.issues[kind][0] }),
      el("p", null, [body]),
      chips || null
    ]);
  }

  function renderIssues() {
    var box = document.querySelector(".issues");
    clear(box);
    var t = tr(), u = t.units, I = D.issues;
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
      lines.push(issueCard(kind, fmt(count), perRoute ? u.routes : u.directions, fill(t.issues[kind][1], vals), repairChips(shown)));
    });
    if (I.no_shape.length) lines.push(issueCard("no_shape", fmt(I.no_shape.length), u.routes, t.issues.no_shape[1], routeChips(I.no_shape, goTo)));

    var table = [];
    var cut = I.no_stops.indexOf("150A") >= 0 && I.no_stops.indexOf("446") >= 0 && byNumber["180"];
    table.push(issueCard("no_stops", fmt(I.no_stops.length), u.routes, t.issues.no_stops[1] + (cut ? t.issues.cutoff : ""), routeChips(I.no_stops, goTo)));
    table.push(issueCard("length", fmt(I.length_round_trip_median, 2) + "×", null, fill(t.issues.length[1], { x: fmt(I.length_round_trip_median, 2) })));
    table.push(issueCard("duration", fmt(I.duration_formula), fill(u.of, { n: fmt(I.routes_in_table) }), fill(t.issues.duration[1], { n: fmt(I.routes_in_table) })));

    var stopsGroup = [
      issueCard("cyrillic", fmt(I.cyrillic_names), u.names, fill(t.issues.cyrillic[1], { n: fmt(I.cyrillic_names) })),
      issueCard("shared", fmt(I.shared_names), u.names, fill(t.issues.shared[1], { n: fmt(I.shared_names), far: fmt(I.shared_names_far_apart) })),
      issueCard("unnamed", fmt(I.unnamed_unused_stops), u.stops, fill(t.issues.unnamed[1], { n: fmt(I.unnamed_unused_stops) }))
    ];

    var fresh = [
      issueCard("unchanged", "0", u.changes, fill(t.issues.unchanged[1], { scraped: dayText(D.meta.scraped), same_as: dayText(D.meta.same_as) })),
      issueCard("missing", fmt(I.missing_from_map.length), u.routes, fill(t.issues.missing[1], { month: monthText(I.counts_month) }), routeChips(I.missing_from_map, goTo)),
      issueCard("api", "1", u.routes, t.issues.api[1])
    ];

    [["lines", lines], ["table", table], ["fresh", fresh], ["stops", stopsGroup]].forEach(function (g) {
      box.appendChild(el("section", { class: "issue-group" }, [el("h3", { text: t.groups[g[0]] }), el("div", { class: "issue-grid" }, g[1])]));
    });
  }

  // ---------------------------------------------------------------- checklist tables

  function goButton(onclick) {
    return el("button", { type: "button", class: "go", onclick: onclick }, [tr().show, icon(ARROW)]);
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
    var t = tr().tables, c;

    c = t.detours.cols;
    var detours = D.detours.filter(function (d) { return d.pop_only === 0; }).sort(function (a, b) { return b.minutes - a.minutes; }).slice(0, 10);
    box.appendChild(table(t.detours, [{ label: c[0], route: true }, { label: c[1] }, { label: c[2], num: true }, { label: c[3], num: true }],
      detours.map(function (d) {
        return {
          cells: [d.r, [stops[d.a][2] + " → " + stops[d.b][2], el("span", { class: "sub", text: fill(tr().card.direction, { d: d.d }) })],
            fmt(d.excess, 1) + " km", "+" + fmt(d.minutes, 1) + (lang === "az" ? " dəq" : " min")],
          go: function () { showView("detours"); select(d.r, { box: d.box, scroll: true }); }
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
          go: function () { showView("duplication"); select(p.r, { scroll: true }); }
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
            document.getElementById("map").scrollIntoView({ behavior: reduceMotion() ? "auto" : "smooth" });
            if (map) map.fitBounds(toBounds(k.box), { padding: [60, 60], maxZoom: 15, animate: !reduceMotion() });
          }
        };
      })));
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
    var stats = document.querySelector(".stats");
    var bottom = stats ? stats.getBoundingClientRect().top - rect.top - 16 : rect.height;
    var areaW = rect.width * (narrow ? 1.05 : 0.66), areaH = Math.max(120, bottom - 24);
    var scale = Math.min(areaW / w, areaH / h);
    var x0 = rect.width - w * scale - (narrow ? -rect.width * 0.04 : rect.width * 0.03), y0 = 12 + (areaH - h * scale) / 2;
    var colors = C().ramp;
    ctx.lineWidth = 1;
    ctx.lineJoin = "round";
    ctx.globalAlpha = theme === "dark" ? 0.55 : 0.5;
    SHAPES.forEach(function (cls) {
      ctx.strokeStyle = colors[cls];
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
    var parts = [];
    if (view !== "directness") parts.push("view=" + view);
    if (selected) parts.push("route=" + encodeURIComponent(selected.n));
    var url = window.location.pathname + window.location.search + (parts.length ? "#" + parts.join("&") : "");
    try { window.history.replaceState(null, "", url); } catch (e) { /* file:// in some browsers */ }
  }
  function readHash() {
    var out = {};
    window.location.hash.slice(1).split("&").forEach(function (kv) {
      var p = kv.split("=");
      if (p.length === 2) out[p[0]] = decodeURIComponent(p[1]);
    });
    return out;
  }
  function applyHash() {
    var h = readHash();
    if (!h.view && !h.route) return false;
    showView(h.view || view, true);
    if (h.route && byNumber[h.route]) select(h.route);
    return true;
  }

  // ---------------------------------------------------------------- start

  function onTheme() {
    theme = currentTheme();
    if (map) {
      showView(view, true);
      drawSelection();
    }
    renderPanel();
    renderCard();
    drawHeroNetwork();
  }

  document.querySelectorAll("[data-set-lang]").forEach(function (b) {
    b.addEventListener("click", function () { setLang(b.getAttribute("data-set-lang"), true); });
  });
  document.querySelectorAll("[data-view]").forEach(function (b) {
    b.addEventListener("click", function () { showView(b.getAttribute("data-view")); });
  });
  var search = document.getElementById("route-search");
  search.addEventListener("input", renderChips);
  search.addEventListener("keydown", function (e) {
    if (e.key !== "Enter") return;
    var q = search.value.trim().toLowerCase();
    var exact = routes.filter(function (r) { return r.n.toLowerCase() === q; })[0];
    var first = exact || routes.filter(function (r) { return r.n.toLowerCase().indexOf(q) === 0; })[0];
    if (first) select(first.n);
  });

  initMap();
  setLang(lang, false);
  showView(view, true);
  if (applyHash()) {
    setTimeout(function () { document.getElementById("map").scrollIntoView(); }, 0);
  }
  window.addEventListener("hashchange", function () { applyHash(); });
  drawHeroNetwork();
  var resizeTimer = null;
  window.addEventListener("resize", function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(drawHeroNetwork, 150);
  });
  if (darkQuery) {
    if (darkQuery.addEventListener) darkQuery.addEventListener("change", onTheme);
    else if (darkQuery.addListener) darkQuery.addListener(onTheme);
  }
})();
