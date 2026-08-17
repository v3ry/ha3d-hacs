"""Gestion du layout Ha3D : chargement, validation, sauvegarde.

Porté depuis le serveur standalone (ha3d_server.py) — mêmes règles.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

_LOGGER = logging.getLogger(__name__)


def demo_layout() -> dict:
    """Layout de démonstration (identique au serveur standalone)."""
    return {
        "house_name": "Ha3D — Demo house",
        "levels": [{
            "name": "rdc", "y_floor": 0, "height": 2.6, "rooms": [
                {"id": "salon", "name": "Living room", "x": 0, "z": 0, "w": 6, "d": 5, "color": "#f0e68c"},
                {"id": "cuisine", "name": "Kitchen", "x": 6, "z": 0, "w": 4, "d": 5, "color": "#98fb98"},
                {"id": "chambre", "name": "Bedroom", "x": 0, "z": 5, "w": 5, "d": 4, "color": "#87ceeb"},
                {"id": "sdb", "name": "Bathroom", "x": 5, "z": 5, "w": 3, "d": 4, "color": "#d8bfd8"},
                {"id": "bureau", "name": "Office", "x": 8, "z": 5, "w": 4, "d": 4, "color": "#ffcc99"},
            ],
            "furniture": [
                {"id": "demo_canap", "type": "model", "name": "Sofa", "model": "Canape", "room": "salon", "x": 0.25, "z": 0.55, "scale": 1.1},
                {"id": "demo_tv", "type": "model", "name": "TV", "model": "TV", "room": "salon", "x": 0.82, "z": 0.5, "scale": 1.0, "rotY": 3.14},
                {"id": "demo_lit", "type": "model", "name": "Bed", "model": "Lit", "room": "chambre", "x": 0.25, "z": 0.5, "scale": 1.0},
                {"id": "demo_table", "type": "model", "name": "Table", "model": "TableManger", "room": "cuisine", "x": 0.5, "z": 0.5, "scale": 1.0},
                {"id": "demo_plante", "type": "model", "name": "Plant", "model": "Plante", "room": "salon", "x": 0.9, "z": 0.15, "scale": 1.0},
            ],
        }],
        "sensors": [
            {"entity": "sensor.demo_temperature_salon", "name": "Living room temp", "room": "salon", "pos": [3, 1.7, 2.2]},
            {"entity": "sensor.demo_humidity_salon", "name": "Living room humidity", "room": "salon", "pos": [4.2, 1.7, 1.5]},
            {"entity": "light.demo_lamp", "name": "Lamp", "room": "salon", "pos": [5.2, 1.2, 3.8]},
            {"entity": "binary_sensor.demo_door", "name": "Front door", "room": "salon", "pos": [0.2, 1.5, 0.2]},
        ],
        "doors": [
            {"id": "porte_salon_cuisine", "name": "Salon ↔ Kitchen", "room": "salon", "rotY": 0, "fixed": 0, "t": 6, "width": 0.9, "height": 2.1, "hinge": "a0", "openSign": 1},
            {"id": "porte_salon_chambre", "name": "Salon ↔ Bedroom", "room": "salon", "rotY": 1.5708, "fixed": 0, "t": 5, "width": 0.9, "height": 2.1, "hinge": "a0", "openSign": 1},
        ],
        "default_camera": {"pos": [-18, 14, 14], "target": [5.5, 1, 3.5]},
    }


def validate_layout(new_layout: dict) -> tuple[bool, str]:
    """Valide la structure d'un layout. Retourne (ok, erreur)."""
    if not isinstance(new_layout, dict):
        return False, "layout is not a JSON object"
    if "sensors" not in new_layout or not isinstance(new_layout["sensors"], list):
        return False, "sensors missing or invalid"
    levels = new_layout.get("levels")
    if not isinstance(levels, list) or not levels:
        return False, "levels missing or empty"
    level = levels[0]
    rooms = level.get("rooms", []) if isinstance(level, dict) else None
    if not isinstance(rooms, list) or not rooms:
        return False, "rooms missing or empty"

    seen_ids: set[str] = set()
    for r in rooms:
        rid = r.get("id") if isinstance(r, dict) else None
        if not rid:
            return False, "room without id"
        if rid in seen_ids:
            return False, f"duplicate room id: {rid}"
        seen_ids.add(rid)
        pts = r.get("pts")
        if pts:
            if not isinstance(pts, list) or len(pts) < 3:
                return False, f"room '{rid}': invalid polygon (pts < 3 vertices)"
            for p in pts:
                if not isinstance(p, (list, tuple)) or len(p) != 2 or not all(
                        isinstance(v, (int, float)) and v == v for v in p):
                    return False, f"room '{rid}': invalid vertex {p}"
        else:
            for k in ("x", "z", "w", "d"):
                v = r.get(k)
                if not isinstance(v, (int, float)) or v != v:
                    return False, f"room '{rid}': invalid {k} ({v})"
            if r.get("w", 0) < 0.5 or r.get("d", 0) < 0.5:
                return False, f"room '{rid}': dimensions too small (< 0.5 m)"

    seen_door_ids: set[str] = set()
    for d in new_layout.get("doors", []):
        did = d.get("id") if isinstance(d, dict) else None
        if did and did in seen_door_ids:
            return False, f"duplicate door id: {did}"
        if did:
            seen_door_ids.add(did)
        for k in ("t", "width"):
            v = d.get(k)
            if not isinstance(v, (int, float)) or v != v or v <= 0:
                return False, f"door '{did or '?'}': invalid {k} ({v})"

    seen_sensors: set[str] = set()
    for s in new_layout["sensors"]:
        e = s.get("entity") if isinstance(s, dict) else None
        if not e:
            return False, "sensor without entity"
        if e in seen_sensors:
            return False, f"duplicate entity: {e}"
        seen_sensors.add(e)

    furn = level.get("furniture", []) if isinstance(level, dict) else []
    seen_furn: set[str] = set()
    for f in furn:
        fid = f.get("id") if isinstance(f, dict) else None
        if not fid:
            return False, "object without id"
        if fid in seen_furn:
            return False, f"duplicate object id: {fid}"
        seen_furn.add(fid)

    views = new_layout.get("camera_views", [])
    if not isinstance(views, list):
        return False, "camera_views must be a list"
    seen_view_names: set[str] = set()
    for v in views:
        if not isinstance(v, dict):
            return False, "invalid camera view (not an object)"
        for k in ("pos", "target"):
            arr = v.get(k)
            if not isinstance(arr, (list, tuple)) or len(arr) != 3 or not all(
                    isinstance(x, (int, float)) and x == x for x in arr):
                return False, f"view '{v.get('name', '?')}': invalid {k}"
        vname = v.get("name")
        if vname and vname in seen_view_names:
            return False, f"duplicate view name: {vname}"
        if vname:
            seen_view_names.add(vname)

    return True, ""


class LayoutStore:
    """Charge/écrit le layout dans config/ha3d/layout.json."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.layout: dict = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, OSError) as e:
                _LOGGER.warning("layout illisible (%s) — démo", e)
        _LOGGER.info("layout.json absent — maison de démonstration")
        return demo_layout()

    def save(self, new_layout: dict) -> tuple[bool, str | None]:
        ok, err = validate_layout(new_layout)
        if not ok:
            return False, f"invalid layout: {err}"
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Backup de l'actuel
            if self.path.exists():
                ts = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
                backup = self.path.with_name(f"layout_{ts}.json")
                backup.write_bytes(self.path.read_bytes())
            self.path.write_text(json.dumps(new_layout, ensure_ascii=False, indent=1), encoding="utf-8")
            self.layout = new_layout
            return True, None
        except OSError as e:
            return False, str(e)

    @property
    def is_demo(self) -> bool:
        return not self.path.exists()
