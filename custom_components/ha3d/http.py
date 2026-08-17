"""Routes HTTP de l'intégration Ha3D.

Reproduit l'API du serveur standalone (/api/ha3d/*) avec l'authentification
native Home Assistant (cookies de session) — plus de token à gérer.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Entités sujettes au toggle (mêmes règles que le standalone)
TOGGLEABLE = ("light", "switch", "input_boolean", "fan", "group")


def _status_entry(sensor: dict, state, get_state=None) -> dict:
    """Construit l'entrée de statut d'un capteur depuis un état HA.

    get_state: callable(entity_id) -> State | None, utilisé pour sum_with.
    """
    sid = sensor["entity"]
    sum_with = sensor.get("sum_with")

    def _num(st) -> float | None:
        if st is None:
            return None
        try:
            return float(st.state)
        except (TypeError, ValueError):
            return None

    if sum_with:
        v1 = _num(state)
        v2 = _num(get_state(sum_with) if get_state else None)
        if v1 is None and v2 is None:
            return {"entity": sid, "state": "unavailable", "unit": "", "attrs": {}}
        total = (abs(v1) if v1 is not None else 0) + (abs(v2) if v2 is not None else 0)
        unit = getattr(state, "unit_of_measurement", "") or "W"
        return {"entity": sid, "state": str(total), "unit": unit,
                "attrs": {"friendly_name": sensor.get("label", sid), "is_sum": True}}

    if state is None:
        return {"entity": sid, "state": "unavailable", "unit": "", "attrs": {}}
    attrs = state.attributes
    return {
        "entity": sid,
        "state": state.state,
        "unit": attrs.get("unit_of_measurement", ""),
        "attrs": {
            "friendly_name": attrs.get("friendly_name", sid),
            "temperature": attrs.get("temperature"),
            "current_temperature": attrs.get("current_temperature"),
            "humidity": attrs.get("humidity"),
            "battery_level": attrs.get("battery_level"),
            "hvac_action": attrs.get("hvac_action"),
            "hvac_mode": attrs.get("hvac_mode"),
        },
    }


def _doors_status(hass: HomeAssistant, layout: dict) -> list:
    out = []
    for d in layout.get("doors", []):
        eid = d.get("entity")
        if not eid:
            continue
        st = hass.states.get(eid)
        out.append({"entity": eid, "state": st.state if st else "unavailable",
                    "name": d.get("name", eid), "id": d.get("id")})
    return out


def _status_payload(hass: HomeAssistant, layout: dict, demo: bool) -> dict:
    """Payload /api/status identique au standalone."""
    sensors = []
    for s in layout["sensors"]:
        st = hass.states.get(s["entity"])
        if demo:
            # Mode démo : valeurs simulées déterministes si l'entité n'existe pas
            if st is None:
                sensors.append(_demo_entry(s))
                continue
        sensors.append(_status_entry(s, st, get_state=hass.states.get))
    lat = getattr(hass.config, "latitude", None)
    lon = getattr(hass.config, "longitude", None)
    return {
        "house_name": layout.get("house_name", "Ma maison"),
        "sensors": sensors,
        "doors": _doors_status(hass, layout),
        "geo": {"lat": lat, "lon": lon},
        "demo": demo,
    }


def _demo_entry(s: dict) -> dict:
    """Valeur simulée déterministe (même logique que le standalone)."""
    eid = s["entity"]
    name = (s.get("label") or eid).lower()
    seed = sum(ord(c) for c in eid)
    base = (seed % 100) / 100.0
    if eid.startswith("sensor.temperature") or ("temp" in name and "hum" not in name):
        return {"entity": eid, "state": f"{19 + round(base * 8, 1)}", "unit": "°C",
                "attrs": {"friendly_name": s.get("label", eid), "demo": True}}
    if eid.startswith("sensor.humidity") or "hum" in name:
        return {"entity": eid, "state": f"{40 + round(base * 30)}", "unit": "%",
                "attrs": {"friendly_name": s.get("label", eid), "demo": True}}
    if eid.startswith("binary_sensor.") or "door" in name or "porte" in name:
        return {"entity": eid, "state": "off", "unit": "",
                "attrs": {"friendly_name": s.get("label", eid), "demo": True}}
    if eid.startswith(("light.", "switch.", "fan.")):
        return {"entity": eid, "state": "on" if base > 0.5 else "off", "unit": "",
                "attrs": {"friendly_name": s.get("label", eid), "demo": True}}
    return {"entity": eid, "state": "21.5", "unit": "°C",
            "attrs": {"friendly_name": s.get("label", eid), "demo": True}}



def _app_data(request):
    """Accès aux données d'intégration depuis une vue (standard hass.data)."""
    return request.app["hass"].data[DOMAIN]


class LayoutView(HomeAssistantView):
    """GET /api/ha3d/layout — layout courant."""

    url = "/api/ha3d/layout"
    name = "api:ha3d:layout"
    requires_auth = True

    async def get(self, request):
        store = _app_data(request)["store"]
        return self.json(store.layout)


class SaveLayoutView(HomeAssistantView):
    """POST /api/ha3d/save-layout — validation + sauvegarde avec backup."""

    url = "/api/ha3d/save-layout"
    name = "api:ha3d:save_layout"
    requires_auth = True

    async def post(self, request):
        store = _app_data(request)["store"]
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return self.json({"ok": False, "error": "bad json"}, status=400)
        ok, err = store.save(data)
        if not ok:
            return self.json({"ok": False, "error": err})
        return self.json({"ok": True, "sensors": len(data.get("sensors", []))})


class StatusView(HomeAssistantView):
    """GET /api/ha3d/status — capteurs en direct + géolocalisation."""

    url = "/api/ha3d/status"
    name = "api:ha3d:status"
    requires_auth = True

    async def get(self, request):
        app = _app_data(request)
        payload = _status_payload(request.app["hass"], app["store"].layout, app["store"].is_demo)
        return self.json(payload)


class ModelsView(HomeAssistantView):
    """GET /api/ha3d/models — liste des modèles 3D disponibles."""

    url = "/api/ha3d/models"
    name = "api:ha3d:models"
    requires_auth = True

    async def get(self, request):
        models_dir = _app_data(request)["models_dir"]
        models = sorted(p.stem for p in models_dir.glob("*.glb"))
        return self.json({"models": models})


class EntitiesView(HomeAssistantView):
    """GET /api/ha3d/entities?q= — recherche d'entités HA."""

    url = "/api/ha3d/entities"
    name = "api:ha3d:entities"
    requires_auth = True

    async def get(self, request):
        q = request.query.get("q", "").lower()
        hass: HomeAssistant = request.app["hass"]
        hits = []
        for state in hass.states.async_all():
            eid = state.entity_id
            name = state.attributes.get("friendly_name", eid)
            if q and q not in eid.lower() and q not in name.lower():
                continue
            hits.append({"entity_id": eid, "friendly_name": name, "domain": state.domain})
        hits.sort(key=lambda h: h["friendly_name"])
        return self.json({"entities": hits[:50]})


class HistoryView(HomeAssistantView):
    """GET /api/ha3d/history?entity=&hours= — historique d'une entité."""

    url = "/api/ha3d/history"
    name = "api:ha3d:history"
    requires_auth = True

    async def get(self, request):
        hass: HomeAssistant = request.app["hass"]
        entity_id = request.query.get("entity", "")
        hours = float(request.query.get("hours", "24"))
        if not entity_id:
            return self.json({"error": "entity missing"}, status=400)
        from homeassistant.components.history import get_significant_states
        from datetime import timedelta, datetime
        end = datetime.now(hass.config.time_zone)
        start = end - timedelta(hours=hours)
        states = await hass.async_add_executor_job(
            get_significant_states, hass, start, end, [entity_id], include_start_time_state=False)
        points = []
        for state in states.get(entity_id, []):
            try:
                points.append({"t": state.last_changed.isoformat(), "v": float(state.state)})
            except (TypeError, ValueError):
                continue
        return self.json({"entity_id": entity_id, "points": points})


class ToggleView(HomeAssistantView):
    """POST /api/ha3d/toggle — bascule une entité (lumière/prise…)."""

    url = "/api/ha3d/toggle"
    name = "api:ha3d:toggle"
    requires_auth = True

    async def post(self, request):
        hass: HomeAssistant = request.app["hass"]
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            return self.json({"ok": False, "error": "bad json"}, status=400)
        entity_id = payload.get("entity_id", "")
        if not entity_id:
            return self.json({"ok": False, "error": "entity_id missing"}, status=400)
        domain = entity_id.split(".")[0]
        if domain not in TOGGLEABLE:
            return self.json({"ok": False, "error": f"domain non togglable: {domain}"})
        await hass.services.async_call(domain, "toggle", {"entity_id": entity_id})
        return self.json({"ok": True})


class EventsView(HomeAssistantView):
    """GET /api/ha3d/events — Server-Sent Events.

    Snapshot initial puis mises à jour temps réel via le bus HA (state_changed).
    """

    url = "/api/ha3d/events"
    name = "api:ha3d:events"
    requires_auth = True

    async def get(self, request):
        hass: HomeAssistant = request.app["hass"]
        app = _app_data(request)
        store = app["store"]

        response = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
        await response.prepare(request)
        request.protocol.set_compression(False)

        # Snapshot initial
        snap = json.dumps({"type": "snapshot", **_status_payload(hass, store.layout, store.is_demo)}, ensure_ascii=False)
        try:
            await response.write(f"data: {snap}\n\n".encode("utf-8"))
        except (ConnectionResetError, RuntimeError):
            return response

        tracked = {s["entity"] for s in store.layout["sensors"]}
        for d in store.layout.get("doors", []):
            if d.get("entity"):
                tracked.add(d["entity"])
        for s in store.layout["sensors"]:
            if s.get("sum_with"):
                tracked.add(s["sum_with"])

        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        unsub = None

        async def _on_state_changed(event) -> None:
            eid = event.data.get("entity_id", "")
            if eid not in tracked:
                return
            st = hass.states.get(eid)
            if st is None:
                return
            # Capteurs du layout concernés (y compris sum_with)
            for s in store.layout["sensors"]:
                if s["entity"] == eid or s.get("sum_with") == eid:
                    entry = _status_entry(s, st, get_state=hass.states.get)
                    try:
                        queue.put_nowait(json.dumps({"type": "update", **entry}, ensure_ascii=False))
                    except asyncio.QueueFull:
                        pass
            # Porte animée
            for d in store.layout.get("doors", []):
                if d.get("entity") == eid:
                    try:
                        queue.put_nowait(json.dumps(
                            {"type": "update", "entity": eid, "state": st.state,
                             "unit": st.attributes.get("unit_of_measurement", ""),
                             "attrs": {"friendly_name": st.attributes.get("friendly_name", eid)}},
                            ensure_ascii=False))
                    except asyncio.QueueFull:
                        pass

        unsub = hass.bus.async_listen("state_changed", _on_state_changed)
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15)
                    await response.write(f"data: {payload}\n\n".encode("utf-8"))
                except asyncio.TimeoutError:
                    await response.write(b": ping\n\n")  # keepalive
        except (ConnectionResetError, RuntimeError, asyncio.CancelledError):
            pass
        finally:
            if unsub:
                unsub()
        return response


def register_views(hass: HomeAssistant, models_dir: Path, store) -> None:
    """Enregistre toutes les vues API sur le webserver HA.

    Les vues lisent le store via request.app[KEY_HASS].data[DOMAIN]
    (mécanisme standard hass.data, stable quelle que soit la version HA).
    """
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["store"] = store
    hass.data[DOMAIN]["models_dir"] = models_dir
    hass.http.register_view(LayoutView())
    hass.http.register_view(SaveLayoutView())
    hass.http.register_view(StatusView())
    hass.http.register_view(ModelsView())
    hass.http.register_view(EntitiesView())
    hass.http.register_view(HistoryView())
    hass.http.register_view(ToggleView())
    hass.http.register_view(EventsView())
