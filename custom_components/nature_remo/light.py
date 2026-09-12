import logging
from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SERVICE_TOGGLE, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform

from .api import RemoAPI
from .const import (
    BUTTON_OFF,
    BUTTON_ON,
    BUTTON_ONOFF,
    DOMAIN,
    Appliances,
    UnexpectedLight,
)

_LOGGER = logging.getLogger(__name__)


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
        RemoLight.async_turn_on.__name__,
    )
    platform.async_register_entity_service(
        SERVICE_TURN_OFF,
        {},
        RemoLight.async_turn_off.__name__,
    )
    platform.async_register_entity_service(
        SERVICE_TOGGLE,
        {},
        RemoLight.async_toggle.__name__,
    )
    entities = []
    api: RemoAPI = hass.data[DOMAIN][entry.entry_id]["api"]
    appliances: Appliances = hass.data[DOMAIN][entry.entry_id]["appliances"]
    for appliance in appliances.light:
        buttons = [button.name for button in appliance.light.buttons or []]
        if BUTTON_ONOFF in buttons:
            one_button = True
        elif BUTTON_ON in buttons and BUTTON_OFF in buttons:
            one_button = False
        else:
            _LOGGER.critical(
                "Unexpected light configuration; please contact the project maintainer"
            )
            raise UnexpectedLight
        entities.append(RemoLight(appliance.id, appliance.nickname, one_button, api))
    async_add_entities(entities)


class RemoLight(LightEntity):
    """Light entity that only supports on/off"""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_has_entity_name = True
    _attr_is_on = False

    def __init__(
        self, light_id: str, name: str, one_button: bool, api: RemoAPI
    ) -> None:
        self.light_id = light_id
        self.api = api
        self._attr_name = name
        self._attr_unique_id = f"{name} @ {light_id}"
        self.one_button = one_button

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light. Assuming that the real state must be OFF no matter of the internal state."""
        if self.is_on:
            self.is_on = False
        await self.async_toggle(**kwargs)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light. Assuming that the real state must be ON no matter of the internal state."""
        if not self.is_on:
            self.is_on = True
        await self.async_toggle(**kwargs)

    async def async_toggle(self, **kwargs: Any) -> None:
        self._attr_is_on = not self._attr_is_on
        if self.one_button:
            await self.api.set_light(self.light_id, BUTTON_ONOFF)
        elif self._attr_is_on:
            await self.api.set_light(self.light_id, BUTTON_ON)
        else:
            await self.api.set_light(self.light_id, BUTTON_OFF)
