/* Rampage RGB – web UI */
'use strict';

const RANDOM = 7;
const SPEED_LABELS = ['Çok yavaş', 'Yavaş', 'Normal', 'Hızlı', 'Çok hızlı'];
const BRIGHT_LABELS = ['Kapalı', '%25', '%50', '%75', '%100'];
const MODE_SWATCH = {
  1: 'linear-gradient(135deg,#ff2e63,#ffb02e,#2fd27f,#2ea8ff)', 2: 'radial-gradient(#2ea8ff, #0b2a40)', 3: '#ff2e63',
  4: 'repeating-radial-gradient(circle,#2ea8ff 0 3px,#0b1a2a 3px 7px)', 5: 'radial-gradient(circle,#ffb02e 0 30%,#2a1a0b 60%)',
  6: 'radial-gradient(circle,#fff 0 15%,#ff2e63 40%,#2a0b14)', 7: 'repeating-linear-gradient(90deg,#2ea8ff 0 4px,#0b1a2a 4px 9px)',
  8: 'linear-gradient(#0b2a40,#2ea8ff)', 9: 'linear-gradient(90deg,#ff2e63,#ffb02e,#2fd27f,#2ea8ff,#a62eff)',
  10: 'conic-gradient(#ff2e63,#ffb02e,#2fd27f,#2ea8ff,#a62eff,#ff2e63)', 11: 'repeating-linear-gradient(45deg,#a62eff 0 5px,#ff2ed1 5px 10px,#2ee6ff 10px 15px)',
  12: 'radial-gradient(circle at 30% 30%,#fff 0 8%,transparent 12%),radial-gradient(circle at 70% 65%,#ffe680 0 8%,transparent 12%),#141a2b',
  13: 'linear-gradient(135deg,#a62eff,#1a0b2a)', 14: 'linear-gradient(90deg,#14301f 0 30%,#2fd27f 30% 70%,#14301f 70%)',
};

const ui = {
  modes: [],
  defaultPalette: [],
  status: null,
  mode: 3,                // selected mode in the UI
  settings: {},           // per-mode {speed, brightness, color, direction_left, palette}
  powerOn: true,
  editingPreset: 0,
  dirtyPalette: {},       // {presetIndex: '#hex'} not yet sent
  lastLocalChange: 0,
  inflight: 0,
  profiles: [],
  keys: [],               // {el, code, x, y, cx, cy}
  presses: [],
};

const $ = (id) => document.getElementById(id);

/* ---------------- API ---------------- */
async function api(method, url, body) {
  try {
    const res = await fetch(url, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok && data.success === undefined) data.success = false;
    return data;
  } catch (e) {
    return { success: false, error: 'Sunucuya ulaşılamıyor. Uygulama kapalı olabilir.', offline: true };
  }
}

function toast(msg, isErr = false) {
  const el = document.createElement('div');
  el.className = 'toast' + (isErr ? ' err' : '');
  el.textContent = msg;
  $('toasts').appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transform = 'translateY(6px)'; }, isErr ? 6000 : 2600);
  setTimeout(() => el.remove(), isErr ? 6300 : 2900);
}

/* ---------------- Status ---------------- */
function applyStatus(st, { force = false } = {}) {
  if (!st) return;
  ui.status = st;
  renderConnection(st);

  const s = st.state || {};
  const userBusy = ui.inflight > 0 || Date.now() - ui.lastLocalChange < 2500;
  if (s.modes) {
    for (const [mid, cfg] of Object.entries(s.modes)) {
      if (!userBusy || force || !ui.settings[mid]) ui.settings[mid] = { ...cfg };
    }
  }
  if (!userBusy || force) {
    ui.perKey = Boolean(s.per_key);
    ui.perKeyTitle = s.mode_title;
    ui.customPreset = s.custom_preset;
    ui.powerOn = s.mode !== 0;
    if (s.mode && !s.per_key) ui.mode = s.mode;
    else if (st.last_on_mode) ui.mode = st.last_on_mode;
    renderAll();
  }
}

function renderConnection(st) {
  const pill = $('status-pill');
  const banner = $('banner');
  if (st.connected) {
    pill.className = 'pill pill-ok';
    $('status-text').textContent = 'Klavye bağlı';
    banner.hidden = true;
  } else {
    const perm = st.error_code === 'permission';
    pill.className = 'pill ' + (perm ? 'pill-err' : 'pill-wait');
    $('status-text').textContent = perm ? 'İzin gerekli' : (st.found ? 'Bağlanılamadı' : 'Klavye aranıyor…');
    banner.hidden = false;
    banner.classList.toggle('err', perm);
    $('banner-title').textContent = perm ? 'macOS erişim izni gerekiyor' : 'Klavyeye ulaşılamıyor';
    $('banner-text').textContent = st.error || 'Klavyeyi USB ile takın.';
  }
  const note = $('sync-note');
  if (!st.connected) note.textContent = '';
  else if (st.readback) note.textContent = 'Klavyeyle eşzamanlı';
  else note.textContent = 'Klavye durumu okunamıyor — son gönderilen ayar';
}

async function pollStatus() {
  if (document.hidden) return;
  const st = await api('GET', '/api/device/status');
  if (st.offline) {
    $('status-pill').className = 'pill pill-err';
    $('status-text').textContent = 'Sunucu kapalı';
    return;
  }
  applyStatus(st);
}

/* ---------------- Apply ---------------- */
let applyTimer = null;
function scheduleApply(delay = 120) {
  ui.lastLocalChange = Date.now();
  clearTimeout(applyTimer);
  applyTimer = setTimeout(applyNow, delay);
}

async function applyNow() {
  const mid = ui.mode;
  const s = cur();
  const body = {
    mode: mid,
    speed: s.speed,
    brightness: s.brightness,
    color: s.color,
    direction_left: s.direction_left,
  };
  if (Object.keys(ui.dirtyPalette).length) body.palette = { ...ui.dirtyPalette };
  ui.dirtyPalette = {};
  await send('/api/device/apply', body);
}

async function send(url, body) {
  ui.inflight++;
  setApplyState('busy', 'Gönderiliyor…');
  const res = await api('POST', url, body);
  ui.inflight--;
  ui.lastLocalChange = Date.now();
  if (res.success) {
    if (res.verified === true) setApplyState('ok', '✓ Klavyeye uygulandı');
    else if (res.verified === false) setApplyState('err', 'Gönderildi, doğrulanamadı');
    else setApplyState('ok', '✓ Gönderildi');
    if (res.status) renderConnection(res.status);
  } else {
    setApplyState('err', 'Uygulanamadı');
    toast(res.error || 'Klavyeye gönderilemedi.', true);
    if (res.status) renderConnection(res.status);
  }
  return res;
}

let applyStateTimer = null;
function setApplyState(kind, text) {
  const el = $('apply-state');
  el.className = 'apply-state ' + kind;
  el.textContent = text;
  clearTimeout(applyStateTimer);
  if (kind !== 'busy') applyStateTimer = setTimeout(() => { el.textContent = ''; }, 3500);
}

/* ---------------- Helpers ---------------- */
function modeInfo(id) { return ui.modes.find((m) => m.id === id) || ui.modes[0]; }
function cur() {
  if (!ui.settings[ui.mode]) {
    ui.settings[ui.mode] = { speed: 2, brightness: 4, color: RANDOM, direction_left: false, palette: [...ui.defaultPalette] };
  }
  const s = ui.settings[ui.mode];
  if (!s.palette) s.palette = [...ui.defaultPalette];
  return s;
}

/* ---------------- Rendering ---------------- */
function renderAll() {
  renderModes();
  renderCustom();
  renderSettings();
  renderPower();
}

function renderPower() {
  const b = $('btn-power');
  b.setAttribute('aria-pressed', String(ui.powerOn));
  $('power-label').textContent = ui.powerOn ? 'Açık' : 'Kapalı';
  let title = ui.powerOn ? `Önizleme · ${modeInfo(ui.mode).title}` : 'Önizleme · Işıklar kapalı';
  if (ui.perKey && ui.powerOn) title = `Önizleme · ${ui.perKeyTitle} (klavyede kayıtlı tuş renkleri)`;
  $('preview-title').textContent = title;
}

function renderCustom() {
  const box = $('custom-profiles');
  if (!box.childElementCount) {
    for (let i = 1; i <= (ui.customCount || 5); i++) {
      const b = document.createElement('button');
      b.setAttribute('role', 'radio');
      b.dataset.v = i;
      b.textContent = `CM${i}`;
      b.title = `Klavyede kayıtlı özel profil ${i} (Fn+${i})`;
      b.onclick = () => selectCustom(i);
      box.appendChild(b);
    }
  }
  box.querySelectorAll('button').forEach((b) => {
    b.setAttribute('aria-checked', String(ui.powerOn && ui.perKey && Number(b.dataset.v) === ui.customPreset));
  });
}

async function selectCustom(i) {
  clearTimeout(applyTimer);
  ui.perKey = true;
  ui.customPreset = i;
  ui.perKeyTitle = `Özel tuş profili ${i}`;
  ui.powerOn = true;
  ui.lastLocalChange = Date.now();
  renderAll();
  await send('/api/device/custom', { profile: i });
}

function renderModes() {
  const box = $('modes');
  if (!box.childElementCount) {
    ui.modes.filter((m) => m.id !== 0).forEach((m) => {
      const b = document.createElement('button');
      b.className = 'mode';
      b.setAttribute('role', 'radio');
      b.dataset.id = m.id;
      b.innerHTML = `<span class="ic"></span><span><span class="t"></span><span class="d"></span></span>`;
      b.querySelector('.ic').style.setProperty('--sw', MODE_SWATCH[m.id] || '#444');
      b.querySelector('.t').textContent = m.title;
      b.querySelector('.d').textContent = m.description;
      b.onclick = () => selectMode(m.id);
      box.appendChild(b);
    });
    $('mode-count').textContent = `${box.childElementCount} efekt`;
  }
  box.querySelectorAll('.mode').forEach((b) => {
    b.setAttribute('aria-checked', String(ui.powerOn && !ui.perKey && Number(b.dataset.id) === ui.mode));
  });
}

function buildSeg(id, labels, getter, setter) {
  const box = $(id);
  if (!box.childElementCount) {
    labels.forEach((label, v) => {
      const b = document.createElement('button');
      b.setAttribute('role', 'radio');
      b.dataset.v = v;
      b.textContent = label;
      box.appendChild(b);
    });
  }
  box.querySelectorAll('button').forEach((b) => {
    b.setAttribute('aria-checked', String(Number(b.dataset.v) === getter()));
    b.onclick = () => setter(Number(b.dataset.v));
  });
}

function renderSettings() {
  const m = modeInfo(ui.mode);
  const s = cur();
  $('settings-title').textContent = m.title;
  $('settings-desc').textContent = m.description + (m.reactive ? ' — tuşlara bastıkça çalışır.' : '');

  buildSeg('seg-brightness', ['0', '1', '2', '3', '4'], () => s.brightness, (v) => { s.brightness = v; changed(); });
  $('brightness-val').textContent = BRIGHT_LABELS[s.brightness];

  $('field-speed').hidden = !m.has_speed;
  buildSeg('seg-speed', ['1', '2', '3', '4', '5'], () => s.speed, (v) => { s.speed = v; changed(); });
  $('speed-val').textContent = SPEED_LABELS[s.speed];

  $('field-direction').hidden = !m.has_direction;
  $('seg-direction').querySelectorAll('button').forEach((b) => {
    b.setAttribute('aria-checked', String(Boolean(Number(b.dataset.v)) === Boolean(s.direction_left)));
    b.onclick = () => { s.direction_left = Boolean(Number(b.dataset.v)); changed(); };
  });

  $('field-color').hidden = !m.has_color;
  $('no-color-note').hidden = m.has_color;
  renderSwatches();
}

function renderSwatches() {
  const s = cur();
  const box = $('swatches');
  box.innerHTML = '';
  const rnd = document.createElement('button');
  rnd.className = 'sw sw-random';
  rnd.textContent = 'Renkli';
  rnd.title = 'Renkli / rastgele';
  rnd.setAttribute('role', 'radio');
  rnd.setAttribute('aria-checked', String(s.color === RANDOM));
  rnd.onclick = () => { s.color = RANDOM; changed(); };
  box.appendChild(rnd);

  s.palette.forEach((hex, i) => {
    const b = document.createElement('button');
    b.className = 'sw';
    b.style.setProperty('--c', hex);
    b.title = `Renk ${i + 1}: ${hex}`;
    b.setAttribute('role', 'radio');
    b.setAttribute('aria-label', `Renk ${i + 1}`);
    b.setAttribute('aria-checked', String(s.color === i));
    b.onclick = () => { s.color = i; ui.editingPreset = i; changed(); };
    box.appendChild(b);
  });

  const editing = s.color !== RANDOM;
  $('color-edit').hidden = !editing;
  if (editing) {
    ui.editingPreset = s.color;
    const hex = s.palette[s.color].toLowerCase();
    $('color-input').value = hex;
    if (document.activeElement !== $('color-hex')) $('color-hex').value = hex.toUpperCase();
  }
  $('color-val').textContent = editing ? `Renk ${s.color + 1}` : 'Renkli';
}

function changed() {
  ui.powerOn = true;
  ui.perKey = false;
  renderAll();
  scheduleApply();
}

function selectMode(id) {
  ui.mode = id;
  ui.dirtyPalette = {};
  changed();
}

function setPresetColor(hex, commit) {
  const s = cur();
  const i = ui.editingPreset;
  s.palette[i] = hex.toUpperCase();
  const sw = $('swatches').children[i + 1];
  if (sw) sw.style.setProperty('--c', hex);
  if (commit) {
    ui.dirtyPalette[i] = s.palette[i];
    changed();
  } else {
    ui.lastLocalChange = Date.now();
  }
}

/* ---------------- Profiles ---------------- */
function profileSwatch(p) {
  const pal = p.palette ? (Array.isArray(p.palette) ? p.palette : Object.values(p.palette)) : [];
  if (p.color !== RANDOM && p.color != null && pal.length) return pal[0];
  return null;
}

function renderProfiles() {
  const list = $('profiles');
  list.innerHTML = '';
  if (!ui.profiles.length) {
    list.innerHTML = '<li class="muted small">Henüz profil yok.</li>';
    return;
  }
  ui.profiles.forEach((p) => {
    const li = document.createElement('li');
    li.className = 'profile';
    const sw = profileSwatch(p);
    const mid = ui.modes.find((m) => m.name === p.mode);
    li.innerHTML = `<span class="dot"></span><button class="name" style="text-align:left;background:none;border:0"></button>
      <span class="meta"></span>`;
    li.querySelector('.dot').style.background = sw || 'conic-gradient(#ff2e63,#2fd27f,#2ea8ff,#ff2e63)';
    li.querySelector('.name').textContent = p.name;
    li.querySelector('.name').title = 'Uygula';
    li.querySelector('.meta').textContent = mid ? mid.title : p.mode;
    li.querySelector('.name').onclick = () => applyProfile(p);

    const apply = document.createElement('button');
    apply.className = 'btn btn-ghost';
    apply.textContent = 'Uygula';
    apply.onclick = () => applyProfile(p);
    li.appendChild(apply);

    if (!p.is_default) {
      const del = document.createElement('button');
      del.className = 'icon-btn';
      del.title = 'Sil';
      del.setAttribute('aria-label', `${p.name} profilini sil`);
      del.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>';
      del.onclick = async () => {
        if (!confirm(`“${p.name}” silinsin mi?`)) return;
        const res = await api('DELETE', `/api/profiles?id=${encodeURIComponent(p.id)}`);
        if (res.success) { ui.profiles = res.profiles; renderProfiles(); }
      };
      li.appendChild(del);
    }
    list.appendChild(li);
  });
}

async function applyProfile(p) {
  clearTimeout(applyTimer);
  const res = await send('/api/profiles/apply', { id: p.id });
  if (res.success) {
    toast(`Profil uygulandı: ${p.name}`);
    const st = await api('GET', '/api/device/status');
    if (!st.offline) {
      // Without readback the server can only echo what was sent; trust it here.
      applyStatus(st, { force: true });
    }
  }
}

async function saveProfile(e) {
  e.preventDefault();
  const name = $('profile-name').value.trim();
  if (!name) { $('profile-name').focus(); return; }
  const s = cur();
  const res = await api('POST', '/api/profiles', {
    name,
    mode: ui.mode,
    speed: s.speed,
    brightness: s.brightness,
    color: s.color,
    direction_left: s.direction_left,
    palette: s.color === RANDOM ? null : { [s.color]: s.palette[s.color] },
  });
  if (res.success) {
    ui.profiles = res.profiles;
    $('profile-name').value = '';
    renderProfiles();
    toast(`“${name}” kaydedildi`);
  } else {
    toast(res.error || 'Kaydedilemedi', true);
  }
}

/* ---------------- Keyboard preview ---------------- */
function buildKeyboard(rows) {
  const kb = $('kb');
  kb.innerHTML = '';
  ui.keys = [];
  let maxX = 0;
  rows.forEach((row, r) => {
    let x = 0;
    const y = r + (r > 0 ? 0.35 : 0);
    row.forEach((k) => {
      const w = k.w || 1;
      const h = k.h || 1;
      if (k.type !== 'spacer') {
        const el = document.createElement('div');
        el.className = 'key';
        el.style.left = `calc(var(--u) * ${x + 0.3} + 2px)`;
        el.style.top = `calc(var(--u) * ${y + 0.3} + 2px)`;
        el.style.width = `calc(var(--u) * ${w} - 4px)`;
        el.style.height = `calc(var(--u) * ${h} - 4px)`;
        el.textContent = k.label || '';
        if (k.sub) {
          const sub = document.createElement('span');
          sub.className = 'sub';
          sub.textContent = k.sub;
          el.prepend(sub);
        }
        const key = { el, code: k.code, x, y, cx: x + w / 2, cy: y + h / 2 };
        el.onpointerdown = () => press(key);
        ui.keys.push(key);
        kb.appendChild(el);
      }
      x += w;
    });
    maxX = Math.max(maxX, x);
  });
  ui.kbW = maxX;
  ui.kbH = rows.length + 0.35;
  ui.keys.forEach((k) => { k.nx = k.cx / maxX; k.ny = k.cy / ui.kbH; });
  // Serpentine order for the snake effect
  const sorted = [...ui.keys].sort((a, b) => (a.y - b.y) || (a.x - b.x));
  const byRow = {};
  sorted.forEach((k) => (byRow[k.y] = byRow[k.y] || []).push(k));
  let order = 0;
  Object.keys(byRow).sort((a, b) => a - b).forEach((ry, i) => {
    const arr = i % 2 ? byRow[ry].slice().reverse() : byRow[ry];
    arr.forEach((k) => { k.order = order++; });
  });
  kb.style.width = `calc(var(--u) * ${maxX + 0.6})`;
  kb.style.height = `calc(var(--u) * ${ui.kbH + 0.6})`;
  fitKeyboard();
}

function fitKeyboard() {
  const avail = $('kb-wrap').clientWidth;
  const u = Math.max(14, Math.min(46, (avail - 4) / (ui.kbW + 0.6)));
  $('kb').style.setProperty('--u', `${u}px`);
}

function press(key) {
  ui.presses.push({ k: key, t: performance.now() / 1000 });
  if (ui.presses.length > 24) ui.presses.shift();
  key.el.classList.add('pressed');
  setTimeout(() => key.el.classList.remove('pressed'), 120);
}

function hexRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
function hsl(h) {
  h = ((h % 360) + 360) % 360 / 60;
  const x = 1 - Math.abs((h % 2) - 1);
  const [r, g, b] = h < 1 ? [1, x, 0] : h < 2 ? [x, 1, 0] : h < 3 ? [0, 1, x] : h < 4 ? [0, x, 1] : h < 5 ? [x, 0, 1] : [1, 0, x];
  return [r * 255, g * 255, b * 255];
}
function hash(n) { const s = Math.sin(n * 127.1) * 43758.5453; return s - Math.floor(s); }

const REACTIVE = new Set([4, 5, 6, 13]);

function effect(mode, k, t, ctx) {
  const { s, base, dir, now } = ctx;
  const random = s.color === RANDOM;
  const pick = (h) => (random ? hsl(h) : base);
  const dx = k.nx - 0.5, dy = (k.ny - 0.5) * 0.45;
  const ang = Math.atan2(dy, dx) * 180 / Math.PI;
  switch (mode) {
    case 1: return [hsl(t * 40), 1];                                   // colour cycle
    case 2: { const ph = t * 1.6; return [pick(Math.floor(ph / (2 * Math.PI)) * 70), (Math.sin(ph - Math.PI / 2) + 1) / 2]; }
    case 3: return [pick(k.x * 17 + k.y * 40), 1];                     // static
    case 7: return [pick(k.nx * 200 + t * 30), (Math.sin(k.nx * 12 - t * 3) + 1) / 2];
    case 8: { const col = Math.round(k.x); const pos = ((t * 0.55 + hash(col)) % 1); const d = (k.ny - pos); return [pick(hash(col + 3) * 360), d < 0 && d > -0.35 ? 1 + d / 0.35 : 0]; }
    case 9: return [hsl(k.nx * 360 - t * 90 * dir), 1];                // rainbow wave
    case 10: return [hsl(ang - t * 90 * dir), 1];                      // rainbow wheel
    case 11: return [hsl(t * 30 + k.order * 9), 0.55 + 0.45 * Math.sin(t * 2 + k.order)];
    case 12: { const v = Math.max(0, Math.sin(t * 1.3 + hash(k.order) * 40)); return [pick(hash(k.order + 9) * 360), v ** 6]; }
    case 14: { const n = ui.keys.length; const head = (t * 14) % n; const d = ((head - k.order) % n + n) % n; return [pick(k.order * 6), d < 10 ? 1 - d / 10 : 0]; }
    default: {
      // reactive effects: 4 ripples, 5 reaction, 6 flash away, 13 shadow
      let a = mode === 13 ? 1 : 0;
      let col = pick(k.order * 5);
      for (const p of ctx.presses) {
        const age = now - p.t;
        const d = Math.hypot(k.cx - p.k.cx, (k.cy - p.k.cy) * 1.1);
        if (mode === 5 && p.k === k) a = Math.max(a, 1 - age / 1.2);
        if (mode === 13 && p.k === k) a = Math.min(a, age / 1.6);
        if (mode === 6) { const ring = age * 9; a = Math.max(a, Math.max(0, 1 - Math.abs(d - ring) / 1.6) * Math.max(0, 1 - age / 1.6)); }
        if (mode === 4) { const ring = age * 7; const v = Math.max(0, 1 - Math.abs(d - ring) / 0.9) * Math.max(0, 1 - age / 2.2); if (v > a) { a = v; if (random) col = hsl(p.t * 97); } }
      }
      return [col, Math.max(0, Math.min(1, a))];
    }
  }
}

function startPreview() {
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let simT = 0;
  let last = performance.now();
  let lastDemo = 0;

  function frame(nowMs) {
    const dt = Math.min(0.1, (nowMs - last) / 1000);
    last = nowMs;
    const now = nowMs / 1000;
    const m = ui.mode;
    const s = cur();
    const info = modeInfo(m);
    simT += dt * (info.has_speed ? 0.35 + s.speed * 0.4 : 1) * (reduced ? 0.3 : 1);

    // Demo presses so reactive effects show something when idle
    if (ui.powerOn && REACTIVE.has(m) && now - lastDemo > 1.4 && ui.keys.length) {
      const lastPress = ui.presses[ui.presses.length - 1];
      if (!lastPress || now - lastPress.t > 2.5) press(ui.keys[Math.floor(Math.random() * ui.keys.length)]);
      lastDemo = now;
    }
    ui.presses = ui.presses.filter((p) => now - p.t < 3);

    const level = ui.powerOn ? s.brightness / 4 : 0;
    const ctx = {
      s, now, presses: ui.presses,
      dir: s.direction_left ? -1 : 1,
      base: hexRgb(s.color === RANDOM ? '#ffffff' : s.palette[s.color] || '#ffffff'),
    };
    for (const k of ui.keys) {
      let col = [0, 0, 0], a = 0;
      if (level > 0) [col, a] = effect(m, k, simT, ctx);
      k.el.style.setProperty('--led', `${col[0] | 0}, ${col[1] | 0}, ${col[2] | 0}`);
      k.el.style.setProperty('--a', (a * (0.25 + 0.75 * level)).toFixed(3));
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

/* ---------------- Events ---------------- */
function setupEvents() {
  $('btn-power').onclick = async () => {
    clearTimeout(applyTimer);
    ui.powerOn = !ui.powerOn;
    ui.lastLocalChange = Date.now();
    renderAll();
    const res = await send(ui.powerOn ? '/api/device/on' : '/api/device/off');
    if (!res.success) { ui.powerOn = !ui.powerOn; renderAll(); }
  };

  $('btn-quit').onclick = async () => {
    if (!confirm('Uygulama kapatılsın mı? Klavye son ayarında kalır.')) return;
    const res = await api('POST', '/api/server/shutdown');
    if (res.success) $('quit-overlay').hidden = false;
  };

  $('btn-retry').onclick = async () => {
    $('btn-retry').disabled = true;
    const res = await api('POST', '/api/device/reconnect');
    $('btn-retry').disabled = false;
    if (res.status) applyStatus(res.status, { force: true });
    if (res.success) toast('Klavyeye bağlanıldı');
    else toast(res.error || 'Bağlanılamadı', true);
  };

  $('color-input').addEventListener('input', (e) => {
    setPresetColor(e.target.value, false);
    $('color-hex').value = e.target.value.toUpperCase();
  });
  $('color-input').addEventListener('change', (e) => setPresetColor(e.target.value, true));
  $('color-hex').addEventListener('change', (e) => {
    let v = e.target.value.trim();
    if (!v.startsWith('#')) v = '#' + v;
    if (/^#[0-9a-fA-F]{6}$/.test(v)) setPresetColor(v, true);
    else { toast('Renk kodu #RRGGBB biçiminde olmalı', true); renderSwatches(); }
  });

  $('save-form').addEventListener('submit', saveProfile);


  // Physical key presses light up the preview (reactive effects)
  const byCode = () => Object.fromEntries(ui.keys.map((k) => [k.code, k]));
  let map = null;
  window.addEventListener('keydown', (e) => {
    if (e.target.matches('input')) return;
    map = map || byCode();
    const k = map[e.code];
    if (k) press(k);
  });

  window.addEventListener('resize', fitKeyboard);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) pollStatus(); });
}

/* ---------------- Init ---------------- */
async function init() {
  const [modes, layout, status, profiles] = await Promise.all([
    api('GET', '/api/device/modes'),
    api('GET', '/api/device/layout'),
    api('GET', '/api/device/status'),
    api('GET', '/api/profiles'),
  ]);
  if (!Array.isArray(modes.modes) || !Array.isArray(layout.rows) || status.offline) {
    $('status-text').textContent = 'Sunucuya bağlanılıyor…';
    $('status-pill').className = 'pill pill-wait';
    setTimeout(init, 1500);
    return;
  }
  ui.modes = modes.modes;
  ui.defaultPalette = modes.default_palette;
  ui.customCount = modes.custom_profiles;
  ui.profiles = Array.isArray(profiles) ? profiles : [];

  setupEvents();
  buildKeyboard(layout.rows || []);
  applyStatus(status, { force: true });
  renderAll();
  renderProfiles();
  startPreview();
  setInterval(pollStatus, 3000);
}

document.addEventListener('DOMContentLoaded', init);
