document.querySelectorAll("[data-terminal]").forEach((button) => {
  button.onclick = async () => {
    const id = button.dataset.terminal;
    const response = await fetch(`/api/vms/${id}/terminal/session`, { method: "POST" });
    if (!response.ok) {
      alert("Terminal ainda não está disponível.");
      return;
    }
    const data = await response.json();
    window.location.href = data.terminal_url;
  };
});

document.querySelectorAll("[data-delete]").forEach((button) => {
  button.onclick = async () => {
    const id = button.dataset.delete;
    const hostname = button.dataset.hostname;
    const confirmHostname = prompt(`Digite ${hostname} para deletar a VM:`);
    if (confirmHostname !== hostname) return;
    const response = await fetch(`/api/vms/${id}`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirm_hostname: confirmHostname }),
    });
    if (!response.ok) {
      alert("Não foi possível deletar a VM.");
      return;
    }
    window.location.reload();
  };
});

document.querySelectorAll("[data-reinstall]").forEach((button) => {
  button.onclick = async () => {
    const id = button.dataset.reinstall;
    const hostname = button.dataset.hostname;
    const confirmHostname = prompt(`Digite ${hostname} para reinstalar a VPS e apagar o disco atual:`);
    if (confirmHostname !== hostname) return;
    const templatesResponse = await fetch("/api/templates");
    if (!templatesResponse.ok) {
      alert("Não foi possível carregar os templates.");
      return;
    }
    const templates = (await templatesResponse.json()).templates || [];
    const enabled = templates.filter((template) => template.enabled).map((template) => template.os);
    const template = prompt(`Template (${enabled.join(", ")}):`, enabled[0] || "");
    if (!template || !enabled.includes(template)) return;
    const rootPassword = prompt("Nova senha root da VPS:");
    if (!rootPassword || rootPassword.length < 8) {
      alert("A senha precisa ter pelo menos 8 caracteres.");
      return;
    }
    const response = await fetch(`/api/vms/${id}/reinstall`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirm_hostname: confirmHostname, template, root_password: rootPassword }),
    });
    if (!response.ok) {
      alert("Não foi possível reinstalar a VPS.");
      return;
    }
    window.location.reload();
  };
});

document.body.addEventListener("htmx:afterRequest", (event) => {
  const path = event.detail.pathInfo?.requestPath || "";
  if (path.includes("/api/vms/")) window.location.reload();
});
