const state = {
  telegramUser: null,
  user: null,
  tasks: [],
  habits: [],
  achievements: [],
  resources: [],
  playlists: [],
  selectedPlaylistId: null,
  selectedPlaylistTracks: [],
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

function toast(message) {
  const node = $("#toast");
  if (!node) return;
  node.textContent = message;
  node.classList.add("show");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => node.classList.remove("show"), 1800);
}

function tgUserFallback() {
  const fromStorage = localStorage.getItem("mentor_webapp_user");
  if (fromStorage) {
    try {
      return JSON.parse(fromStorage);
    } catch {
      /* no-op */
    }
  }
  const randomId = Number(localStorage.getItem("mentor_webapp_id")) || Date.now();
  localStorage.setItem("mentor_webapp_id", String(randomId));
  const fallback = {
    id: randomId,
    username: "webapp_dev",
    first_name: "Web",
    last_name: "User",
  };
  localStorage.setItem("mentor_webapp_user", JSON.stringify(fallback));
  return fallback;
}

function getTelegramUser() {
  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
    tg.setHeaderColor?.("#07101f");
    tg.setBackgroundColor?.("#0f172a");
  }
  return tg?.initDataUnsafe?.user || tgUserFallback();
}

function userPayload() {
  return {
    telegram_id: state.telegramUser.id,
    username: state.telegramUser.username || null,
    first_name: state.telegramUser.first_name || "Пользователь",
    last_name: state.telegramUser.last_name || null,
  };
}

async function api(path, options = {}) {
  const cfg = {
    method: options.method || "GET",
    headers: { "Content-Type": "application/json" },
  };
  if (options.body) cfg.body = JSON.stringify(options.body);
  const res = await fetch(path, cfg);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || "Ошибка API");
  }
  return data;
}

function showTab(tabName) {
  $$(".tab").forEach((tab) => tab.classList.toggle("active", tab.id === `tab-${tabName}`));
  $$(".nav-btn").forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === tabName));
}

function renderHeader() {
  if (!state.user) return;
  $("#userCaption").textContent = `${state.user.display_name} · @${state.user.username || "user"}`;
  $("#mentorHeader").textContent = state.user.settings?.mentor_name || "Железный ментор";
  $("#mentorSubtitle").textContent = `режим: ${state.user.settings?.mentor_persona || state.user.ai_mode}`;
}

function renderDashboard() {
  if (!state.user) return;
  $("#statLevel").textContent = state.user.level;
  $("#statXp").textContent = state.user.total_xp_earned;
  $("#statDiscipline").textContent = Math.round(state.user.discipline_score);
  $("#statGrowth").textContent = Math.round(state.user.growth_score);

  const active = state.tasks.filter((t) => t.status !== "done");
  const done = state.tasks.filter((t) => t.status === "done").slice(0, 8);

  $("#todoToday").innerHTML = active
    .slice(0, 8)
    .map((t) => `<li>⬜ ${escapeHtml(t.title)}</li>`)
    .join("") || "<li>Пусто</li>";
  $("#doneToday").innerHTML = done
    .map((t) => `<li>✅ ${escapeHtml(t.title)}</li>`)
    .join("") || "<li>Пока нет</li>";

  $("#achievements").innerHTML = state.achievements
    .slice(0, 24)
    .map((a) => `<span class="chip">${a.emoji} ${escapeHtml(a.name)}</span>`)
    .join("") || "<span class=\"chip\">Пока нет достижений</span>";
}

function taskBadge(priority) {
  return {
    low: "🟢",
    medium: "🟡",
    high: "🟠",
    critical: "🔴",
  }[priority] || "🟡";
}

function renderTasks() {
  const list = $("#tasksList");
  list.innerHTML = "";
  const sorted = [...state.tasks].sort((a, b) => (a.status === "done") - (b.status === "done"));
  if (!sorted.length) {
    list.innerHTML = "<div class=\"item\">Пока задач нет</div>";
    return;
  }
  sorted.forEach((t) => {
    const row = document.createElement("div");
    row.className = "item";
    row.innerHTML = `
      <div class="item-head">
        <strong>${taskBadge(t.priority)} ${escapeHtml(t.title)}</strong>
        <small>${t.status === "done" ? "✅" : "⬜"}</small>
      </div>
      <p>дедлайн: ${t.deadline || "—"} | повтор: ${t.recurrence_type || "нет"} | напоминание: ${t.remind_time || "—"}</p>
      ${t.status !== "done" ? `<button class="pill secondary js-task-done" data-id="${t.id}">Выполнено</button>` : ""}
    `;
    list.appendChild(row);
  });
}

function renderHabits() {
  const list = $("#habitsList");
  list.innerHTML = "";
  if (!state.habits.length) {
    list.innerHTML = "<div class=\"item\">Привычки не добавлены</div>";
    return;
  }
  state.habits.forEach((h) => {
    const row = document.createElement("div");
    row.className = "item";
    row.innerHTML = `
      <div class="item-head">
        <strong>${escapeHtml(h.emoji)} ${escapeHtml(h.name)}</strong>
        <small>🔥 ${h.current_streak}</small>
      </div>
      <p>напоминание: ${h.remind_enabled ? h.remind_time || "вкл" : "выкл"}</p>
      <button class="pill secondary js-habit-check" data-id="${h.id}">Отметить</button>
    `;
    list.appendChild(row);
  });
}

function renderLearning() {
  const list = $("#learningList");
  list.innerHTML = "";
  if (!state.resources.length) {
    list.innerHTML = "<div class=\"item\">Материалов пока нет</div>";
    return;
  }
  state.resources.forEach((r) => {
    const row = document.createElement("div");
    row.className = "item";
    row.innerHTML = `
      <div class="item-head">
        <strong>${r.is_completed ? "✅" : "📌"} ${escapeHtml(r.title)}</strong>
        <small>${escapeHtml(r.resource_type)}</small>
      </div>
      <p>${escapeHtml(r.topic || "без темы")} ${r.url ? `| <a href="${escapeAttr(r.url)}" target="_blank">ссылка</a>` : ""}</p>
      ${!r.is_completed ? `<button class="pill secondary js-learning-done" data-id="${r.id}">Прошел</button>` : ""}
    `;
    list.appendChild(row);
  });
}

function renderPlaylists() {
  const list = $("#playlistList");
  list.innerHTML = "";
  if (!state.playlists.length) {
    list.innerHTML = "<div class=\"item\">Плейлистов пока нет</div>";
    return;
  }
  state.playlists.forEach((p) => {
    const row = document.createElement("div");
    row.className = "item";
    row.innerHTML = `
      <div class="item-head">
        <strong>${escapeHtml(p.emoji)} ${escapeHtml(p.name)}</strong>
        <small>${state.selectedPlaylistId === p.id ? "выбран" : ""}</small>
      </div>
      <button class="pill secondary js-playlist-select" data-id="${p.id}">Открыть</button>
    `;
    list.appendChild(row);
  });
}

function renderTracks() {
  const list = $("#trackList");
  list.innerHTML = "";
  if (!state.selectedPlaylistId) {
    list.innerHTML = "<div class=\"item\">Выбери плейлист слева</div>";
    return;
  }
  if (!state.selectedPlaylistTracks.length) {
    list.innerHTML = "<div class=\"item\">В выбранном плейлисте нет треков</div>";
    return;
  }
  state.selectedPlaylistTracks.forEach((t) => {
    const row = document.createElement("div");
    row.className = "item";
    row.innerHTML = `
      <div class="item-head">
        <strong>${escapeHtml(t.title || "Без названия")}</strong>
        <small>#${t.position}</small>
      </div>
      <p>${escapeHtml(t.performer || "Не указан")} ${t.file_id ? `| <a href="${escapeAttr(t.file_id)}" target="_blank">слушать</a>` : ""}</p>
    `;
    list.appendChild(row);
  });
}

function renderPermissions() {
  const box = $("#aiPerms");
  const perms = state.user?.settings?.ai_permissions || {};
  const rows = [
    ["read_tasks", "Читать задачи"],
    ["read_habits", "Читать привычки"],
    ["read_journal", "Читать журнал"],
    ["read_stats", "Читать статистику"],
    ["create_tasks", "Создавать задачи"],
    ["modify_tasks", "Изменять задачи"],
    ["read_resources", "Читать обучение"],
  ];
  box.innerHTML = rows
    .map(([key, label]) => `
      <label class="item">
        <div class="item-head">
          <strong>${label}</strong>
          <input type="checkbox" class="js-ai-perm" data-key="${key}" ${perms[key] ? "checked" : ""}/>
        </div>
      </label>
    `)
    .join("");
}

function addChat(role, text) {
  const log = $("#chatLog");
  const node = document.createElement("div");
  node.className = `chat-msg ${role}`;
  node.textContent = text;
  log.appendChild(node);
  log.scrollTop = log.scrollHeight;
}

async function loadBootstrap() {
  const data = await api("/api/v1/bootstrap", { method: "POST", body: userPayload() });
  state.user = data.user;
  state.tasks = data.tasks || [];
  state.habits = data.habits || [];
  state.achievements = data.achievements || [];
  state.resources = data.resources || [];
  state.playlists = data.playlists || [];
  renderHeader();
  renderDashboard();
  renderTasks();
  renderHabits();
  renderLearning();
  renderPlaylists();
  renderTracks();
  renderPermissions();

  $("#mentorForm [name='mentor_name']").value = state.user.settings?.mentor_name || "";
  $("#mentorForm [name='mentor_persona']").value = state.user.settings?.mentor_persona || "goggins";
}

async function loadTodayPlan() {
  const data = await api(`/api/v1/mentor/today-plan?telegram_id=${state.telegramUser.id}`);
  $("#todayPlan").textContent = data.reply || "Нет данных";
}

async function loadPlaylistTracks(playlistId) {
  const data = await api(`/api/v1/playlists/${playlistId}?telegram_id=${state.telegramUser.id}`);
  state.selectedPlaylistId = playlistId;
  state.selectedPlaylistTracks = data.tracks || [];
  renderPlaylists();
  renderTracks();
}

function escapeHtml(s = "") {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttr(s = "") {
  return escapeHtml(s);
}

function wireTabs() {
  $$(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => showTab(btn.dataset.tab));
  });
}

function wireActions() {
  $("#refreshBtn").addEventListener("click", async () => {
    await loadBootstrap();
    toast("Обновлено");
  });

  $("#todayPlanBtn").addEventListener("click", async () => {
    await loadTodayPlan();
    toast("План готов");
  });

  $("#taskForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    const recurrenceType = f.get("recurrence_type") || null;
    const remindTime = f.get("remind_time") || null;
    await api("/api/v1/tasks", {
      method: "POST",
      body: {
        telegram_id: state.telegramUser.id,
        title: f.get("title"),
        priority: f.get("priority"),
        deadline: f.get("deadline") || null,
        is_recurring: Boolean(recurrenceType),
        recurrence_type: recurrenceType,
        recurrence_date: f.get("recurrence_date") || null,
        remind_enabled: Boolean(remindTime),
        remind_time: remindTime,
        remind_text: f.get("remind_text") || null,
      },
    });
    e.target.reset();
    await loadBootstrap();
    toast("Задача создана");
  });

  $("#quickTaskForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    const data = await api("/api/v1/tasks/quick", {
      method: "POST",
      body: {
        telegram_id: state.telegramUser.id,
        title: f.get("title"),
        difficulty: f.get("difficulty"),
      },
    });
    e.target.reset();
    await loadBootstrap();
    toast(`+${data.xp_earned} XP`);
  });

  $("#tasksList").addEventListener("click", async (e) => {
    const btn = e.target.closest(".js-task-done");
    if (!btn) return;
    const taskId = btn.dataset.id;
    await api(`/api/v1/tasks/${taskId}/complete`, {
      method: "POST",
      body: { telegram_id: state.telegramUser.id },
    });
    await loadBootstrap();
    toast("Задача закрыта");
  });

  $("#habitForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    await api("/api/v1/habits", {
      method: "POST",
      body: {
        telegram_id: state.telegramUser.id,
        name: f.get("name"),
        emoji: f.get("emoji") || "✅",
        remind_time: f.get("remind_time") || "21:00",
        remind_enabled: true,
        remind_text: f.get("remind_text") || null,
      },
    });
    e.target.reset();
    await loadBootstrap();
    toast("Привычка создана");
  });

  $("#habitsList").addEventListener("click", async (e) => {
    const btn = e.target.closest(".js-habit-check");
    if (!btn) return;
    await api(`/api/v1/habits/${btn.dataset.id}/check`, {
      method: "POST",
      body: { telegram_id: state.telegramUser.id },
    });
    await loadBootstrap();
    toast("Отмечено");
  });

  $("#mentorForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    await api("/api/v1/profile", {
      method: "PATCH",
      body: {
        telegram_id: state.telegramUser.id,
        mentor_name: f.get("mentor_name"),
        mentor_persona: f.get("mentor_persona"),
      },
    });
    await loadBootstrap();
    toast("Ментор обновлен");
  });

  $("#chatForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    const text = String(f.get("message") || "").trim();
    if (!text) return;
    addChat("user", text);
    e.target.reset();
    const data = await api("/api/v1/mentor/chat", {
      method: "POST",
      body: { telegram_id: state.telegramUser.id, message: text },
    });
    addChat("bot", data.reply || "Пусто");
  });

  $("#learningForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    await api("/api/v1/learning", {
      method: "POST",
      body: {
        telegram_id: state.telegramUser.id,
        resource_type: f.get("resource_type"),
        title: f.get("title"),
        topic: f.get("topic") || null,
        url: f.get("url") || null,
      },
    });
    e.target.reset();
    await loadBootstrap();
    toast("Ресурс добавлен");
  });

  $("#suggestForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    const topic = String(f.get("topic") || "").trim();
    if (!topic) return;
    const data = await api(`/api/v1/learning/suggest?topic=${encodeURIComponent(topic)}`);
    const box = $("#suggestions");
    box.innerHTML = (data.suggestions || [])
      .map((s) => `
        <div class="item">
          <div class="item-head"><strong>${escapeHtml(s.title)}</strong><small>${escapeHtml(s.resource_type)}</small></div>
          <p>${escapeHtml(s.description || "")} ${s.url ? `| <a href="${escapeAttr(s.url)}" target="_blank">открыть</a>` : ""}</p>
        </div>
      `)
      .join("");
  });

  $("#learningList").addEventListener("click", async (e) => {
    const btn = e.target.closest(".js-learning-done");
    if (!btn) return;
    await api(`/api/v1/learning/${btn.dataset.id}/done`, {
      method: "POST",
      body: { telegram_id: state.telegramUser.id },
    });
    await loadBootstrap();
    toast("Отмечено как пройдено");
  });

  $("#playlistForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    await api("/api/v1/playlists", {
      method: "POST",
      body: {
        telegram_id: state.telegramUser.id,
        name: f.get("name"),
        emoji: f.get("emoji") || "🎵",
      },
    });
    e.target.reset();
    await loadBootstrap();
    toast("Плейлист создан");
  });

  $("#playlistList").addEventListener("click", async (e) => {
    const btn = e.target.closest(".js-playlist-select");
    if (!btn) return;
    await loadPlaylistTracks(btn.dataset.id);
  });

  $("#trackForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!state.selectedPlaylistId) {
      toast("Сначала выбери плейлист");
      return;
    }
    const f = new FormData(e.target);
    await api(`/api/v1/playlists/${state.selectedPlaylistId}/tracks`, {
      method: "POST",
      body: {
        telegram_id: state.telegramUser.id,
        title: f.get("title"),
        performer: f.get("performer") || null,
        url: f.get("url") || null,
      },
    });
    e.target.reset();
    await loadPlaylistTracks(state.selectedPlaylistId);
    await loadBootstrap();
    toast("Трек добавлен");
  });

  $("#aiPerms").addEventListener("change", async (e) => {
    const input = e.target.closest(".js-ai-perm");
    if (!input) return;
    const patch = { ai_permissions: { [input.dataset.key]: input.checked } };
    await api("/api/v1/settings", {
      method: "PATCH",
      body: { telegram_id: state.telegramUser.id, patch },
    });
    await loadBootstrap();
    toast("Права обновлены");
  });

  $$("[data-cleanup-history]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const period = btn.dataset.cleanupHistory;
      await api("/api/v1/cleanup/history", {
        method: "POST",
        body: { telegram_id: state.telegramUser.id, period },
      });
      await loadBootstrap();
      toast(`История очищена (${period})`);
    });
  });

  $("#deleteProfileBtn").addEventListener("click", async () => {
    const ok = window.confirm("Удалить профиль полностью? Это нельзя отменить.");
    if (!ok) return;
    await api("/api/v1/cleanup/profile", {
      method: "POST",
      body: { telegram_id: state.telegramUser.id },
    });
    toast("Профиль удален");
    setTimeout(() => window.location.reload(), 500);
  });
}

async function init() {
  state.telegramUser = getTelegramUser();
  wireTabs();
  wireActions();
  showTab("dashboard");
  addChat("bot", "Готов к работе. Напиши цель или попроси план на сегодня.");
  await loadBootstrap();
}

init().catch((err) => {
  console.error(err);
  toast(err.message || "Ошибка запуска");
});
