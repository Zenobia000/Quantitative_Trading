// Scrum board 前端：拖拉 + 自動雙向同步。
// 任何卡片移動 / 編輯 → debounce 後整份 POST /api/board → 後端寫 scrum_board.json + 同步 WBS。
"use strict";

const API = "/api/board";
let board = null;          // 整份看板真相源（記憶體副本）
let activeMilestone = "all";
let editingId = null;

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls) => { const n = document.createElement(tag); if (cls) n.className = cls; return n; };

// ── 載入 ────────────────────────────────────────────────────────────────
async function loadBoard() {
  setSync("idle", "● 載入中");
  const res = await fetch(API);
  board = await res.json();
  render();
  setSync("saved", "● 已同步");
}

// ── 儲存（debounce）──────────────────────────────────────────────────────
let saveTimer = null;
function scheduleSave() {
  setSync("saving", "● 儲存中…");
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveBoard, 500);
}
async function saveBoard() {
  try {
    const res = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(board),
    });
    const data = await res.json();
    if (!data.ok) throw new Error("server rejected");
    setSync("saved", data.syncedWbs ? "● 已同步 WBS" : "● 已存檔（WBS 缺 marker）");
  } catch (err) {
    console.error(err);
    setSync("error", "● 儲存失敗");
  }
}

function setSync(state, text) {
  const pill = $("#syncPill");
  pill.dataset.state = state;
  pill.textContent = text;
}

// ── 渲染 ────────────────────────────────────────────────────────────────
function render() {
  $("#subtitle").textContent =
    `真相源 dev_docs/scrum_board.json · 最後更新 ${board.updatedAt || "—"}`;
  renderStats();
  renderFilters();
  renderColumns();
}

function visibleCards() {
  return board.cards.filter(
    (c) => activeMilestone === "all" || c.milestone === activeMilestone
  );
}

function renderStats() {
  const cards = board.cards;
  const done = cards.filter((c) => c.column === "done").length;
  const wip = cards.filter((c) => c.column === "in_progress" || c.column === "review").length;
  $("#stats").innerHTML = `
    <div class="stat"><b>${cards.length}</b><span>總卡片</span></div>
    <div class="stat"><b>${done}</b><span>已完成</span></div>
    <div class="stat"><b>${wip}</b><span>進行中</span></div>
    <div class="stat"><b>${Math.round((done / cards.length) * 100)}%</b><span>完成率</span></div>`;
}

function renderFilters() {
  const milestones = ["all", ...new Set(board.cards.map((c) => c.milestone).filter(Boolean))];
  const box = $("#milestoneFilters");
  box.innerHTML = "";
  milestones.forEach((m) => {
    const chip = el("button", "filter-chip" + (m === activeMilestone ? " active" : ""));
    chip.textContent = m === "all" ? "全部" : m;
    chip.onclick = () => { activeMilestone = m; render(); };
    box.appendChild(chip);
  });
}

function renderColumns() {
  const boardEl = $("#board");
  boardEl.innerHTML = "";
  const cards = visibleCards();
  board.columns.forEach((col) => {
    const colCards = cards
      .filter((c) => c.column === col.id)
      .sort((a, b) => (a.order ?? 0) - (b.order ?? 0));

    const column = el("div", "column");
    column.dataset.colId = col.id;

    const head = el("div", "column-head");
    head.innerHTML = `<span>${col.emoji ? col.emoji + " " : ""}${col.title}</span>
      <span class="count">${colCards.length}</span>`;
    column.appendChild(head);

    const body = el("div", "column-body");
    body.dataset.colId = col.id;
    colCards.forEach((c) => body.appendChild(renderCard(c)));
    column.appendChild(body);

    // 拖放目標
    column.addEventListener("dragover", (e) => { e.preventDefault(); column.classList.add("dragover"); });
    column.addEventListener("dragleave", () => column.classList.remove("dragover"));
    column.addEventListener("drop", (e) => {
      e.preventDefault();
      column.classList.remove("dragover");
      const id = e.dataTransfer.getData("text/plain");
      moveCard(id, col.id);
    });

    boardEl.appendChild(column);
  });
}

function renderCard(c) {
  const card = el("div", "card");
  card.draggable = true;
  card.dataset.id = c.id;
  if (c.milestone) card.dataset.ms = c.milestone;

  const goalHtml = escapeHtml(c.goal || "")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

  card.innerHTML = `
    <div class="card-top">
      <span class="card-title">${escapeHtml(c.title)}</span>
      ${c.milestone ? `<span class="card-ms">${c.milestone}</span>` : ""}
    </div>
    ${c.dates ? `<div class="card-dates">📅 ${escapeHtml(c.dates)}</div>` : ""}
    ${c.goal ? `<div class="card-goal">${goalHtml}</div>` : ""}
    ${c.wbs ? `<div class="card-wbs">${escapeHtml(c.wbs)}</div>` : ""}`;

  card.addEventListener("dragstart", (e) => {
    e.dataTransfer.setData("text/plain", c.id);
    card.classList.add("dragging");
  });
  card.addEventListener("dragend", () => card.classList.remove("dragging"));
  card.addEventListener("dblclick", () => openModal(c.id));
  return card;
}

// ── 卡片操作 ────────────────────────────────────────────────────────────
function moveCard(id, colId) {
  const c = board.cards.find((x) => x.id === id);
  if (!c || c.column === colId) return;
  c.column = colId;
  // 放到該欄末端
  const maxOrder = Math.max(-1, ...board.cards.filter((x) => x.column === colId).map((x) => x.order ?? 0));
  c.order = maxOrder + 1;
  render();
  scheduleSave();
}

function openModal(id) {
  editingId = id;
  const c = id ? board.cards.find((x) => x.id === id) : {};
  const f = $("#cardForm");
  f.title.value = c.title || "";
  f.milestone.value = c.milestone || "";
  f.dates.value = c.dates || "";
  f.wbs.value = c.wbs || "";
  f.goal.value = c.goal || "";
  $("#modalTitle").textContent = id ? "編輯卡片" : "新增卡片";
  $("#deleteCardBtn").style.display = id ? "" : "none";
  $("#modalBackdrop").hidden = false;
}
function closeModal() { $("#modalBackdrop").hidden = true; editingId = null; }

function submitCard(e) {
  e.preventDefault();
  const f = e.target;
  const data = {
    title: f.title.value.trim(),
    milestone: f.milestone.value,
    dates: f.dates.value.trim(),
    wbs: f.wbs.value.trim(),
    goal: f.goal.value.trim(),
  };
  if (editingId) {
    Object.assign(board.cards.find((x) => x.id === editingId), data);
  } else {
    const order = Math.max(-1, ...board.cards.filter((x) => x.column === "backlog").map((x) => x.order ?? 0)) + 1;
    board.cards.push({ id: "card-" + slug(data.title), kind: "task", column: "backlog", order, ...data });
  }
  closeModal();
  render();
  scheduleSave();
}

function deleteCard() {
  if (!editingId) return;
  board.cards = board.cards.filter((x) => x.id !== editingId);
  closeModal();
  render();
  scheduleSave();
}

// ── 工具 ────────────────────────────────────────────────────────────────
function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[m]));
}
function slug(s) {
  return (s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "x") + "-" + (board.cards.length + 1);
}

function exportJson() {
  const blob = new Blob([JSON.stringify(board, null, 2)], { type: "application/json" });
  const a = el("a");
  a.href = URL.createObjectURL(blob);
  a.download = "scrum_board.json";
  a.click();
}

// ── 事件綁定 ────────────────────────────────────────────────────────────
$("#addCardBtn").onclick = () => openModal(null);
$("#cancelBtn").onclick = closeModal;
$("#deleteCardBtn").onclick = deleteCard;
$("#cardForm").addEventListener("submit", submitCard);
$("#exportBtn").onclick = exportJson;
$("#reloadBtn").onclick = loadBoard;
$("#modalBackdrop").addEventListener("click", (e) => { if (e.target.id === "modalBackdrop") closeModal(); });

loadBoard();
