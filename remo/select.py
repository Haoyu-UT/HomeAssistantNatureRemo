"""File for selecting signal"""

import logging

import voluptuous as vol

from homeassistant.components.select import (
    ATTR_OPTION,
    SERVICE_SELECT_OPTION,
    SelectEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_platform

from .api import RemoAPI
from .const import DOMAIN, Appliance, Appliances, NoSignalError, Signal

_LOGGER = logging.getLogger(__name__)


def extract_general_appliance(properties: dict) -> Appliance:
    """Build general Appliance from given properties"""
    app_id, app_name = properties["id"], properties["nickname"]
    signals = []
    for signal in properties["signals"]:
        signal_id, signal_name = signal["id"], signal["name"]
        signals.append(Signal(signal_id, signal_name))
    if signals:
        return Appliance(app_id, app_name, signals)
    else:
        raise NoSignalError


def extract_light_appliance(properties: dict) -> Appliance:
    """Build light Appliance from given properties"""
    app_id, app_name = properties["id"], properties["nickname"]
    signals = [button["name"] for button in properties["light"]["buttons"]]
    return Appliance(app_id, app_name, signals)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: entity_platform.AddEntitiesCallback,
) -> None:
    """Set up nature remo appliances from a config entry."""
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_SELECT_OPTION,
        {vol.Required(ATTR_OPTION): cv.string},
        "async_select_option",
    )
    entities = []
    api: RemoAPI = hass.data[DOMAIN][entry.entry_id]["api"]
    appliances: Appliances = hass.data[DOMAIN][entry.entry_id]["appliances"]
    hass.data[DOMAIN][entry.entry_id]["signal_appliances"] = []
    hass.data[DOMAIN][entry.entry_id]["signal_entities"] = []
    for properties in appliances.others:
        try:
            appliance: Appliance = extract_general_appliance(properties)
        except NoSignalError:
            logging.exception(
                "appliance %s has no signal binded", properties["nickname"]
            )
        else:
            hass.data[DOMAIN][entry.entry_id]["signal_appliances"].append(appliance)
            signal_entity = SignalEntity(appliance, api)
            hass.data[DOMAIN][entry.entry_id]["signal_entities"].append(signal_entity)
            entities.append(signal_entity)
    for properties in appliances.light:
        appliance: Appliance = extract_light_appliance(properties)
        hass.data[DOMAIN][entry.entry_id]["signal_appliances"].append(appliance)
        signal_entity = LightSignalEntity(appliance, api)
        hass.data[DOMAIN][entry.entry_id]["signal_entities"].append(signal_entity)
        entities.append(signal_entity)
    async_add_entities(entities)


class SignalEntity(SelectEntity):
    """Class for containing signals"""

    _attr_has_entity_name = True

    def __init__(self, appliance: Appliance, api: RemoAPI) -> None:
        self.api = api
        self._attr_name = f"Signals @ {appliance.name}"
        self._attr_unique_id = f"Signals @ {appliance.id}"
        self.signals: list[Signal] = appliance.signals
        self._attr_options = [
            f"{i+1}. {signal.name}" for i, signal in enumerate(self.signals)
        ]
        self._attr_current_option = self._attr_options[0]
        self.option_idx_map = {option: i for i, option in enumerate(self._attr_options)}
        self.current_option_idx = 0

    def select_option(self, option: str) -> None:
        """Change the selected option."""
        self._attr_current_option = option
        self.current_option_idx = self.option_idx_map[option]

    async def send_signal(self):
        """Send signal of current selection"""
        signal_id = self.signals[self.current_option_idx].id
        return await self.api.send_ir_signal(signal_id)


class LightSignalEntity(SelectEntity):
    """Class for containing signals of lights"""

    _attr_has_entity_name = True

    def __init__(self, appliance: Appliance, api: RemoAPI) -> None:
        self.api = api
        self.light_id = appliance.id
        self.buttons: list[str] = appliance.signals
        self._attr_name = f"Signals @ {appliance.name}"
        self._attr_unique_id = f"Signals @ {appliance.id}"
        self._attr_options = [
            f"{i+1}. {signal}" for i, signal in enumerate(self.buttons)
        ]
        self._attr_current_option = self._attr_options[0]
        self.current_button = self.buttons[0]
        self.option_idx_map = {option: i for i, option in enumerate(self._attr_options)}

    def select_option(self, option: str) -> None:
        """Change the selected option."""
        self._attr_current_option = option
        self.current_button = self.buttons[self.option_idx_map[option]]

    async def send_signal(self):
        """Send signal of current selection"""
        return await self.api.send_light_signal(self.light_id, self.current_button)
