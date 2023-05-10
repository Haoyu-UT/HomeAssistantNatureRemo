"""File for sending signal"""
import logging

from homeassistant.components.button import SERVICE_PRESS, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform

from .const import DOMAIN, Appliance, NetworkError
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
    signal_entities = hass.data[DOMAIN][entry.entry_id]["signal_entities"]
    appliances = hass.data[DOMAIN][entry.entry_id]["signal_appliances"]
    for appliance, signal_entity in zip(appliances, signal_entities):
        entities.append(ApplianceEntity(appliance, signal_entity))
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
