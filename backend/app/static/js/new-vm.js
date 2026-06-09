document.getElementById("create-vm-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = Object.fromEntries(new FormData(form).entries());
  data.disk_gb = Number(data.disk_gb);

  const message = document.getElementById("form-message");
  message.textContent = "Criando job...";

  const response = await fetch("/api/vms", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    message.textContent = error?.error?.message || "Erro ao criar VM.";
    message.className = "error";
    return;
  }
  window.location.href = "/";
});

