function connectSSE() {
  // Mode intégration HACS : le temps réel est relayé par le panel parent
  // via postMessage (événements state_changed HA). Pas de SSE ni de fetch
  // streaming — EventSource ne peut pas porter de Bearer token.
  window._sseFailed = false;
  window._sseStopped = false;
  sseConnected = true;  // le relay du panel est le canal temps réel
  updateSSEIndicator();
  document.getElementById('statusbar').textContent = t('sse.reconnect');
  // Enregistre les entités suivies (le panel filtre côté iframe)
  const ids = sensors.map(s => s.cfg.entity);
  for (const s of sensors) { if (s.cfg.sum_with) ids.push(s.cfg.sum_with); }
  for (const d of (layout.doors || [])) { if (d.entity) ids.push(d.entity); }
  setTrackedEntities(ids);
}
