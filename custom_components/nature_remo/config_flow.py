"""Config flow for nature_remo integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .api import RemoAPI
from .const import (
    CONF_LIGHTS,
    CONF_OFF_BUTTON,
    CONF_ON_BUTTON,
    CONF_POLLING_INTERVAL_POWER_METER,
    CONF_POLLING_INTERVAL_SENSOR,
    CONF_TOKEN,
    DOMAIN,
    AuthError,
    NetworkError,
)
from .light_buttons import button_choices, default_buttons
from .models import ApplianceResponse

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TOKEN): str,
        vol.Optional(CONF_POLLING_INTERVAL_SENSOR, default=60): int,
        vol.Optional(CONF_POLLING_INTERVAL_POWER_METER, default=60): int,
    }
)


async def validate_input(data: dict[str, Any]) -> list[ApplianceResponse]:
    """Check the token works and return the lights that need configuring."""
    remo = RemoAPI(data[CONF_TOKEN])
    if not await remo.authenticate():
        raise AuthError
    return (await remo.fetch_grouped_appliances()).light


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for nature_remo."""

    VERSION = 2
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._data: dict[str, Any] = {}
        self._lights: list[ApplianceResponse] = []
        self._light_index = 0

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                lights = await validate_input(user_input)
            except NetworkError:
                _LOGGER.exception("Network error during config")
                errors["base"] = "network_error"
            except AuthError:
                _LOGGER.exception("Authorization failed during config")
                errors["base"] = "invalid_token"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during config")
                errors["base"] = "unknown"
            else:
                self._data = {**user_input, CONF_LIGHTS: {}}
                # Lights whose remote offers no button cannot be switched, so
                # there is nothing to ask about.
                self._lights = [light for light in lights if button_choices(light)]
                self._light_index = 0
                return await self.async_step_light()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_light(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask which buttons switch each light on and off.

        One form per light, because the buttons a remote offers differ between
        them.  Picking the same button twice means the remote has only a
        toggle, and the light is then switched by toggling.
        """
        if user_input is not None:
            appliance = self._lights[self._light_index]
            self._data[CONF_LIGHTS][appliance.id] = {
                CONF_ON_BUTTON: user_input[CONF_ON_BUTTON],
                CONF_OFF_BUTTON: user_input[CONF_OFF_BUTTON],
            }
            self._light_index += 1

        if self._light_index >= len(self._lights):
            return self.async_create_entry(title="Nature Remo", data=self._data)

        appliance = self._lights[self._light_index]
        choices = button_choices(appliance)
        options = [
            selector.SelectOptionDict(value=name, label=label)
            for name, label in choices.items()
        ]
        button_selector = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=options, mode=selector.SelectSelectorMode.DROPDOWN
            )
        )
        default_on, default_off = default_buttons(list(choices))
        return self.async_show_form(
            step_id="light",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ON_BUTTON, default=default_on): button_selector,
                    vol.Required(CONF_OFF_BUTTON, default=default_off): button_selector,
                }
            ),
            description_placeholders={
                "name": appliance.nickname,
                "current": str(self._light_index + 1),
                "total": str(len(self._lights)),
            },
        )
