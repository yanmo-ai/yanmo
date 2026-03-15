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

/* ---- Wheel Step Section Scroll ---- */
(function () {
  const sections = Array.from(document.querySelectorAll('section'))
    .filter((el, idx, arr) => arr.indexOf(el) === idx)
    .sort((a, b) => a.offsetTop - b.offsetTop);

  if (!sections.length) return;

  let isAnimating = false;
  let gestureLocked = false;
  let deltaBuffer = 0;
  let releaseTimer = null;
  const STEP_THRESHOLD = 80;
  const WHEEL_IDLE_MS = 170;

  function scheduleGestureRelease() {
    if (releaseTimer) window.clearTimeout(releaseTimer);
    releaseTimer = window.setTimeout(() => {
      if (isAnimating) {
        scheduleGestureRelease();
        return;
      }
      gestureLocked = false;
      deltaBuffer = 0;
    }, WHEEL_IDLE_MS);
  }

  function findScrollableAncestor(el) {
    let node = el;
    while (node && node !== document.body) {
      if (!(node instanceof HTMLElement)) {
        node = node.parentElement;
        continue;
      }
      const style = window.getComputedStyle(node);
      const canScrollY = /(auto|scroll|overlay)/.test(style.overflowY) && node.scrollHeight > node.clientHeight;
      if (canScrollY) return node;
      node = node.parentElement;
    }
    return null;
  }

  function shouldKeepNativeScroll(target, direction) {
    const container = findScrollableAncestor(target);
    if (!container) return false;

    const atTop = container.scrollTop <= 0;
    const atBottom = Math.ceil(container.scrollTop + container.clientHeight) >= container.scrollHeight;

    if (direction > 0 && !atBottom) return true;
    if (direction < 0 && !atTop) return true;
    return false;
  }

  function currentSectionIndex() {
    const probeY = window.scrollY + window.innerHeight * 0.45;
    let idx = 0;
    for (let i = 0; i < sections.length; i += 1) {
      if (sections[i].offsetTop <= probeY) idx = i;
      else break;
    }
    return idx;
  }

  function scrollToSection(index) {
    const clamped = Math.max(0, Math.min(sections.length - 1, index));
    const target = sections[clamped];
    const sectionHeight = target.offsetHeight;
    const centeredTop = target.offsetTop - Math.max(0, (window.innerHeight - sectionHeight) / 2);
    const maxScrollTop = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    const top = Math.max(0, Math.min(maxScrollTop, centeredTop));
    isAnimating = true;
    gestureLocked = true;
    window.scrollTo({ top, behavior: 'smooth' });

    window.setTimeout(() => {
      isAnimating = false;
    }, 650);
  }

  window.addEventListener('wheel', (e) => {
    const direction = Math.sign(e.deltaY);
    if (!direction) return;

    if (shouldKeepNativeScroll(e.target, direction)) return;

    scheduleGestureRelease();

    if (isAnimating || gestureLocked) {
      e.preventDefault();
      return;
    }

    if (deltaBuffer && Math.sign(deltaBuffer) !== direction) {
      deltaBuffer = 0;
    }

    deltaBuffer += e.deltaY;
    if (Math.abs(deltaBuffer) < STEP_THRESHOLD) {
      e.preventDefault();
      return;
    }

    const step = deltaBuffer > 0 ? 1 : -1;
    deltaBuffer = 0;

    const next = currentSectionIndex() + step;
    if (next < 0 || next >= sections.length) return;

    e.preventDefault();
    scrollToSection(next);
  }, { passive: false });
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

