from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SERVICE_TOGGLE, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform

from .api import RemoAPI
from .const import DOMAIN, Appliances


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: entity_platform.AddEntitiesCallback,
) -> None:
    """Set up nature remo appliances from a config entry."""
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_TURN_ON,
        {},
        RemoLight.async_toggle.__name__,
    )
    platform.async_register_entity_service(
        SERVICE_TURN_OFF,
        {},
        RemoLight.async_toggle.__name__,
    )
    platform.async_register_entity_service(
        SERVICE_TOGGLE,
        {},
        RemoLight.async_toggle.__name__,
    )
    entities = []
    api: RemoAPI = hass.data[DOMAIN][entry.entry_id]["api"]
    appliances: Appliances = hass.data[DOMAIN][entry.entry_id]["appliances"]
    for properties in appliances.light:
        entities.append(RemoLight(properties["id"], properties["nickname"], api))
    async_add_entities(entities)


class RemoLight(LightEntity):
    """Light entity that only supports on/off"""

    _attr_color_mode = ColorMode.ONOFF
    _attr_has_entity_name = True
    _attr_is_on = False

    def __init__(self, light_id: str, name: str, api: RemoAPI) -> None:
        self.light_id = light_id
        self.api = api
        self._attr_name = name
        self._attr_unique_id = f"{name} @ {light_id}"

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._attr_is_on = True
        await self.async_toggle(**kwargs)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        await self.async_toggle(**kwargs)

    async def async_toggle(self, **kwargs: Any) -> None:
        self._attr_is_on = not self._attr_is_on
        await self.api.send_light_signal(self.light_id, "onoff")
