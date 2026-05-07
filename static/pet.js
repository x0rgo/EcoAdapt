// pet.js — EcoAdapt animated plant companion
// Pothos prototype. SVG + anime.js state machine. Zero backend changes.

const Pet = (() => {
  'use strict';

  const S = {
    IDLE:    'idle',
    THIRSTY: 'thirsty',
    WATERED: 'watered',
    HOT:     'hot',
    COLD:    'cold',
    DIM:     'dim',
    NIGHT:   'night',
  };

  // Original leaf fills for cold-state restoration
  const LEAF_FILLS = ['#5A9E4A', '#6DB35A', '#4E9040', '#5A9E4A'];

  let state    = S.IDLE;
  let speaking = false;
  let blinkTimer = null;
  let zzzTimer   = null;

  // SVG element refs
  let svg, petGroup;
  let pupilL, pupilR, eyeL, eyeR;
  let browL, browR, mouthEl;
  let leaf1, leaf2, leaf3, leaf4;
  let fx;

  // ── INIT ─────────────────────────────────────────────────
  function init() {
    svg = document.getElementById('petSvg');
    if (!svg || typeof anime === 'undefined') return;

    petGroup = document.getElementById('petGroup');
    pupilL   = document.getElementById('pupilL');
    pupilR   = document.getElementById('pupilR');
    eyeL     = document.getElementById('eyeL');
    eyeR     = document.getElementById('eyeR');
    browL    = document.getElementById('browL');
    browR    = document.getElementById('browR');
    mouthEl  = document.getElementById('petMouth');
    leaf1    = document.getElementById('leaf1');
    leaf2    = document.getElementById('leaf2');
    leaf3    = document.getElementById('leaf3');
    leaf4    = document.getElementById('leaf4');
    fx       = document.getElementById('petFx');

    bindEvents();
    enter(S.IDLE);
    checkNight();
    setInterval(checkNight, 60000);
  }

  // ── STATE MACHINE ─────────────────────────────────────────
  function enter(next) {
    if (state === next && next !== S.WATERED) return;
    const prev = state;
    state = next;

    anime.remove([petGroup, leaf1, leaf2, leaf3, leaf4]);
    clearTimeout(blinkTimer);
    clearInterval(zzzTimer);

    // Restore leaf colours when leaving cold
    if (prev === S.COLD) restoreLeafColors();

    switch (next) {
      case S.IDLE:    doIdle();    break;
      case S.THIRSTY: doThirsty(); break;
      case S.WATERED: doWatered(); break;
      case S.HOT:     doHot();     break;
      case S.COLD:    doCold();    break;
      case S.DIM:     doDim();     break;
      case S.NIGHT:   doNight();   break;
    }
  }

  // ── STATES ────────────────────────────────────────────────
  function doIdle() {
    breathe(2800);
    swayLeaf(leaf1, -40, -46, 3400);
    swayLeaf(leaf2,  50,  44, 2900, 300);
    swayLeaf(leaf3, -52, -58, 3100, 600);
    swayLeaf(leaf4,  38,  44, 2700, 150);
    face('neutral');
    scheduleBlinkAndLook();
  }

  function doThirsty() {
    breathe(4500);
    rotateTo(leaf1, -62); rotateTo(leaf2, 68);
    rotateTo(leaf3, -70); rotateTo(leaf4,  55);
    face('sad');
    scheduleBlinkAndLook();
    loopParticle('💧', 3600);
  }

  function doWatered() {
    face('happy');
    anime({
      targets: petGroup,
      translateY: [0, -22, 0, -10, 0],
      duration: 750,
      easing: 'easeOutBounce',
    });
    rotateTo(leaf1, -36); rotateTo(leaf2, 46);
    rotateTo(leaf3, -44); rotateTo(leaf4, 34);
    burst('✨', 10);
    setTimeout(() => enter(S.IDLE), 3500);
  }

  function doHot() {
    anime({ targets: petGroup, translateX: [-1, 1], duration: 210,
            easing: 'easeInOutSine', direction: 'alternate', loop: true });
    rotateTo(leaf1, -55); rotateTo(leaf2, 62);
    face('hot');
    loopParticle('💦', 2300);
  }

  function doCold() {
    anime({ targets: petGroup, translateX: [-2, 2], duration: 75,
            easing: 'linear', direction: 'alternate', loop: true });
    face('cold');
    anime({ targets: '.petLeaf', fill: '#a8c8f0', duration: 1000 });
  }

  function doDim() {
    breathe(5000);
    rotateTo(leaf1, -50); rotateTo(leaf2, 56);
    face('sleepy');
    zzzTimer = setInterval(() => { if (state === S.DIM) spawnZzz(); }, 2800);
    spawnZzz();
  }

  function doNight() {
    breathe(6000);
    face('sleeping');
    zzzTimer = setInterval(() => { if (state === S.NIGHT) spawnZzz(); }, 2600);
    spawnZzz();
  }

  // ── MOTION HELPERS ────────────────────────────────────────
  function breathe(dur) {
    anime({ targets: petGroup, translateY: [0, -5], duration: dur,
            easing: 'easeInOutSine', direction: 'alternate', loop: true });
  }

  function swayLeaf(el, a, b, dur, delay = 0) {
    anime({ targets: el, rotate: [a + 'deg', b + 'deg'], duration: dur,
            easing: 'easeInOutSine', direction: 'alternate', loop: true, delay });
  }

  function rotateTo(el, deg) {
    anime({ targets: el, rotate: deg + 'deg', duration: 900, easing: 'easeOutQuad' });
  }

  function restoreLeafColors() {
    document.querySelectorAll('.petLeaf').forEach((l, i) =>
      anime({ targets: l, fill: LEAF_FILLS[i] || '#5A9E4A', duration: 900 }));
  }

  function loopParticle(emoji, interval) {
    const drop = () => {
      if (state !== S.THIRSTY && state !== S.HOT) return;
      particle(emoji, 3, 0.85);
      setTimeout(drop, interval + Math.random() * 800);
    };
    drop();
  }

  // ── FACE EXPRESSIONS ─────────────────────────────────────
  // All mouth/brow paths use M x,y Q cx,cy x,y (same command count → anime.js can morph)
  const FACES = {
    neutral:  { mouth: 'M -9,14 Q 0,19 9,14',   browL: 'M -22,-11 Q -14,-15 -7,-11', browR: 'M 7,-11 Q 14,-15 22,-11', eyeScY: 1    },
    happy:    { mouth: 'M -10,11 Q 0,22 10,11',  browL: 'M -22,-13 Q -14,-17 -7,-13', browR: 'M 7,-13 Q 14,-17 22,-13', eyeScY: 0.72 },
    sad:      { mouth: 'M -9,18 Q 0,12 9,18',    browL: 'M -22,-9 Q -14,-11 -7,-14',  browR: 'M 7,-14 Q 14,-11 22,-9',  eyeScY: 1    },
    hot:      { mouth: 'M -8,16 Q 0,12 8,16',    browL: 'M -22,-9 Q -14,-12 -7,-9',   browR: 'M 7,-9 Q 14,-12 22,-9',   eyeScY: 0.85 },
    cold:     { mouth: 'M -9,16 Q 0,11 9,16',    browL: 'M -22,-12 Q -14,-15 -7,-12', browR: 'M 7,-12 Q 14,-15 22,-12', eyeScY: 1    },
    sleepy:   { mouth: 'M -7,15 Q 0,18 7,15',    browL: 'M -22,-10 Q -14,-12 -7,-10', browR: 'M 7,-10 Q 14,-12 22,-10', eyeScY: 0.32 },
    sleeping: { mouth: 'M -6,15 Q 0,18 6,15',    browL: 'M -22,-10 Q -14,-12 -7,-10', browR: 'M 7,-10 Q 14,-12 22,-10', eyeScY: 0.05 },
    speaking: { mouth: 'M -9,11 Q 0,23 9,11',    browL: 'M -22,-13 Q -14,-16 -7,-13', browR: 'M 7,-13 Q 14,-16 22,-13', eyeScY: 1    },
  };

  function face(mood) {
    const f = FACES[mood] || FACES.neutral;
    anime({ targets: mouthEl, d: [{ value: f.mouth }], duration: 350, easing: 'easeOutQuad' });
    anime({ targets: browL,   d: [{ value: f.browL }], duration: 350, easing: 'easeOutQuad' });
    anime({ targets: browR,   d: [{ value: f.browR }], duration: 350, easing: 'easeOutQuad' });
    anime({ targets: [eyeL, eyeR], scaleY: f.eyeScY, duration: 250, easing: 'easeOutQuad' });
  }

  function blink() {
    anime({ targets: [eyeL, eyeR], scaleY: [null, 0.05, null], duration: 180, easing: 'easeInOutQuad' });
  }

  function scheduleBlinkAndLook() {
    clearTimeout(blinkTimer);
    const delay = 2800 + Math.random() * 3800;
    blinkTimer = setTimeout(() => {
      if (state !== S.IDLE && state !== S.THIRSTY) return;
      blink();
      setTimeout(() => {
        const dx = (Math.random() - 0.5) * 5;
        const dy = (Math.random() - 0.5) * 3.5;
        anime({ targets: [pupilL, pupilR], cx: dx, cy: dy, duration: 280, easing: 'easeOutQuad' });
        setTimeout(() => {
          anime({ targets: [pupilL, pupilR], cx: 0, cy: 0, duration: 280, easing: 'easeOutQuad' });
          if (state === S.IDLE || state === S.THIRSTY) scheduleBlinkAndLook();
        }, 1300);
      }, 200);
    }, delay);
  }

  // ── PARTICLES ─────────────────────────────────────────────
  function mkText(ch, x, y, size) {
    const el = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    el.textContent = ch;
    el.setAttribute('x', x);
    el.setAttribute('y', y);
    el.setAttribute('font-size', size);
    el.setAttribute('text-anchor', 'middle');
    el.setAttribute('opacity', '0');
    fx.appendChild(el);
    return el;
  }

  function particle(emoji, spread = 4, opacity = 0.9) {
    const x = 88 + Math.random() * 24;
    const y = 105 + Math.random() * 30;
    const el = mkText(emoji, x, y, 11);
    anime({
      targets: el,
      opacity: [0, opacity, 0],
      translateY: -18 - Math.random() * 22,
      translateX: (Math.random() - 0.5) * spread * 8,
      duration: 1100 + Math.random() * 400,
      easing: 'easeOutQuad',
      complete: () => el.remove(),
    });
  }

  function burst(emoji, count) {
    for (let i = 0; i < count; i++)
      setTimeout(() => particle(emoji, 8, 1), i * 80);
  }

  function spawnZzz() {
    const chars = ['z', 'z', 'Z'];
    const size  = 8 + Math.random() * 7;
    const el    = mkText(chars[Math.floor(Math.random() * 3)], 114 + Math.random() * 8, 100, size);
    el.setAttribute('fill', '#99aabb');
    el.setAttribute('font-style', 'italic');
    anime({
      targets: el,
      opacity: [0, 0.8, 0],
      translateY: -28,
      translateX: 10 + Math.random() * 8,
      duration: 2200,
      easing: 'easeOutQuad',
      complete: () => el.remove(),
    });
  }

  function spawnHearts() {
    for (let i = 0; i < 4; i++)
      setTimeout(() => particle('💚', 5, 1), i * 130);
  }

  // ── EVENTS ────────────────────────────────────────────────
  function bindEvents() {
    svg.addEventListener('mousemove', onMove);
    svg.addEventListener('mouseleave', () =>
      anime({ targets: [pupilL, pupilR], cx: 0, cy: 0, duration: 400, easing: 'easeOutQuad' }));
    svg.addEventListener('click', onClick);
    svg.addEventListener('touchend', e => { e.preventDefault(); onClick(); });
  }

  function onMove(e) {
    if (state === S.NIGHT || state === S.DIM) return;
    const r  = svg.getBoundingClientRect();
    const cx = r.left + r.width * 0.5;
    const cy = r.top  + r.height * 0.46;
    const dx = Math.max(-4, Math.min(4, (e.clientX - cx) / r.width  * 14));
    const dy = Math.max(-3, Math.min(3, (e.clientY - cy) / r.height * 12));
    anime({ targets: [pupilL, pupilR], cx: dx, cy: dy, duration: 80, easing: 'linear' });
  }

  function onClick() {
    if (state === S.NIGHT) return;
    face('happy');
    anime({
      targets: petGroup,
      scaleX: [1, 0.88, 1.08, 1],
      scaleY: [1, 1.08, 0.90, 1],
      duration: 480,
      easing: 'easeOutElastic(1, 0.5)',
    });
    spawnHearts();
    setTimeout(() => face(curFace()), 900);
  }

  function curFace() {
    const map = {
      [S.IDLE]: 'neutral', [S.THIRSTY]: 'sad', [S.HOT]: 'hot',
      [S.COLD]: 'cold',    [S.DIM]: 'sleepy',  [S.NIGHT]: 'sleeping',
    };
    return map[state] || 'neutral';
  }

  // ── PUBLIC API ────────────────────────────────────────────
  function onReading(d) {
    if (isNight()) { enter(S.NIGHT); return; }
    const m = d.moisture    ?? 50;
    const t = d.temperature ?? 20;
    const l = d.light       ?? 500;
    if      (m < 30)  enter(S.THIRSTY);
    else if (t > 35)  enter(S.HOT);
    else if (t < 10)  enter(S.COLD);
    else if (l < 100) enter(S.DIM);
    else if (m > 65 && state === S.THIRSTY) enter(S.WATERED);
    else              enter(S.IDLE);
  }

  function onSpeechStart() {
    speaking = true;
    (function tick() {
      if (!speaking) return;
      const open = Math.random() > 0.45;
      anime({
        targets: mouthEl,
        d: [{ value: open ? FACES.speaking.mouth : FACES.neutral.mouth }],
        duration: 110,
        easing: 'linear',
        complete: () => setTimeout(tick, 90 + Math.random() * 110),
      });
    })();
  }

  function onSpeechEnd() {
    speaking = false;
    face(curFace());
  }

  function onAchievement() {
    burst('✨', 8);
    setTimeout(() => burst('⭐', 5), 200);
    anime({ targets: petGroup, scale: [1, 1.12, 1], duration: 600, easing: 'easeOutBack' });
    face('happy');
    setTimeout(() => face(curFace()), 2500);
  }

  function isNight() { const h = new Date().getHours(); return h >= 21 || h < 7; }

  function checkNight() {
    if (isNight() && state !== S.NIGHT) enter(S.NIGHT);
    else if (!isNight() && state === S.NIGHT) enter(S.IDLE);
  }

  return { init, onReading, onSpeechStart, onSpeechEnd, onAchievement };
})();
