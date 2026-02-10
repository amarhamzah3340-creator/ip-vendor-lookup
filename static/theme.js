(function () {
  const root = document.documentElement;
  let hue = 224;

  function pulseTheme() {
    hue = (hue + 0.25) % 360;
    const accent = `hsl(${hue}, 88%, 67%)`;
    root.style.setProperty("--button", accent);
  }

  setInterval(pulseTheme, 120);
})();
