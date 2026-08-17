#!/usr/bin/env python3
"""Synchronise le frontend du repo standalone (v3ry/ha3d) vers l'intégration HACS.

Usage : python3 tools/sync_frontend.py <chemin-standalone> [--check]
Adapte les chemins API (/api/* → /api/ha3d/*) et modèles (/models/ → /ha3d/models/).
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

REPLACEMENTS = [
    ("'/api/history?entity='", "'/api/ha3d/history?entity='"),
    ("'/api/layout'", "'/api/ha3d/layout'"),
    ("'/api/models'", "'/api/ha3d/models'"),
    ("'/api/save-layout'", "'/api/ha3d/save-layout'"),
    ("'/api/status'", "'/api/ha3d/status'"),
    ("'/api/toggle'", "'/api/ha3d/toggle'"),
    ("fetch(`/api/entities?q=${encodeURIComponent(q)}`)", "fetch(`/api/ha3d/entities?q=${encodeURIComponent(q)}`)"),
    ("gltfLoader.load('/models/'", "gltfLoader.load('/ha3d/models/'"),
    ("new EventSource('/api/events')", "new EventSource('/api/ha3d/events')"),
]

# Remplacements CDN → fichiers locaux (le CSP de HA bloque les scripts externes)
CDN_REPLACEMENTS = [
    ("https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js", "vendor/three.min.js"),
    ("https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js", "vendor/OrbitControls.js"),
    ("https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js", "vendor/GLTFLoader.js"),
]

# Bloc auth HA injecté après le marqueur CONFIG (token via postMessage du panel)
AUTH_BLOCK = """// ============ CONFIG ============
// Auth HA (mode intégration HACS) : le token est reçu du panel parent
// via postMessage, puis injecté dans tous les fetch (Bearer).
let haToken = null;
const haTokenWaiters = [];
window.addEventListener('message', (evt) => {
  if (evt.data && evt.data.type === 'ha3d-auth' && evt.data.token) {
    haToken = evt.data.token;
    // Réveille tous les fetch en attente
    const ws = haTokenWaiters.splice(0);
    ws.forEach(w => w(true));
  }
});

// Attend que le token arrive (résout false si timeout). Envoie au passage
// une demande au panel parent (il répond par postMessage 'ha3d-auth').
function waitForHaToken(timeout = 5000) {
  if (haToken) return Promise.resolve(true);
  try { window.parent.postMessage({ type: 'ha3d-request-token' }, '*'); } catch (e) {}
  return new Promise(resolve => {
    let done = false;
    const t = setTimeout(() => { if (!done) { done = true; resolve(false); } }, timeout);
    haTokenWaiters.push(ok => { if (!done) { done = true; clearTimeout(t); resolve(ok); } });
  });
}

// Wrapper fetch : injecte le Bearer token HA. Attend le token au premier
// appel (course au démarrage) et réessaie une fois sur 401.
async function apiFetch(url, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (haToken) headers['Authorization'] = 'Bearer ' + haToken;
  let resp = await fetch(url, { ...opts, headers, credentials: 'same-origin' });
  if (resp.status === 401 && !haToken) {
    // Le token n'était pas encore là : on l'attend puis on réessaie une fois
    const got = await waitForHaToken();
    if (got) {
      headers['Authorization'] = 'Bearer ' + haToken;
      resp = await fetch(url, { ...opts, headers, credentials: 'same-origin' });
    }
  }
  return resp;
}
"""

# Vérifications post-sync : aucun chemin standalone ne doit subsister
GUARDS = [
    "fetch('/api/layout'",
    "fetch('/api/status'",
    "fetch('/api/models'",
    "fetch('/api/save-layout'",
    "fetch('/api/toggle'",
    "fetch('/api/history?entity='",
    "new EventSource('/api/events')",
    "gltfLoader.load('/models/'",
]


def sync(src: Path, dst: Path, check: bool = False) -> list[str]:
    if not src.exists():
        print(f"❌ source introuvable: {src}", file=sys.stderr)
        sys.exit(1)
    dst.mkdir(parents=True, exist_ok=True)
    html = src.read_text(encoding="utf-8")

    missing = []
    for old, new in REPLACEMENTS:
        if old not in html:
            missing.append(old)
        else:
            html = html.replace(old, new)

    # Garde-fous : aucun chemin standalone ne doit rester
    for g in GUARDS:
        if g in html:
            missing.append(f"GARDE: {g}")

    # CDN → local (CSP HA)
    for cdn, local in CDN_REPLACEMENTS:
        if cdn in html:
            html = html.replace(cdn, local)
        else:
            missing.append(f"CDN absent (déjà local ?): {cdn[:50]}")

    # Injection du bloc auth HA (remplace le marqueur CONFIG original)
    config_marker = "// ============ CONFIG ============"
    if config_marker in html:
        html = html.replace(config_marker, AUTH_BLOCK.strip(), 1)
    else:
        missing.append("marqueur CONFIG introuvable pour l'auth")
    # Tous les fetch /api/ha3d/* passent par apiFetch (Bearer token)
    html = html.replace("fetch('/api/ha3d/", "apiFetch('/api/ha3d/")

    # SSE : remplace la fonction connectSSE (EventSource) par la version
    # streaming avec Bearer token (EventSource ne gère pas les headers).
    sse_fn = (Path(__file__).resolve().parent / "sse_streaming.js").read_text(encoding="utf-8").strip()
    sse_start = html.find("function connectSSE()")
    if sse_start >= 0:
        depth = 0
        i = sse_start
        in_str = None
        while i < len(html):
            c = html[i]
            if in_str:
                if c == "\\":
                    i += 2
                    continue
                if c == in_str:
                    in_str = None
            else:
                if c in "'\"`":
                    in_str = c
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        break
            i += 1
        html = html[:sse_start] + sse_fn + html[i + 1:]
    else:
        missing.append("connectSSE introuvable")

    target = dst / "index.html"
    if check:
        if target.exists() and target.read_text(encoding="utf-8") == html:
            print(f"✓ {target} à jour")
            return []
        print(f"✗ {target} doit être resynchronisé")
        return ["outdated"]

    target.write_text(html, encoding="utf-8")
    print(f"✓ index.html synchronisé → {target} ({len(html)//1024} Ko)")

    # Modèles : copie seulement si absent ou plus récent
    src_models = src.parent / "models"
    dst_models = dst / "models"
    if src_models.exists():
        dst_models.mkdir(exist_ok=True)
        for glb in src_models.glob("*.glb"):
            d = dst_models / glb.name
            if not d.exists() or glb.stat().st_mtime > d.stat().st_mtime:
                shutil.copy2(glb, d)
        print(f"✓ modèles synchronisés ({len(list(dst_models.glob('*.glb')))} .glb)")

    if missing:
        print(f"⚠️ {len(missing)} motifs non trouvés (front à vérifier):")
        for m in missing:
            print(f"   - {m[:80]}")
    return missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("standalone", help="dossier du repo standalone (avec index.html)")
    ap.add_argument("--check", action="store_true", help="vérifie sans écrire")
    args = ap.parse_args()

    src = Path(args.standalone) / "index.html"
    dst = Path(__file__).resolve().parent.parent / "custom_components" / "ha3d" / "frontend"
    missing = sync(src, dst, check=args.check)
    if args.check and missing:
        sys.exit(1)


if __name__ == "__main__":
    main()
