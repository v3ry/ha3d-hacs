// Ha3D panel — custom element pour la sidebar Home Assistant.
// Le panel sert de PROXY : il fait les appels API via hass.fetchWithAuth
// (auth native HA, aucun token à gérer) et relaie les résultats à l'iframe
// via postMessage. Le temps réel passe par hass.connection.subscribeEvents.
class Ha3dPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._hass = null;
    this._iframe = null;
    this._rendered = false;
    this._unsub = null;

    window.addEventListener('message', async (evt) => {
      const d = evt.data;
      if (!d || d.type !== 'ha3d-fetch') return;
      const { id, url, method, body } = d;
      try {
        if (!this._hass) throw new Error('hass not ready');
        const init = { method: method || 'GET' };
        if (body !== undefined && body !== null) {
          init.headers = { 'Content-Type': 'application/json' };
          init.body = JSON.stringify(body);
        }
        const resp = await this._hass.fetchWithAuth(url, init);
        let data = null;
        try { data = await resp.json(); } catch (e) { /* non-JSON */ }
        if (evt.source && evt.source.postMessage) {
          evt.source.postMessage(
            { type: 'ha3d-fetch-result', id, ok: resp.ok, status: resp.status, data },
            '*'
          );
        }
      } catch (e) {
        if (evt.source && evt.source.postMessage) {
          evt.source.postMessage(
            { type: 'ha3d-fetch-result', id, ok: false, status: 0, data: null, error: String(e) },
            '*'
          );
        }
      }
    });
  }

  set hass(hass) {
    this._hass = hass;
    this._setupEventBridge();
  }

  get hass() {
    return this._hass;
  }

  // Relaie les state_changed HA à l'iframe (remplace le SSE, qui exige
  // un Bearer token sur EventSource — impossible).
  _setupEventBridge() {
    if (!this._hass || !this._hass.connection || this._unsub) return;
    try {
      this._unsub = this._hass.connection.subscribeEvents((evt) => {
        if (!this._iframe || !this._iframe.contentWindow) return;
        if (evt.event_type !== 'state_changed') return;
        const eid = evt.data && evt.data.entity_id;
        const ns = evt.data && evt.data.new_state;
        if (!eid) return;
        const attrs = ns ? ns.attributes : {};
        const msg = {
          type: 'ha3d-state-changed',
          entity: eid,
          state: ns ? ns.state : null,
          unit: attrs.unit_of_measurement || '',
          attrs: {
            friendly_name: attrs.friendly_name,
            temperature: attrs.temperature,
            current_temperature: attrs.current_temperature,
            humidity: attrs.humidity,
            battery_level: attrs.battery_level,
            hvac_action: attrs.hvac_action,
            hvac_mode: attrs.hvac_mode,
          },
        };
        this._iframe.contentWindow.postMessage(msg, '*');
      }, 'state_changed');
    } catch (e) {
      // subscribeEvents indisponible → le polling de l'iframe prend le relais
    }
  }

  connectedCallback() {
    if (this._rendered) return;
    this._rendered = true;

    // Le custom element doit remplir toute la hauteur du conteneur HA
    // (sinon l'iframe fait 100% de rien → canvas three.js ~0 px de haut).
    const style = document.createElement('style');
    // Selon la version de HA, un parent intermédiaire ne fournit pas de
    // hauteur exploitable. Une hauteur viewport explicite évite un iframe 0px.
    style.textContent = `
      :host {
        display: block;
        position: relative;
        width: 100%;
        height: calc(100vh - var(--header-height, 56px));
        min-height: 480px;
        overflow: hidden;
        box-sizing: border-box;
      }
    `;
    this.shadowRoot.appendChild(style);

    const iframe = document.createElement('iframe');
    iframe.src = '/ha3d/index.html';
    iframe.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;border:none;display:block;';
    this._iframe = iframe;
    this.shadowRoot.appendChild(iframe);
    this._setupEventBridge();
  }
}

customElements.define('ha3d-panel', Ha3dPanel);

// Export requis pour être chargé comme module ES6 par le loader de HA.
export {};
