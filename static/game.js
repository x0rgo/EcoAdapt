// game.js — Sundrop Garden: Cookie Clicker minigame
// Triggered by clicking the plant 10 times (3 after first unlock).
// Fully self-contained — zero backend changes.

const ClickGame = (() => {
  'use strict';

  const SAVE_KEY = 'ecoadapt_garden';
  const TICK_MS  = 50; // 20fps

  // ── BUILDINGS ──────────────────────────────────────────────
  const BLDG = [
    { id:'worm',     emoji:'🪱', name:'Earthworm',        desc:'Tills soil. Every little bit helps.',              cost:15,     rate:0.1  },
    { id:'rain',     emoji:'💧', name:'Raindrop',         desc:'Drips nutrients in automatically.',                cost:100,    rate:0.5  },
    { id:'bee',      emoji:'🐝', name:'Bee',              desc:'Brings pollen from distant flowers.',              cost:500,    rate:2    },
    { id:'sun',      emoji:'☀️', name:'Sunbeam',          desc:'A focused shaft of golden light.',                 cost:2000,   rate:8    },
    { id:'mycelium', emoji:'🍄', name:'Mycelium Network', desc:'The underground internet of the forest.',          cost:10000,  rate:25   },
    { id:'moon',     emoji:'🌙', name:'Moon Cycle',       desc:'Harnesses the power of the lunar tide.',           cost:50000,  rate:100  },
    { id:'dna',      emoji:'🧬', name:'Plant DNA',        desc:'Engineered for maximum photosynthesis.',           cost:200000, rate:400  },
    { id:'storm',    emoji:'⛈️',  name:'Thunderstorm',    desc:'Raw elemental energy. Uncontrollable. Delicious.', cost:1e6,    rate:1600 },
  ];

  // ── UPGRADES ───────────────────────────────────────────────
  const UPGRADES = [
    { id:'soil',    name:'Rich Soil',        desc:'+2 per click.',              cost:100,    req:null,       reqN:0, apply:g=>{ g.clickBonus+=2; }            },
    { id:'compost', name:'Compost Heap',     desc:'+10 per click.',             cost:500,    req:null,       reqN:0, apply:g=>{ g.clickBonus+=10; }           },
    { id:'fert',    name:'Fertilizer',       desc:'All buildings ×2.',          cost:1000,   req:'worm',     reqN:1, apply:g=>{ g.bldgMult*=2; }              },
    { id:'lamp',    name:'Grow Lamp',        desc:'Clicks ×2.',                 cost:2000,   req:null,       reqN:0, apply:g=>{ g.clickMult*=2; }             },
    { id:'acid',    name:'Acid Rain',        desc:'Raindrops produce ×3.',      cost:5000,   req:'rain',     reqN:1, apply:g=>{ g.boosts.rain=(g.boosts.rain||1)*3; }},
    { id:'queen',   name:'Queen Bee',        desc:'Bees produce ×4.',           cost:15000,  req:'bee',      reqN:1, apply:g=>{ g.boosts.bee=(g.boosts.bee||1)*4;  }},
    { id:'ritual',  name:'Rain Ritual',      desc:'All buildings ×3.',          cost:25000,  req:'mycelium', reqN:1, apply:g=>{ g.bldgMult*=3; }              },
    { id:'thumb',   name:'Golden Thumb',     desc:'Clicks ×5.',                 cost:100000, req:null,       reqN:0, apply:g=>{ g.clickMult*=5; }             },
    { id:'corona',  name:'Solar Corona',     desc:'Sunbeams produce ×5.',       cost:200000, req:'sun',      reqN:5, apply:g=>{ g.boosts.sun=(g.boosts.sun||1)*5;  }},
    { id:'network', name:'Hyphal Broadband', desc:'Mycelium ×6.',               cost:500000, req:'mycelium', reqN:5, apply:g=>{ g.boosts.mycelium=(g.boosts.mycelium||1)*6; }},
    { id:'god',     name:'Plant God',        desc:'Everything ×10.',            cost:1e6,    req:'dna',      reqN:1, apply:g=>{ g.bldgMult*=10; g.clickMult*=10; }},
    { id:'storm2',  name:'Eye of the Storm', desc:'Thunderstorms ×8.',          cost:5e6,    req:'storm',    reqN:1, apply:g=>{ g.boosts.storm=(g.boosts.storm||1)*8; }},
  ];

  // ── MILESTONES ─────────────────────────────────────────────
  const MILESTONES = [
    [10,      '🌱 First sprout!'],
    [100,     '🌿 Your garden grows.'],
    [1000,    '🌳 A forest stirs.'],
    [10000,   '🍄 The mycelium awakens.'],
    [100000,  '🌍 You are the forest now.'],
    [1000000, '🌌 Photosynthesis singularity.'],
    [1e7,     '🧬 Planet-scale chlorophyll.'],
    [1e9,     '☀️ You have become the sun.'],
    [1e12,    '🌌 The garden spans galaxies.'],
  ];

  // ── PLANT EVOLUTION ────────────────────────────────────────
  const CLICKER_STAGES = ['🌱','🌿','🌳','🌲','🎋','🏕️','🌍','🌌'];

  // ── GAME STATE ─────────────────────────────────────────────
  const def = () => ({
    sundrops:   0,
    lifetime:   0,
    clickBonus: 1,
    clickMult:  1,
    bldgMult:   1,
    boosts:     {},
    owned:      {},
    bought:     [],
  });

  let g            = def();
  let loopId       = null;
  let clickCount   = 0;
  let everOpened   = false;
  let milestones   = new Set();
  let overlay      = null;

  // ── SAVE / LOAD ────────────────────────────────────────────
  function save() {
    try { localStorage.setItem(SAVE_KEY, JSON.stringify(g)); } catch(_) {}
  }
  function load() {
    try {
      const raw = localStorage.getItem(SAVE_KEY);
      if (raw) {
        g = Object.assign(def(), JSON.parse(raw));
        milestones = new Set(MILESTONES.filter(([n])=>g.lifetime>=n).map(([n])=>n));
        everOpened = true;
      }
    } catch(_) {}
  }

  // ── RATES ──────────────────────────────────────────────────
  function bldgRate(id) {
    const b = BLDG.find(b=>b.id===id);
    return (g.owned[id]||0) * b.rate * (g.boosts[id]||1) * g.bldgMult;
  }
  function perSec()   { return BLDG.reduce((s,b)=>s+bldgRate(b.id), 0); }
  function perClick() { return Math.max(1, g.clickBonus * g.clickMult); }
  function bldgCost(b){ return Math.ceil(b.cost * Math.pow(1.15, g.owned[b.id]||0)); }

  // ── FORMAT ─────────────────────────────────────────────────
  function fmt(n) {
    n = Math.floor(n);
    if (n>=1e15) return (n/1e15).toFixed(2)+' Qa';
    if (n>=1e12) return (n/1e12).toFixed(2)+' T';
    if (n>=1e9)  return (n/1e9 ).toFixed(2)+' B';
    if (n>=1e6)  return (n/1e6 ).toFixed(2)+' M';
    if (n>=1e3)  return (n/1e3 ).toFixed(1)+' K';
    return n.toString();
  }
  function fmtRate(n) {
    if (n>=1e6)  return (n/1e6).toFixed(1)+'M/s';
    if (n>=1e3)  return (n/1e3).toFixed(1)+'K/s';
    return n.toFixed(1)+'/s';
  }

  // ── GAME LOOP ──────────────────────────────────────────────
  function startLoop() {
    if (loopId) return;
    loopId = setInterval(()=>{
      const gain = perSec() * (TICK_MS/1000);
      g.sundrops += gain;
      g.lifetime += gain;
      checkMilestones();
      renderStats();
      renderShop();
    }, TICK_MS);
  }
  function stopLoop() { clearInterval(loopId); loopId=null; save(); }

  // ── MILESTONES ─────────────────────────────────────────────
  function checkMilestones() {
    for (const [n,msg] of MILESTONES) {
      if (g.lifetime>=n && !milestones.has(n)) {
        milestones.add(n);
        flashMilestone(msg);
      }
    }
  }
  function flashMilestone(msg) {
    const el = overlay && overlay.querySelector('#ggMilestone');
    if (!el) return;
    el.textContent = msg;
    el.classList.add('show');
    setTimeout(()=>el.classList.remove('show'), 3500);
  }

  // ── RENDER ─────────────────────────────────────────────────
  function renderStats() {
    if (!overlay) return;
    qs('#ggCount').textContent    = fmt(g.sundrops)+' ☀️';
    qs('#ggRate').textContent     = fmtRate(perSec());
    qs('#ggLifetime').textContent = 'Lifetime: '+fmt(g.lifetime)+' ☀️';
    qs('#ggClickVal').textContent = '+'+fmt(perClick())+' ☀️ per click';
  }

  function renderShop() {
    if (!overlay) return;
    BLDG.forEach(b=>{
      const row = qs(`#gg-b-${b.id}`);
      if (!row) return;
      const cost = bldgCost(b);
      const cnt  = g.owned[b.id]||0;
      const btn  = row.querySelector('.gg-buy-btn');
      btn.disabled = g.sundrops < cost;
      btn.textContent = '☀️ '+fmt(cost);
      row.querySelector('.gg-bcnt').textContent  = cnt ? `×${cnt}` : '';
      row.querySelector('.gg-brate').textContent = cnt ? fmtRate(bldgRate(b.id)) : '';
    });
    UPGRADES.forEach(u=>{
      const el = qs(`#gg-u-${u.id}`);
      if (!el) return;
      if (g.bought.includes(u.id)) { el.style.display='none'; return; }
      const visible = !u.req || (g.owned[u.req]||0) >= u.reqN;
      el.style.display = visible ? '' : 'none';
      el.querySelector('.gg-upg-btn').disabled = g.sundrops < u.cost;
    });
    // evolve big plant
    const total = Object.values(g.owned).reduce((s,v)=>s+v,0);
    const idx   = Math.min(Math.floor(total/8), CLICKER_STAGES.length-1);
    const big   = qs('#ggBigPlant');
    if (big && big.textContent !== CLICKER_STAGES[idx]) big.textContent = CLICKER_STAGES[idx];
  }

  function qs(sel) { return overlay && overlay.querySelector(sel); }

  // ── BUILD OVERLAY ──────────────────────────────────────────
  function buildOverlay() {
    // Inject styles once
    if (!document.getElementById('gg-styles')) {
      const s = document.createElement('style');
      s.id = 'gg-styles';
      s.textContent = `
#ggOverlay{position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.84);display:flex;align-items:center;justify-content:center;animation:ggFadeIn .2s ease}
@keyframes ggFadeIn{from{opacity:0}to{opacity:1}}
#ggPanel{background:#0d1a0f;border:1px solid #2a5a2a;border-radius:16px;width:min(920px,96vw);max-height:90vh;display:flex;flex-direction:column;box-shadow:0 24px 80px #000a,0 0 60px #3cb43c0d;overflow:hidden;position:relative}
#ggHeader{display:flex;justify-content:space-between;align-items:flex-start;padding:18px 22px 14px;border-bottom:1px solid #1a3a1a;background:linear-gradient(180deg,#091508,#0d1a0f);flex-shrink:0}
#ggTitle{font-family:'Playfair Display',serif;font-size:21px;color:#7be07b;margin-bottom:3px}
#ggCount{font-size:26px;font-weight:600;color:#d4f0d4;font-family:'DM Mono',monospace}
#ggSubrow{display:flex;gap:18px;margin-top:3px}
#ggRate,#ggLifetime{font-size:11px;color:#4a8a4a;font-family:'DM Mono',monospace}
#ggCloseBtn{background:transparent;border:1px solid #2a4a2a;color:#7be07b;font-size:16px;cursor:pointer;border-radius:8px;padding:5px 9px;transition:all .15s;flex-shrink:0;line-height:1}
#ggCloseBtn:hover{background:#1a3a1a;border-color:#5ab05a}
#ggMain{display:flex;flex:1;min-height:0;overflow:hidden}
#ggClickArea{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:28px 20px;min-width:190px;border-right:1px solid #1a3a1a;flex-shrink:0;gap:10px}
#ggBigPlant{font-size:96px;cursor:pointer;user-select:none;transition:transform .08s ease;filter:drop-shadow(0 0 18px #64dc6440);line-height:1.05}
#ggBigPlant:hover{filter:drop-shadow(0 0 30px #64dc6468)}
#ggBigPlant.clicked{transform:scale(.86) rotate(-4deg)}
#ggClickVal{font-size:12px;color:#5ab05a;font-family:'DM Mono',monospace;text-align:center}
#ggResetBtn{margin-top:6px;background:transparent;border:1px solid #1e2e1e;color:#3a5a3a;font-size:10px;cursor:pointer;border-radius:5px;padding:3px 8px;font-family:'DM Mono',monospace;transition:all .15s}
#ggResetBtn:hover{border-color:#5ab05a;color:#7be07b}
#ggShop{flex:1;display:flex;flex-direction:column;overflow:hidden}
#ggShopTabs{display:flex;border-bottom:1px solid #1a3a1a;flex-shrink:0}
.gg-tab{flex:1;padding:11px;background:transparent;border:none;color:#3a5a3a;font-size:12px;cursor:pointer;font-family:'DM Mono',monospace;transition:all .15s;border-bottom:2px solid transparent}
.gg-tab.active{color:#7be07b;border-bottom-color:#5ab05a;background:#0a140b}
.gg-tab:hover:not(.active){color:#5ab05a;background:#0b160c}
.gg-tabpanel{flex:1;overflow-y:auto;padding:6px}
.gg-tabpanel::-webkit-scrollbar{width:3px}
.gg-tabpanel::-webkit-scrollbar-thumb{background:#2a4a2a;border-radius:2px}
.gg-brow{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:7px;margin-bottom:3px;border:1px solid transparent;transition:border-color .15s}
.gg-brow:hover{border-color:#1a3a1a;background:#0a140c}
.gg-bemoji{font-size:24px;flex-shrink:0;width:32px;text-align:center}
.gg-binfo{flex:1;min-width:0}
.gg-bname{font-size:12px;color:#b8d8b8;font-family:'DM Sans',sans-serif}
.gg-bcnt{color:#7be07b;font-family:'DM Mono',monospace;font-size:11px;margin-left:4px}
.gg-brate{font-size:10px;color:#3a6a3a;font-family:'DM Mono',monospace;margin-top:1px}
.gg-bdesc{font-size:10px;color:#2a4a2a;margin-top:1px;font-style:italic}
.gg-buy-btn{background:#091e09;border:1px solid #2a522a;color:#7be07b;font-size:11px;cursor:pointer;border-radius:5px;padding:5px 8px;font-family:'DM Mono',monospace;transition:all .15s;white-space:nowrap;flex-shrink:0}
.gg-buy-btn:hover:not(:disabled){background:#163016;border-color:#5ab05a}
.gg-buy-btn:disabled{opacity:.3;cursor:not-allowed}
.gg-upg{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:7px;margin-bottom:3px;border:1px solid #162416}
.gg-upg:hover{background:#0a140c}
.gg-upg-info{flex:1}
.gg-upg-name{font-size:12px;color:#b8d8b8}
.gg-upg-desc{font-size:10px;color:#3a6a3a;margin-top:2px}
.gg-upg-btn{background:#091e09;border:1px solid #2a522a;color:#7be07b;font-size:11px;cursor:pointer;border-radius:5px;padding:5px 8px;font-family:'DM Mono',monospace;transition:all .15s;white-space:nowrap;flex-shrink:0}
.gg-upg-btn:hover:not(:disabled){background:#163016;border-color:#5ab05a}
.gg-upg-btn:disabled{opacity:.3;cursor:not-allowed}
.gg-float{position:fixed;font-size:15px;font-weight:700;color:#7be07b;font-family:'DM Mono',monospace;pointer-events:none;z-index:10000;white-space:nowrap;animation:ggFloat .85s ease-out forwards}
@keyframes ggFloat{0%{opacity:1;transform:translateY(0) scale(1.1)}100%{opacity:0;transform:translateY(-55px) scale(.95)}}
#ggMilestone{position:absolute;bottom:18px;left:50%;transform:translateX(-50%) translateY(16px);background:#0a220a;border:1px solid #4a9a4a;border-radius:20px;padding:7px 18px;font-size:13px;color:#7be07b;font-family:'DM Mono',monospace;opacity:0;transition:all .4s ease;pointer-events:none;white-space:nowrap;z-index:1}
#ggMilestone.show{opacity:1;transform:translateX(-50%) translateY(0)}
@media(max-width:600px){#ggMain{flex-direction:column}#ggClickArea{border-right:none;border-bottom:1px solid #1a3a1a;padding:16px;min-width:unset}#ggBigPlant{font-size:68px}}`;
      document.head.appendChild(s);
    }

    const div = document.createElement('div');
    div.id = 'ggOverlay';
    div.innerHTML = `
<div id="ggPanel">
  <div id="ggHeader">
    <div>
      <div id="ggTitle">☀️ Sundrop Garden</div>
      <div id="ggCount">0 ☀️</div>
      <div id="ggSubrow"><span id="ggRate">0/s</span><span id="ggLifetime">Lifetime: 0 ☀️</span></div>
    </div>
    <button id="ggCloseBtn" title="Back to plant">✕</button>
  </div>

  <div id="ggMain">
    <div id="ggClickArea">
      <div id="ggBigPlant" title="Click me!">🌱</div>
      <div id="ggClickVal">+1 ☀️ per click</div>
      <button id="ggResetBtn">🌱 Start over</button>
    </div>

    <div id="ggShop">
      <div id="ggShopTabs">
        <button class="gg-tab active" data-tab="buildings">🌱 Buildings</button>
        <button class="gg-tab" data-tab="upgrades">⚗️ Upgrades</button>
      </div>

      <div id="ggTab-buildings" class="gg-tabpanel">
        ${BLDG.map(b=>`
        <div class="gg-brow" id="gg-b-${b.id}">
          <div class="gg-bemoji">${b.emoji}</div>
          <div class="gg-binfo">
            <div class="gg-bname">${b.name}<span class="gg-bcnt"></span></div>
            <div class="gg-brate"></div>
            <div class="gg-bdesc">${b.desc}</div>
          </div>
          <button class="gg-buy-btn" data-id="${b.id}">☀️ ${fmt(b.cost)}</button>
        </div>`).join('')}
      </div>

      <div id="ggTab-upgrades" class="gg-tabpanel" style="display:none">
        ${UPGRADES.map(u=>`
        <div class="gg-upg" id="gg-u-${u.id}" style="display:none">
          <div class="gg-upg-info">
            <div class="gg-upg-name">${u.name}</div>
            <div class="gg-upg-desc">${u.desc}</div>
          </div>
          <button class="gg-upg-btn" data-id="${u.id}" disabled>☀️ ${fmt(u.cost)}</button>
        </div>`).join('')}
      </div>
    </div>
  </div>

  <div id="ggMilestone"></div>
</div>`;

    // Tab switching
    div.querySelectorAll('.gg-tab').forEach(tab=>{
      tab.addEventListener('click', ()=>{
        div.querySelectorAll('.gg-tab').forEach(t=>t.classList.remove('active'));
        div.querySelectorAll('.gg-tabpanel').forEach(p=>p.style.display='none');
        tab.classList.add('active');
        div.querySelector(`#ggTab-${tab.dataset.tab}`).style.display='';
      });
    });

    // Buy buildings
    div.querySelectorAll('.gg-buy-btn').forEach(btn=>{
      btn.addEventListener('click', ()=>buyBuilding(btn.dataset.id));
    });

    // Buy upgrades
    div.querySelectorAll('.gg-upg-btn').forEach(btn=>{
      btn.addEventListener('click', ()=>buyUpgrade(btn.dataset.id));
    });

    // Click plant
    div.querySelector('#ggBigPlant').addEventListener('click', onBigClick);

    // Close
    div.querySelector('#ggCloseBtn').addEventListener('click', close);
    div.addEventListener('click', e=>{ if(e.target===div) close(); });

    // Reset
    div.querySelector('#ggResetBtn').addEventListener('click', ()=>{
      if (!confirm('Reset all garden progress? This cannot be undone.')) return;
      g = def();
      milestones.clear();
      save();
      renderStats();
      renderShop();
      flashMilestone('🌱 Garden reset. Fresh start!');
    });

    document.body.appendChild(div);
    return div;
  }

  // ── OPEN / CLOSE ───────────────────────────────────────────
  function open(firstTime) {
    if (!overlay) {
      load();
      overlay = buildOverlay();
    } else {
      overlay.style.display = 'flex';
    }
    if (firstTime) {
      if (typeof Pet !== 'undefined') Pet.onAchievement();
      fetch('/api/achievements/unlock-garden', { method: 'POST' }).catch(()=>{});
    }
    renderStats();
    renderShop();
    startLoop();
  }

  function close() {
    if (overlay) overlay.style.display = 'none';
    stopLoop();
  }

  // ── CLICK ACTIONS ──────────────────────────────────────────
  function onBigClick(e) {
    const gain = perClick();
    g.sundrops += gain;
    g.lifetime += gain;
    checkMilestones();
    save();
    renderStats();
    renderShop();

    const plant = qs('#ggBigPlant');
    plant.classList.add('clicked');
    setTimeout(()=>plant.classList.remove('clicked'), 80);

    // Floating number
    const el = document.createElement('div');
    el.className = 'gg-float';
    el.textContent = '+'+fmt(gain)+' ☀️';
    el.style.cssText = `left:${e.clientX-30}px;top:${e.clientY-10}px`;
    document.body.appendChild(el);
    setTimeout(()=>el.remove(), 900);
  }

  function buyBuilding(id) {
    const b = BLDG.find(b=>b.id===id);
    if (!b) return;
    const cost = bldgCost(b);
    if (g.sundrops < cost) return;
    g.sundrops -= cost;
    g.owned[id] = (g.owned[id]||0)+1;
    save();
    renderStats();
    renderShop();
  }

  function buyUpgrade(id) {
    const u = UPGRADES.find(u=>u.id===id);
    if (!u || g.bought.includes(id) || g.sundrops<u.cost) return;
    g.sundrops -= u.cost;
    g.bought.push(id);
    u.apply(g);
    save();
    renderStats();
    renderShop();
  }

  // ── PUBLIC: called by pet.js onClick ───────────────────────
  function tick() {
    clickCount++;
    const threshold = everOpened ? 3 : 10;
    if (clickCount >= threshold) {
      clickCount  = 0;
      const first = !everOpened;
      everOpened  = true;
      open(first);
    }
  }

  // Pre-check localStorage so repeat visitors get 3-click threshold immediately
  try { if (localStorage.getItem(SAVE_KEY)) everOpened = true; } catch(_) {}

  return { tick, open };
})();
