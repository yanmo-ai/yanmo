/* ============================================
   言墨 · JavaScript
   - Navbar scroll effect
   - Scroll reveal animations
   ============================================ */

/* ---- Navbar Scroll ---- */
(function () {
  const nav = document.querySelector('.navbar');
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 40);
  }, { passive: true });
})();

/* ---- Scroll Reveal ---- */
(function () {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry, i) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
  );

  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
})();
/* ---- Recording Preview Start On First View ---- */
(function () {
  const section = document.querySelector('#recording');
  const video = section?.querySelector('.rec-vibe-preview video');

  if (!section || !video) return;

  let hasStarted = false;

  function ensureSource() {
    if (video.currentSrc || video.src) return;
    const source = video.dataset.src;
    if (!source) return;
    video.src = source;
    video.load();
  }

  function startPreview() {
    if (hasStarted) return;
    ensureSource();
    hasStarted = true;
    section.classList.add('recording-started');
    video.currentTime = 0;
    const playPromise = video.play();
    if (playPromise && typeof playPromise.catch === 'function') {
      playPromise.catch(() => {
        hasStarted = false;
      });
    }
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        startPreview();
        observer.unobserve(entry.target);
      });
    },
    { threshold: 0.45 }
  );

  observer.observe(section);
})();

/* ---- Auto-update Download Links from GitHub Releases ---- */
/* Scans all releases, sorts by tag version descending, picks latest .exe and .dmg */
(function () {
  function parseVersion(tag) {
    var m = (tag || '').match(/(\d+)\.(\d+)\.(\d+)/);
    return m ? [+m[1], +m[2], +m[3]] : [0, 0, 0];
  }

  fetch('https://api.github.com/repos/yanmo-ai/yanmo/releases')
    .then(function (res) { return res.json(); })
    .then(function (releases) {
      if (!Array.isArray(releases)) return;
      releases.sort(function (a, b) {
        var va = parseVersion(a.tag_name);
        var vb = parseVersion(b.tag_name);
        return (vb[0] - va[0]) || (vb[1] - va[1]) || (vb[2] - va[2]);
      });
      var winUrl = null;
      var macUrl = null;
      for (var i = 0; i < releases.length; i++) {
        if (winUrl && macUrl) break;
        var assets = releases[i].assets;
        if (!assets) continue;
        for (var j = 0; j < assets.length; j++) {
          var url = assets[j].browser_download_url;
          if (!winUrl && url.endsWith('.exe')) winUrl = url;
          if (!macUrl && url.endsWith('.dmg')) macUrl = url;
        }
      }
      if (winUrl) {
        var btn = document.getElementById('btn-download-windows');
        if (btn) btn.href = winUrl;
      }
      if (macUrl) {
        var btn = document.getElementById('btn-download-mac');
        if (btn) btn.href = macUrl;
      }
    })
    .catch(function () { /* keep fallback links */ });
})();

/* ---- FAQ Smooth Open ---- */
(function () {
  document.querySelectorAll('.faq-item').forEach(item => {
    item.addEventListener('toggle', () => {
      if (item.open) {
        // close others
        document.querySelectorAll('.faq-item[open]').forEach(other => {
          if (other !== item) other.removeAttribute('open');
        });
      }
    });
  });
})();

