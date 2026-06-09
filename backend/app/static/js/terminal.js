const container = document.getElementById("terminal");
const statusEl = document.getElementById("terminal-status");
const term = new Terminal({ convertEol: false, cursorBlink: true });
term.open(container);
term.focus();

const protocol = window.location.protocol === "https:" ? "wss" : "ws";
const sessionId = container.dataset.session;
const ws = new WebSocket(`${protocol}://${window.location.host}/terminal/ws?session_id=${sessionId}`);
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

