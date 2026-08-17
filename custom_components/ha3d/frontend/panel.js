// Ha3D panel — custom element pour la sidebar Home Assistant.
// Charge le visualiseur 3D (frontend standalone) dans un iframe plein écran
// et transmet le token d'accès HA à l'iframe (l'API /api/ha3d/* exige un
// Bearer token — pas de cookie).
class Ha3dPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._token = null;
    this._iframe = null;
    this._rendered = false;
    // Handshake : l'iframe demande le token quand elle est prête
    window.addEventListener('message', (evt) => {
      if (evt.data && evt.data.type === 'ha3d-request-token') {
        this._sendToken();
      }
    });
  }

  set hass(hass) {
    // Appelé par le frontend HA avec l'état courant (contient le token d'accès)
    this._hass = hass;
    const tok = hass && hass.auth ? hass.auth.accessToken : null;
    if (tok) this._token = tok;
    this._sendToken();
  }

  get hass() {
    return this._hass;
  }

  _sendToken() {
    if (!this._token) return;
    if (this._iframe && this._iframe.contentWindow) {
      this._iframe.contentWindow.postMessage(
        { type: 'ha3d-auth', token: this._token },
        '*'
      );
    }
  }

  connectedCallback() {
    if (this._rendered) return;
    this._rendered = true;
    const iframe = document.createElement('iframe');
    iframe.src = '/ha3d/index.html';
    iframe.style.cssText = 'width:100%;height:100%;border:none;display:block;';
    this._iframe = iframe;
    this.shadowRoot.appendChild(iframe);
    // Transmet le token dès que l'iframe est prête (et à chaque changement)
    iframe.addEventListener('load', () => this._sendToken());
    this._sendToken();
  }
}

customElements.define('ha3d-panel', Ha3dPanel);

// Export requis pour être chargé comme module ES6 par le loader de HA.
export {};
