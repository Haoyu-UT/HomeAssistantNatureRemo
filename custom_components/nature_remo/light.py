import datetime
import logging
from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SERVICE_TOGGLE, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

from .api import RemoAPI
from .const import DOMAIN, Appliances
from .coordinator import ApplianceCoordinator
from .light_buttons import resolve_buttons
from .models import ApplianceResponse, LightState

_LOGGER = logging.getLogger(__name__)

# The power values the API reports for a light.
POWER_ON = "on"
POWER_OFF = "off"

# How long a report is distrusted after a command is sent. See
# RemoLight._may_predate_own_command for why a window is needed at all.
COMMAND_SETTLE_TIME = datetime.timedelta(seconds=15)


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
    entry_storage: dict = hass.data[DOMAIN][entry.entry_id]
    api: RemoAPI = entry_storage["api"]
    appliances: Appliances = entry_storage["appliances"]
    coordinator: ApplianceCoordinator = entry_storage["appliance_coordinator"]
    for appliance in appliances.light:
        buttons = resolve_buttons(entry.data, appliance)
        if buttons is None:
            _LOGGER.error(
                "Light %s exposes no button, so it cannot be switched",
                appliance.nickname,
            )
            continue
        on_button, off_button = buttons
        entities.append(RemoLight(appliance, on_button, off_button, api, coordinator))
    async_add_entities(entities)


class RemoLight(CoordinatorEntity, LightEntity):
    """Light entity that only supports on/off"""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_has_entity_name = True
    _attr_is_on = False

    def __init__(
        self,
        appliance: ApplianceResponse,
        on_button: str,
        off_button: str,
        api: RemoAPI,
        coordinator: ApplianceCoordinator,
    ) -> None:
        # this step sets self.coordinator
        super().__init__(coordinator)
        self.light_id = appliance.id
        self.api = api
        self._attr_name = appliance.nickname
        self._attr_unique_id = f"{appliance.nickname} @ {appliance.id}"
        self.on_button = on_button
        self.off_button = off_button
        self._command_button: str | None = None
        self._command_sent_at: datetime.datetime | None = None
        if appliance.light is not None:
            self._absorb_reported_state(appliance.light.state)

    @property
    def toggle_only(self) -> bool:
        """Whether the same button was chosen for on and for off."""
        return self.on_button == self.off_button

    def _may_predate_own_command(self, state: LightState) -> bool:
        """Whether a report could have been taken before our last command.

        An air conditioner's settings carry updated_at, so a stale report is
        recognisable; LightState carries no timestamp, so a poll already in
        flight when a command is sent cannot be told apart from a fresh one.
        Reports are distrusted for a short window instead, which ends early
        once the API echoes back the button that was sent.
        """
        if self._command_sent_at is None:
            return False
        if dt_util.utcnow() - self._command_sent_at > COMMAND_SETTLE_TIME:
            return False
        return state.last_button != self._command_button

    def _absorb_reported_state(self, state: LightState | None) -> bool:
        """Adopt the power the API reports, returning whether it changed.

        This is the only way a press of the physical remote reaches Home
        Assistant: the device reports it to the cloud, and the cloud is polled.
        """
        if state is None or state.power not in (POWER_ON, POWER_OFF):
            return False
        if self._may_predate_own_command(state):
            return False
        is_on = state.power == POWER_ON
        if is_on == self._attr_is_on:
            return False
        self._attr_is_on = is_on
        return True

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        appliance = next(
            (
                light
                for light in self.coordinator.data.light
                if light.id == self.light_id
            ),
            None,
        )
        if appliance is None or appliance.light is None:
            return
        if self._absorb_reported_state(appliance.light.state):
            self.async_write_ha_state()

    async def _send(self, button: str) -> None:
        """Press a button, remembering it so its report can be recognised."""
        self._command_button = button
        self._command_sent_at = dt_util.utcnow()
        await self.api.set_light(self.light_id, button)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light.

        With separate buttons the on button says what it does, so it is sent
        directly.  A single toggle button can only be toggled, so the real
        state is assumed to be off; use toggle instead where that matters.
        """
        if not self.toggle_only:
            self._attr_is_on = True
            await self._send(self.on_button)
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
            await self._send(self.off_button)
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
        await self._send(button)
