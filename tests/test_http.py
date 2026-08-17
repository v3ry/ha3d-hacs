"""Tests de la couche HTTP avec un faux hass (sans Home Assistant installé)."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path

# Stub des modules homeassistant + aiohttp pour importer http.py hors HA
_aiohttp = types.ModuleType("aiohttp")
_aiohttp_web = types.ModuleType("aiohttp.web")
_aiohttp_web.StreamResponse = object
sys.modules["aiohttp"] = _aiohttp
sys.modules["aiohttp.web"] = _aiohttp_web

_ha = types.ModuleType("homeassistant")
_ha.core = types.ModuleType("homeassistant.core")
_ha.core.HomeAssistant = object
_ha.const = types.ModuleType("homeassistant.const")
_ha.const.STATE_ON = "on"
_http = types.ModuleType("homeassistant.components.http")
_http.HomeAssistantView = object
sys.modules["homeassistant"] = _ha
sys.modules["homeassistant.core"] = _ha.core
sys.modules["homeassistant.const"] = _ha.const
sys.modules["homeassistant.components"] = types.ModuleType("homeassistant.components")
sys.modules["homeassistant.components.http"] = _http

# Charge http.py isolément (le package complet exigerait HA) — stub const
BASE = Path(__file__).resolve().parent.parent / "custom_components" / "ha3d"
sys.path.insert(0, str(BASE))
_const = types.ModuleType("custom_components.ha3d.const")
_const.DOMAIN = "ha3d"
sys.modules["custom_components"] = types.ModuleType("custom_components")
sys.modules["custom_components.ha3d"] = types.ModuleType("custom_components.ha3d")
sys.modules["custom_components.ha3d.const"] = _const

_spec = importlib.util.spec_from_file_location("custom_components.ha3d.http", BASE / "http.py")
http = importlib.util.module_from_spec(_spec)
sys.modules["custom_components.ha3d.http"] = http
_spec.loader.exec_module(http)

_status_entry = http._status_entry
_status_payload = http._status_payload
_demo_entry = http._demo_entry
_doors_status = http._doors_status


class FakeState:
    def __init__(self, entity_id, state, attributes=None):
        self.entity_id = entity_id
        self.state = state
        self.attributes = attributes or {}
        self.domain = entity_id.split(".")[0]

    @property
    def unit_of_measurement(self):
        return self.attributes.get("unit_of_measurement", "")


class FakeStates:
    def __init__(self, states):
        self._states = {s.entity_id: s for s in states}

    def get(self, entity_id):
        return self._states.get(entity_id)

    def async_all(self):
        return list(self._states.values())


class FakeConfig:
    latitude = 45.83
    longitude = 4.62


class FakeHass:
    def __init__(self, states):
        self.states = FakeStates(states)
        self.config = FakeConfig()


LAYOUT = {
    "house_name": "Test",
    "levels": [{"rooms": [{"id": "r1"}]}],
    "sensors": [
        {"entity": "sensor.temp", "room": "r1"},
        {"entity": "sensor.hum", "room": "r1"},
    ],
    "doors": [
        {"id": "d1", "entity": "binary_sensor.porte", "name": "Porte"},
    ],
}


class TestStatusEntry(unittest.TestCase):
    def test_entite_normale(self):
        st = FakeState("sensor.temp", "22.5", {"unit_of_measurement": "°C", "friendly_name": "Temp"})
        out = _status_entry({"entity": "sensor.temp"}, st)
        self.assertEqual(out["state"], "22.5")
        self.assertEqual(out["unit"], "°C")
        self.assertEqual(out["attrs"]["friendly_name"], "Temp")

    def test_entite_absente(self):
        out = _status_entry({"entity": "sensor.inconnu"}, None)
        self.assertEqual(out["state"], "unavailable")

    def test_sum_with(self):
        st = FakeState("sensor.a", "100")
        get_state = lambda eid: FakeState("sensor.b", "50") if eid == "sensor.b" else None
        out = _status_entry({"entity": "sensor.total", "sum_with": "sensor.b"}, st, get_state=get_state)
        self.assertEqual(float(out["state"]), 150.0)
        self.assertEqual(out["unit"], "W")


class TestDemoEntry(unittest.TestCase):
    def test_temperature(self):
        out = _demo_entry({"entity": "sensor.temperature_salon"})
        self.assertEqual(out["unit"], "°C")
        self.assertGreaterEqual(float(out["state"]), 19)

    def test_light(self):
        out = _demo_entry({"entity": "light.lampe"})
        self.assertIn(out["state"], ("on", "off"))


class TestStatusPayload(unittest.TestCase):
    def test_payload_complet(self):
        hass = FakeHass([
            FakeState("sensor.temp", "21.0", {"unit_of_measurement": "°C"}),
            FakeState("binary_sensor.porte", "on"),
        ])
        p = _status_payload(hass, LAYOUT, demo=False)
        self.assertEqual(p["house_name"], "Test")
        self.assertEqual(p["geo"], {"lat": 45.83, "lon": 4.62})
        self.assertEqual(p["sensors"][0]["state"], "21.0")
        self.assertEqual(p["doors"][0]["state"], "on")

    def test_demo_simule_absents(self):
        hass = FakeHass([])
        p = _status_payload(hass, LAYOUT, demo=True)
        # En mode démo, les capteurs absents reçoivent une valeur simulée
        self.assertEqual(p["sensors"][0]["unit"], "°C")
        self.assertTrue(p["demo"])
        # Les portes sans état → unavailable (pas de simulation pour les portes)
        self.assertEqual(p["doors"][0]["state"], "unavailable")


class TestDoorsStatus(unittest.TestCase):
    def test_avec_entite(self):
        hass = FakeHass([FakeState("binary_sensor.porte", "off")])
        out = _doors_status(hass, LAYOUT)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["state"], "off")
        self.assertEqual(out[0]["name"], "Porte")


if __name__ == "__main__":
    unittest.main()
