"""File for sending signal"""
import logging

from homeassistant.components.button import SERVICE_PRESS, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform

from .api import RemoAPI
from .const import DOMAIN, TV_BUTTON_LABEL_MAP, Appliance, Appliances, NetworkError
from .select import LightSignalEntity, SignalEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: entity_platform.AddEntitiesCallback,
) -> None:
    """Set up nature remo appliances from a config entry."""
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_PRESS,
        {},
        ApplianceEntity._async_press_action.__name__,
    )
    entities = []
    api: RemoAPI = hass.data[DOMAIN][entry.entry_id]["api"]
    appliances: Appliances = hass.data[DOMAIN][entry.entry_id]["appliances"]
    signal_entities = hass.data[DOMAIN][entry.entry_id]["signal_entities"]
    signal_appliances = hass.data[DOMAIN][entry.entry_id]["signal_appliances"]
    for appliance, signal_entity in zip(signal_appliances, signal_entities):
        entities.append(ApplianceEntity(appliance, signal_entity))
    for properties in appliances.tv:
        app_id = properties["id"]
        app_name = properties["nickname"]
        tv_buttons = properties.get("tv", {}).get("buttons", [])
        for button_info in tv_buttons:
            button_name = button_info["name"]
            label = TV_BUTTON_LABEL_MAP.get(button_name, button_name)
            entities.append(TvButtonEntity(app_id, app_name, button_name, label, api))
    async_add_entities(entities)


class ApplianceEntity(ButtonEntity):
    """Class for sending signals on general appliances"""

    _attr_has_entity_name = True

    def __init__(
        self, appliance: Appliance, signal_entity: SignalEntity | LightSignalEntity
    ) -> None:
        self._attr_name = f"Send Signal @ {appliance.name}"
        self._attr_unique_id = f"Send Signal @ {appliance.id}"
        self.signal_entity = signal_entity

    async def async_press(self) -> None:
        """Press the button."""
        try:
            await self.signal_entity.send_signal()
        except NetworkError as err:
            _LOGGER.exception(err)
        except Exception as err:
            _LOGGER.exception(err)


class TvButtonEntity(ButtonEntity):
    """Button entity for a single TV remote button"""

    _attr_has_entity_name = True

    def __init__(
        self,
        app_id: str,
        app_name: str,
        button_name: str,
        label: str,
        api: RemoAPI,
    ) -> None:
        self.app_id = app_id
        self.button_name = button_name
        self.api = api
        self._attr_name = f"{label} @ {app_name}"
        self._attr_unique_id = f"tv_{app_id}_{button_name}"

    async def async_press(self) -> None:
        """Send the TV button signal."""
        try:
            await self.api.send_tv_signal(self.app_id, self.button_name)
        except NetworkError as err:
            _LOGGER.exception(err)
        except Exception as err:
            _LOGGER.exception(err)
