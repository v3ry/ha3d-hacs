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

# Vérifications post-sync : aucun chemin /api/ non-adapté ne doit subsister
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
