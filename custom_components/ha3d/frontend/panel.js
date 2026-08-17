// Ha3D panel — custom element pour la sidebar Home Assistant.
// Charge le visualiseur 3D (frontend standalone) dans un iframe plein écran.
class Ha3dPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    if (this._rendered) return;
    this._rendered = true;
    const iframe = document.createElement('iframe');
    iframe.src = '/ha3d/index.html';
    iframe.style.cssText = 'width:100%;height:100%;border:none;display:block;';
    this.shadowRoot.appendChild(iframe);
  }
}

customElements.define('ha3d-panel', Ha3dPanel);
