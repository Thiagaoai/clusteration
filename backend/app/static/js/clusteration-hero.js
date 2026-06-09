(() => {
  const video = document.getElementById("clusteration-hero-video");
  if (video) {
    const source = video.dataset.hlsSrc;
    if (source && window.Hls && window.Hls.isSupported()) {
      const hls = new window.Hls({ enableWorker: false });
      hls.loadSource(source);
      hls.attachMedia(video);
      hls.on(window.Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => {});
      });
    } else if (source && video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = source;
      video.addEventListener("canplay", () => video.play().catch(() => {}), { once: true });
    }
  }

  const toggle = document.querySelector("[data-menu-toggle]");
  const menu = document.querySelector("[data-mobile-menu]");
  if (!toggle || !menu) return;

  const setOpen = (isOpen) => {
    document.body.classList.toggle("mobile-menu-open", isOpen);
    toggle.setAttribute("aria-expanded", String(isOpen));
  };

  toggle.addEventListener("click", () => {
    setOpen(!document.body.classList.contains("mobile-menu-open"));
  });

  menu.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => setOpen(false));
  });
})();
