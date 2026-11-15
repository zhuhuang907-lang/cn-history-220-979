/* cn-history-220-979 — static browser for catalog, game data and periods.
   No dependencies. Data is loaded from site/data/*.json. */
(function () {
  "use strict";

  const DATA = "data/";
  const TABS = ["catalog", "faction", "character", "event", "location", "glossary", "disambiguation", "period"];
  const GAME_KEYS = {
    faction: "factions",
    character: "characters",
    event: "events",
    location: "locations",
    glossary: "glossary",
    disambiguation: "disambiguation",
  };
  const KIND_LABELS = {
    catalog: "史料",
    faction: "政权",
    character: "人物",
    event: "事件",
    location: "地点",
    glossary: "术语",
    disambiguation: "同名辨析",
    period: "时代",
  };
  const TYPE_LABELS = {
    primary: "古籍",
    modern: "现代研究",
    fiction: "小说/演义",
    database: "数据库/工具",
    empire: "帝国",
    kingdom: "王国",
    dynasty: "王朝",
    warlord: "军阀",
    "regional-regime": "地方政权",
    "tribal-confederation": "部族联盟",
    rebel: "起义军",
    garrison: "军镇",
    "city-state": "城邦",
    war: "战争",
    battle: "战役",
    rebellion: "起义/叛乱",
    coup: "政变",
    succession: "继位/代立",
    reform: "改革",
    treaty: "条约",
    massacre: "屠杀",
    migration: "迁徙",
    disaster: "灾害",
    cultural: "文化",
    religious: "宗教",
    administrative: "行政",
    diplomatic: "外交",
    capital: "都城",
    city: "城市",
    fortress: "堡垒",
    pass: "关隘",
    region: "区域",
    river: "河流",
    port: "港口",
    "religious-site": "宗教圣地",
    battlefield: "战场",
    institution: "制度",
    military: "军事",
    economy: "经济",
    society: "社会",
    ethnicity: "民族",
    religion: "宗教",
    culture: "文化",
    geography: "地理",
    title: "官称",
    law: "法律",
  };
  const RELIABILITY_TITLES = {
    A: "正史、编年史、政书或同时代原始文献",
    "A/B": "基本可靠，但有后世辑佚或整理",
    B: "别史、方志、笔记、文集、碑志",
    "B/C": "混合来源、成书较晚",
    C: "类书、总集、后世汇编",
    M: "现代研究（仅书目）",
    F: "小说、演义、影视（非史实）",
    D: "数据库、工具书、地图集",
  };
  const PRIORITY_LABELS = { core: "核心", extended: "扩展", reference: "参考" };
  const FULLTEXT_LABELS = { included: "库内全文", partial: "部分全文", external: "仅外链" };
  const PERIOD_ORDER = [
    "东汉末", "三国", "西晋", "东晋", "十六国", "南朝", "北朝", "隋",
    "初唐", "盛唐", "中唐", "晚唐", "五代", "十国", "宋初统一",
    "宋初", "唐", "两晋", "魏晋", "南北朝", "宋", "跨期", "秦汉", "两汉", "先秦",
  ];

  const state = {
    tab: "catalog",
    query: "",
    type: "",
    period: "",
    reliability: "",
    sort: "default",
    catalog: [],
    catalogById: new Map(),
    periods: [],
    periodById: new Map(),
    texts: {},
    stats: {},
    gameIndex: {},
    game: {},
    maps: {},
    selected: null,
  };

  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    if (attrs) {
      for (const [key, value] of Object.entries(attrs)) {
        if (value === undefined || value === null || value === false) continue;
        if (key === "class") node.className = value;
        else if (key === "text") node.textContent = value;
        else if (key === "dataset") Object.assign(node.dataset, value);
        else if (key.startsWith("on") && typeof value === "function") {
          node.addEventListener(key.slice(2).toLowerCase(), value);
        } else {
          node.setAttribute(key, value === true ? "" : String(value));
        }
      }
    }
    for (const child of children.flat(Infinity)) {
      if (child === undefined || child === null || child === false) continue;
      node.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return node;
  }

  function fmtInt(value) {
    if (value === undefined || value === null || Number.isNaN(Number(value))) return "—";
    return new Intl.NumberFormat("zh-CN").format(Number(value));
  }

  function fmtYear(value) {
    if (value === undefined || value === null || value === "") return "—";
    const n = Number(value);
    if (Number.isNaN(n)) return String(value);
    return n < 0 ? "前" + fmtInt(Math.abs(n)) : fmtInt(n);
  }

  function fmtRange(start, end) {
    if (start === undefined || start === null) {
      if (end === undefined || end === null) return "—";
      return "–" + fmtYear(end);
    }
    if (end === undefined || end === null) return fmtYear(start) + "–";
    return fmtYear(start) + "–" + fmtYear(end);
  }

  function label(value, fallback) {
    return TYPE_LABELS[value] || fallback || value || "—";
  }

  function statusLabel(value) {
    return FULLTEXT_LABELS[value] || value || "—";
  }

  function itemName(item, tab) {
    if (!item) return "—";
    if (tab === "catalog") return item.title || item.id;
    if (tab === "glossary") return item.term || item.id;
    if (tab === "disambiguation") return item.term || item.id;
    if (tab === "period") return item.name || item.id;
    return item.name || item.id;
  }

  function itemSubtitle(item, tab) {
    if (!item) return "";
    if (tab === "catalog") {
      const authors = (item.authors || []).map((a) => a.name).filter(Boolean).join("、");
      const parts = [];
      if (authors) parts.push(authors);
      if (item.date) parts.push(item.date);
      if (item.title_en) parts.push(item.title_en);
      return parts.join(" · ");
    }
    if (tab === "faction") {
      return [label(item.type), item.period, fmtRange(item.start, item.end)].filter(Boolean).join(" · ");
    }
    if (tab === "character") {
      const faction = state.maps.faction && state.maps.faction.get(item.faction_id);
      return [faction ? faction.name : item.faction_id, item.period, (item.roles || []).join("、")].filter(Boolean).join(" · ");
    }
    if (tab === "event") {
      const loc = state.maps.location && state.maps.location.get(item.location_id);
      return [fmtYear(item.year), label(item.type), loc ? loc.name : ""].filter(Boolean).join(" · ");
    }
    if (tab === "location") {
      return [label(item.type), item.modern_name].filter(Boolean).join(" · ");
    }
    if (tab === "glossary") {
      return [label(item.category), (item.periods || []).join("、")].filter(Boolean).join(" · ");
    }
    if (tab === "disambiguation") {
      const n = (item.conflicts || []).length;
      return n ? n + " 组同名实体" : "同名辨析";
    }
    if (tab === "period") {
      return fmtRange(item.start, item.end);
    }
    return "";
  }

  function itemSummary(item, tab) {
    if (!item) return "";
    if (tab === "catalog") return item.summary || "";
    if (tab === "glossary") return item.definition || "";
    if (tab === "disambiguation") return item.guidance || "";
    return item.summary || "";
  }

  function itemPeriods(item, tab) {
    if (!item) return [];
    if (tab === "catalog") return item.periods || [];
    if (tab === "faction" || tab === "character" || tab === "event") return item.period ? [item.period] : [];
    if (tab === "location" || tab === "glossary") return item.periods || [];
    if (tab === "disambiguation") return (item.conflicts || []).map((c) => c.period).filter(Boolean);
    if (tab === "period") return item.name ? [item.name] : [];
    return [];
  }

  function itemYear(item, tab) {
    if (!item) return Infinity;
    if (tab === "catalog") return item.cover_start ?? Infinity;
    if (tab === "faction") return item.start ?? Infinity;
    if (tab === "character") return item.birth ?? Infinity;
    if (tab === "event") return item.year ?? Infinity;
    if (tab === "period") return item.start ?? Infinity;
    return Infinity;
  }

  function itemType(item, tab) {
    if (!item) return "";
    if (tab === "catalog") return item.type || "";
    if (tab === "faction" || tab === "event" || tab === "location") return item.type || "";
    if (tab === "glossary") return item.category || "";
    return "";
  }

  function searchText(item) {
    try {
      return JSON.stringify(item).toLowerCase();
    } catch (_err) {
      return "";
    }
  }

  function badge(text, cls, title) {
    return el("span", { class: "badge " + (cls || ""), title: title || undefined, text: String(text) });
  }

  function reliabilityBadge(value) {
    if (!value) return null;
    return badge(value, "reliability-" + value.replace("/", ""), RELIABILITY_TITLES[value] || "可信度");
  }

  function itemBadges(item, tab) {
    const out = [];
    if (tab === "catalog") {
      out.push(badge(label(item.type), "type"));
      const r = reliabilityBadge(item.reliability);
      if (r) out.push(r);
      if (item.priority) out.push(badge(PRIORITY_LABELS[item.priority] || item.priority));
      const ft = item.fulltext || {};
      if (ft.status) out.push(badge(statusLabel(ft.status), "fulltext-" + ft.status));
    } else if (tab === "faction") {
      out.push(badge(label(item.type), "type"));
      if (item.period) out.push(badge(item.period));
      const r = reliabilityBadge(item.reliability);
      if (r) out.push(r);
    } else if (tab === "character") {
      const faction = state.maps.faction && state.maps.faction.get(item.faction_id);
      if (faction) out.push(badge(faction.name));
      if (item.period) out.push(badge(item.period));
      const r = reliabilityBadge(item.reliability);
      if (r) out.push(r);
    } else if (tab === "event") {
      out.push(badge(label(item.type), "type"));
      if (item.period) out.push(badge(item.period));
      const r = reliabilityBadge(item.reliability);
      if (r) out.push(r);
    } else if (tab === "location") {
      out.push(badge(label(item.type), "type"));
      const r = reliabilityBadge(item.reliability);
      if (r) out.push(r);
    } else if (tab === "glossary") {
      out.push(badge(label(item.category), "type"));
      const r = reliabilityBadge(item.reliability);
      if (r) out.push(r);
    } else if (tab === "disambiguation") {
      const n = (item.conflicts || []).length;
      if (n) out.push(badge(n + " 组"));
    } else if (tab === "period") {
      if (item.parent) out.push(badge("子时代"));
    }
    return out;
  }

  function getItems(tab) {
    if (tab === "catalog") return state.catalog;
    if (tab === "period") return state.periods;
    return state.game[GAME_KEYS[tab]] || [];
  }

  function getItem(tab, id) {
    if (tab === "catalog") return state.catalogById.get(id);
    if (tab === "period") return state.periodById.get(id);
    return state.maps[tab] ? state.maps[tab].get(id) : undefined;
  }

  function resolveEntity(id) {
    for (const tab of ["faction", "character", "event", "location", "glossary", "period"]) {
      const item = state.maps[tab] && state.maps[tab].get(id);
      if (item) return { tab, item };
    }
    return null;
  }

  function catalogChip(id) {
    const item = state.catalogById.get(id);
    if (!item) return badge(id);
    return el("a", {
      class: "badge",
      href: "#/catalog/" + encodeURIComponent(id),
      text: item.title || id,
      title: "在史料目录中查看",
    });
  }

  function entityChip(id, kind) {
    const resolved = kind ? { tab: kind, item: state.maps[kind] && state.maps[kind].get(id) } : resolveEntity(id);
    if (!resolved || !resolved.item) return badge(id);
    const name = itemName(resolved.item, resolved.tab);
    return el("a", {
      class: "badge",
      href: "#/" + resolved.tab + "/" + encodeURIComponent(id),
      text: name,
      title: KIND_LABELS[resolved.tab] || resolved.tab,
    });
  }

  function chipList(ids, kind) {
    const wrap = el("div", { class: "source-list" });
    (ids || []).forEach((id) => wrap.append(kind ? entityChip(id, kind) : catalogChip(id)));
    return wrap;
  }

  function sourceSection(ids) {
    if (!ids || !ids.length) return null;
    return el("section", null, el("h3", { text: "来源" }), chipList(ids));
  }

  function dl(rows) {
    const list = el("dl");
    rows.forEach(([term, value]) => {
      if (value === undefined || value === null || value === "" || (Array.isArray(value) && value.length === 0)) return;
      list.append(el("dt", { text: term }));
      const dd = el("dd");
      if (Array.isArray(value)) {
        value.forEach((v) => dd.append(v instanceof Node ? v : document.createTextNode(String(v))));
      } else if (value instanceof Node) {
        dd.append(value);
      } else {
        dd.textContent = String(value);
      }
      list.append(dd);
    });
    return list;
  }

  function section(title, ...children) {
    return el("section", null, el("h3", { text: title }), ...children);
  }

  function bulletList(values, renderer) {
    if (!values || !values.length) return null;
    const ul = el("ul");
    values.forEach((value) => {
      const li = el("li");
      if (renderer) {
        const rendered = renderer(value);
        li.append(rendered instanceof Node ? rendered : document.createTextNode(String(rendered)));
      } else {
        li.textContent = String(value);
      }
      ul.append(li);
    });
    return ul;
  }

  function linksSection(links) {
    const entries = Object.entries(links || {}).filter(([, value]) => value);
    if (!entries.length) return null;
    const wrap = el("div", { class: "source-list" });
    const names = {
      wikisource: "Wikisource",
      ctext: "CTEXT",
      wikipedia: "维基百科",
      github: "GitHub",
      doi: "DOI",
      isbn: "ISBN",
      publisher: "出版社",
      url: "链接",
    };
    entries.forEach(([key, value]) => {
      const text = names[key] || key;
      if (/^https?:\/\//i.test(String(value))) {
        wrap.append(el("a", { class: "badge", href: String(value), target: "_blank", rel: "noopener", text }));
      } else {
        wrap.append(badge(text + "：" + value));
      }
    });
    return section("外链", wrap);
  }

  function renderStats() {
    const box = $("#stats");
    const texts = state.texts || {};
    const counts = (state.gameIndex && state.gameIndex.counts) || {};
    const stats = state.stats || {};
    const parts = [
      fmtInt(stats.total) + " 条目",
      fmtInt(stats.included) + " 部全文",
      fmtInt(texts.book_count) + " 部古籍 / " + fmtInt(texts.volume_count) + " 卷 / " + fmtInt(Math.round((texts.chars || 0) / 10000)) + " 万字",
      fmtInt(counts.factions) + " 政权",
      fmtInt(counts.characters) + " 人物",
      fmtInt(counts.events) + " 事件",
    ];
    box.replaceChildren();
    parts.forEach((part, index) => {
      if (index) box.append(el("span", { class: "dot", text: "·" }));
      box.append(el("span", { text: part }));
    });
  }

  function periodOptions() {
    const seen = new Set();
    const values = [];
    const add = (value) => {
      if (value && !seen.has(value)) {
        seen.add(value);
        values.push(value);
      }
    };
    if (state.tab === "catalog") {
      PERIOD_ORDER.forEach(add);
      state.catalog.forEach((item) => (item.periods || []).forEach(add));
    } else {
      state.periods.forEach((p) => add(p.name));
      getItems(state.tab).forEach((item) => itemPeriods(item, state.tab).forEach(add));
    }
    const order = new Map(PERIOD_ORDER.map((name, index) => [name, index]));
    return values.sort((a, b) => {
      const ia = order.has(a) ? order.get(a) : 999;
      const ib = order.has(b) ? order.get(b) : 999;
      return ia - ib || a.localeCompare(b, "zh-Hans-CN");
    });
  }

  function typeOptions() {
    const values = Array.from(new Set(getItems(state.tab).map((item) => itemType(item, state.tab)).filter(Boolean)));
    values.sort((a, b) => label(a).localeCompare(label(b), "zh-Hans-CN"));
    return values;
  }

  function reliabilityOptions() {
    const order = ["A", "A/B", "B", "B/C", "C", "M", "F", "D"];
    const present = new Set(getItems(state.tab).map((item) => item.reliability).filter(Boolean));
    return order.filter((value) => present.has(value));
  }

  function fillSelect(select, values, current, labeler) {
    select.replaceChildren(el("option", { value: "", text: "全部" }));
    values.forEach((value) => {
      select.append(el("option", { value, text: labeler ? labeler(value) : value }));
    });
    select.value = values.includes(current) ? current : "";
    return select.value;
  }

  function renderFilters() {
    const types = typeOptions();
    const periods = periodOptions();
    const reliabilities = reliabilityOptions();

    state.type = fillSelect($("#type-filter"), types, state.type, (value) => label(value));
    state.period = fillSelect($("#period-filter"), periods, state.period);
    state.reliability = fillSelect($("#reliability-filter"), reliabilities, state.reliability);

    const typeLabel = $("#type-filter").closest("label");
    const reliabilityLabel = $("#reliability-filter").closest("label");
    const periodLabel = $("#period-filter").closest("label");
    typeLabel.hidden = types.length === 0;
    reliabilityLabel.hidden = reliabilities.length === 0;
    periodLabel.hidden = state.tab === "period" || periods.length === 0;
  }

  function matches(item) {
    if (state.query) {
      const haystack = searchText(item);
      const tokens = state.query.toLowerCase().split(/\s+/).filter(Boolean);
      if (!tokens.every((token) => haystack.includes(token))) return false;
    }
    if (state.type && itemType(item, state.tab) !== state.type) return false;
    if (state.period && !itemPeriods(item, state.tab).includes(state.period)) return false;
    if (state.reliability && item.reliability !== state.reliability) return false;
    return true;
  }

  function score(item) {
    if (!state.query) return 0;
    const name = itemName(item, state.tab).toLowerCase();
    const q = state.query.toLowerCase();
    if (name === q) return 100;
    if (name.startsWith(q)) return 80;
    if (name.includes(q)) return 60;
    return 0;
  }

  function filteredItems() {
    const items = getItems(state.tab).filter(matches);
    const direction = state.sort === "name" ? 1 : -1;
    items.sort((a, b) => {
      if (state.query && state.sort === "default") {
        const diff = score(b) - score(a);
        if (diff) return diff;
      }
      if (state.sort === "year") {
        const ya = itemYear(a, state.tab);
        const yb = itemYear(b, state.tab);
        if (ya !== yb) return (ya - yb) * direction;
      }
      return itemName(a, state.tab).localeCompare(itemName(b, state.tab), "zh-Hans-CN");
    });
    return items;
  }

  function renderCard(item) {
    const tab = state.tab;
    const card = el("button", { class: "card", type: "button", dataset: { id: item.id } });
    const top = el("div", { class: "card-top" });
    top.append(el("h3", { text: itemName(item, tab) }));
    card.append(top);

    const subtitle = itemSubtitle(item, tab);
    if (subtitle) card.append(el("p", { class: "subtitle", text: subtitle }));

    const summary = itemSummary(item, tab);
    if (summary) card.append(el("p", { text: summary }));

    const badges = itemBadges(item, tab);
    if (badges.length) {
      const box = el("div", { class: "badges" });
      badges.forEach((b) => b && box.append(b));
      card.append(box);
    }

    card.addEventListener("click", () => selectItem(tab, item.id));
    return card;
  }

  function renderResults() {
    const items = filteredItems();
    const results = $("#results");
    results.replaceChildren();
    items.forEach((item) => results.append(renderCard(item)));
    $("#result-count").textContent = "共 " + fmtInt(items.length) + " 条 · " + (KIND_LABELS[state.tab] || "数据");
    $("#empty").hidden = items.length !== 0;

    if (state.selected) {
      const cards = $$(".card", results);
      const selected = cards.find((card) => card.dataset.id === state.selected.id);
      if (selected) selected.classList.add("is-selected");
    }
  }

  function detailTitle(item, tab) {
    if (tab === "catalog") return item.title || item.id;
    return itemName(item, tab);
  }

  function detailSubtitle(item, tab) {
    const parts = [];
    if (tab === "catalog") {
      if (item.title_trad && item.title_trad !== item.title) parts.push(item.title_trad);
      if (item.title_en) parts.push(item.title_en);
      const authors = (item.authors || []).map((a) => a.name).filter(Boolean).join("、");
      if (authors) parts.push(authors);
      if (item.date) parts.push(item.date);
    } else if (tab === "faction") {
      if (item.name_en) parts.push(item.name_en);
      if (item.aliases && item.aliases.length) parts.push("别名：" + item.aliases.join("、"));
    } else if (tab === "character") {
      if (item.courtesy_name) parts.push("字 " + item.courtesy_name);
      if (item.name_en) parts.push(item.name_en);
      if (item.aliases && item.aliases.length) parts.push("别名：" + item.aliases.join("、"));
    } else if (tab === "event") {
      if (item.name_en) parts.push(item.name_en);
      if (item.aliases && item.aliases.length) parts.push("别名：" + item.aliases.join("、"));
    } else if (tab === "location") {
      if (item.modern_name) parts.push("今 " + item.modern_name);
      if (item.name_en) parts.push(item.name_en);
    } else if (tab === "glossary") {
      if (item.term_en) parts.push(item.term_en);
      if (item.aliases && item.aliases.length) parts.push("别名：" + item.aliases.join("、"));
    } else if (tab === "period") {
      parts.push(fmtRange(item.start, item.end));
    }
    return parts.join(" · ");
  }

  function renderCatalogDetail(item) {
    const nodes = [];
    if (item.summary) nodes.push(el("p", { class: "lede", text: item.summary }));

    const authors = (item.authors || []).map((a) => {
      const extra = [a.dates, a.role].filter(Boolean).join("，");
      return extra ? a.name + "（" + extra + "）" : a.name;
    }).filter(Boolean).join("；");
    const ft = item.fulltext || {};
    let ftText = statusLabel(ft.status);
    if (ft.volumes_available) ftText += " · " + fmtInt(ft.volumes_available) + " 卷";
    if (ft.chars) ftText += " · " + fmtInt(ft.chars) + " 字";

    nodes.push(dl([
      ["类型", label(item.type)],
      ["可信度", item.reliability ? badge(item.reliability, "reliability-" + item.reliability.replace("/", ""), RELIABILITY_TITLES[item.reliability]) : ""],
      ["优先级", PRIORITY_LABELS[item.priority] || item.priority],
      ["作者", authors],
      ["成书/版本", item.date],
      ["覆盖年代", fmtRange(item.cover_start, item.cover_end)],
      ["体裁", item.genre],
      ["结构", item.structure],
      ["全文", ftText],
      ["库内路径", ft.path ? el("code", { text: ft.path }) : ""],
    ]));

    if (ft.note) nodes.push(el("p", { class: "empty-note", text: ft.note }));
    if (item.game_use) nodes.push(section("游戏用途", el("p", { text: item.game_use })));
    if (item.caveats) nodes.push(section("注意事项", el("p", { text: item.caveats })));

    const links = linksSection(item.links);
    if (links) nodes.push(links);

    if (item.tags && item.tags.length) {
      const box = el("div", { class: "source-list" });
      item.tags.forEach((tag) => box.append(badge(tag)));
      nodes.push(section("标签", box));
    }

    if (ft.status === "included" && ft.path) {
      nodes.push(section(
        "本地检索",
        el("p", { text: "在仓库根目录运行以下命令，可检索本书全文：" }),
        el("p", null, el("code", { text: "python scripts/search.py --book " + item.id + " <关键词>" }))
      ));
    }

    const sources = sourceSection(item.sources);
    if (sources) nodes.push(sources);
    return nodes;
  }

  function renderFactionDetail(item) {
    const nodes = [];
    if (item.summary) nodes.push(el("p", { class: "lede", text: item.summary }));
    nodes.push(dl([
      ["类型", label(item.type)],
      ["时代", item.period],
      ["起止", fmtRange(item.start, item.end)],
      ["都城", item.capital],
      ["疆域", item.territory],
      ["建立者", (item.founders || []).join("、")],
      ["关键君主", (item.key_rulers || []).join("、")],
      ["意识形态", item.ideology],
      ["军事", item.military],
      ["经济", item.economy],
      ["可信度", item.reliability ? badge(item.reliability, "reliability-" + item.reliability.replace("/", ""), RELIABILITY_TITLES[item.reliability]) : ""],
    ]));
    if (item.strengths && item.strengths.length) nodes.push(section("优势", bulletList(item.strengths)));
    if (item.weaknesses && item.weaknesses.length) nodes.push(section("弱点", bulletList(item.weaknesses)));
    if (item.game_hooks && item.game_hooks.length) nodes.push(section("游戏钩子", bulletList(item.game_hooks)));
    if (item.allies && item.allies.length) nodes.push(section("盟友", chipList(item.allies, "faction")));
    if (item.enemies && item.enemies.length) nodes.push(section("敌人", chipList(item.enemies, "faction")));
    if (item.vassals && item.vassals.length) nodes.push(section("附庸", chipList(item.vassals, "faction")));
    const sources = sourceSection(item.sources);
    if (sources) nodes.push(sources);
    return nodes;
  }

  function renderCharacterDetail(item) {
    const nodes = [];
    if (item.summary) nodes.push(el("p", { class: "lede", text: item.summary }));
    const faction = state.maps.faction && state.maps.faction.get(item.faction_id);
    nodes.push(dl([
      ["时代", item.period],
      ["阵营", faction ? entityChip(item.faction_id, "faction") : item.faction_id],
      ["生卒", fmtRange(item.birth, item.death)],
      ["籍贯", item.birth_place],
      ["角色", (item.roles || []).join("、")],
      ["标签", (item.tags || []).join("、")],
      ["性格", (item.traits || []).join("、")],
      ["可信度", item.reliability ? badge(item.reliability, "reliability-" + item.reliability.replace("/", ""), RELIABILITY_TITLES[item.reliability]) : ""],
    ]));

    if (item.relationships && item.relationships.length) {
      const ul = el("ul");
      item.relationships.forEach((rel) => {
        const li = el("li");
        li.append(entityChip(rel.target, "character"));
        li.append(document.createTextNode(" · " + (rel.type || "关系") + (rel.note ? "：" + rel.note : "")));
        ul.append(li);
      });
      nodes.push(section("关系", ul));
    }
    if (item.events && item.events.length) nodes.push(section("相关事件", chipList(item.events, "event")));
    if (item.quotes && item.quotes.length) {
      const wrap = el("div");
      item.quotes.forEach((quote) => {
        wrap.append(el("blockquote", { class: "quote" },
          document.createTextNode("“" + quote.text + "”"),
          el("cite", { text: quote.source || "" })
        ));
      });
      nodes.push(section("史料引文", wrap));
    }
    if (item.game_use) nodes.push(section("游戏用途", el("p", { text: item.game_use })));
    const sources = sourceSection(item.sources);
    if (sources) nodes.push(sources);
    return nodes;
  }

  function renderEventDetail(item) {
    const nodes = [];
    if (item.summary) nodes.push(el("p", { class: "lede", text: item.summary }));
    const loc = state.maps.location && state.maps.location.get(item.location_id);
    nodes.push(dl([
      ["年份", fmtRange(item.year, item.end_year)],
      ["类型", label(item.type)],
      ["时代", item.period],
      ["地点", loc ? entityChip(item.location_id, "location") : item.location_id],
      ["参战方", chipList(item.factions, "faction")],
      ["人物", chipList(item.characters, "character")],
      ["可信度", item.reliability ? badge(item.reliability, "reliability-" + item.reliability.replace("/", ""), RELIABILITY_TITLES[item.reliability]) : ""],
    ]));
    if (item.causes) nodes.push(section("起因", el("p", { text: item.causes })));
    if (item.course) nodes.push(section("经过", el("p", { text: item.course })));
    if (item.outcome) nodes.push(section("结果", el("p", { text: item.outcome })));
    if (item.significance) nodes.push(section("意义", el("p", { text: item.significance })));
    if (item.game_hooks && item.game_hooks.length) nodes.push(section("游戏钩子", bulletList(item.game_hooks)));
    const sources = sourceSection(item.sources);
    if (sources) nodes.push(sources);
    return nodes;
  }

  function renderLocationDetail(item) {
    const nodes = [];
    if (item.summary) nodes.push(el("p", { class: "lede", text: item.summary }));
    const coords = item.lat !== null && item.lat !== undefined && item.lon !== null && item.lon !== undefined
      ? item.lat + ", " + item.lon
      : "";
    nodes.push(dl([
      ["类型", label(item.type)],
      ["今地", item.modern_name],
      ["省份", item.province],
      ["坐标", coords],
      ["时期", (item.periods || []).join("、")],
      ["战略价值", item.strategic_value],
      ["可信度", item.reliability ? badge(item.reliability, "reliability-" + item.reliability.replace("/", ""), RELIABILITY_TITLES[item.reliability]) : ""],
    ]));
    if (item.events && item.events.length) nodes.push(section("相关事件", chipList(item.events, "event")));
    const sources = sourceSection(item.sources);
    if (sources) nodes.push(sources);
    return nodes;
  }

  function renderGlossaryDetail(item) {
    const nodes = [];
    if (item.definition) nodes.push(el("p", { class: "lede", text: item.definition }));
    nodes.push(dl([
      ["分类", label(item.category)],
      ["时期", (item.periods || []).join("、")],
      ["可信度", item.reliability ? badge(item.reliability, "reliability-" + item.reliability.replace("/", ""), RELIABILITY_TITLES[item.reliability]) : ""],
    ]));
    if (item.game_use) nodes.push(section("游戏用途", el("p", { text: item.game_use })));
    if (item.related && item.related.length) {
      const box = el("div", { class: "source-list" });
      item.related.forEach((id) => box.append(entityChip(id)));
      nodes.push(section("相关术语", box));
    }
    const sources = sourceSection(item.sources);
    if (sources) nodes.push(sources);
    return nodes;
  }

  function renderDisambiguationDetail(item) {
    const nodes = [];
    if (item.guidance) nodes.push(el("p", { class: "lede", text: item.guidance }));
    if (item.conflicts && item.conflicts.length) {
      const ul = el("ul");
      item.conflicts.forEach((conflict) => {
        const li = el("li");
        if (conflict.entity_id) {
          li.append(entityChip(conflict.entity_id));
        } else {
          li.append(el("strong", { text: conflict.name }));
        }
        li.append(document.createTextNode(" · " + (conflict.period || "") + (conflict.note ? "：" + conflict.note : "")));
        ul.append(li);
      });
      nodes.push(section("同名实体", ul));
    }
    const sources = sourceSection(item.sources);
    if (sources) nodes.push(sources);
    return nodes;
  }

  function renderPeriodDetail(item) {
    const nodes = [];
    if (item.summary) nodes.push(el("p", { class: "lede", text: item.summary }));
    nodes.push(dl([
      ["起止", fmtRange(item.start, item.end)],
      ["上级时代", item.parent],
    ]));
    if (item.themes && item.themes.length) nodes.push(section("主题", bulletList(item.themes)));
    if (item.game_hooks && item.game_hooks.length) nodes.push(section("游戏钩子", bulletList(item.game_hooks)));
    if (item.key_events && item.key_events.length) nodes.push(section("关键事件", bulletList(item.key_events)));
    const sources = sourceSection(item.sources);
    if (sources) nodes.push(sources);
    return nodes;
  }

  function renderDetail(tab, id) {
    const item = getItem(tab, id);
    if (!item) {
      clearDetail();
      return;
    }
    const body = $("#detail-body");
    body.replaceChildren();

    const header = el("div");
    header.append(el("h2", { text: detailTitle(item, tab) }));
    const subtitle = detailSubtitle(item, tab);
    if (subtitle) header.append(el("p", { class: "subtitle", text: subtitle }));
    const badges = itemBadges(item, tab);
    if (badges.length) {
      const box = el("div", { class: "badges" });
      badges.forEach((b) => b && box.append(b));
      header.append(box);
    }
    body.append(header);

    let nodes = [];
    if (tab === "catalog") nodes = renderCatalogDetail(item);
    else if (tab === "faction") nodes = renderFactionDetail(item);
    else if (tab === "character") nodes = renderCharacterDetail(item);
    else if (tab === "event") nodes = renderEventDetail(item);
    else if (tab === "location") nodes = renderLocationDetail(item);
    else if (tab === "glossary") nodes = renderGlossaryDetail(item);
    else if (tab === "disambiguation") nodes = renderDisambiguationDetail(item);
    else if (tab === "period") nodes = renderPeriodDetail(item);
    nodes.forEach((node) => body.append(node));

    $("#detail-kind").textContent = KIND_LABELS[tab] || "详情";
    $("#detail").hidden = false;
    $(".layout").classList.add("has-detail");
    state.selected = { tab, id };

    $$(".card", $("#results")).forEach((card) => {
      card.classList.toggle("is-selected", card.dataset.id === id);
    });

    if (window.matchMedia("(max-width: 980px)").matches) {
      $("#detail").scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function clearDetail() {
    state.selected = null;
    $("#detail").hidden = true;
    $("#detail-body").replaceChildren();
    $(".layout").classList.remove("has-detail");
    $$(".card.is-selected").forEach((card) => card.classList.remove("is-selected"));
    if (location.hash) {
      history.replaceState(null, "", location.pathname + location.search);
    }
  }

  function updateActiveTab() {
    $$(".tab").forEach((tab) => {
      const active = tab.dataset.tab === state.tab;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", active ? "true" : "false");
    });
  }

  function setTab(tab) {
    if (!TABS.includes(tab)) return;
    state.tab = tab;
    state.query = "";
    state.type = "";
    state.period = "";
    state.reliability = "";
    state.sort = "default";
    $("#search").value = "";
    $("#sort-order").value = "default";
    updateActiveTab();
    clearDetail();
    renderFilters();
    renderResults();
  }

  function selectItem(tab, id, options) {
    const opts = options || {};
    if (!TABS.includes(tab) || !getItem(tab, id)) return;
    if (tab !== state.tab) {
      state.tab = tab;
      state.query = "";
      state.type = "";
      state.period = "";
      state.reliability = "";
      state.sort = "default";
      $("#search").value = "";
      $("#sort-order").value = "default";
      updateActiveTab();
      renderFilters();
      renderResults();
    }
    renderDetail(tab, id);
    if (opts.updateHash !== false) {
      history.replaceState(null, "", "#/" + tab + "/" + encodeURIComponent(id));
    }
  }

  function parseHash() {
    const raw = location.hash.replace(/^#\/?/, "");
    if (!raw) return null;
    const parts = raw.split("/");
    const tab = parts.shift();
    const id = decodeURIComponent(parts.join("/"));
    if (!TABS.includes(tab) || !id) return null;
    return { tab, id };
  }

  function handleHash() {
    const parsed = parseHash();
    if (parsed) selectItem(parsed.tab, parsed.id, { updateHash: false });
    else clearDetail();
  }

  function bindEvents() {
    $$(".tab").forEach((tab) => {
      tab.addEventListener("click", () => setTab(tab.dataset.tab));
    });

    $("#search-form").addEventListener("submit", (event) => {
      event.preventDefault();
      state.query = $("#search").value.trim();
      renderResults();
    });

    let timer = null;
    $("#search").addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        state.query = $("#search").value.trim();
        renderResults();
      }, 140);
    });

    ["type-filter", "period-filter", "reliability-filter"].forEach((id) => {
      $("#" + id).addEventListener("change", (event) => {
        if (id === "type-filter") state.type = event.target.value;
        else if (id === "period-filter") state.period = event.target.value;
        else state.reliability = event.target.value;
        renderResults();
      });
    });

    $("#sort-order").addEventListener("change", (event) => {
      state.sort = event.target.value;
      renderResults();
    });

    $("#close-detail").addEventListener("click", clearDetail);

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") clearDetail();
    });

    window.addEventListener("hashchange", handleHash);

    $("#theme-toggle").addEventListener("click", () => {
      const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      try {
        localStorage.setItem("cn-history-theme", next);
      } catch (_err) { /* ignore */ }
    });
  }

  function initTheme() {
    let saved = null;
    try {
      saved = localStorage.getItem("cn-history-theme");
    } catch (_err) { /* ignore */ }
    if (saved === "dark" || saved === "light") {
      document.documentElement.dataset.theme = saved;
    } else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      document.documentElement.dataset.theme = "dark";
    }
  }

  async function fetchJson(path) {
    const response = await fetch(DATA + path, { cache: "no-cache" });
    if (!response.ok) throw new Error(path + ": HTTP " + response.status);
    return response.json();
  }

  function showLoadError(error) {
    const results = $("#results");
    results.replaceChildren(el("div", { class: "empty" },
      el("h3", { text: "无法载入数据" }),
      el("p", { text: "若直接双击打开 index.html，浏览器会阻止读取本地 JSON。请在仓库根目录运行：" }),
      el("p", null, el("code", { text: "python -m http.server 8000" })),
      el("p", { text: "然后访问 http://localhost:8000/site/。" }),
      el("p", { class: "empty-note", text: String(error && error.message ? error.message : error) })
    ));
    $("#result-count").textContent = "载入失败";
    $("#stats").textContent = "数据未载入";
  }

  async function boot() {
    initTheme();
    try {
      const payloads = await Promise.all([
        fetchJson("catalog.json"),
        fetchJson("catalog_stats.json"),
        fetchJson("periods.json"),
        fetchJson("texts_index.json"),
        fetchJson("game/index.json"),
        fetchJson("game/factions.json"),
        fetchJson("game/characters.json"),
        fetchJson("game/events.json"),
        fetchJson("game/locations.json"),
        fetchJson("game/glossary.json"),
        fetchJson("game/disambiguation.json"),
      ]);
      state.catalog = payloads[0];
      state.stats = payloads[1];
      state.periods = payloads[2];
      state.texts = payloads[3];
      state.gameIndex = payloads[4];
      state.game = {
        factions: payloads[5],
        characters: payloads[6],
        events: payloads[7],
        locations: payloads[8],
        glossary: payloads[9],
        disambiguation: payloads[10],
      };
      state.catalogById = new Map(state.catalog.map((item) => [item.id, item]));
      state.periodById = new Map(state.periods.map((item) => [item.id, item]));
      state.maps = {
        faction: new Map(state.game.factions.map((item) => [item.id, item])),
        character: new Map(state.game.characters.map((item) => [item.id, item])),
        event: new Map(state.game.events.map((item) => [item.id, item])),
        location: new Map(state.game.locations.map((item) => [item.id, item])),
        glossary: new Map(state.game.glossary.map((item) => [item.id, item])),
        disambiguation: new Map(state.game.disambiguation.map((item) => [item.id, item])),
        period: state.periodById,
      };
      renderStats();
      updateActiveTab();
      renderFilters();
      renderResults();
      bindEvents();
      handleHash();
    } catch (error) {
      showLoadError(error);
    }
  }

  boot();
})();
