/**
 * Rampage RGB Keyboard Controller - Web App Logic
 */

// Application State
const state = {
  connected: false,
  deviceInfo: null,
  activeMode: 1,
  brightness: 4,
  speed: 3,
  powerOn: true,
  layout: null,
  groups: {},
  modes: [],
  profiles: [],
  selectedKeys: new Set(),
  activeGroup: 'all',
  animFrameId: null
};

// Mode Icons
const MODE_ICONS = {
  off: '⏻',
  rainbow: '🌈',
  static: '🔴',
  snake: '🐍'
};

// API Helpers
async function apiGet(endpoint) {
  try {
    const res = await fetch(endpoint);
    return await res.json();
  } catch (err) {
    console.error(`GET ${endpoint} failed:`, err);
    return null;
  }
}

async function apiPost(endpoint, data = {}) {
  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await res.json();
  } catch (err) {
    console.error(`POST ${endpoint} failed:`, err);
    return null;
  }
}

// Toast Notifications
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 200);
  }, 3000);
}

// Initialize Application
async function initApp() {
  console.log('Initializing Rampage RGB Controller UI...');
  
  // 1. Fetch initial definitions in parallel
  const [layoutData, modesData, statusData, profilesData] = await Promise.all([
    apiGet('/api/device/layout'),
    apiGet('/api/device/modes'),
    apiGet('/api/device/status'),
    apiGet('/api/profiles')
  ]);

  if (layoutData) {
    state.layout = layoutData.rows;
    state.groups = layoutData.groups;
  }
  if (modesData) state.modes = modesData;
  if (profilesData) state.profiles = profilesData;

  if (statusData) {
    updateDeviceStatus(statusData);
  }

  // 2. Render UI components
  renderGroupButtons();
  renderKeyboard();
  renderModesList();
  renderProfilesList();
  setupEventListeners();

  // 3. Start Keyboard Glow Animation Loop
  startKeyboardAnimation();

  // 4. Background polling for device status
  setInterval(checkStatus, 3000);
}

// Update Status Badge
function updateDeviceStatus(statusData) {
  state.connected = statusData.connected;
  state.deviceInfo = statusData.device;
  
  const badge = document.getElementById('device-status-badge');
  const text = document.getElementById('status-text');
  
  if (state.connected) {
    badge.className = 'status-pill status-connected';
    text.textContent = 'Bağlı • ' + (statusData.device.name || 'Rampage RGB');
  } else {
    badge.className = 'status-pill status-disconnected';
    text.textContent = 'Klavye Aranıyor...';
  }

  if (statusData.state) {
    const s = statusData.state;
    state.activeMode = s.mode;
    state.speed = s.speed;
    state.brightness = s.brightness;
    
    // Sync slider controls
    document.getElementById('slider-brightness').value = state.brightness;
    document.getElementById('brightness-val-text').textContent = `%${state.brightness * 25} (${state.brightness}/4)`;
    
    document.getElementById('slider-speed').value = state.speed;
    const speedLabels = ['Çok Yavaş', 'Yavaş', 'Normal', 'Hızlı', 'Çok Hızlı'];
    document.getElementById('speed-val-text').textContent = `${speedLabels[state.speed]} (${state.speed}/4)`;
  }
}

async function checkStatus() {
  const statusData = await apiGet('/api/device/status');
  if (statusData) {
    updateDeviceStatus(statusData);
  }
}

// Render Quick Selection Group Chips
function renderGroupButtons() {
  const container = document.getElementById('group-buttons-container');
  container.innerHTML = '';

  const groupKeys = Object.keys(state.groups);
  groupKeys.forEach(gKey => {
    const grp = state.groups[gKey];
    const btn = document.createElement('button');
    btn.className = `chip-btn ${state.activeGroup === gKey ? 'active' : ''}`;
    btn.textContent = grp.title.split(' (')[0];
    btn.onclick = () => selectGroup(gKey);
    container.appendChild(btn);
  });
}

function selectGroup(groupKey) {
  state.activeGroup = groupKey;
  state.selectedKeys.clear();

  if (state.groups[groupKey]) {
    state.groups[groupKey].keys.forEach(k => state.selectedKeys.add(k));
  }

  document.querySelectorAll('.chip-btn').forEach(btn => {
    btn.classList.toggle('active', btn.textContent === state.groups[groupKey].title.split(' (')[0]);
  });

  document.querySelectorAll('.key-cap').forEach(el => {
    const code = el.dataset.code;
    el.classList.toggle('key-selected', state.selectedKeys.has(code));
  });

  const countEl = document.getElementById('selection-count');
  countEl.textContent = `${state.selectedKeys.size} tuş seçildi (${state.groups[groupKey].title})`;
}

// Render Interactive Turkish Q Keyboard
function renderKeyboard() {
  const chassis = document.getElementById('keyboard-chassis');
  chassis.innerHTML = '';

  if (!state.layout) return;

  const baseUnit = 48; // px for 1.0 width

  state.layout.forEach(row => {
    const rowEl = document.createElement('div');
    rowEl.className = 'kb-row';

    row.forEach(key => {
      const keyEl = document.createElement('div');
      keyEl.className = `key-cap type-${key.type || 'alpha'}`;
      keyEl.dataset.code = key.code;

      const width = (key.w || 1.0) * baseUnit + ((key.w || 1.0) - 1) * 6;
      keyEl.style.width = `${width}px`;

      if (key.h && key.h > 1.0) {
        keyEl.style.height = `${key.h * baseUnit + (key.h - 1) * 6}px`;
      }

      if (key.type !== 'spacer') {
        const legend = document.createElement('span');
        legend.className = 'key-legend';
        legend.textContent = key.label || '';
        keyEl.appendChild(legend);

        if (key.sub) {
          const sub = document.createElement('span');
          sub.className = 'key-sublegend';
          sub.textContent = key.sub;
          keyEl.appendChild(sub);
        }

        keyEl.onclick = () => {
          state.selectedKeys.clear();
          state.selectedKeys.add(key.code);
          state.activeGroup = 'custom';
          document.querySelectorAll('.chip-btn').forEach(b => b.classList.remove('active'));
          
          document.querySelectorAll('.key-cap').forEach(el => {
            el.classList.toggle('key-selected', state.selectedKeys.has(el.dataset.code));
          });
          document.getElementById('selection-count').textContent = `${state.selectedKeys.size} tuş seçildi (${key.label})`;
        };
      }

      rowEl.appendChild(keyEl);
    });

    chassis.appendChild(rowEl);
  });

  selectGroup('all');
}

// Render Lighting Modes Cards
function renderModesList() {
  const container = document.getElementById('modes-list-container');
  container.innerHTML = '';

  // Filter modes: 1 (rainbow), 2 (static red), 3 (snake), 0 (off)
  const displayModes = state.modes.filter(m => [1, 2, 3, 0].includes(m.id));

  displayModes.forEach(mode => {
    const item = document.createElement('div');
    item.className = `mode-item ${state.activeMode === mode.id ? 'active' : ''}`;
    item.dataset.modeId = mode.id;

    const icon = MODE_ICONS[mode.name] || '💡';
    
    let badgesHtml = '';
    if (mode.has_speed) badgesHtml += '<span class="meta-badge">Hız Ayarlı</span>';
    if (mode.has_brightness) badgesHtml += '<span class="meta-badge">Parlaklık Ayarlı</span>';

    item.innerHTML = `
      <div class="mode-icon">${icon}</div>
      <div class="mode-info">
        <div class="mode-title">${mode.title}</div>
        <div class="mode-meta">${badgesHtml}</div>
      </div>
    `;

    item.onclick = () => selectMode(mode.id);
    container.appendChild(item);
  });

  document.getElementById('mode-count').textContent = `${displayModes.length} Mod`;
}

// Select & Apply a Mode
async function selectMode(modeId) {
  state.activeMode = modeId;
  state.powerOn = (modeId !== 0);
  
  document.querySelectorAll('.mode-item').forEach(el => {
    el.classList.toggle('active', parseInt(el.dataset.modeId) === modeId);
  });

  const speedGroup = document.getElementById('speed-param-group');
  if (speedGroup) {
    speedGroup.style.display = (modeId === 1 || modeId === 3) ? 'flex' : 'none';
  }

  // Send API command to device
  const res = await apiPost('/api/device/mode', {
    mode: modeId,
    speed: state.speed,
    brightness: state.brightness
  });

  if (res && res.success) {
    const modeObj = state.modes.find(m => m.id === modeId);
    showToast(`Uygulandı: ${modeObj ? modeObj.title.split(' (')[0] : modeId}`);
  }
}

// Render Saved Profiles
function renderProfilesList() {
  const container = document.getElementById('profiles-list-container');
  container.innerHTML = '';

  state.profiles.forEach(p => {
    const card = document.createElement('div');
    card.className = 'profile-card';

    const colorDot = p.color ? `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${p.color};margin-right:6px;"></span>` : '';

    card.innerHTML = `
      <div class="profile-info">
        <div class="profile-name">${colorDot}${p.name}</div>
        <div class="profile-desc">${p.description || p.mode}</div>
      </div>
      <div class="profile-actions">
        <button class="btn btn-secondary btn-sm btn-apply-profile">Uygula</button>
      </div>
    `;

    card.querySelector('.btn-apply-profile').onclick = async () => {
      const res = await apiPost('/api/profiles/apply', { id: p.id });
      if (res && res.success) {
        document.querySelectorAll('.profile-card').forEach(c => c.classList.remove('active-profile'));
        card.classList.add('active-profile');
        showToast(`Profil uygulandı: ${p.name}`);
        if (res.state) {
          updateDeviceStatus({ connected: true, device: state.deviceInfo, state: res.state });
        }
      }
    };

    container.appendChild(card);
  });
}

// Event Listeners Setup
function setupEventListeners() {
  // Power Button
  const pwrBtn = document.getElementById('btn-power');
  pwrBtn.onclick = async () => {
    state.powerOn = !state.powerOn;
    if (!state.powerOn) {
      pwrBtn.classList.add('active-power');
      await apiPost('/api/device/off');
      selectMode(0);
      showToast('Klavye ışıkları kapatıldı (Off).');
    } else {
      pwrBtn.classList.remove('active-power');
      await selectMode(1);
      showToast('Klavye ışıkları açıldı (Gökkuşağı).');
    }
  };

  // Shutdown Application Button
  const shutdownBtn = document.getElementById('btn-shutdown-app');
  shutdownBtn.onclick = async () => {
    const confirmed = confirm("Uygulama kapatılacak. Klavyenizin mevcut aydınlatma ayarları korunacaktır. Çıkmak istiyor musunuz?");
    if (!confirmed) return;

    const res = await apiPost('/api/server/shutdown');
    if (res && res.success) {
      document.getElementById('shutdown-overlay').style.display = 'flex';
      showToast('Uygulama kapatıldı. Klavye ayarları korundu.');
    }
  };

  // Quick Action Buttons
  document.getElementById('btn-quick-rainbow').onclick = () => selectMode(1);
  document.getElementById('btn-quick-red').onclick = () => selectMode(2);
  document.getElementById('btn-quick-snake').onclick = () => selectMode(3);
  document.getElementById('btn-quick-off').onclick = () => selectMode(0);

  // Brightness Slider
  const bSlider = document.getElementById('slider-brightness');
  bSlider.oninput = (e) => {
    state.brightness = parseInt(e.target.value);
    document.getElementById('brightness-val-text').textContent = `%${state.brightness * 25} (${state.brightness}/4)`;
  };
  bSlider.onchange = async () => {
    await apiPost('/api/device/mode', {
      mode: state.activeMode,
      speed: state.speed,
      brightness: state.brightness
    });
  };

  // Speed Slider
  const sSlider = document.getElementById('slider-speed');
  sSlider.oninput = (e) => {
    state.speed = parseInt(e.target.value);
    const speedLabels = ['Çok Yavaş', 'Yavaş', 'Normal', 'Hızlı', 'Çok Hızlı'];
    document.getElementById('speed-val-text').textContent = `${speedLabels[state.speed]} (${state.speed}/4)`;
  };
  sSlider.onchange = async () => {
    await apiPost('/api/device/mode', {
      mode: state.activeMode,
      speed: state.speed,
      brightness: state.brightness
    });
  };
}

// Realtime Keyboard Backlight Visualizer Animation Loop
function startKeyboardAnimation() {
  let time = 0;

  function renderFrame() {
    time += 0.03 * (state.speed + 1);

    const keyElements = document.querySelectorAll('.key-cap:not(.type-spacer)');
    keyElements.forEach((keyEl, index) => {
      if (!state.powerOn || state.activeMode === 0) {
        keyEl.classList.remove('key-active-led');
        keyEl.style.removeProperty('--key-active-glow');
        return;
      }

      keyEl.classList.add('key-active-led');

      if (state.activeMode === 1) { // Rainbow wave
        const hue = (time * 20 + index * 4) % 360;
        keyEl.style.setProperty('--key-active-glow', `hsl(${hue}, 100%, 55%)`);
      } else if (state.activeMode === 2) { // Static Red
        keyEl.style.setProperty('--key-active-glow', '#FF0000');
      } else if (state.activeMode === 3) { // Snake
        const isSnake = Math.sin(time * 3 + index * 0.4) > 0.5;
        keyEl.style.setProperty('--key-active-glow', isSnake ? '#00FF00' : '#FF0055');
      } else {
        keyEl.style.setProperty('--key-active-glow', '#FF0000');
      }
    });

    state.animFrameId = requestAnimationFrame(renderFrame);
  }

  renderFrame();
}

document.addEventListener('DOMContentLoaded', initApp);
