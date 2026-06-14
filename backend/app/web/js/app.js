const app = document.getElementById("app");
let dashboardRefresh = null;

const THEME_KEY = "tac-theme";
function currentTheme() { try { return localStorage.getItem(THEME_KEY) || "light"; } catch (_) { return "light"; } }
function applyTheme(t) { document.documentElement.dataset.theme = t; try { localStorage.setItem(THEME_KEY, t); } catch (_) {} }
function toggleTheme() { applyTheme(currentTheme() === "dark" ? "light" : "dark"); }
function themeIcon() { return currentTheme() === "dark" ? "☀" : "☾"; }
function bindThemeToggle() {
  document.querySelectorAll("[data-theme-toggle]").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      toggleTheme();
      document.querySelectorAll("[data-theme-toggle]").forEach((b) => { b.textContent = themeIcon(); });
      event.stopPropagation();
    });
  });
}
applyTheme(currentTheme());

// ----- password reveal (eye) toggle, shared by login + create-VM -----
const EYE_ICON = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/><circle cx="12" cy="12" r="3.2"/></svg>';
const EYE_OFF_ICON = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.5 10.5 0 0 1 12 20C5 20 1 12 1 12a18.6 18.6 0 0 1 5.06-5.94M9.9 4.24A9.5 9.5 0 0 1 12 4c7 0 11 8 11 8a18.7 18.7 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="2" y1="2" x2="22" y2="22"/></svg>';
function pwToggle() { return `<button type="button" class="password-toggle" data-pw-toggle aria-label="Mostrar senha" title="Mostrar senha">${EYE_ICON}</button>`; }
document.addEventListener("click", (event) => {
  const btn = event.target.closest && event.target.closest("[data-pw-toggle]");
  if (!btn) return;
  event.preventDefault();
  const field = btn.closest(".password-field");
  const input = field && field.querySelector("input");
  if (!input) return;
  const reveal = input.type === "password";
  input.type = reveal ? "text" : "password";
  btn.innerHTML = reveal ? EYE_OFF_ICON : EYE_ICON;
  btn.setAttribute("aria-label", reveal ? "Ocultar senha" : "Mostrar senha");
  btn.setAttribute("title", reveal ? "Ocultar senha" : "Mostrar senha");
  btn.classList.toggle("revealed", reveal);
});

const api = async (path, options = {}) => {
  const response = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (response.status === 401) {
    renderLogin();
    throw new Error("not authenticated");
  }
  return response;
};

const shell = (content) => `
  <div class="admin-shell">
    <aside class="admin-sidebar">
      <a href="/" class="admin-logo" aria-label="Thiagao Ai Cluster">
        <img src="/img/thiagao-cluster-icon.png" alt="Thiagao Ai Cluster">
      </a>
      <nav class="admin-nav" aria-label="Navegação principal">
        <a class="admin-nav-item" href="/" data-route><span>▦</span>Visão geral</a>
        <a class="admin-nav-item" href="/vms/new" data-route><span>＋</span>Criar VM</a>
        <a class="admin-nav-item" href="/#inventory" data-route><span>⌁</span>Inventário</a>
        <a class="admin-nav-item" href="/atividade" data-route><span>◷</span>Atividade</a>
      </nav>
      <div class="tenant-lock">
        <span class="status-dot"></span>
        <div>
          <strong>Tenant único</strong>
          <small>Sessão admin obrigatória</small>
        </div>
      </div>
    </aside>
    <div class="admin-workspace">
      <header class="admin-topbar">
        <div>
          <span>Painel seguro de cluster</span>
          <strong>Thiagao Ai Cluster / cluster.thiagaoai.online</strong>
        </div>
        <div class="topbar-actions">
          <button class="ghost-button icon-btn" type="button" data-theme-toggle aria-label="Alternar tema claro/escuro">${themeIcon()}</button>
          <a class="ghost-button" href="/trocar-senha" data-route>Trocar senha</a>
          <button class="ghost-button" type="button" data-logout>Sair</button>
        </div>
      </header>
      <main>${content}</main>
    </div>
  </div>
`;

function bindShellEvents() {
  document.querySelectorAll("[data-route]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      history.pushState(null, "", link.getAttribute("href"));
      router();
    });
  });
  document.querySelector("[data-logout]")?.addEventListener("click", async () => {
    await api("/api/auth/logout", { method: "POST" });
    renderLogin();
  });
  bindThemeToggle();
}

function renderLogin(error = "", notice = "") {
  app.innerHTML = `
    <main class="login-page">
      <section class="login-animation-layer" aria-hidden="true">
        <video id="clusteration-hero-video" class="dashboard-video" muted autoplay loop playsinline data-hls-src="https://stream.mux.com/tLkHO1qZoaaQOUeVWo8hEBeGQfySP02EPS02BmnNFyXys.m3u8"></video>
        <div class="dashboard-scrim"></div>
        <div class="grid-lines login-grid-lines"><span></span><span></span><span></span></div>
        <svg class="center-glow login-glow" viewBox="0 0 900 240" aria-hidden="true">
          <defs>
            <filter id="loginCyanGlowBlur">
              <feGaussianBlur stdDeviation="25"></feGaussianBlur>
            </filter>
          </defs>
          <ellipse cx="450" cy="110" rx="330" ry="54" fill="#1f9d83" opacity="0.48" filter="url(#loginCyanGlowBlur)"></ellipse>
          <ellipse cx="450" cy="108" rx="240" ry="34" fill="#54f4d1" opacity="0.18" filter="url(#loginCyanGlowBlur)"></ellipse>
        </svg>
      </section>
      <form class="card form-card login-card" id="login-form">
        <img class="login-logo" src="/img/thiagao-cluster-logo.png" alt="Thiagao Ai Cluster">
        <span class="eyebrow">Admin · tenant único</span>
        <h1>Acesso seguro ao cluster</h1>
        <p>Login obrigatório para proteger inventário, terminais e ações das suas VMs.</p>
        ${error ? `<p class="error">${error}</p>` : ""}
        ${notice ? `<p class="success">${notice}</p>` : ""}
        <label><span>Usuário</span><input name="username" autocomplete="username" autocapitalize="none" autocorrect="off" spellcheck="false" required></label>
        <label><span>Senha</span><div class="password-field"><input name="password" type="password" autocomplete="current-password" required>${pwToggle()}</div></label>
        <button class="primary-button" type="submit">Entrar</button>
        <button class="ghost-button" type="button" data-forgot style="margin-top:6px">Esqueci minha senha</button>
      </form>
    </main>
  `;
  startHeroVideo();
  document.querySelector("[data-forgot]")?.addEventListener("click", () => { history.pushState(null, "", "/recuperar"); renderReset(); });
  document.getElementById("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const body = JSON.stringify(Object.fromEntries(new FormData(event.currentTarget).entries()));
    const response = await fetch("/api/auth/login", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body,
    });
    if (!response.ok) {
      renderLogin("Credenciais inválidas.");
      return;
    }
    history.pushState(null, "", "/");
    router();
  });
}

function renderReset(stage = "request", message = "") {
  const isErr = message.startsWith("!");
  const text = message.replace(/^!/, "");
  app.innerHTML = `
    <main class="login-page">
      <section class="login-animation-layer" aria-hidden="true">
        <div class="dashboard-scrim"></div>
        <div class="grid-lines login-grid-lines"><span></span><span></span><span></span></div>
      </section>
      <form class="card form-card login-card" id="reset-form">
        <img class="login-logo" src="/img/thiagao-cluster-logo.png" alt="Thiagao Ai Cluster">
        <span class="eyebrow">Redefinir senha</span>
        <h1>Esqueci minha senha</h1>
        ${message ? `<p class="${isErr ? "error" : "success"}">${esc(text)}</p>` : ""}
        ${stage === "request" ? `
          <p>Vamos enviar um código de 6 dígitos para o seu email cadastrado.</p>
          <button class="primary-button" type="submit">Enviar código por email</button>
        ` : `
          <p>Digite o código que chegou no seu email e escolha a nova senha.</p>
          <label><span>Código (6 dígitos)</span><input name="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" required></label>
          <label><span>Nova senha (mín. 8)</span><div class="password-field"><input name="new_password" type="password" minlength="8" autocomplete="new-password" required>${pwToggle()}</div></label>
          <button class="primary-button" type="submit">Redefinir senha</button>
        `}
        <button class="ghost-button" type="button" data-back-login style="margin-top:6px">Voltar ao login</button>
      </form>
    </main>
  `;
  document.querySelector("[data-back-login]").addEventListener("click", () => { history.pushState(null, "", "/login"); renderLogin(); });
  document.getElementById("reset-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (stage === "request") {
      const r = await fetch("/api/auth/forgot", { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" } });
      const d = await r.json().catch(() => null);
      if (r.ok) renderReset("confirm", `Código enviado para ${d && d.to ? d.to : "seu email"}. Veja sua caixa de entrada (e o spam).`);
      else renderReset("request", "!" + ((d && d.error && d.error.message) || "Não foi possível enviar o email agora."));
      return;
    }
    const data = Object.fromEntries(new FormData(event.currentTarget).entries());
    const r = await fetch("/api/auth/reset", { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
    const d = await r.json().catch(() => null);
    if (r.ok) { history.pushState(null, "", "/login"); renderLogin("", "Senha redefinida! Entre com a nova senha."); }
    else renderReset("confirm", "!" + ((d && d.error && d.error.message) || "Código inválido ou expirado."));
  });
}

function renderChangePassword(message = "") {
  const isErr = message.startsWith("!");
  const text = message.replace(/^!/, "");
  app.innerHTML = shell(`
    <section class="section-header">
      <div><span class="eyebrow">Conta</span><h1>Trocar senha</h1><p>Defina uma nova senha de acesso ao painel.</p></div>
    </section>
    <div class="card form-card">
      ${message ? `<p class="${isErr ? "error" : "success"}">${esc(text)}</p>` : ""}
      <form id="change-form" class="form">
        <label><span>Senha atual</span><div class="password-field"><input name="current_password" type="password" autocomplete="current-password" required>${pwToggle()}</div></label>
        <label><span>Nova senha (mín. 8)</span><div class="password-field"><input name="new_password" type="password" minlength="8" autocomplete="new-password" required>${pwToggle()}</div></label>
        <div class="form-actions">
          <a class="ghost-button" href="/" data-route>Cancelar</a>
          <button class="primary-button" type="submit">Salvar nova senha</button>
        </div>
      </form>
    </div>
  `);
  bindShellEvents();
  document.getElementById("change-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget).entries());
    const r = await fetch("/api/auth/change-password", { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
    const d = await r.json().catch(() => null);
    if (r.ok) { history.pushState(null, "", "/"); renderDashboard(); }
    else renderChangePassword("!" + ((d && d.error && d.error.message) || "Não foi possível trocar a senha."));
  });
}

async function renderDashboard() {
  const response = await api("/api/vms");
  const { vms } = await response.json();
  const hasTransient = vms.some((vm) =>
    ["creating", "provisioning", "starting", "stopping", "rebooting", "deleting"].includes(vm.status),
  );
  app.innerHTML = shell(`
    <section class="cluster-admin-dashboard">
      <video id="clusteration-hero-video" class="dashboard-video" muted autoplay loop playsinline data-hls-src="https://stream.mux.com/tLkHO1qZoaaQOUeVWo8hEBeGQfySP02EPS02BmnNFyXys.m3u8"></video>
      <div class="dashboard-scrim"></div>
      <div class="grid-lines admin-grid-lines" aria-hidden="true"><span></span><span></span><span></span></div>
      <div class="dashboard-layout">
        <section class="admin-hero-card reveal">
          <div>
            <a class="hero-badge" href="#inventory" data-route>
              <span class="hero-badge-dot"></span>Cluster soberano · Proxmox VE 9.2<span class="hero-badge-arrow">→</span>
            </a>
            <h1>Central de comando<br>do cluster<span>.</span></h1>
            <p class="hero-type" data-typewriter="Provisione, monitore e abra o terminal das suas VMs Proxmox — em segundos, com segurança single-tenant."></p>
          </div>
          <div class="hero-pills">
            <a class="pill pill-solid" href="/vms/new" data-route>Criar VM</a>
            <a class="pill" href="#inventory" data-route>Ver inventário</a>
            <a class="pill" href="#inventory" data-route>Abrir terminal</a>
            <button type="button" class="pill pill-outline" data-copy="cluster.thiagaoai.online">cluster.thiagaoai.online<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="11" height="11" rx="2"></rect><path d="M5 15V5a2 2 0 0 1 2-2h10"></path></svg></button>
          </div>
        </section>
        <aside class="liquid-card admin-security-card" id="security">
          <span>[ 2025 ]</span>
          <h2>Operações <em>privadas</em> do cluster</h2>
          <p>Login obrigatório antes de inventário, terminal SSH e ações críticas de VM.</p>
        </aside>
      </div>
    </section>
    <section class="content dashboard-content" id="inventory">
      <section class="stats-grid">
        <article class="card stat-card green"><span>VMs ativas</span><strong>${vms.filter((vm) => vm.status === "running").length}</strong><small>Compute online agora</small></article>
        <article class="card stat-card blue"><span>Inventário total</span><strong>${vms.length}</strong><small>VMs gerenciadas</small></article>
        <article class="card stat-card amber"><span>Jobs em andamento</span><strong>${hasTransient ? "Sim" : "Não"}</strong><small>Atualiza sozinho quando ativo</small></article>
        <article class="card stat-card slate"><span>Modo de acesso</span><strong>Privado</strong><small>Admin · tenant único</small></article>
      </section>
      <section class="section-header">
        <div><span class="eyebrow">Operações de compute</span><h1>Inventário e ações de VM</h1><p>Ligar, desligar, reiniciar, abrir terminal e excluir — tudo após login de admin.</p></div>
        <a class="primary-button" href="/vms/new" data-route>Criar VM</a>
      </section>
      ${vmTable(vms)}
    </section>
  `);
  bindShellEvents();
  bindDashboardActions();
  startHeroVideo();
  runHeroEffects();
  clearTimeout(dashboardRefresh);
  if (hasTransient) dashboardRefresh = setTimeout(() => { if (window.location.pathname === "/") renderDashboard(); }, 5000);
}

function runHeroEffects() {
  document.querySelectorAll("[data-typewriter]").forEach((el) => {
    const text = el.getAttribute("data-typewriter") || "";
    el.textContent = "";
    const cursor = document.createElement("span");
    cursor.className = "type-cursor";
    el.appendChild(cursor);
    let i = 0;
    const tick = () => {
      if (i < text.length) {
        cursor.insertAdjacentText("beforebegin", text.charAt(i));
        i += 1;
        setTimeout(tick, 24);
      } else {
        cursor.remove();
      }
    };
    setTimeout(tick, 420);
  });
  document.querySelectorAll("[data-copy]").forEach((btn) => {
    btn.addEventListener("click", () => {
      try { navigator.clipboard?.writeText(btn.getAttribute("data-copy") || ""); } catch (_) {}
      btn.classList.add("copied");
      setTimeout(() => btn.classList.remove("copied"), 1200);
    });
  });
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

const STATUS_LABEL = { running: "ativa", stopped: "parada", error: "erro", creating: "criando", provisioning: "provisionando", starting: "ligando", stopping: "desligando", rebooting: "reiniciando", deleting: "excluindo", deleted: "excluída" };
function statusLabel(s) { return STATUS_LABEL[s] || s; }
function sshBadge(s) { return s === "ready" ? "badge-running" : (s === "failed" ? "badge-failed" : "badge-pending"); }

function vmTable(vms) {
  const rows = vms.map((vm) => `
    <tr>
      <td data-label="Hostname"><strong>${esc(vm.hostname)}</strong>${vm.last_error ? `<div class="vm-error" title="${esc(vm.last_error)}">⚠ ${esc(vm.last_error)}</div>` : ""}</td>
      <td data-label="Status"><span class="badge badge-${vm.status}">${statusLabel(vm.status)}</span></td>
      <td data-label="SSH"><span class="badge ${sshBadge(vm.ssh_status)}">${esc(vm.ssh_status)}</span></td>
      <td data-label="IP">${esc(vm.ip_address) || "—"}</td>
      <td data-label="Template">${esc(vm.template)}</td>
      <td data-label="Recursos">${vm.cpu} CPU · ${vm.memory_mb} MB · ${vm.disk_gb} GB</td>
      <td class="actions" data-label="Ações">
        <button class="ghost-button" data-action="start" data-id="${vm.id}" ${vm.actions.can_start ? "" : "disabled"}>Ligar</button>
        <button class="ghost-button" data-action="stop" data-id="${vm.id}" ${vm.actions.can_stop ? "" : "disabled"}>Desligar</button>
        <button class="ghost-button" data-action="reboot" data-id="${vm.id}" ${vm.actions.can_reboot ? "" : "disabled"}>Reiniciar</button>
        ${vm.actions.can_recheck ? `<button class="ghost-button" data-recheck="${vm.id}">Re-checar SSH</button>` : ""}
        <button class="primary-button" data-terminal="${vm.id}" data-hostname="${esc(vm.hostname)}" ${vm.actions.can_terminal ? "" : "disabled"}>Terminal</button>
        <button class="danger-button" data-delete="${vm.id}" data-hostname="${esc(vm.hostname)}" ${vm.actions.can_delete ? "" : "disabled"}>Excluir</button>
      </td>
    </tr>
  `).join("");
  return `
    <section class="card">
      <div class="card-title"><h2>Inventário de VMs</h2><span class="pill">${vms.length} recursos</span></div>
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>Hostname</th><th>Status</th><th>SSH</th><th>IP</th><th>Template</th><th>Recursos</th><th>Ações</th></tr></thead>
          <tbody>${rows || `<tr><td colspan="7" class="empty">Nenhuma VM criada ainda.</td></tr>`}</tbody>
        </table>
      </div>
    </section>
  `;
}

async function errMsg(res) {
  try { const j = await res.json(); return j?.error?.message || null; } catch (_) { return null; }
}

async function withLoading(button, fn) {
  if (button.dataset.loading === "1") return;
  button.dataset.loading = "1";
  button.classList.add("is-loading");
  button.disabled = true;
  try { await fn(); }
  finally {
    if (document.body.contains(button)) {
      button.dataset.loading = "0";
      button.classList.remove("is-loading");
      button.disabled = false;
    }
  }
}

function toast(message, type = "ok") {
  let wrap = document.getElementById("toasts");
  if (!wrap) { wrap = document.createElement("div"); wrap.id = "toasts"; wrap.className = "toasts"; document.body.appendChild(wrap); }
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.textContent = message;
  wrap.appendChild(el);
  requestAnimationFrame(() => el.classList.add("show"));
  setTimeout(() => { el.classList.remove("show"); setTimeout(() => el.remove(), 250); }, 3400);
}

function confirmModal({ title, body, confirmText = "Confirmar", cancelText = "Cancelar", danger = false, requireText = null }) {
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.innerHTML = `
      <div class="modal" role="dialog" aria-modal="true">
        <h3>${esc(title)}</h3>
        <div class="modal-body">${body}</div>
        ${requireText ? `<input class="modal-input" type="text" placeholder="${esc(requireText)}" autocapitalize="none" autocorrect="off" spellcheck="false">` : ""}
        <div class="modal-actions">
          <button class="ghost-button" type="button" data-cancel>${esc(cancelText)}</button>
          <button class="${danger ? "danger-button" : "primary-button"}" type="button" data-confirm ${requireText ? "disabled" : ""}>${esc(confirmText)}</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    const input = overlay.querySelector(".modal-input");
    const confirmBtn = overlay.querySelector("[data-confirm]");
    const close = (val) => { overlay.remove(); document.removeEventListener("keydown", onKey); resolve(val); };
    const onKey = (e) => { if (e.key === "Escape") close(false); };
    document.addEventListener("keydown", onKey);
    if (input) {
      input.addEventListener("input", () => { confirmBtn.disabled = input.value !== requireText; });
      setTimeout(() => input.focus(), 30);
    }
    overlay.addEventListener("click", (e) => { if (e.target === overlay) close(false); });
    overlay.querySelector("[data-cancel]").addEventListener("click", () => close(false));
    confirmBtn.addEventListener("click", () => { if (requireText && input.value !== requireText) return; close(true); });
  });
}

function bindDashboardActions() {
  document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => withLoading(button, async () => {
      const res = await api(`/api/vms/${button.dataset.id}/${button.dataset.action}`, { method: "POST" });
      if (!res.ok) { toast(await errMsg(res) || "Ação não permitida agora.", "error"); return; }
      toast(`VM ${({ start: "ligando", stop: "desligando", reboot: "reiniciando" }[button.dataset.action] || "processando")}…`);
      renderDashboard();
    }));
  });
  document.querySelectorAll("[data-recheck]").forEach((button) => {
    button.addEventListener("click", () => withLoading(button, async () => {
      const res = await api(`/api/vms/${button.dataset.recheck}/ssh-check`, { method: "POST" });
      if (!res.ok) { toast(await errMsg(res) || "Não foi possível checar o SSH.", "error"); return; }
      toast("Re-checando o SSH da VM…");
      renderDashboard();
    }));
  });
  document.querySelectorAll("[data-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      const host = button.dataset.hostname;
      const ok = await confirmModal({
        title: "Excluir VM",
        body: `Isso apaga a VM <strong>${esc(host)}</strong> <strong>permanentemente</strong> no Proxmox (disco incluído). Digite o hostname para confirmar:`,
        confirmText: "Excluir VM",
        danger: true,
        requireText: host,
      });
      if (!ok) return;
      await withLoading(button, async () => {
        const res = await api(`/api/vms/${button.dataset.delete}`, { method: "DELETE", body: JSON.stringify({ confirm_hostname: host }) });
        if (!res.ok) { toast(await errMsg(res) || "Erro ao excluir.", "error"); return; }
        toast("VM em exclusão…");
        renderDashboard();
      });
    });
  });
  document.querySelectorAll("[data-terminal]").forEach((button) => {
    button.addEventListener("click", () => withLoading(button, async () => {
      const response = await api(`/api/vms/${button.dataset.terminal}/terminal/session`, { method: "POST" });
      if (!response.ok) { toast(await errMsg(response) || "Terminal ainda não está pronto.", "error"); return; }
      const data = await response.json();
      const vm = encodeURIComponent(button.dataset.terminal);
      const host = encodeURIComponent(button.dataset.hostname || "VM");
      history.pushState(null, "", `/terminal?session=${encodeURIComponent(data.session_id)}&vm=${vm}&host=${host}`);
      router();
    }));
  });
}

async function renderNewVm() {
  const [templatesResponse, optionsResponse] = await Promise.all([api("/api/templates"), api("/api/options")]);
  const { templates } = await templatesResponse.json();
  const options = await optionsResponse.json();
  app.innerHTML = shell(`
    <section class="section-header">
      <div><span class="eyebrow">Provisionamento</span><h1>Criar VM</h1><p>Escolha template, recursos e disco para iniciar uma nova VPS interna.</p></div>
    </section>
    <div class="card form-card">
      ${options.missing_runtime.length ? `<p class="error">Ambiente Proxmox ainda não configurado: ${options.missing_runtime.join(", ")}.</p>` : ""}
      <form id="create-vm-form" class="form form-grid">
        <label><span>Hostname</span><input name="hostname" pattern="[a-zA-Z0-9](-?[a-zA-Z0-9]){0,126}" title="letras, números e hífen (não pode começar/terminar com hífen)" required></label>
        <label><span>Template</span><select name="template">${templates.map((template) => `<option value="${template.os}" ${template.enabled ? "" : "disabled"}>${template.name}</option>`).join("")}</select></label>
        <label><span>Tamanho</span><select name="size">${Object.entries(options.sizes).map(([key, size]) => `<option value="${key}">${size.label}</option>`).join("")}</select></label>
        <label><span>Disco</span><select name="disk_gb">${options.disk_choices.map((gb) => `<option value="${gb}">${gb} GB</option>`).join("")}</select></label>
        <label><span>Senha root</span><div class="password-field"><input id="root-password" name="root_password" type="password" minlength="8" required>${pwToggle()}</div></label>
        <div class="form-actions">
          <a class="ghost-button" href="/" data-route>Cancelar</a>
          <button class="primary-button" type="submit" ${options.missing_runtime.length ? "disabled" : ""}>Criar VM</button>
        </div>
      </form>
      <p id="form-message"></p>
    </div>
  `);
  bindShellEvents();
  document.getElementById("create-vm-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget).entries());
    data.disk_gb = Number(data.disk_gb);
    const message = document.getElementById("form-message");
    message.textContent = "Criando job...";
    const response = await api("/api/vms", { method: "POST", body: JSON.stringify(data) });
    if (!response.ok) {
      const error = await response.json().catch(() => null);
      message.textContent = error?.error?.message || "Erro ao criar VM.";
      message.className = "error";
      return;
    }
    history.pushState(null, "", "/");
    router();
  });
}

const AUDIT_LABELS = {
  "vm.create": "Criou VM", "vm.delete": "Excluiu VM", "vm.start": "Ligou VM",
  "vm.stop": "Desligou VM", "vm.reboot": "Reiniciou VM",
  "auth.login": "Login", "auth.login_failed": "Login falhou",
  "auth.login_blocked": "Login bloqueado", "auth.logout": "Logout",
};
function auditLabel(a) { return AUDIT_LABELS[a] || a; }
function auditBadge(a) {
  if (a === "vm.delete" || a === "auth.login_failed" || a === "auth.login_blocked") return "badge-error";
  if (a === "vm.create") return "badge-running";
  return "";
}
function auditRow(e) {
  const when = e.created_at ? new Date(e.created_at).toLocaleString() : "—";
  const target = e.target_label ? esc(e.target_label) : (e.target_type ? esc(e.target_type) : "—");
  const detail = e.detail && Object.keys(e.detail).length ? esc(JSON.stringify(e.detail)) : "—";
  return `<tr>
    <td data-label="Quando">${esc(when)}</td>
    <td data-label="Ação"><span class="badge ${auditBadge(e.action)}">${esc(auditLabel(e.action))}</span></td>
    <td data-label="Alvo"><strong>${target}</strong></td>
    <td data-label="Usuário">${esc(e.actor || "—")}</td>
    <td data-label="Origem">${esc(e.source_ip || "—")}</td>
    <td data-label="Detalhes"><code style="font-size:11px; word-break:break-all">${detail}</code></td>
  </tr>`;
}

async function renderAudit() {
  const response = await api("/api/audit?limit=200");
  const { events } = await response.json();
  app.innerHTML = shell(`
    <section class="section-header">
      <div><span class="eyebrow">Auditoria</span><h1>Atividade</h1><p>Registro imutável de ações administrativas — quem fez o quê, em qual VM, de onde e quando.</p></div>
    </section>
    <div class="card">
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>Quando</th><th>Ação</th><th>Alvo</th><th>Usuário</th><th>Origem (IP)</th><th>Detalhes</th></tr></thead>
          <tbody>
            ${events.length ? events.map(auditRow).join("") : `<tr><td class="empty" colspan="6">Nenhuma atividade registrada ainda.</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>
  `);
  bindShellEvents();
}

function renderTerminal() {
  const params = new URLSearchParams(window.location.search);
  const sessionId = params.get("session");
  const vmId = params.get("vm") || "";
  const host = params.get("host") || "VM";
  app.innerHTML = `
    <section class="term-workspace" id="term-workspace">
      <header class="term-bar">
        <div class="term-bar-left">
          <button class="term-btn" id="term-back" title="Voltar ao painel">‹ Painel</button>
          <span class="term-host">${host}</span>
        </div>
        <div class="term-tabs" id="term-tabs"></div>
        <div class="term-bar-right">
          <button class="term-btn" id="term-newtab" title="Nova aba"${vmId ? "" : " disabled"}>+ Aba</button>
          <button class="term-btn" id="term-full" title="Tela cheia">⛶ Tela cheia</button>
        </div>
      </header>
      <div class="term-stage" id="term-stage"></div>
    </section>
  `;
  const mgr = new TerminalWorkspace(vmId, document.getElementById("term-stage"), document.getElementById("term-tabs"));
  document.getElementById("term-back").addEventListener("click", () => { mgr.destroy(); history.pushState(null, "", "/"); router(); });
  document.getElementById("term-newtab").addEventListener("click", () => mgr.newTab());
  document.getElementById("term-full").addEventListener("click", () => mgr.toggleFullscreen());
  if (sessionId) mgr.addTab(sessionId);
}

class TerminalWorkspace {
  constructor(vmId, stage, tabsEl) {
    this.vmId = vmId;
    this.stage = stage;
    this.tabsEl = tabsEl;
    this.tabs = [];
    this.active = null;
    this.seq = 0;
    this._onResize = () => { this.syncHeight(); this.fitActive(); };
    window.addEventListener("resize", this._onResize);
    if (window.visualViewport) window.visualViewport.addEventListener("resize", this._onResize);
    this.syncHeight();
  }
  syncHeight() {
    const ws = document.getElementById("term-workspace");
    if (ws && window.visualViewport) ws.style.height = window.visualViewport.height + "px";
  }
  async newTab() {
    if (!this.vmId) return;
    try {
      const res = await api(`/api/vms/${this.vmId}/terminal/session`, { method: "POST" });
      if (!res.ok) { alert("Não foi possível abrir uma nova aba agora."); return; }
      const data = await res.json();
      this.addTab(data.session_id);
    } catch (_) { alert("Erro ao abrir nova aba."); }
  }
  addTab(sessionId) {
    const id = ++this.seq;
    const pane = document.createElement("div");
    pane.className = "term-pane";
    this.stage.appendChild(pane);
    const term = new Terminal({ convertEol: false, cursorBlink: true, fontSize: 13, fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace", theme: { background: "#0a0a0a" } });
    let fit = null;
    try { fit = new FitAddon.FitAddon(); term.loadAddon(fit); } catch (_) {}
    term.open(pane);
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${protocol}://${window.location.host}/terminal/ws?session_id=${encodeURIComponent(sessionId)}`);
    ws.binaryType = "arraybuffer";
    const tab = { id, sessionId, term, fit, ws, pane, status: "connecting", ping: null };
    ws.onopen = () => { tab.status = "connected"; this.fitActive(); this.renderTabs(); };
    ws.onmessage = (event) => {
      if (typeof event.data === "string") {
        try {
          const p = JSON.parse(event.data);
          if (p.type === "status") tab.status = p.status;
          else if (p.type === "error") tab.status = p.message || "erro";
          else if (p.type === "close") tab.status = p.reason || "fechado";
          this.renderTabs();
        } catch (_) {}
        return;
      }
      term.write(new Uint8Array(event.data));
    };
    ws.onclose = () => { tab.status = "fechado"; this.renderTabs(); };
    term.onData((d) => { if (ws.readyState === WebSocket.OPEN) ws.send(new TextEncoder().encode(d)); });
    term.onResize(({ cols, rows }) => { if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "resize", cols, rows })); });
    tab.ping = setInterval(() => { if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "ping" })); }, 20000);
    this.tabs.push(tab);
    this.activate(tab);
  }
  activate(tab) {
    this.active = tab;
    this.tabs.forEach((t) => { t.pane.style.display = t === tab ? "block" : "none"; });
    this.renderTabs();
    requestAnimationFrame(() => { this.fitActive(); try { tab.term.focus(); } catch (_) {} });
  }
  fitActive() {
    const t = this.active;
    if (!t || !t.fit) return;
    try { t.fit.fit(); t.term.scrollToBottom(); } catch (_) {}
  }
  closeTab(tab) {
    try { clearInterval(tab.ping); } catch (_) {}
    try { tab.ws.close(); } catch (_) {}
    try { tab.term.dispose(); } catch (_) {}
    tab.pane.remove();
    this.tabs = this.tabs.filter((t) => t !== tab);
    if (this.active === tab) {
      const next = this.tabs[this.tabs.length - 1];
      if (next) { this.activate(next); return; }
      this.destroy();
      history.pushState(null, "", "/");
      router();
      return;
    }
    this.renderTabs();
  }
  renderTabs() {
    if (!this.tabsEl) return;
    this.tabsEl.innerHTML = "";
    this.tabs.forEach((t, i) => {
      const cls = t.status === "connected" ? "ok" : (t.status === "connecting" ? "wait" : "off");
      const btn = document.createElement("button");
      btn.className = "term-tab" + (t === this.active ? " active" : "");
      btn.innerHTML = `<span class="term-tab-dot ${cls}"></span>Aba ${i + 1}<span class="term-tab-x" data-x>×</span>`;
      btn.addEventListener("click", (event) => {
        if (event.target && event.target.hasAttribute("data-x")) { event.stopPropagation(); this.closeTab(t); return; }
        this.activate(t);
      });
      this.tabsEl.appendChild(btn);
    });
  }
  toggleFullscreen() {
    const el = document.getElementById("term-workspace");
    if (!el) return;
    if (document.fullscreenElement) {
      if (document.exitFullscreen) document.exitFullscreen();
    } else if (el.requestFullscreen) {
      el.requestFullscreen().catch(() => el.classList.toggle("term-fs"));
    } else {
      el.classList.toggle("term-fs");
    }
    setTimeout(() => this.fitActive(), 140);
  }
  destroy() {
    window.removeEventListener("resize", this._onResize);
    if (window.visualViewport) window.visualViewport.removeEventListener("resize", this._onResize);
    this.tabs.forEach((t) => {
      try { clearInterval(t.ping); } catch (_) {}
      try { t.ws.close(); } catch (_) {}
      try { t.term.dispose(); } catch (_) {}
    });
    this.tabs = [];
  }
}

function startHeroVideo() {
  const video = document.getElementById("clusteration-hero-video");
  if (!video) return;
  // On phones the continuous HLS stream saturates the connection and the page
  // appears stuck "loading" — drop it and keep the static scrim/glow background.
  const isSmall = window.matchMedia && window.matchMedia("(max-width: 720px)").matches;
  const saveData = navigator.connection && navigator.connection.saveData;
  if (isSmall || saveData) {
    video.removeAttribute("autoplay");
    video.remove();
    return;
  }
  const src = video.dataset.hlsSrc;
  if (!src) return;
  if (window.Hls && Hls.isSupported()) {
    const hls = new Hls({ enableWorker: false });
    hls.loadSource(src);
    hls.attachMedia(video);
    hls.on(Hls.Events.MANIFEST_PARSED, () => {
      video.play().catch(() => {});
    });
  } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
    video.src = src;
    video.addEventListener("canplay", () => video.play().catch(() => {}), { once: true });
  } else {
    video.src = src;
    video.play().catch(() => {});
  }
}

function renderLanding() {
  app.innerHTML = `
    <div class="landing landing-light" id="landing">
      <video id="landing-video" class="landing-video" muted playsinline preload="auto" src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260530_042513_df96a13b-6155-4f6e-8b93-c9dee66fba08.mp4"></video>
      <header class="landing-nav">
        <a class="landing-logo" href="/login" data-login><img class="landing-logo-img" src="/img/thiagao-cluster-icon.png" alt="Thiagao Ai Cluster"></a>
        <nav class="landing-links">
          <a href="/login" data-login>Overview</a><span class="sep">, </span><a href="/login" data-login>Inventory</a><span class="sep">, </span><a href="/login" data-login>Docs</a>
        </nav>
        <a class="landing-getin" href="/login" data-login>Acessar painel</a>
        <button class="landing-theme" type="button" data-theme-toggle aria-label="Alternar tema">${themeIcon()}</button>
        <button class="landing-burger" type="button" aria-label="Abrir menu"><span></span><span></span><span></span></button>
      </header>
      <div class="landing-overlay">
        <a href="/login" data-login>Overview</a>
        <a href="/login" data-login>Inventory</a>
        <a href="/login" data-login>Docs</a>
        <a href="/login" data-login class="ov-getin">Acessar painel</a>
      </div>
      <main class="landing-hero">
        <div class="landing-inner">
          <p class="landing-intro">Olá, esse é o Clusteration,<br>seu Secure Cluster Panel — cluster.thiagaoai.online</p>
          <p class="landing-type" data-typewriter="Painel single-tenant para provisionar, monitorar, acessar terminal e controlar suas VMs Proxmox com segurança."></p>
          <div class="landing-pills">
            <button class="lpill" type="button" data-login>Acessar painel</button>
            <button class="lpill" type="button" data-login>Criar VM</button>
            <button class="lpill" type="button" data-login>Ver inventário</button>
            <button class="lpill" type="button" data-login>Abrir terminal</button>
            <button class="lpill lpill-outline" type="button" data-copy="dockplus@dockplusai.com">Fale com a gente: <span class="lpill-u">dockplus@dockplusai.com</span><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="11" height="11" rx="2"></rect><path d="M5 15V5a2 2 0 0 1 2-2h10"></path></svg></button>
          </div>
        </div>
      </main>
    </div>
  `;
  const goLogin = (event) => {
    if (event) event.preventDefault();
    document.body.classList.remove("landing-menu-open");
    history.pushState(null, "", "/login");
    renderLogin();
  };
  document.querySelectorAll("[data-login]").forEach((el) => el.addEventListener("click", goLogin));
  const burger = document.querySelector(".landing-burger");
  if (burger) burger.addEventListener("click", () => document.body.classList.toggle("landing-menu-open"));
  bindThemeToggle();
  runHeroEffects();
  startLandingVideo();
}

function startLandingVideo() {
  const video = document.getElementById("landing-video");
  if (!video) return;
  // Respect data-saver only; otherwise the hero video appears everywhere.
  if (navigator.connection && navigator.connection.saveData) {
    video.removeAttribute("src");
    video.remove();
    return;
  }
  const isSmall = window.matchMedia && window.matchMedia("(max-width: 768px)").matches;
  if (isSmall) {
    // Touch devices have no mouse to scrub: gently autoplay/loop so the visual still shows.
    video.setAttribute("loop", "");
    video.muted = true;
    const playMobile = () => video.play().catch(() => {});
    if (video.readyState >= 2) playMobile();
    else video.addEventListener("loadeddata", playMobile, { once: true });
    try { video.load(); } catch (_) {}
    return;
  }
  const enableScrub = () => {
    let targetTime = video.duration ? video.duration * 0.15 : 0;
    let prevX = null;
    let seeking = false;
    const SENS = 0.8;
    const doSeek = () => {
      if (!video.duration) return;
      if (Math.abs(video.currentTime - targetTime) < 0.02) { seeking = false; return; }
      seeking = true;
      try { video.currentTime = targetTime; } catch (_) { seeking = false; }
    };
    video.addEventListener("seeked", () => {
      if (Math.abs(video.currentTime - targetTime) > 0.03) doSeek();
      else seeking = false;
    });
    try { video.currentTime = targetTime; } catch (_) {}
    window.addEventListener("mousemove", (event) => {
      if (!document.getElementById("landing-video")) return;
      if (prevX === null) { prevX = event.clientX; return; }
      const delta = event.clientX - prevX;
      prevX = event.clientX;
      const dur = video.duration || 0;
      if (!dur) return;
      targetTime = Math.max(0, Math.min(dur, targetTime + (delta / window.innerWidth) * SENS * dur));
      if (!seeking) doSeek();
    });
  };
  if (video.readyState >= 1 && video.duration) enableScrub();
  else video.addEventListener("loadedmetadata", enableScrub, { once: true });
  try { video.load(); } catch (_) {}
}

async function router() {
  clearTimeout(dashboardRefresh);
  let authed = false;
  try {
    const res = await fetch("/api/auth/me", { credentials: "include", headers: { "Content-Type": "application/json" } });
    authed = res.ok;
  } catch {
    authed = false;
  }
  if (!authed) {
    if (window.location.pathname === "/login") return renderLogin();
    if (window.location.pathname === "/recuperar") return renderReset();
    return renderLanding();
  }
  if (window.location.pathname === "/vms/new") return renderNewVm();
  if (window.location.pathname === "/trocar-senha") return renderChangePassword();
  if (window.location.pathname === "/atividade") return renderAudit();
  if (window.location.pathname === "/terminal") return renderTerminal();
  return renderDashboard();
}

window.addEventListener("popstate", router);
router();
