"""Tests de l'intégration Ha3D (partie sans Home Assistant)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "custom_components" / "ha3d"))
import layout as h


def _valid_layout():
    return {
        "house_name": "Test",
        "levels": [{"name": "rdc", "y_floor": 0, "height": 2.6, "rooms": [
            {"id": "salon", "name": "Salon", "x": 0, "z": 0, "w": 5, "d": 4, "color": "#fff"},
        ]}],
        "sensors": [{"entity": "sensor.a", "room": "salon"}],
        "doors": [{"id": "p1", "t": 2, "width": 0.9, "room": "salon", "rotY": 0, "fixed": 0}],
        "furniture": [],
    }


class TestValidateLayout(unittest.TestCase):
    def test_layout_valide(self):
        self.assertEqual(h.validate_layout(_valid_layout()), (True, ""))

    def test_demo_layout_valide(self):
        ok, err = h.validate_layout(h.demo_layout())
        self.assertTrue(ok, f"démo invalide : {err}")

    def test_piece_sans_id(self):
        l = _valid_layout()
        l["levels"][0]["rooms"][0].pop("id")
        self.assertFalse(h.validate_layout(l)[0])

    def test_capteur_duplique(self):
        l = _valid_layout()
        l["sensors"].append({"entity": "sensor.a", "room": "salon"})
        self.assertFalse(h.validate_layout(l)[0])

    def test_polygone_trop_petit(self):
        l = _valid_layout()
        l["levels"][0]["rooms"][0]["pts"] = [[0, 0], [1, 0]]
        self.assertFalse(h.validate_layout(l)[0])

    def test_porte_invalide(self):
        l = _valid_layout()
        l["doors"][0]["width"] = 0
        self.assertFalse(h.validate_layout(l)[0])


class TestLayoutStore(unittest.TestCase):
    def test_demo_par_defaut(self):
        with tempfile.TemporaryDirectory() as td:
            store = h.LayoutStore(Path(td) / "layout.json")
            self.assertTrue(store.is_demo)
            self.assertEqual(store.layout["house_name"], "Ha3D — Demo house")

    def test_save_et_reload(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "layout.json"
            store = h.LayoutStore(path)
            l = _valid_layout()
            ok, err = store.save(l)
            self.assertTrue(ok, err)
            self.assertTrue(path.exists())
            self.assertFalse(store.is_demo)
            # Backup créé au second save
            ok2, _ = store.save(_valid_layout())
            self.assertTrue(ok2)
            backups = list(Path(td).glob("layout_*.json"))
            self.assertEqual(len(backups), 1)

    def test_refus_layout_invalide(self):
        with tempfile.TemporaryDirectory() as td:
            store = h.LayoutStore(Path(td) / "layout.json")
            ok, err = store.save({"nope": True})
            self.assertFalse(ok)
            self.assertIn("invalid layout", err)


if __name__ == "__main__":
    unittest.main()
