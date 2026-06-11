const app = document.getElementById("app");

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
      <a href="/" class="admin-logo" aria-label="Clusteration painel">
        <img src="/img/clusteration-logo.svg" alt="Clusteration">
      </a>
      <nav class="admin-nav" aria-label="Navegação principal">
        <a class="admin-nav-item" href="/" data-route><span>▦</span>Overview</a>
        <a class="admin-nav-item" href="/vms/new" data-route><span>＋</span>Create VM</a>
        <a class="admin-nav-item" href="/#inventory" data-route><span>⌁</span>Inventory</a>
      </nav>
      <div class="tenant-lock">
        <span class="status-dot"></span>
        <div>
          <strong>Single tenant</strong>
          <small>Admin session required</small>
        </div>
      </div>
    </aside>
    <div class="admin-workspace">
      <header class="admin-topbar">
        <div>
          <span>Secure cluster panel</span>
          <strong>Clusteration / cluster.thiagaoai.online</strong>
        </div>
        <button class="ghost-button" type="button" data-logout>Logout</button>
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
}

function renderLogin(error = "") {
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
        <img class="login-logo" src="/img/clusteration-logo.svg" alt="Clusteration">
        <span class="eyebrow">Single-tenant admin</span>
        <h1>Secure cluster access</h1>
        <p>Login obrigatório para proteger inventário, terminais e ações das suas VMs.</p>
        ${error ? `<p class="error">${error}</p>` : ""}
        <label><span>Usuário</span><input name="username" autocomplete="username" autocapitalize="none" autocorrect="off" spellcheck="false" required></label>
        <label><span>Senha</span><input name="password" type="password" autocomplete="current-password" required></label>
        <button class="primary-button" type="submit">Entrar</button>
      </form>
    </main>
  `;
  startHeroVideo();
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
            <h1>Cluster admin<br>command center<span>.</span></h1>
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
          <h2>Private <em>Cluster</em> Operations</h2>
          <p>Login obrigatório antes de inventário, terminal SSH e ações críticas de VM.</p>
        </aside>
      </div>
    </section>
    <section class="content dashboard-content" id="inventory">
      <section class="stats-grid">
        <article class="card stat-card green"><span>Running VMs</span><strong>${vms.filter((vm) => vm.status === "running").length}</strong><small>Compute online now</small></article>
        <article class="card stat-card blue"><span>Total inventory</span><strong>${vms.length}</strong><small>Managed VM records</small></article>
        <article class="card stat-card amber"><span>Lifecycle jobs</span><strong>${hasTransient ? "Sim" : "Não"}</strong><small>Auto-refresh when active</small></article>
        <article class="card stat-card slate"><span>Access mode</span><strong>Private</strong><small>Single-tenant admin</small></article>
      </section>
      <section class="section-header">
        <div><span class="eyebrow">Compute operations</span><h1>VM inventory and actions</h1><p>Start, stop, reboot, open terminal sessions, and delete only after authenticated admin access.</p></div>
        <a class="primary-button" href="/vms/new" data-route>Create VM</a>
      </section>
      ${vmTable(vms)}
    </section>
  `);
  bindShellEvents();
  bindDashboardActions();
  startHeroVideo();
  runHeroEffects();
  if (hasTransient) setTimeout(renderDashboard, 5000);
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

function vmTable(vms) {
  const rows = vms.map((vm) => `
    <tr>
      <td data-label="Hostname"><strong>${vm.hostname}</strong></td>
      <td data-label="Status"><span class="badge badge-${vm.status}">${vm.status}</span></td>
      <td data-label="SSH">${vm.ssh_status}</td>
      <td data-label="IP">${vm.ip_address || "-"}</td>
      <td data-label="Template">${vm.template}</td>
      <td data-label="Recursos">${vm.cpu} CPU / ${vm.memory_mb} MB / ${vm.disk_gb} GB</td>
      <td class="actions" data-label="Ações">
        <button class="ghost-button" data-action="start" data-id="${vm.id}" ${vm.actions.can_start ? "" : "disabled"}>Start</button>
        <button class="ghost-button" data-action="stop" data-id="${vm.id}" ${vm.actions.can_stop ? "" : "disabled"}>Stop</button>
        <button class="ghost-button" data-action="reboot" data-id="${vm.id}" ${vm.actions.can_reboot ? "" : "disabled"}>Reboot</button>
        <button class="primary-button" data-terminal="${vm.id}" ${vm.actions.can_terminal ? "" : "disabled"}>Terminal</button>
        <button class="danger-button" data-delete="${vm.id}" data-hostname="${vm.hostname}" ${vm.actions.can_delete ? "" : "disabled"}>Delete</button>
      </td>
    </tr>
  `).join("");
  return `
    <section class="card">
      <div class="card-title"><h2>Inventário de VMs</h2><span class="pill">${vms.length} recursos</span></div>
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>Hostname</th><th>Status</th><th>SSH</th><th>IP</th><th>Template</th><th>Recursos</th><th>Ações</th></tr></thead>
          <tbody>${rows || `<tr><td colspan="7" class="empty">Nenhuma VM criada.</td></tr>`}</tbody>
        </table>
      </div>
    </section>
  `;
}

function bindDashboardActions() {
  document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      await api(`/api/vms/${button.dataset.id}/${button.dataset.action}`, { method: "POST" });
      renderDashboard();
    });
  });
  document.querySelectorAll("[data-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      const confirmHostname = prompt(`Digite ${button.dataset.hostname} para deletar a VM:`);
      if (confirmHostname !== button.dataset.hostname) return;
      await api(`/api/vms/${button.dataset.delete}`, {
        method: "DELETE",
        body: JSON.stringify({ confirm_hostname: confirmHostname }),
      });
      renderDashboard();
    });
  });
  document.querySelectorAll("[data-terminal]").forEach((button) => {
    button.addEventListener("click", async () => {
      const response = await api(`/api/vms/${button.dataset.terminal}/terminal/session`, { method: "POST" });
      if (!response.ok) {
        alert("Terminal ainda não está disponível.");
        return;
      }
      const data = await response.json();
      history.pushState(null, "", `/terminal?session=${encodeURIComponent(data.session_id)}`);
      router();
    });
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
        <label><span>Hostname</span><input name="hostname" pattern="[A-Za-z0-9]([A-Za-z0-9\-]{0,126}[A-Za-z0-9])?" required></label>
        <label><span>Template</span><select name="template">${templates.map((template) => `<option value="${template.os}" ${template.enabled ? "" : "disabled"}>${template.name}</option>`).join("")}</select></label>
        <label><span>Tamanho</span><select name="size">${Object.entries(options.sizes).map(([key, size]) => `<option value="${key}">${size.label}</option>`).join("")}</select></label>
        <label><span>Disco</span><select name="disk_gb">${options.disk_choices.map((gb) => `<option value="${gb}">${gb} GB</option>`).join("")}</select></label>
        <label><span>Senha root</span><input id="root-password" name="root_password" type="password" minlength="8" required></label>
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

function renderTerminal() {
  const sessionId = new URLSearchParams(window.location.search).get("session");
  app.innerHTML = shell(`
    <div class="terminal-header card">
      <div><span class="eyebrow">Console SSH</span><h1>Terminal</h1></div>
      <span class="pill warn" id="terminal-status">connecting</span>
    </div>
    <div id="terminal" data-session="${sessionId || ""}"></div>
  `);
  bindShellEvents();
  const container = document.getElementById("terminal");
  const statusEl = document.getElementById("terminal-status");
  const term = new Terminal({ convertEol: false, cursorBlink: true });
  term.open(container);
  term.focus();
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${protocol}://${window.location.host}/terminal/ws?session_id=${encodeURIComponent(sessionId)}`);
  ws.binaryType = "arraybuffer";
  ws.onmessage = (event) => {
    if (typeof event.data === "string") {
      const payload = JSON.parse(event.data);
      if (payload.type === "status") statusEl.textContent = payload.status;
      if (payload.type === "error") statusEl.textContent = payload.message;
      if (payload.type === "close") statusEl.textContent = payload.reason;
      return;
    }
    term.write(new Uint8Array(event.data));
  };
  term.onData((data) => ws.readyState === WebSocket.OPEN && ws.send(new TextEncoder().encode(data)));
  term.onResize(({ cols, rows }) => {
    if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "resize", cols, rows }));
  });
  setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "ping" }));
  }, 20000);
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
        <a class="landing-logo" href="/login" data-login>clusteration<sup>®</sup><span class="landing-aster">✳︎</span></a>
        <nav class="landing-links">
          <a href="/login" data-login>Overview</a><span class="sep">, </span><a href="/login" data-login>Inventory</a><span class="sep">, </span><a href="/login" data-login>Docs</a>
        </nav>
        <a class="landing-getin" href="/login" data-login>Acessar painel</a>
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
  runHeroEffects();
  startLandingVideo();
}

function startLandingVideo() {
  const video = document.getElementById("landing-video");
  if (!video) return;
  const isSmall = window.matchMedia && window.matchMedia("(max-width: 768px)").matches;
  if (isSmall || (navigator.connection && navigator.connection.saveData)) {
    video.removeAttribute("src");
    video.remove();
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
  let authed = false;
  try {
    const res = await fetch("/api/auth/me", { credentials: "include", headers: { "Content-Type": "application/json" } });
    authed = res.ok;
  } catch {
    authed = false;
  }
  if (!authed) {
    if (window.location.pathname === "/login") return renderLogin();
    return renderLanding();
  }
  if (window.location.pathname === "/vms/new") return renderNewVm();
  if (window.location.pathname === "/terminal") return renderTerminal();
  return renderDashboard();
}

window.addEventListener("popstate", router);
router();
