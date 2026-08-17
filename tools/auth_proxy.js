// ============ CONFIG ============
// Mode intégration HACS : le PANEL parent sert de proxy API. Les fetch
// sont relayés par postMessage (le panel utilise hass.fetchWithAuth,
// auth native HA — aucun token à gérer côté iframe). Le temps réel passe
// par les événements state_changed relayés (remplace le SSE).
const _fetchWaiters = {};
let _fetchReqId = 0;

window.addEventListener('message', (evt) => {
  const d = evt.data;
  if (!d) return;
  if (d.type === 'ha3d-fetch-result') {
    const w = _fetchWaiters[d.id];
    if (w) {
      delete _fetchWaiters[d.id];
      w(d);
    }
  } else if (d.type === 'ha3d-state-changed') {
    // Événement temps réel relayé par le panel (remplace le SSE)
    if (typeof handleRelayedState === 'function') handleRelayedState(d);
  }
});

// Wrapper fetch : relaie la requête au panel parent via postMessage.
async function apiFetch(url, opts = {}) {
  return new Promise(resolve => {
    const id = ++_fetchReqId;
    _fetchWaiters[id] = (r) => {
      resolve({
        ok: r.ok,
        status: r.status || 0,
        json: () => Promise.resolve(r.data),
        text: () => Promise.resolve(JSON.stringify(r.data)),
      });
    };
    let body = null;
    if (opts.body) {
      try { body = JSON.parse(opts.body); } catch (e) { body = opts.body; }
    }
    try {
      window.parent.postMessage(
        { type: 'ha3d-fetch', id, url, method: opts.method || 'GET', body },
        '*'
      );
    } catch (e) {
      delete _fetchWaiters[id];
      resolve({ ok: false, status: 0, json: () => Promise.resolve({}), text: () => Promise.resolve('') });
    }
  });
}

// Liste des entités suivies (pour filtrer les événements state_changed).
let _trackedEntities = new Set();
function setTrackedEntities(ids) {
  _trackedEntities = new Set(ids);
}

// Handler des événements state_changed relayés par le panel (remplace SSE).
function handleRelayedState(msg) {
  // Course au démarrage : tant que le layout n'est pas chargé, on ignore les
  // événements relayés (le snapshot initial les couvrira).
  if (!layout || !sensors) return;
  if (!msg.entity || !_trackedEntities.has(msg.entity)) {
    // Les portes animées ont leur propre entité, suivie séparément
    if (!(msg.entity && doorAnims.some(a => a.entity === msg.entity)) &&
        !(garageDoorEntity() && msg.entity === garageDoorEntity())) {
      return;
    }
  }
  const s = sensors.find(x => x.cfg.entity === msg.entity);
  if (s) {
    s.st = { state: msg.state, unit: msg.unit, attrs: msg.attrs || {} };
    const entry = sensorMeshes.find(m => m.sensor === s);
    if (entry) drawSensorLabel(entry);
  }
  refreshSensorColors();
  if (garageDoorEntity() && msg.entity === garageDoorEntity()) updateGarageDoor(msg.state);
  if (doorAnims.some(a => a.entity === msg.entity)) doorStates[msg.entity] = msg.state;
  updateAlerts(sensors);
}
