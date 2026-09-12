import logging
from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SERVICE_TOGGLE, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform

from .api import RemoAPI
from .const import DOMAIN, Appliances
from .light_buttons import resolve_buttons

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
        buttons = resolve_buttons(entry.data, appliance)
        if buttons is None:
            _LOGGER.error(
                "Light %s exposes no button, so it cannot be switched",
                appliance.nickname,
            )
            continue
        on_button, off_button = buttons
        entities.append(
            RemoLight(appliance.id, appliance.nickname, on_button, off_button, api)
        )
    async_add_entities(entities)


class RemoLight(LightEntity):
    """Light entity that only supports on/off"""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_has_entity_name = True
    _attr_is_on = False

    def __init__(
        self,
        light_id: str,
        name: str,
        on_button: str,
        off_button: str,
        api: RemoAPI,
    ) -> None:
        self.light_id = light_id
        self.api = api
        self._attr_name = name
        self._attr_unique_id = f"{name} @ {light_id}"
        self.on_button = on_button
        self.off_button = off_button

    @property
    def toggle_only(self) -> bool:
        """Whether the same button was chosen for on and for off."""
        return self.on_button == self.off_button

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light.

        With separate buttons the on button says what it does, so it is sent
        directly.  A single toggle button can only be toggled, so the real
        state is assumed to be off; use toggle instead where that matters.
        """
        if not self.toggle_only:
            self._attr_is_on = True
            await self.api.set_light(self.light_id, self.on_button)
            return
        if self.is_on:
            self._attr_is_on = False
        await self.async_toggle(**kwargs)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light.

        The mirror of async_turn_on: sent directly where an off button exists,
        otherwise the real state is assumed to be on and the light is toggled.
        """
        if not self.toggle_only:
            self._attr_is_on = False
            await self.api.set_light(self.light_id, self.off_button)
            return
        if not self.is_on:
            self._attr_is_on = True
        await self.async_toggle(**kwargs)

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the light.

        When on and off are the same button this sends it either way, which is
        what toggling a single-button remote means.
        """
        self._attr_is_on = not self._attr_is_on
        button = self.on_button if self._attr_is_on else self.off_button
        await self.api.set_light(self.light_id, button)
