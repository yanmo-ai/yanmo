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

