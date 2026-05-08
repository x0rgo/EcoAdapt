// pet.js — EcoAdapt animated plant companion
// Parametric per-species character system. SVG + anime.js state machine.

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

  // ── SPECIES VISUAL CONFIG ────────────────────────────────
  // Each species defines: leaf shape(s), 4 leaf colors, leaf positions/rotations,
  // pot palette, optional stem, optional accent (flower/spathe), and optional
  // body override (for non-leafy species like cactus).

  const LEAF_SHAPES = {
    heart:      'M0,14 C-17,5 -15,-18 0,-22 C15,-18 17,5 0,14',
    heartSmall: 'M0,12 C-13,4 -11,-14 0,-18 C11,-14 13,4 0,12',
    heartUp:    'M0,13 C-15,4 -13,-16 0,-20 C13,-16 15,4 0,13',
    monstera:   'M0,14 C-21,4 -22,-22 0,-26 C22,-22 21,4 0,14',  // wider
    sword:      'M0,14 C-5,4 -6,-22 0,-26 C6,-22 5,4 0,14',      // narrow pointed
    fat:        'M0,8 C-9,4 -9,-11 0,-13 C9,-11 9,4 0,8',         // short fleshy
    frond:      'M0,16 C-3,8 -4,-22 0,-26 C4,-22 3,8 0,16',       // narrow long
    longLeaf:   'M0,18 C-4,8 -4,-26 0,-30 C4,-26 4,8 0,18',       // very long curve
    oval:       'M0,12 C-10,5 -10,-15 0,-17 C10,-15 10,5 0,12',   // rounded oval
  };

  // Standard 4-leaf placement (used by most species)
  const STANDARD_LAYOUT = [
    { tx: 86,  ty: 155, rot: -40, originY: 12 },
    { tx: 114, ty: 140, rot:  50, originY: 12 },
    { tx: 80,  ty: 118, rot: -52, originY: 11 },
    { tx: 118, ty: 105, rot:  38, originY: 10 },
  ];

  // Rosette (succulent) — leaves cluster low and spread radially
  const ROSETTE_LAYOUT = [
    { tx: 78,  ty: 175, rot: -78, originY: 8 },
    { tx: 122, ty: 175, rot:  78, originY: 8 },
    { tx: 88,  ty: 162, rot: -32, originY: 8 },
    { tx: 112, ty: 162, rot:  32, originY: 8 },
  ];

  // Frond layout (fern, zz_plant) — symmetric paired leaves on a stem
  const FROND_LAYOUT = [
    { tx: 84,  ty: 165, rot: -55, originY: 13 },
    { tx: 116, ty: 165, rot:  55, originY: 13 },
    { tx: 86,  ty: 130, rot: -52, originY: 13 },
    { tx: 114, ty: 130, rot:  52, originY: 13 },
  ];

  // Orchid layout — 2 long base leaves + flower spike with 2 small leaves
  const ORCHID_LAYOUT = [
    { tx: 84,  ty: 178, rot: -68, originY: 16 },
    { tx: 116, ty: 178, rot:  68, originY: 16 },
    { tx: 90,  ty: 158, rot: -45, originY: 16 },
    { tx: 110, ty: 158, rot:  45, originY: 16 },
  ];

  const SPECIES_VISUALS = {
    pothos: {
      leafShape: 'heart',
      leaf3Shape: 'heartUp',
      leaf4Shape: 'heartSmall',
      leafColors: ['#5A9E4A', '#6DB35A', '#4E9040', '#5A9E4A'],
      leafStroke: '#3E7234',
      pot: { body: '#C1694F', hi: '#D4845A', lo: '#A04535' },
      stem: 'M100,190 C98,170 102,152 99,132 C97,116 101,98 100,82',
      stemColor: '#4A7C40',
      layout: STANDARD_LAYOUT,
    },
    monstera: {
      leafShape: 'monstera',
      leaf3Shape: 'monstera',
      leaf4Shape: 'monstera',
      leafColors: ['#2E6440', '#3A7A52', '#1F4A2E', '#306846'],
      leafStroke: '#1A3823',
      pot: { body: '#C1694F', hi: '#D4845A', lo: '#A04535' },
      stem: 'M100,190 C98,170 102,152 99,132 C97,116 101,98 100,82',
      stemColor: '#3A6230',
      layout: STANDARD_LAYOUT,
    },
    peace_lily: {
      leafShape: 'sword',
      leaf3Shape: 'sword',
      leaf4Shape: 'sword',
      leafColors: ['#3D7F4A', '#4A8F58', '#346B40', '#3D7F4A'],
      leafStroke: '#26562F',
      pot: { body: '#F5F5F5', hi: '#FFFFFF', lo: '#D8D8D8' },
      stem: 'M100,190 C99,170 101,150 100,132 C99,116 101,98 100,82',
      stemColor: '#2E6638',
      layout: STANDARD_LAYOUT,
      accent: 'spathe',
    },
    cactus: {
      // No leaves — barrel body. We still emit leaf1-4 as invisible nubs
      // so animation hooks (rotateTo, color shift on cold) don't crash.
      body: 'barrel',
      bodyFill: '#5A9E4A',
      bodyStroke: '#3E7234',
      spineColor: '#F5EAB8',
      flowerFill: '#FF6B9D',
      leafColors: ['#5A9E4A', '#5A9E4A', '#5A9E4A', '#5A9E4A'],
      leafStroke: '#3E7234',
      leafShape: 'fat',
      leaf3Shape: 'fat',
      leaf4Shape: 'fat',
      pot: { body: '#C1694F', hi: '#D4845A', lo: '#A04535' },
      // Cactus leaves are tiny side nubs (mostly hidden by body)
      layout: [
        { tx: 70,  ty: 145, rot: -90, originY: 8 },
        { tx: 130, ty: 145, rot:  90, originY: 8 },
        { tx: 72,  ty: 175, rot: -90, originY: 8 },
        { tx: 128, ty: 175, rot:  90, originY: 8 },
      ],
    },
    succulent: {
      leafShape: 'fat',
      leaf3Shape: 'fat',
      leaf4Shape: 'fat',
      leafColors: ['#7BB870', '#8FC880', '#6FA862', '#7BB870'],
      leafStroke: '#4A7140',
      pot: { body: '#A8A8A8', hi: '#C0C0C0', lo: '#888888' },
      stem: null,
      stemColor: null,
      layout: ROSETTE_LAYOUT,
    },
    fern: {
      leafShape: 'frond',
      leaf3Shape: 'frond',
      leaf4Shape: 'frond',
      leafColors: ['#4A8F40', '#5A9F50', '#3F8038', '#4A8F40'],
      leafStroke: '#2D5728',
      pot: { body: '#8B6F47', hi: '#A08560', lo: '#6A5236' },
      stem: 'M100,190 C100,170 100,150 100,130 C100,115 100,100 100,85',
      stemColor: '#3D7038',
      layout: FROND_LAYOUT,
    },
    orchid: {
      leafShape: 'longLeaf',
      leaf3Shape: 'longLeaf',
      leaf4Shape: 'longLeaf',
      leafColors: ['#3F7E4A', '#4A8E55', '#346D40', '#3F7E4A'],
      leafStroke: '#26562F',
      pot: { body: '#E8DEEF', hi: '#F4ECF8', lo: '#C8BCD2' },
      stem: 'M100,190 C100,170 100,150 100,130 C100,115 100,100 100,82',
      stemColor: '#2E6638',
      layout: ORCHID_LAYOUT,
      accent: 'orchidBloom',
    },
    zz_plant: {
      leafShape: 'oval',
      leaf3Shape: 'oval',
      leaf4Shape: 'oval',
      leafColors: ['#2E6E3A', '#3A8048', '#246030', '#2E6E3A'],
      leafStroke: '#1A4220',
      pot: { body: '#3A3A3A', hi: '#5A5A5A', lo: '#202020' },
      stem: 'M100,190 C100,170 100,150 100,132 C100,118 100,100 100,82',
      stemColor: '#1F4220',
      layout: FROND_LAYOUT,
    },
  };

  // ── STATE ────────────────────────────────────────────────
  let state    = S.IDLE;
  let speaking = false;
  let blinkTimer = null;
  let zzzTimer   = null;
  let currentSpecies = 'pothos';
  let LEAF_FILLS = SPECIES_VISUALS.pothos.leafColors.slice();

  // SVG element refs (re-bound on setSpecies)
  let svg, petGroup;
  let pupilL, pupilR, eyeL, eyeR;
  let browL, browR, mouthEl;
  let leaf1, leaf2, leaf3, leaf4;
  let fx;

  // ── SVG BUILDER ──────────────────────────────────────────
  function buildPetSvg(species) {
    const cfg = SPECIES_VISUALS[species] || SPECIES_VISUALS.pothos;

    // Pot is shared across all species (just colors change)
    const pot = `
      <rect x="48" y="183" width="104" height="14" rx="7" fill="#8B5E3C"/>
      <rect x="52" y="184" width="48" height="6" rx="3" fill="#A07040" opacity="0.45"/>
      <path d="M60,197 L140,197 L130,252 L70,252 Z" fill="${cfg.pot.body}"/>
      <path d="M67,197 L78,197 L72,249 L63,244 Z" fill="${cfg.pot.hi}" opacity="0.4"/>
      <path d="M133,197 L140,197 L130,252 L125,252 Z" fill="${cfg.pot.lo}" opacity="0.28"/>
      <ellipse cx="100" cy="192" rx="44" ry="8" fill="#4E2E14"/>
      <ellipse cx="100" cy="190" rx="38" ry="4.5" fill="#5C3A1E" opacity="0.55"/>
    `;

    // Body — special case for cactus, otherwise stem + leaves
    let body = '';

    if (cfg.body === 'barrel') {
      // Barrel cactus: vertical oval body with rib lines and spines
      body = `
        <ellipse cx="100" cy="140" rx="32" ry="55" fill="${cfg.bodyFill}" stroke="${cfg.bodyStroke}" stroke-width="1.2"/>
        <path d="M85,90 Q83,140 87,190" stroke="${cfg.bodyStroke}" stroke-width="0.8" fill="none" opacity="0.55"/>
        <path d="M115,90 Q117,140 113,190" stroke="${cfg.bodyStroke}" stroke-width="0.8" fill="none" opacity="0.55"/>
        <path d="M100,86 L100,194" stroke="${cfg.bodyStroke}" stroke-width="0.6" fill="none" opacity="0.4"/>
        ${spineRows(cfg.spineColor)}
        <path d="M100,90 Q88,82 92,72 Q100,68 108,72 Q112,82 100,90 Z" fill="${cfg.flowerFill}" opacity="0.95"/>
        <circle cx="100" cy="80" r="2.5" fill="#FFE066"/>
      `;
    } else {
      // Standard: optional stem + 4 leaves
      if (cfg.stem) {
        body += `<path d="${cfg.stem}" stroke="${cfg.stemColor}" stroke-width="3.5" fill="none" stroke-linecap="round"/>`;
      }
      body += renderLeaf(1, cfg.layout[0], cfg.leafShape, cfg.leafColors[0], cfg.leafStroke);
      body += renderLeaf(2, cfg.layout[1], cfg.leafShape, cfg.leafColors[1], cfg.leafStroke);
      body += renderLeaf(3, cfg.layout[2], cfg.leaf3Shape || cfg.leafShape, cfg.leafColors[2], cfg.leafStroke);
      body += renderLeaf(4, cfg.layout[3], cfg.leaf4Shape || cfg.leafShape, cfg.leafColors[3], cfg.leafStroke);

      // Accent flowers/spathes
      if (cfg.accent === 'spathe') {
        body += `
          <path d="M100,82 Q88,72 90,55 Q100,42 110,55 Q112,72 100,82 Z" fill="#FFFFFF" stroke="#E8E8E8" stroke-width="0.6"/>
          <path d="M100,55 L100,82" stroke="#E8C94A" stroke-width="2" stroke-linecap="round"/>
        `;
      } else if (cfg.accent === 'orchidBloom') {
        body += `
          <path d="M100,72 Q92,60 95,52 Q100,46 105,52 Q108,60 100,72 Z" fill="#E8A2C8" opacity="0.95"/>
          <path d="M88,70 Q82,62 88,55 Q96,55 96,65 Q92,72 88,70 Z" fill="#D08AB0" opacity="0.9"/>
          <path d="M112,70 Q118,62 112,55 Q104,55 104,65 Q108,72 112,70 Z" fill="#D08AB0" opacity="0.9"/>
          <circle cx="100" cy="62" r="2.5" fill="#FFE066"/>
          <path d="M100,82 L100,68" stroke="#5A8A4A" stroke-width="1.2" fill="none"/>
        `;
      }
    }

    // Face (centered at 100,118)
    const face = `
      <g transform="translate(100,118)">
        <ellipse cx="-22" cy="7" rx="7" ry="5" fill="#FF9999" opacity="0.28"/>
        <ellipse cx="22"  cy="7" rx="7" ry="5" fill="#FF9999" opacity="0.28"/>
        <g transform="translate(-15,0)">
          <g id="eyeL">
            <circle r="9" fill="white"/>
            <circle id="pupilL" cx="0" cy="0" r="5" fill="#3a3020"/>
            <circle cx="2.5" cy="-2.5" r="1.8" fill="white" opacity="0.9"/>
          </g>
        </g>
        <g transform="translate(15,0)">
          <g id="eyeR">
            <circle r="9" fill="white"/>
            <circle id="pupilR" cx="0" cy="0" r="5" fill="#3a3020"/>
            <circle cx="2.5" cy="-2.5" r="1.8" fill="white" opacity="0.9"/>
          </g>
        </g>
        <path id="browL" d="M -22,-11 Q -14,-15 -7,-11" stroke="#5a4030" stroke-width="2.2" fill="none" stroke-linecap="round"/>
        <path id="browR" d="M 7,-11 Q 14,-15 22,-11"   stroke="#5a4030" stroke-width="2.2" fill="none" stroke-linecap="round"/>
        <path id="petMouth" d="M -9,14 Q 0,19 9,14" stroke="#5a4030" stroke-width="2.2" fill="none" stroke-linecap="round"/>
      </g>
    `;

    return pot + body + face + '<g id="petFx"></g>';
  }

  function renderLeaf(n, pos, shapeKey, fill, stroke) {
    const path = LEAF_SHAPES[shapeKey] || LEAF_SHAPES.heart;
    return `
      <g transform="translate(${pos.tx},${pos.ty})">
        <g id="leaf${n}" style="transform-origin:0px ${pos.originY}px;transform:rotate(${pos.rot}deg)">
          <path class="petLeaf" d="${path}" fill="${fill}" stroke="${stroke}" stroke-width="0.8"/>
        </g>
      </g>
    `;
  }

  function spineRows(color) {
    // Rows of small horizontal spines along the cactus body
    const rows = [];
    for (let y = 100; y < 188; y += 12) {
      for (let x = 80; x <= 120; x += 8) {
        rows.push(`<line x1="${x}" y1="${y}" x2="${x+3}" y2="${y-1}" stroke="${color}" stroke-width="1" opacity="0.85"/>`);
      }
    }
    return rows.join('');
  }

  // ── REF BINDING ──────────────────────────────────────────
  function bindRefs() {
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
  }

  // ── INIT ─────────────────────────────────────────────────
  function init() {
    svg = document.getElementById('petSvg');
    if (!svg || typeof anime === 'undefined') return;
    setSpecies(currentSpecies, /*reenter=*/false);
    bindEvents();
    enter(S.IDLE);
    checkNight();
    setInterval(checkNight, 60000);
  }

  // Public: swap the character to a different species.
  function setSpecies(species, reenter = true) {
    if (!SPECIES_VISUALS[species]) species = 'pothos';
    currentSpecies = species;
    LEAF_FILLS = SPECIES_VISUALS[species].leafColors.slice();

    const group = document.getElementById('petGroup');
    if (!group) return;
    // Stop in-flight animations on the old elements
    if (typeof anime !== 'undefined') anime.remove(['#petGroup', '#leaf1', '#leaf2', '#leaf3', '#leaf4']);
    group.innerHTML = buildPetSvg(species);
    bindRefs();

    if (reenter) {
      // Re-enter current state so animations re-attach to new elements
      const prev = state;
      state = null;  // force re-enter
      enter(prev || S.IDLE);
    }
  }

  // ── STATE MACHINE ─────────────────────────────────────────
  function enter(next) {
    if (state === next && next !== S.WATERED) return;
    const prev = state;
    state = next;

    if (typeof anime !== 'undefined') {
      anime.remove([petGroup, leaf1, leaf2, leaf3, leaf4]);
    }
    clearTimeout(blinkTimer);
    clearInterval(zzzTimer);

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
    if (!el) return;
    anime({ targets: el, rotate: [a + 'deg', b + 'deg'], duration: dur,
            easing: 'easeInOutSine', direction: 'alternate', loop: true, delay });
  }

  function rotateTo(el, deg) {
    if (!el) return;
    anime({ targets: el, rotate: deg + 'deg', duration: 900, easing: 'easeOutQuad' });
  }

  function restoreLeafColors() {
    document.querySelectorAll('.petLeaf').forEach((l, i) =>
      anime({ targets: l, fill: LEAF_FILLS[i] || LEAF_FILLS[0] || '#5A9E4A', duration: 900 }));
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
    if (!mouthEl || !browL || !browR || !eyeL || !eyeR) return;
    anime({ targets: mouthEl, d: [{ value: f.mouth }], duration: 350, easing: 'easeOutQuad' });
    anime({ targets: browL,   d: [{ value: f.browL }], duration: 350, easing: 'easeOutQuad' });
    anime({ targets: browR,   d: [{ value: f.browR }], duration: 350, easing: 'easeOutQuad' });
    anime({ targets: [eyeL, eyeR], scaleY: f.eyeScY, duration: 250, easing: 'easeOutQuad' });
  }

  function blink() {
    if (!eyeL || !eyeR) return;
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
        if (pupilL && pupilR)
          anime({ targets: [pupilL, pupilR], cx: dx, cy: dy, duration: 280, easing: 'easeOutQuad' });
        setTimeout(() => {
          if (pupilL && pupilR)
            anime({ targets: [pupilL, pupilR], cx: 0, cy: 0, duration: 280, easing: 'easeOutQuad' });
          if (state === S.IDLE || state === S.THIRSTY) scheduleBlinkAndLook();
        }, 1300);
      }, 200);
    }, delay);
  }

  // ── PARTICLES ─────────────────────────────────────────────
  function mkText(ch, x, y, size) {
    if (!fx) return null;
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
    if (!el) return;
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
    if (!el) return;
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
    if (!svg) return;
    svg.addEventListener('mousemove', onMove);
    svg.addEventListener('mouseleave', () => {
      if (pupilL && pupilR)
        anime({ targets: [pupilL, pupilR], cx: 0, cy: 0, duration: 400, easing: 'easeOutQuad' });
    });
    svg.addEventListener('click', onClick);
    svg.addEventListener('touchend', e => { e.preventDefault(); onClick(); });
  }

  function onMove(e) {
    if (state === S.NIGHT || state === S.DIM) return;
    if (!pupilL || !pupilR) return;
    const r  = svg.getBoundingClientRect();
    const cx = r.left + r.width * 0.5;
    const cy = r.top  + r.height * 0.46;
    const dx = Math.max(-4, Math.min(4, (e.clientX - cx) / r.width  * 14));
    const dy = Math.max(-3, Math.min(3, (e.clientY - cy) / r.height * 12));
    anime({ targets: [pupilL, pupilR], cx: dx, cy: dy, duration: 80, easing: 'linear' });
  }

  function onClick() {
    if (state === S.NIGHT) return;
    if (typeof ClickGame !== 'undefined') ClickGame.tick();
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
      if (!mouthEl) { speaking = false; return; }
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
    if (petGroup)
      anime({ targets: petGroup, scale: [1, 1.12, 1], duration: 600, easing: 'easeOutBack' });
    face('happy');
    setTimeout(() => face(curFace()), 2500);
  }

  function isNight() { const h = new Date().getHours(); return h >= 21 || h < 7; }

  function checkNight() {
    if (isNight() && state !== S.NIGHT) enter(S.NIGHT);
    else if (!isNight() && state === S.NIGHT) enter(S.IDLE);
  }

  return { init, setSpecies, onReading, onSpeechStart, onSpeechEnd, onAchievement };
})();
