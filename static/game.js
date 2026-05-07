// game.js — Sundrop Garden: Cookie Clicker minigame
// Triggered by clicking the plant 10 times (3 after first unlock).
// Self-contained except for /api/achievements/unlock-game endpoint.

const ClickGame = (() => {
  'use strict';

  const SAVE_KEY = 'ecoadapt_garden';
  const TICK_MS  = 50; // 20fps

  // ── BUILDINGS ──────────────────────────────────────────────
  const BLDG = [
    { id:'worm',     emoji:'🪱', name:'Earthworm',         desc:'Tills soil. Every little bit helps.',                  cost:15,     rate:0.1   },
    { id:'rain',     emoji:'💧', name:'Raindrop',          desc:'Drips nutrients in automatically.',                    cost:100,    rate:0.5   },
    { id:'bee',      emoji:'🐝', name:'Bee',               desc:'Brings pollen from distant flowers.',                  cost:500,    rate:2     },
    { id:'sun',      emoji:'☀️', name:'Sunbeam',           desc:'A focused shaft of golden light.',                     cost:2000,   rate:8     },
    { id:'mycelium', emoji:'🍄', name:'Mycelium Network',  desc:'The underground internet of the forest.',              cost:10000,  rate:25    },
    { id:'moon',     emoji:'🌙', name:'Moon Cycle',        desc:'Harnesses the power of the lunar tide.',               cost:50000,  rate:100   },
    { id:'dna',      emoji:'🧬', name:'Plant DNA',         desc:'Engineered for maximum photosynthesis.',               cost:200000, rate:400   },
    { id:'storm',    emoji:'⛈️',  name:'Thunderstorm',     desc:'Raw elemental energy. Uncontrollable. Delicious.',     cost:1e6,    rate:1600  },
    { id:'volcano',  emoji:'🌋', name:'Volcano',           desc:'Mineral-rich ash falls onto your garden.',             cost:1e7,    rate:6400  },
    { id:'orbit',    emoji:'🪐', name:'Planetarium',       desc:'Plants grown in zero-G. The leaves are weird.',        cost:1e8,    rate:25000 },
    { id:'time',     emoji:'⏰',  name:'Time Loop',        desc:'Tomorrow’s harvest. Today.',                           cost:5e8,    rate:100000},
    { id:'cosmic',   emoji:'🌌', name:'Cosmic Garden',     desc:'A nebula of pure chlorophyll.',                        cost:1e10,   rate:5e5   },
    { id:'multi',    emoji:'🌈', name:'Multiverse',        desc:'Every garden, in every reality, working for you.',     cost:1e12,   rate:25e5  },
  ];

  // ── UPGRADES ───────────────────────────────────────────────
  const UPGRADES = [
    // Click upgrades
    { id:'soil',     name:'Rich Soil',          desc:'+2 per click.',           cost:100,   req:null,        reqN:0,  apply:g=>{ g.clickBonus+=2;     }},
    { id:'compost',  name:'Compost Heap',       desc:'+10 per click.',          cost:500,   req:null,        reqN:0,  apply:g=>{ g.clickBonus+=10;    }},
    { id:'lamp',     name:'Grow Lamp',          desc:'Clicks ×2.',              cost:2000,  req:null,        reqN:0,  apply:g=>{ g.clickMult*=2;      }},
    { id:'thumb',    name:'Golden Thumb',       desc:'Clicks ×5.',              cost:100000,req:null,        reqN:0,  apply:g=>{ g.clickMult*=5;      }},
    { id:'cell',     name:'Cellular Burst',     desc:'+100 per click.',         cost:5e7,   req:null,        reqN:0,  apply:g=>{ g.clickBonus+=100;   }},
    { id:'photon',   name:'Photonic Click',     desc:'Clicks ×100.',            cost:1e9,   req:'sun',       reqN:50, apply:g=>{ g.clickMult*=100;    }},
    // Per-building boosts
    { id:'fert',     name:'Fertilizer',         desc:'All buildings ×2.',       cost:1000,  req:'worm',      reqN:1,  apply:g=>{ g.bldgMult*=2;       }},
    { id:'acid',     name:'Acid Rain',          desc:'Raindrops ×3.',           cost:5000,  req:'rain',      reqN:1,  apply:g=>{ g.boosts.rain=(g.boosts.rain||1)*3;  }},
    { id:'queen',    name:'Queen Bee',          desc:'Bees ×4.',                cost:15000, req:'bee',       reqN:1,  apply:g=>{ g.boosts.bee=(g.boosts.bee||1)*4;    }},
    { id:'corona',   name:'Solar Corona',       desc:'Sunbeams ×5.',            cost:200000,req:'sun',       reqN:5,  apply:g=>{ g.boosts.sun=(g.boosts.sun||1)*5;    }},
    { id:'network',  name:'Hyphal Broadband',   desc:'Mycelium ×6.',            cost:500000,req:'mycelium',  reqN:5,  apply:g=>{ g.boosts.mycelium=(g.boosts.mycelium||1)*6; }},
    { id:'lunar',    name:'Lunar Mastery',      desc:'Moon Cycles ×8.',         cost:5e6,   req:'moon',      reqN:10, apply:g=>{ g.boosts.moon=(g.boosts.moon||1)*8;  }},
    { id:'genetic',  name:'Genetic Engineer',   desc:'Plant DNA ×10.',          cost:5e7,   req:'dna',       reqN:10, apply:g=>{ g.boosts.dna=(g.boosts.dna||1)*10;   }},
    { id:'storm2',   name:'Eye of the Storm',   desc:'Thunderstorms ×8.',       cost:5e6,   req:'storm',     reqN:1,  apply:g=>{ g.boosts.storm=(g.boosts.storm||1)*8; }},
    { id:'volcanic', name:'Volcanic Heart',     desc:'Volcanoes ×15.',          cost:5e8,   req:'volcano',   reqN:5,  apply:g=>{ g.boosts.volcano=(g.boosts.volcano||1)*15; }},
    { id:'orbital',  name:'Cosmic Resonance',   desc:'Planetariums ×20.',       cost:5e9,   req:'orbit',     reqN:5,  apply:g=>{ g.boosts.orbit=(g.boosts.orbit||1)*20; }},
    { id:'paradox',  name:'Time Paradox',       desc:'Time Loops ×50.',         cost:1e11,  req:'time',      reqN:5,  apply:g=>{ g.boosts.time=(g.boosts.time||1)*50; }},
    { id:'verdant',  name:'Verdant Multiverse', desc:'Cosmic & Multiverse ×100.', cost:1e13, req:'cosmic',  reqN:1,  apply:g=>{ g.boosts.cosmic=(g.boosts.cosmic||1)*100; g.boosts.multi=(g.boosts.multi||1)*100; }},
    // Global multipliers
    { id:'ritual',   name:'Rain Ritual',        desc:'All buildings ×3.',       cost:25000, req:'mycelium',  reqN:1,  apply:g=>{ g.bldgMult*=3;       }},
    { id:'god',      name:'Plant God',          desc:'Everything ×10.',         cost:1e6,   req:'dna',       reqN:1,  apply:g=>{ g.bldgMult*=10; g.clickMult*=10; }},
    { id:'whole',    name:'The Whole Garden',   desc:'Everything ×50. Requires 1+ of every building.', cost:1e12, req:null, reqN:0, gate:g=>BLDG.every(b=>(g.owned[b.id]||0)>=1), apply:g=>{ g.bldgMult*=50; g.clickMult*=50; }},
  ];

  // ── BOSSES ─────────────────────────────────────────────────
  // Each boss: hp = base, drain = % of perSec stolen while alive, reward = mult of perSec.
  const BOSSES = [
    { id:'snail',  emoji:'🐌', name:'Snail',         hp:8,   drain:0.10, reward:30,   tier:0     },
    { id:'cater',  emoji:'🐛', name:'Caterpillar',   hp:20,  drain:0.15, reward:45,   tier:100   },
    { id:'aphid',  emoji:'🐜', name:'Aphid Swarm',   hp:50,  drain:0.20, reward:60,   tier:1000  },
    { id:'locust', emoji:'🦗', name:'Locust',        hp:120, drain:0.25, reward:90,   tier:10000 },
    { id:'blight', emoji:'🦠', name:'Blight',        hp:280, drain:0.30, reward:120,  tier:100000},
    { id:'drought',emoji:'🍂', name:'Drought',       hp:600, drain:0.40, reward:180,  tier:1e6   },
    { id:'tornado',emoji:'🌪️',name:'Tornado',       hp:1400,drain:0.50, reward:240,  tier:1e8   },
    { id:'demon', emoji:'👹',  name:'Garden Demon',  hp:3500,drain:0.60, reward:360,  tier:1e10  },
  ];

  // ── ACHIEVEMENTS (game-side) ───────────────────────────────
  const GAME_ACHS = [
    { id:'click_100',     check:g=>g.totalClicks>=100   },
    { id:'click_1000',    check:g=>g.totalClicks>=1000  },
    { id:'click_10000',   check:g=>g.totalClicks>=10000 },
    { id:'earn_1m',       check:g=>g.lifetime>=1e6      },
    { id:'earn_1b',       check:g=>g.lifetime>=1e9      },
    { id:'earn_1t',       check:g=>g.lifetime>=1e12     },
    { id:'buy_all',       check:g=>BLDG.every(b=>(g.owned[b.id]||0)>=1) },
    { id:'mass_prod',     check:g=>BLDG.some(b=>(g.owned[b.id]||0)>=100) },
    { id:'pest_control',  check:g=>g.bossesKilled>=1    },
    { id:'exterminator',  check:g=>g.bossesKilled>=10   },
    { id:'apex',          check:g=>g.bossesKilled>=100  },
    { id:'method',        check:g=>g.bought.length>=UPGRADES.length },
  ];

  // ── MILESTONES (in-game banner) ────────────────────────────
  const MILESTONES = [
    [10,    '🌱 First sprout!'],
    [100,   '🌿 Your garden grows.'],
    [1000,  '🌳 A forest stirs.'],
    [10000, '🍄 The mycelium awakens.'],
    [1e5,   '🌍 You are the forest now.'],
    [1e6,   '🌌 Photosynthesis singularity.'],
    [1e7,   '🧬 Planet-scale chlorophyll.'],
    [1e9,   '☀️ You have become the sun.'],
    [1e12,  '🌈 The garden spans realities.'],
    [1e15,  '🌀 Beyond the multiverse.'],
  ];

  const CLICKER_STAGES = ['🌱','🌿','🌳','🌲','🎋','🏕️','🌍','🌌','🌈','🌀'];

  // ── STATE ──────────────────────────────────────────────────
  const def = () => ({
    sundrops:    0,
    lifetime:    0,
    clickBonus:  1,
    clickMult:   1,
    bldgMult:    1,
    boosts:      {},
    owned:       {},
    bought:      [],
    totalClicks: 0,
    bossesKilled:0,
    achEarned:   [],
    nextBossAt:  0,
  });

  let g           = def();
  let loopId      = null;
  let clickCount  = 0;
  let everOpened  = false;
  let milestones  = new Set();
  let overlay     = null;
  let boss        = null; // { def, hp, maxHp }

  // ── SAVE / LOAD ────────────────────────────────────────────
  function save() { try { localStorage.setItem(SAVE_KEY, JSON.stringify(g)); } catch(_) {} }
  function load() {
    try {
      const raw = localStorage.getItem(SAVE_KEY);
      if (raw) {
        g = Object.assign(def(), JSON.parse(raw));
        if (!Array.isArray(g.achEarned)) g.achEarned = [];
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
    if (n>=1e18) return (n/1e18).toFixed(2)+' Qi';
    if (n>=1e15) return (n/1e15).toFixed(2)+' Qa';
    if (n>=1e12) return (n/1e12).toFixed(2)+' T';
    if (n>=1e9)  return (n/1e9 ).toFixed(2)+' B';
    if (n>=1e6)  return (n/1e6 ).toFixed(2)+' M';
    if (n>=1e3)  return (n/1e3 ).toFixed(1)+' K';
    return n.toString();
  }
  function fmtRate(n) {
    if (n>=1e9) return (n/1e9).toFixed(1)+'B/s';
    if (n>=1e6) return (n/1e6).toFixed(1)+'M/s';
    if (n>=1e3) return (n/1e3).toFixed(1)+'K/s';
    return n.toFixed(1)+'/s';
  }

  // ── GAME LOOP ──────────────────────────────────────────────
  function startLoop() {
    if (loopId) return;
    loopId = setInterval(()=>{
      const ps   = perSec();
      let gain   = ps * (TICK_MS/1000);
      // Boss drain
      if (boss) gain -= ps * boss.def.drain * (TICK_MS/1000);
      g.sundrops = Math.max(0, g.sundrops + gain);
      if (gain > 0) g.lifetime += gain;
      maybeSpawnBoss();
      checkMilestones();
      checkAchievements();
      renderStats();
      renderShop();
      renderBoss();
    }, TICK_MS);
  }
  function stopLoop() { clearInterval(loopId); loopId=null; save(); }

  // ── BOSS ───────────────────────────────────────────────────
  function maybeSpawnBoss() {
    if (boss) return;
    if (g.lifetime < 50) return;
    if (Date.now() < g.nextBossAt) return;
    // Pick highest-tier boss the player qualifies for
    const candidates = BOSSES.filter(b => g.lifetime >= b.tier);
    if (!candidates.length) return;
    const def = candidates[Math.floor(Math.random() * candidates.length)];
    const totalBldg = Object.values(g.owned).reduce((s,v)=>s+v,0);
    const hp = Math.ceil(def.hp + totalBldg * 0.4);
    boss = { def, hp, maxHp: hp };
  }

  function damageBoss() {
    if (!boss) return;
    boss.hp--;
    flashBoss();
    if (boss.hp <= 0) defeatBoss();
  }

  function defeatBoss() {
    if (!boss) return;
    const reward = perSec() * boss.def.reward;
    g.sundrops   += reward;
    g.lifetime   += reward;
    g.bossesKilled++;
    flashMilestone(`💥 ${boss.def.name} defeated! +${fmt(reward)} ☀️`);
    boss = null;
    g.nextBossAt = Date.now() + 60000 + Math.random() * 120000; // 60–180s
    save();
    renderBoss();
  }

  function flashBoss() {
    const el = qs('#ggBossEmoji');
    if (!el) return;
    el.classList.remove('hit');
    void el.offsetWidth;
    el.classList.add('hit');
  }

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
    const el = qs('#ggMilestone');
    if (!el) return;
    el.textContent = msg;
    el.classList.add('show');
    setTimeout(()=>el.classList.remove('show'), 3500);
  }

  // ── ACHIEVEMENTS ───────────────────────────────────────────
  function checkAchievements() {
    for (const a of GAME_ACHS) {
      if (g.achEarned.includes(a.id)) continue;
      if (a.check(g)) earnAchievement(a.id);
    }
  }
  function earnAchievement(id) {
    if (g.achEarned.includes(id)) return;
    g.achEarned.push(id);
    save();
    fetch('/api/achievements/unlock-game', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    }).catch(()=>{});
  }

  // ── RENDER ─────────────────────────────────────────────────
  function qs(sel) { return overlay && overlay.querySelector(sel); }

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
      const visible = (!u.req || (g.owned[u.req]||0) >= u.reqN) && (!u.gate || u.gate(g));
      el.style.display = visible ? '' : 'none';
      el.querySelector('.gg-upg-btn').disabled = g.sundrops < u.cost;
    });
    // evolve big plant
    const total = Object.values(g.owned).reduce((s,v)=>s+v,0);
    const idx   = Math.min(Math.floor(total/8), CLICKER_STAGES.length-1);
    const big   = qs('#ggBigPlant');
    if (big && big.textContent !== CLICKER_STAGES[idx]) big.textContent = CLICKER_STAGES[idx];
  }

  function renderBoss() {
    const wrap = qs('#ggBossWrap');
    if (!wrap) return;
    if (!boss) { wrap.style.display = 'none'; return; }
    wrap.style.display = '';
    qs('#ggBossEmoji').textContent = boss.def.emoji;
    qs('#ggBossName').textContent  = boss.def.name;
    const pct = (boss.hp / boss.maxHp) * 100;
    qs('#ggBossHpFill').style.width = pct + '%';
    qs('#ggBossHpTxt').textContent  = `${boss.hp}/${boss.maxHp} HP`;
  }

  // ── BUILD OVERLAY ──────────────────────────────────────────
  function buildOverlay() {
    if (!document.getElementById('gg-styles')) {
      const s = document.createElement('style');
      s.id = 'gg-styles';
      s.textContent = `
#ggOverlay{position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.84);display:flex;align-items:center;justify-content:center;animation:ggFadeIn .2s ease;padding:8px}
@keyframes ggFadeIn{from{opacity:0}to{opacity:1}}
#ggPanel{background:#0d1a0f;border:1px solid #2a5a2a;border-radius:16px;width:min(960px,100%);max-height:96vh;display:flex;flex-direction:column;box-shadow:0 24px 80px #000a,0 0 60px #3cb43c0d;overflow:hidden;position:relative}
#ggPanel.fullscreen{width:100%;max-width:100%;max-height:100vh;height:100vh;border-radius:0;border:none}
#ggHeader{display:flex;justify-content:space-between;align-items:flex-start;padding:16px 20px 12px;border-bottom:1px solid #1a3a1a;background:linear-gradient(180deg,#091508,#0d1a0f);flex-shrink:0;gap:10px}
#ggTitle{font-family:'Playfair Display',serif;font-size:20px;color:#7be07b;margin-bottom:3px}
#ggCount{font-size:24px;font-weight:600;color:#d4f0d4;font-family:'DM Mono',monospace}
#ggSubrow{display:flex;gap:14px;margin-top:3px;flex-wrap:wrap}
#ggRate,#ggLifetime{font-size:11px;color:#4a8a4a;font-family:'DM Mono',monospace}
.gg-headbtn{background:transparent;border:1px solid #2a4a2a;color:#7be07b;font-size:14px;cursor:pointer;border-radius:8px;padding:5px 9px;transition:all .15s;flex-shrink:0;line-height:1;font-family:inherit}
.gg-headbtn:hover{background:#1a3a1a;border-color:#5ab05a}
.gg-headbtns{display:flex;gap:6px;flex-shrink:0}
#ggMain{display:flex;flex:1;min-height:0;overflow:hidden}
#ggClickArea{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px;min-width:200px;border-right:1px solid #1a3a1a;flex-shrink:0;gap:10px;position:relative}
#ggBigPlant{font-size:96px;cursor:pointer;user-select:none;transition:transform .08s ease;filter:drop-shadow(0 0 18px #64dc6440);line-height:1.05}
#ggBigPlant:hover{filter:drop-shadow(0 0 30px #64dc6468)}
#ggBigPlant.clicked{transform:scale(.86) rotate(-4deg)}
#ggClickVal{font-size:12px;color:#5ab05a;font-family:'DM Mono',monospace;text-align:center}
#ggBossWrap{position:absolute;inset:auto 12px 12px 12px;background:#1a0a0a;border:1px solid #6a2424;border-radius:10px;padding:12px;display:none;animation:ggBossIn .3s ease}
@keyframes ggBossIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
#ggBossTop{display:flex;align-items:center;gap:10px;margin-bottom:6px}
#ggBossEmoji{font-size:32px;cursor:pointer;user-select:none;transition:transform .08s ease;line-height:1}
#ggBossEmoji.hit{animation:ggBossHit .15s ease}
@keyframes ggBossHit{0%{transform:scale(1)}50%{transform:scale(.85) rotate(8deg);filter:drop-shadow(0 0 6px #f55)}100%{transform:scale(1)}}
#ggBossName{font-family:'Playfair Display',serif;color:#f5a5a5;font-size:14px;flex:1}
#ggBossHpTxt{font-size:10px;color:#d88;font-family:'DM Mono',monospace}
#ggBossHpBar{background:#2a0a0a;border-radius:3px;height:6px;overflow:hidden}
#ggBossHpFill{background:linear-gradient(90deg,#a02020,#e04040);height:100%;transition:width .15s ease}
#ggResetBtn{margin-top:6px;background:transparent;border:1px solid #1e2e1e;color:#3a5a3a;font-size:10px;cursor:pointer;border-radius:5px;padding:3px 8px;font-family:'DM Mono',monospace;transition:all .15s}
#ggResetBtn:hover{border-color:#5ab05a;color:#7be07b}
#ggKillCount{font-size:10px;color:#3a6a3a;font-family:'DM Mono',monospace;margin-top:4px}
#ggShop{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}
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
.gg-upg-info{flex:1;min-width:0}
.gg-upg-name{font-size:12px;color:#b8d8b8}
.gg-upg-desc{font-size:10px;color:#3a6a3a;margin-top:2px}
.gg-upg-btn{background:#091e09;border:1px solid #2a522a;color:#7be07b;font-size:11px;cursor:pointer;border-radius:5px;padding:5px 8px;font-family:'DM Mono',monospace;transition:all .15s;white-space:nowrap;flex-shrink:0}
.gg-upg-btn:hover:not(:disabled){background:#163016;border-color:#5ab05a}
.gg-upg-btn:disabled{opacity:.3;cursor:not-allowed}
.gg-float{position:fixed;font-size:15px;font-weight:700;color:#7be07b;font-family:'DM Mono',monospace;pointer-events:none;z-index:10000;white-space:nowrap;animation:ggFloat .85s ease-out forwards}
.gg-float.dmg{color:#f88}
@keyframes ggFloat{0%{opacity:1;transform:translateY(0) scale(1.1)}100%{opacity:0;transform:translateY(-55px) scale(.95)}}
#ggMilestone{position:absolute;bottom:18px;left:50%;transform:translateX(-50%) translateY(16px);background:#0a220a;border:1px solid #4a9a4a;border-radius:20px;padding:7px 18px;font-size:13px;color:#7be07b;font-family:'DM Mono',monospace;opacity:0;transition:all .4s ease;pointer-events:none;white-space:nowrap;z-index:1;max-width:90vw;text-align:center}
#ggMilestone.show{opacity:1;transform:translateX(-50%) translateY(0)}
@media(max-width:680px){#ggMain{flex-direction:column}#ggClickArea{border-right:none;border-bottom:1px solid #1a3a1a;padding:14px;min-width:unset}#ggBigPlant{font-size:68px}#ggBossWrap{position:static;margin-top:8px}#ggHeader{padding:12px 14px 10px}#ggTitle{font-size:17px}#ggCount{font-size:20px}}`;
      document.head.appendChild(s);
    }

    const div = document.createElement('div');
    div.id = 'ggOverlay';
    div.innerHTML = `
<div id="ggPanel">
  <div id="ggHeader">
    <div style="min-width:0">
      <div id="ggTitle">☀️ Sundrop Garden</div>
      <div id="ggCount">0 ☀️</div>
      <div id="ggSubrow"><span id="ggRate">0/s</span><span id="ggLifetime">Lifetime: 0 ☀️</span></div>
    </div>
    <div class="gg-headbtns">
      <button class="gg-headbtn" id="ggFullBtn" title="Toggle fullscreen">⛶</button>
      <button class="gg-headbtn" id="ggCloseBtn" title="Back to plant">✕</button>
    </div>
  </div>

  <div id="ggMain">
    <div id="ggClickArea">
      <div id="ggBigPlant" title="Click me!">🌱</div>
      <div id="ggClickVal">+1 ☀️ per click</div>
      <div id="ggKillCount"></div>
      <button id="ggResetBtn">🌱 Start over</button>

      <div id="ggBossWrap">
        <div id="ggBossTop">
          <div id="ggBossEmoji" title="Click to attack!">🐌</div>
          <div style="flex:1;min-width:0">
            <div id="ggBossName">Snail</div>
            <div id="ggBossHpTxt">10/10 HP</div>
          </div>
        </div>
        <div id="ggBossHpBar"><div id="ggBossHpFill" style="width:100%"></div></div>
      </div>
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

    // Tabs
    div.querySelectorAll('.gg-tab').forEach(tab=>{
      tab.addEventListener('click', ()=>{
        div.querySelectorAll('.gg-tab').forEach(t=>t.classList.remove('active'));
        div.querySelectorAll('.gg-tabpanel').forEach(p=>p.style.display='none');
        tab.classList.add('active');
        div.querySelector(`#ggTab-${tab.dataset.tab}`).style.display='';
      });
    });

    // Buy
    div.querySelectorAll('.gg-buy-btn').forEach(b=>b.addEventListener('click', ()=>buyBuilding(b.dataset.id)));
    div.querySelectorAll('.gg-upg-btn').forEach(b=>b.addEventListener('click', ()=>buyUpgrade(b.dataset.id)));

    // Click
    div.querySelector('#ggBigPlant').addEventListener('click', onBigClick);
    div.querySelector('#ggBossEmoji').addEventListener('click', onBossClick);

    // Buttons
    div.querySelector('#ggCloseBtn').addEventListener('click', close);
    div.querySelector('#ggFullBtn').addEventListener('click', toggleFullscreen);
    div.addEventListener('click', e=>{ if(e.target===div) close(); });

    // Reset
    div.querySelector('#ggResetBtn').addEventListener('click', ()=>{
      if (!confirm('Reset all garden progress? Achievements stay unlocked.')) return;
      const keep = g.achEarned.slice();
      g = def();
      g.achEarned = keep;
      milestones.clear();
      boss = null;
      save();
      renderStats();
      renderShop();
      renderBoss();
      flashMilestone('🌱 Garden reset. Fresh start!');
    });

    document.body.appendChild(div);
    return div;
  }

  // ── FULLSCREEN ─────────────────────────────────────────────
  function toggleFullscreen() {
    const panel = qs('#ggPanel');
    if (!panel) return;
    if (!document.fullscreenElement) {
      panel.requestFullscreen?.().then(()=>panel.classList.add('fullscreen')).catch(()=>panel.classList.toggle('fullscreen'));
    } else {
      document.exitFullscreen?.();
      panel.classList.remove('fullscreen');
    }
  }
  document.addEventListener('fullscreenchange', () => {
    const panel = qs('#ggPanel');
    if (panel) panel.classList.toggle('fullscreen', !!document.fullscreenElement);
  });

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
      fetch('/api/achievements/unlock-game', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: 'secret_garden' }),
      }).catch(()=>{});
    }
    renderStats();
    renderShop();
    renderBoss();
    if (g.bossesKilled > 0) qs('#ggKillCount').textContent = `Pests defeated: ${g.bossesKilled}`;
    startLoop();
  }

  function close() {
    if (overlay) overlay.style.display = 'none';
    if (document.fullscreenElement) document.exitFullscreen?.();
    stopLoop();
  }

  // ── CLICK ACTIONS ──────────────────────────────────────────
  function onBigClick(e) {
    const gain = perClick();
    g.sundrops += gain;
    g.lifetime += gain;
    g.totalClicks++;
    save();
    renderStats();
    renderShop();
    const plant = qs('#ggBigPlant');
    plant.classList.add('clicked');
    setTimeout(()=>plant.classList.remove('clicked'), 80);
    spawnFloat('+'+fmt(gain)+' ☀️', e.clientX, e.clientY, false);
  }

  function onBossClick(e) {
    if (!boss) return;
    e.stopPropagation();
    damageBoss();
    spawnFloat('-1 HP', e.clientX, e.clientY, true);
  }

  function spawnFloat(text, x, y, dmg) {
    const el = document.createElement('div');
    el.className = 'gg-float' + (dmg ? ' dmg' : '');
    el.textContent = text;
    el.style.cssText = `left:${x-30}px;top:${y-10}px`;
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

  // ── PUBLIC ─────────────────────────────────────────────────
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

  try { if (localStorage.getItem(SAVE_KEY)) everOpened = true; } catch(_) {}

  return { tick, open };
})();
