"""File for sending signal"""
import asyncio
import logging


from homeassistant.components.button import SERVICE_PRESS, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform

from .api import RemoAPI
from .const import DOMAIN, GeneralAppliance, NetworkError
from .select import SignalEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: entity_platform.AddEntitiesCallback,
) -> None:
    """Set up nature remo appliances from a config entry."""
    _LOGGER.warning("start button setup")
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_PRESS,
        {},
        ApplianceEntity._async_press_action.__name__,
    )
    entities = []
    api: RemoAPI = hass.data[DOMAIN][entry.entry_id]["api"]
    signal_entities = hass.data[DOMAIN][entry.entry_id]["signal_entities"]
    appliances = hass.data[DOMAIN][entry.entry_id]["appliances"]
    for appliance, signal_entity in zip(appliances, signal_entities):
        entities.append(ApplianceEntity(appliance, signal_entity, api))
    async_add_entities(entities)


class ApplianceEntity(ButtonEntity):
    """Class for sending signals"""

    _attr_has_entity_name = True

    def __init__(
        self, appliance: GeneralAppliance, signal_entity: SignalEntity, api: RemoAPI
    ) -> None:
        self._attr_name = f"Send Signal @ {appliance.name}"
        self._attr_unique_id = f"Send Signal @ {appliance.id}"
        self.signal_entity = signal_entity
        self.api = api

    def press(self) -> None:
        """Press the button."""
        asyncio.run(self.async_press)

    async def async_press(self) -> None:
        """Press the button."""
        signal_id = self.signal_entity.get_signal_id()
        if signal_id is not None:
            try:
                await self.api.send_ir_signal(signal_id)
            except NetworkError as err:
                _LOGGER.exception(err)
            except Exception as err:
                _LOGGER.exception(err)
