const API = "";

const MOODS = [
  { id: "great", label: "아주 좋음", score: 5, emoji: "😁" },
  { id: "good", label: "좋음", score: 4, emoji: "🙂" },
  { id: "okay", label: "보통", score: 3, emoji: "😐" },
  { id: "down", label: "우울", score: 2, emoji: "😔" },
  { id: "bad", label: "힘듦", score: 1, emoji: "😣" },
];

let selectedMood = null;
let currentEntries = [];

const tabButtons = document.querySelectorAll(".tab");
const panels = {
  check: document.getElementById("panel-check"),
  history: document.getElementById("panel-history"),
  chat: document.getElementById("panel-chat"),
};

const healthEl = document.getElementById("health");
const moodGrid = document.getElementById("mood-grid");
const dateInput = document.getElementById("entry-date");
const commentInput = document.getElementById("comment");
const saveBtn = document.getElementById("save-btn");
const loadBtn = document.getElementById("load-btn");
const saveMessage = document.getElementById("save-message");

const summaryList = document.getElementById("summary-list");
const noticeList = document.getElementById("notice-list");
const historyList = document.getElementById("history-list");
const trendCanvas = document.getElementById("trend-canvas");

const chatBox = document.getElementById("chat-box");
const chatInput = document.getElementById("chat-input");
const chatSend = document.getElementById("chat-send");
const chatSource = document.getElementById("chat-source");
const chatAnalysis = document.getElementById("chat-analysis");

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

function setMessage(msg, warn = false) {
  saveMessage.textContent = msg;
  saveMessage.className = warn ? "message warn" : "message";
}

function renderMoodCards() {
  moodGrid.innerHTML = MOODS.map((m) => `
    <button type="button" class="mood-card ${selectedMood === m.id ? "selected" : ""}" data-id="${m.id}">
      <span class="emoji">${m.emoji}</span>
      <span class="label">${m.label}</span>
    </button>
  `).join("");

  moodGrid.querySelectorAll(".mood-card").forEach((btn) => {
    btn.addEventListener("click", () => {
      selectedMood = btn.dataset.id;
      renderMoodCards();
    });
  });
}

async function apiGet(path) {
  const res = await fetch(`${API}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET ${path} failed`);
  return await res.json();
}

async function apiPost(path, payload) {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || `POST ${path} failed`);
  }
  return await res.json();
}

async function loadEntryByDate() {
  const date = dateInput.value;
  if (!date) {
    setMessage("날짜를 선택하세요.", true);
    return;
  }

  const data = await apiGet(`/api/entry?date=${encodeURIComponent(date)}`);
  const e = data.entry;
  if (!e) {
    selectedMood = null;
    commentInput.value = "";
    renderMoodCards();
    setMessage("해당 날짜 기록이 없습니다.");
    return;
  }

  selectedMood = e.moodId;
  commentInput.value = e.comment || "";
  renderMoodCards();
  setMessage("기록을 불러왔습니다.");
}

async function saveEntry() {
  const date = dateInput.value;
  const comment = commentInput.value.trim();
  if (!date) {
    setMessage("날짜를 선택하세요.", true);
    return;
  }
  if (!selectedMood) {
    setMessage("기분을 선택하세요.", true);
    return;
  }

  await apiPost("/api/entry", { date, moodId: selectedMood, comment });
  setMessage("저장 완료");
  await refreshHistory();
}

function renderSummary(summary) {
  const out = [];
  out.push(`총 기록: ${summary.count}일`);
  out.push(`평균 점수: ${summary.averageScore}`);
  summaryList.innerHTML = out.map((x) => `<li>${x}</li>`).join("");

  const notices = summary.notices?.length ? summary.notices : ["알림 없음"];
  noticeList.innerHTML = notices.map((x) => `<li>${x}</li>`).join("");
}

function renderHistory(entries) {
  const sorted = [...entries].sort((a, b) => (a.date > b.date ? -1 : 1));
  historyList.innerHTML = sorted.length
    ? sorted.map((e) => `<li><strong>${e.date}</strong> · ${e.mood?.emoji || ""} ${e.mood?.label || e.moodId}<br/>${e.comment || "(코멘트 없음)"}</li>`).join("")
    : "<li>기록 없음</li>";
}

function drawTrend(entries) {
  const ctx = trendCanvas.getContext("2d");
  const w = trendCanvas.width;
  const h = trendCanvas.height;
  ctx.clearRect(0, 0, w, h);

  ctx.strokeStyle = "#d9e3ef";
  for (let i = 1; i <= 5; i++) {
    const y = (h - 20) - ((h - 40) * (i - 1) / 4);
    ctx.beginPath();
    ctx.moveTo(30, y);
    ctx.lineTo(w - 10, y);
    ctx.stroke();
    ctx.fillStyle = "#71879d";
    ctx.font = "11px sans-serif";
    ctx.fillText(String(i), 10, y + 4);
  }

  const trend = [...entries].sort((a, b) => (a.date < b.date ? -1 : 1)).slice(-30);
  if (!trend.length) {
    ctx.fillStyle = "#73889d";
    ctx.fillText("데이터가 없습니다", 40, h / 2);
    return;
  }

  const stepX = trend.length > 1 ? (w - 50) / (trend.length - 1) : 0;
  ctx.strokeStyle = "#0f766e";
  ctx.lineWidth = 2;
  ctx.beginPath();

  trend.forEach((e, idx) => {
    const x = 30 + stepX * idx;
    const y = (h - 20) - ((h - 40) * (e.score - 1) / 4);
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.fillStyle = "#0f766e";
  trend.forEach((e, idx) => {
    const x = 30 + stepX * idx;
    const y = (h - 20) - ((h - 40) * (e.score - 1) / 4);
    ctx.beginPath();
    ctx.arc(x, y, 2.8, 0, Math.PI * 2);
    ctx.fill();
  });
}

async function refreshHistory() {
  const [entriesData, summaryData] = await Promise.all([
    apiGet("/api/entries"),
    apiGet("/api/summary"),
  ]);
  currentEntries = entriesData.entries || [];
  renderSummary(summaryData);
  renderHistory(currentEntries);
  drawTrend(currentEntries);
}

function renderChat(messages) {
  chatBox.innerHTML = (messages || []).map((m) => `
    <div class="chat-msg">
      <div class="role">${m.role === "assistant" ? "calm-bot" : "me"} · ${m.createdAt || ""}</div>
      <div class="text">${m.content}</div>
    </div>
  `).join("");
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function refreshChat() {
  const [history, insights] = await Promise.all([apiGet("/api/chat/history"), apiGet("/api/chat/insights")]);
  renderChat(history.messages || []);
  const emotions = (insights.emotions || []).join(", ") || "없음";
  const causes = (insights.causes || []).join(", ") || "없음";
  const actions = (insights.actions || []).map((x) => `<li>권장 액션: ${x}</li>`).join("");
  chatAnalysis.innerHTML = `<li>감정 신호: ${emotions}</li><li>원인 후보: ${causes}</li>${actions}`;
}

async function sendChat() {
  const msg = chatInput.value.trim();
  if (!msg) return;
  chatInput.value = "";
  const res = await apiPost("/api/chat", { message: msg });
  const a = res.analysis || {};
  chatSource.textContent = `응답 소스: ${res.source || "unknown"}`;
  const actions = (a.actions || []).map((x) => `<li>권장 액션: ${x}</li>`).join("");
  chatAnalysis.innerHTML = `<li>감정 신호: ${(a.emotions || []).join(", ") || "없음"}</li><li>원인 후보: ${(a.causes || []).join(", ") || "없음"}</li>${actions}`;
  await refreshChat();
}

function switchTab(tab) {
  tabButtons.forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  Object.entries(panels).forEach(([k, el]) => el.classList.toggle("active", k === tab));
  if (tab === "history") refreshHistory().catch(() => {});
  if (tab === "chat") refreshChat().catch(() => {});
}

async function initHealth() {
  try {
    const data = await apiGet("/api/health");
    healthEl.textContent = `서버 연결됨 (${data.time})`;
  } catch {
    healthEl.textContent = "서버 연결 실패 - server.py 실행 필요";
    healthEl.classList.add("warn");
  }
}

function bind() {
  tabButtons.forEach((b) => b.addEventListener("click", () => switchTab(b.dataset.tab)));
  saveBtn.addEventListener("click", () => saveEntry().catch((e) => setMessage(String(e), true)));
  loadBtn.addEventListener("click", () => loadEntryByDate().catch((e) => setMessage(String(e), true)));
  chatSend.addEventListener("click", () => sendChat().catch(() => {}));
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendChat().catch(() => {});
    }
  });
}

function init() {
  dateInput.value = todayStr();
  renderMoodCards();
  bind();
  initHealth();
  refreshHistory().catch(() => {});
}

init();
