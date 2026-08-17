function connectSSE() {
  window._sseFailed = false;
  window._sseStopped = false;
  // SSE via fetch streaming : EventSource ne permet pas d'envoyer un header
  // Authorization (exigé par l'API HA moderne).
  let reader = null;
  let buffer = '';
  const connect = async () => {
    if (window._sseStopped) return;
    try {
      const resp = await apiFetch('/api/ha3d/events');
      if (!resp.ok || !resp.body) throw new Error('SSE HTTP ' + resp.status);
      sseConnected = true;
      updateSSEIndicator();
      document.getElementById('statusbar').textContent = t('sse.reconnect');
      reader = resp.body.getReader();
      const dec = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += dec.decode(value, { stream: true });
        let idx;
        while ((idx = buffer.indexOf('\n\n')) >= 0) {
          const chunk = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          const line = chunk.split('\n').find(l => l.startsWith('data: '));
          if (!line) continue;
          try {
            const msg = JSON.parse(line.slice(6));
            if (msg.type === 'snapshot') {
              sseConnected = true;
              applyStatusData(msg);
            } else if (msg.type === 'update') {
              // Mise à jour d'une seule entité
              const s = sensors.find(x => x.cfg.entity === msg.entity);
              if (s) {
                s.st = { state: msg.state, unit: msg.unit, attrs: msg.attrs || {} };
                const entry = sensorMeshes.find(m => m.sensor === s);
                if (entry) drawSensorLabel(entry);
              }
              refreshSensorColors();  // icônes + lumières 3D en direct (pas d'attente du polling)
              // Porte garage si concernée (entité éditable dans le layout)
              if (garageDoorEntity() && msg.entity === garageDoorEntity()) updateGarageDoor(msg.state);
              // Porte animée (état on = ouverte)
              if (msg.entity && doorAnims.some(a => a.entity === msg.entity)) doorStates[msg.entity] = msg.state;
              updateAlerts(sensors);
            }
          } catch (e) { /* ignore */ }
        }
      }
      sseConnected = false;
      updateSSEIndicator();
    } catch (e) {
      sseConnected = false;
      updateSSEIndicator();
      // Reconnexion automatique (le polling 60 s reprend en attendant)
      setTimeout(connect, 5000);
    }
  };
  connect();
}
