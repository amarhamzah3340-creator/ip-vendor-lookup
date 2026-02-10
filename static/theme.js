(function () {
  const root = document.documentElement;
  let hue = 222;

  function applyTheme() {
    const primary = `hsl(${hue}, 92%, 60%)`;
    root.style.setProperty("--button", primary);
  }

  function pulse() {
    hue = 220 + Math.sin(Date.now() / 2400) * 6;
    applyTheme();
  }

  window.addEventListener("manual-theme-refresh", () => {
    hue = 216 + Math.random() * 18;
    applyTheme();
  });

  setInterval(pulse, 160);
  applyTheme();
})();
