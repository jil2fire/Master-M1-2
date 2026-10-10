const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL?.replace(/\/$/, "");
const $ = (selector) => document.querySelector(selector);
let records = [];
let currentConversationId = null;
let editingId = null;

const dateLabel = (value) => value ? value.slice(5).replace("-", ".") : "—";
const number = (value, suffix = "건") => value == null ? "—" : `${Number(value).toLocaleString("ko-KR")}${suffix}`;

function status(selector, message, success = false) {
  const element = $(selector);
  element.textContent = message;
  element.classList.toggle("success", success);
}

async function request(path, options = {}) {
  if (!API_BASE_URL) throw new Error("API 주소가 설정되지 않았습니다. config.js를 확인해 주세요.");
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}) },
  });
  let body;
  try { body = await response.json(); } catch { body = {}; }
  if (!response.ok) {
    const detail = body.detail;
    throw new Error(typeof detail === "string" ? detail : `요청에 실패했습니다 (${response.status})`);
  }
  return body;
}

function renderSummary(summary) {
  const metrics = summary.metrics;
  $("#stat-period").textContent = summary.period || "기록 없음";
  $("#stat-count").textContent = `${summary.count}개 기록`;
  $("#stat-average").textContent = number(metrics?.average);
  $("#stat-max").textContent = number(metrics?.max?.value);
  $("#stat-max-date").textContent = metrics?.max?.date || "—";
  $("#stat-trend").textContent = summary.trend?.label || "분석 대기";
  $("#stat-trend-detail").textContent = summary.trend?.change_rate == null
    ? (summary.trend_message || "기록을 추가해 주세요")
    : `직전 14일 대비 ${summary.trend.change_rate > 0 ? "+" : ""}${summary.trend.change_rate}%`;
  $("#as-of").textContent = summary.as_of_date
    ? `데이터 최신일 ${summary.as_of_date} 기준 최근 14일`
    : "데이터가 없습니다";
  $("#stat-total").textContent = number(metrics?.total);
  $("#stat-weekday").textContent = number(metrics?.weekday_average);
  $("#stat-weekend").textContent = number(metrics?.weekend_average);
  $("#stat-recent7").textContent = number(metrics?.recent_7_day_average);
  const coverage = summary.trend_coverage;
  $("#coverage").textContent = coverage
    ? `최근 ${coverage.recent_observed_days}일 · 직전 ${coverage.previous_observed_days}일 관측${summary.trend_message ? ` / ${summary.trend_message}` : ""}`
    : "데이터 관리에서 첫 기록을 추가해 주세요.";
}

function svg(name, attributes = {}) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value));
  return element;
}

function renderChart() {
  const target = $("#chart");
  target.replaceChildren();
  if (!records.length) {
    const empty = document.createElement("p");
    empty.className = "chart-empty";
    empty.textContent = "예약 기록을 추가하면 그래프가 표시됩니다.";
    target.append(empty);
    return;
  }
  const items = records;
  const W = 900, H = 285, left = 40, right = 12, top = 20, bottom = 35;
  const max = Math.max(10, ...items.map(item => item.value));
  const x = index => left + (items.length === 1 ? 0 : index * (W - left - right) / (items.length - 1));
  const y = value => top + (max - value) * (H - top - bottom) / max;
  const root = svg("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `최근 ${items.length}개 기록의 예약 건수와 7일 이동 평균` });
  for (let n = 0; n <= 3; n++) {
    const value = max * n / 3;
    root.append(svg("line", { x1: left, x2: W - right, y1: y(value), y2: y(value), stroke: "#b7c9c1", "stroke-opacity": ".45", "stroke-dasharray": "4 6" }));
    const label = svg("text", { x: 0, y: y(value) + 4, fill: "#839994", "font-size": 11 });
    label.textContent = String(Math.round(value));
    root.append(label);
  }
  const pathFor = values => values.map((value, index) => `${index ? "L" : "M"}${x(index).toFixed(1)},${y(value).toFixed(1)}`).join(" ");
  const averages = items.map(item => {
    const end = Date.parse(`${item.date}T00:00:00Z`);
    const start = end - 6 * 86400000;
    const values = records.filter(row => {
      const day = Date.parse(`${row.date}T00:00:00Z`);
      return day >= start && day <= end;
    }).map(row => row.value);
    return values.reduce((a, b) => a + b, 0) / values.length;
  });
  root.append(svg("path", { d: pathFor(items.map(item => item.value)), fill: "none", stroke: "#32ab77", "stroke-width": 2.5, "stroke-linecap": "round", "stroke-linejoin": "round" }));
  root.append(svg("path", { d: pathFor(averages), fill: "none", stroke: "#6c9cc9", "stroke-width": 3, "stroke-linecap": "round", "stroke-linejoin": "round" }));
  for (const index of [0, Math.floor((items.length - 1) / 2), items.length - 1]) {
    const label = svg("text", { x: x(index), y: H - 5, fill: "#839994", "font-size": 11, "text-anchor": index === 0 ? "start" : index === items.length - 1 ? "end" : "middle" });
    label.textContent = dateLabel(items[index].date);
    root.append(label);
  }
  for (let index = 0; index < items.length; index++) {
    const point = svg("circle", { cx: x(index), cy: y(items[index].value), r: 3, fill: "#32ab77" });
    const title = svg("title");
    title.textContent = `${items[index].date}: ${items[index].value}건 / 7일 평균 ${averages[index].toFixed(1)}건`;
    point.append(title);
    root.append(point);
  }
  target.append(root);
}

function renderRows() {
  const body = $("#data-rows");
  body.replaceChildren();
  $("#row-count").textContent = `${records.length}건`;
  if (!records.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 4;
    cell.textContent = "기록이 없습니다. 첫 예약 기록을 추가해 주세요.";
    row.append(cell);
    body.append(row);
    return;
  }
  for (const item of [...records].reverse()) {
    const row = document.createElement("tr");
    for (const value of [item.date, `${item.value}건`, item.memo || "—"]) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    }
    const actions = document.createElement("td");
    const edit = document.createElement("button");
    edit.type = "button";
    edit.textContent = "수정";
    edit.addEventListener("click", () => beginEdit(item));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "delete";
    remove.textContent = "삭제";
    remove.addEventListener("click", () => removeRecord(item));
    actions.append(edit, remove);
    row.append(actions);
    body.append(row);
  }
}

function beginEdit(item) {
  editingId = item.id;
  $("#data-form-title").textContent = "기록 수정";
  $("#data-submit").textContent = "변경 저장";
  $("#data-cancel").hidden = false;
  $("#data-date").value = item.date;
  $("#data-value").value = item.value;
  $("#data-memo").value = item.memo || "";
  $("#data-form").scrollIntoView({ behavior: "smooth", block: "center" });
}

function resetForm() {
  editingId = null;
  $("#data-form").reset();
  $("#data-form-title").textContent = "새 기록 추가";
  $("#data-submit").textContent = "기록 추가";
  $("#data-cancel").hidden = true;
}

async function refreshData() {
  const [items, summary] = await Promise.all([request("/api/data"), request("/api/data/summary")]);
  records = items;
  renderRows();
  renderSummary(summary);
  renderChart();
}

async function removeRecord(item) {
  if (!confirm(`${item.date} 기록을 삭제할까요?`)) return;
  try {
    await request(`/api/data/${encodeURIComponent(item.id)}`, { method: "DELETE" });
    await refreshData();
    status("#data-status", "기록을 삭제했습니다.", true);
  } catch (error) { status("#data-status", error.message); }
}

async function saveRecord(event) {
  event.preventDefault();
  const submit = $("#data-submit");
  submit.disabled = true;
  const payload = {
    date: $("#data-date").value,
    value: Number($("#data-value").value),
    memo: $("#data-memo").value,
  };
  try {
    await request(editingId ? `/api/data/${encodeURIComponent(editingId)}` : "/api/data", {
      method: editingId ? "PUT" : "POST", body: JSON.stringify(payload),
    });
    resetForm();
    await refreshData();
    status("#data-status", "기록을 저장했습니다.", true);
  } catch (error) { status("#data-status", error.message); }
  finally { submit.disabled = false; }
}

function downloadCsv() {
  if (!records.length) { status("#data-status", "다운로드할 기록이 없습니다."); return; }
  const escape = value => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const csv = ["date,value,memo", ...records.map(item => [item.date, item.value, item.memo].map(escape).join(","))].join("\r\n");
  const url = URL.createObjectURL(new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "seatscope-reservations.csv";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function renderMessages(messages) {
  const container = $("#chat-messages");
  container.replaceChildren();
  if (!messages.length) {
    const welcome = document.createElement("div");
    welcome.className = "welcome";
    const symbol = document.createElement("span");
    symbol.className = "welcome-symbol";
    symbol.textContent = "✳";
    const title = document.createElement("h3");
    title.textContent = "무엇이 궁금하신가요?";
    const copy = document.createElement("p");
    copy.textContent = "“최근 예약 추세가 어때?”처럼 저장된 데이터에 관해 물어보세요.";
    welcome.append(symbol, title, copy);
    container.append(welcome);
  }
  for (const message of messages) {
    const element = document.createElement("div");
    element.className = `message ${message.role}`;
    element.textContent = message.content;
    container.append(element);
  }
  container.scrollTop = container.scrollHeight;
}

async function loadConversation(id) {
  try {
    const item = await request(`/api/conversations/${encodeURIComponent(id)}`);
    currentConversationId = id;
    renderMessages(item.messages);
    await refreshConversations();
    status("#chat-status", "");
  } catch (error) { status("#chat-status", error.message); }
}

async function refreshConversations() {
  const items = await request("/api/conversations");
  const target = $("#conversation-list");
  target.replaceChildren();
  if (!items.length) {
    const empty = document.createElement("p");
    empty.className = "empty-small";
    empty.textContent = "아직 저장된 대화가 없습니다.";
    target.append(empty);
  }
  for (const item of items) {
    const entry = document.createElement("div");
    entry.className = `conversation-entry${item.id === currentConversationId ? " active" : ""}`;
    const open = document.createElement("button");
    open.type = "button";
    const title = document.createElement("strong");
    title.textContent = item.title;
    const date = document.createElement("small");
    date.textContent = new Date(item.updated_at).toLocaleString("ko-KR");
    open.append(title, date);
    open.addEventListener("click", () => loadConversation(item.id));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.setAttribute("aria-label", `${item.title} 삭제`);
    remove.textContent = "×";
    remove.addEventListener("click", async () => {
      if (!confirm("이 대화를 삭제할까요?")) return;
      try {
        await request(`/api/conversations/${encodeURIComponent(item.id)}`, { method: "DELETE" });
        if (currentConversationId === item.id) newChat();
        await refreshConversations();
      } catch (error) { status("#chat-status", error.message); }
    });
    entry.append(open, remove);
    target.append(entry);
  }
}

function newChat() {
  currentConversationId = null;
  renderMessages([]);
  status("#chat-status", "");
  refreshConversations().catch(error => status("#chat-status", error.message));
  $("#chat-input").focus();
}

async function sendChat(event) {
  event.preventDefault();
  const input = $("#chat-input");
  const message = input.value.trim();
  if (!message) return;
  const button = $("#chat-send");
  button.disabled = true;
  input.disabled = true;
  $("#chat-loading").hidden = false;
  status("#chat-status", "");
  const slow = setTimeout(() => status("#chat-status", "서버를 깨우는 중입니다. 최대 1분 정도 걸릴 수 있어요."), 3000);
  try {
    const result = await request("/api/chat", {
      method: "POST", body: JSON.stringify({ message, conversation_id: currentConversationId }),
    });
    input.value = "";
    await loadConversation(result.conversation_id);
  } catch (error) { status("#chat-status", error.message); }
  finally {
    clearTimeout(slow);
    button.disabled = false;
    input.disabled = false;
    $("#chat-loading").hidden = true;
    input.focus();
  }
}

function initTheme() {
  const saved = localStorage.getItem("seatscope-theme");
  if (saved === "dark") document.documentElement.dataset.theme = "dark";
  $("#theme-toggle").addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("seatscope-theme", next);
  });
}

async function init() {
  initTheme();
  $("#data-form").addEventListener("submit", saveRecord);
  $("#data-cancel").addEventListener("click", resetForm);
  $("#download-csv").addEventListener("click", downloadCsv);
  $("#chat-form").addEventListener("submit", sendChat);
  $("#new-chat").addEventListener("click", newChat);
  const results = await Promise.allSettled([refreshData(), refreshConversations()]);
  if (results[0].status === "rejected") {
    status("#data-status", results[0].reason.message);
    $("#as-of").textContent = "서버 연결 실패";
    const cell = $("#data-rows td");
    if (cell) cell.textContent = "데이터를 불러오지 못했습니다.";
  }
  if (results[1].status === "rejected") status("#chat-status", results[1].reason.message);
}

init();
