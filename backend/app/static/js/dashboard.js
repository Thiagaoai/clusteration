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

document.body.addEventListener("htmx:afterRequest", (event) => {
  const path = event.detail.pathInfo?.requestPath || "";
  if (path.includes("/api/vms/")) window.location.reload();
});

