/* AI 股票分析日报 —— 前端逻辑：读取 data.json，动态渲染。零框架，纯原生 JS。
   红涨绿跌（国内习惯）。所有展示均为技术形态描述，不构成投资建议。 */
(function () {
  "use strict";

  var state = { rows: [], filtered: [], market: "ALL", keyword: "" };

  // 拉取数据（带时间戳避免缓存）
  fetch("data.json?t=" + Date.now())
    .then(function (r) { if (!r.ok) throw new Error("data.json 不存在"); return r.json(); })
    .then(render)
    .catch(function (e) {
      document.getElementById("subtitle").textContent = "暂无数据，请先运行分析生成 data.json";
      console.error(e);
    });

  function render(data) {
    var s = data.summary;
    state.rows = data.rows || [];
    state.filtered = state.rows.slice();

    document.getElementById("subtitle").textContent =
      s.date + " · 共 " + s.total + " 只 · 真实行情 " + s.live_count + " 只";
    document.getElementById("gen-time").textContent = "生成时间：" + s.generated_at;

    // 仿真数据提示
    if (s.live_count < s.total) {
      var b = document.getElementById("banner");
      b.classList.remove("hidden");
      b.innerHTML = "⚠️ 部分或全部为<b>仿真数据</b>（" + (s.total - s.live_count) +
        " 只未取到真实行情，可能因网络/限流）。仿真仅用于演示分析流程，不代表真实市场。";
    }

    renderStats(s);
    renderTops(s);
    renderFilters();
    renderRows();
    bindEvents();
  }

  function renderStats(s) {
    var cards = [
      { v: s.total, l: "标的总数" },
      { v: s.buy_count, l: "偏多", cls: "up" },
      { v: s.sell_count, l: "偏空", cls: "down" },
      { v: s.hold_count, l: "观望" },
      { v: s.live_count + "/" + s.total, l: "真实行情" },
    ];
    document.getElementById("stats").innerHTML = cards.map(function (c) {
      return '<div class="stat"><div class="v ' + (c.cls || "") + '">' + c.v +
        '</div><div class="l">' + c.l + "</div></div>";
    }).join("");
  }

  function renderTops(s) {
    document.getElementById("top-bull").innerHTML = topList(s.top_bull);
    document.getElementById("top-bear").innerHTML = topList(s.top_bear);
  }
  function topList(arr) {
    if (!arr || !arr.length) return '<li class="empty">今日无</li>';
    return arr.map(function (x) {
      return "<li><b>" + esc(x.name) + "</b>（" + esc(x.rec) + " " + fmtScore(x.score) + "）</li>";
    }).join("");
  }

  function renderFilters() {
    var markets = ["ALL"];
    state.rows.forEach(function (r) { if (markets.indexOf(r.market) < 0) markets.push(r.market); });
    var label = { ALL: "全部", US: "美股", HK: "港股", SH: "沪A", SZ: "深A" };
    document.getElementById("market-filters").innerHTML = markets.map(function (m) {
      return '<button data-m="' + m + '" class="' + (m === state.market ? "active" : "") +
        '">' + (label[m] || m) + "</button>";
    }).join("");
  }

  function renderRows() {
    var kw = state.keyword.toLowerCase();
    state.filtered = state.rows.filter(function (r) {
      var okM = state.market === "ALL" || r.market === state.market;
      var okK = !kw || r.name.toLowerCase().indexOf(kw) >= 0 || r.symbol.toLowerCase().indexOf(kw) >= 0;
      return okM && okK;
    });
    // 按评分绝对值排序，强信号靠前
    state.filtered.sort(function (a, b) {
      return Math.abs(b.signal.score) - Math.abs(a.signal.score);
    });

    document.getElementById("rows").innerHTML = state.filtered.map(function (r, i) {
      var sig = r.signal;
      var chg = r.change_pct;
      var chgCls = chg > 0 ? "up" : (chg < 0 ? "down" : "");
      var chgTxt = (chg > 0 ? "+" : "") + chg.toFixed(2) + "%";
      return "<tr data-i=" + i + ">" +
        "<td>" + esc(r.name) + (r.live ? "" : ' <span class="muted">(仿真)</span>') + "</td>" +
        "<td class='muted'>" + esc(r.symbol) + "</td>" +
        "<td>" + esc(r.market_label || r.market) + "</td>" +
        "<td class='num'>" + r.price.toFixed(2) + "</td>" +
        "<td class='num " + chgCls + "'>" + chgTxt + "</td>" +
        "<td class='num'>" + fmtScore(sig.score) + "</td>" +
        "<td><span class='badge b-" + sig.recommendation_level + "'>" + esc(sig.recommendation) + "</span></td>" +
        "<td class='num'>" + (sig.rsi == null ? "-" : sig.rsi) + "</td>" +
        "<td class='num'>" + (sig.j == null ? "-" : sig.j) + "</td>" +
        "<td>" + spark(r.closes) + "</td>" +
        "</tr>";
    }).join("");
  }

  // 内联 SVG 迷你走势图（红涨绿跌：末值≥首值为红，否则绿）
  function spark(closes) {
    if (!closes || closes.length < 2) return "";
    var w = 120, h = 30, pad = 2;
    var min = Math.min.apply(null, closes), max = Math.max.apply(null, closes);
    var span = max - min || 1;
    var step = (w - pad * 2) / (closes.length - 1);
    var pts = closes.map(function (c, i) {
      var x = pad + i * step;
      var y = h - pad - (c - min) / span * (h - pad * 2);
      return x.toFixed(1) + "," + y.toFixed(1);
    }).join(" ");
    var color = closes[closes.length - 1] >= closes[0] ? "#e23b3b" : "#18a058";
    return '<svg class="spark" width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + " " + h +
      '"><polyline fill="none" stroke="' + color + '" stroke-width="1.5" points="' + pts + '"/></svg>';
  }

  function openModal(r) {
    var sig = r.signal;
    var reasons = (sig.reasons || []).map(function (x) {
      return '<div class="reason ' + x.side + '">' + (x.side === "bull" ? "🔴 " : "🟢 ") + esc(x.text) + "</div>";
    }).join("") || '<div class="muted">今日无明显信号触发（观望）。</div>';

    var kv = [
      ["评分", fmtScore(sig.score)], ["建议", sig.recommendation],
      ["RSI", sig.rsi == null ? "-" : sig.rsi],
      ["MACD柱", sig.macd_hist == null ? "-" : sig.macd_hist],
      ["KDJ-K", sig.k == null ? "-" : sig.k], ["KDJ-J", sig.j == null ? "-" : sig.j],
      ["MA20", sig.ma20 == null ? "-" : sig.ma20], ["MA60", sig.ma60 == null ? "-" : sig.ma60],
      ["布林上/下", (sig.upper == null ? "-" : sig.upper) + " / " + (sig.lower == null ? "-" : sig.lower)],
    ].map(function (p) {
      return '<div><div class="l">' + p[0] + '</div><div class="v">' + p[1] + "</div></div>";
    }).join("");

    document.getElementById("modal-body").innerHTML =
      "<h3>" + esc(r.name) + ' <span class="muted">' + esc(r.symbol) + "</span></h3>" +
      '<p class="muted">' + esc(r.market_label || r.market) + (r.live ? "" : " · 仿真数据") + "</p>" +
      spark(r.closes) +
      '<div class="kv">' + kv + "</div>" +
      "<h4>信号明细</h4>" + reasons;
    document.getElementById("modal").classList.remove("hidden");
  }

  function bindEvents() {
    document.getElementById("market-filters").addEventListener("click", function (e) {
      if (e.target.tagName !== "BUTTON") return;
      state.market = e.target.getAttribute("data-m");
      renderFilters(); renderRows();
    });
    document.getElementById("search").addEventListener("input", function (e) {
      state.keyword = e.target.value; renderRows();
    });
    document.getElementById("rows").addEventListener("click", function (e) {
      var tr = e.target.closest("tr"); if (!tr) return;
      openModal(state.filtered[+tr.getAttribute("data-i")]);
    });
    document.getElementById("modal-close").addEventListener("click", closeModal);
    document.getElementById("modal").addEventListener("click", function (e) {
      if (e.target.id === "modal") closeModal();
    });
  }
  function closeModal() { document.getElementById("modal").classList.add("hidden"); }

  function fmtScore(n) { return (n > 0 ? "+" : "") + n; }
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
})();
