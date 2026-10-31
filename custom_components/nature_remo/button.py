"""File for sending signal"""
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform

from .const import DOMAIN, Appliance
from .select import LightSignalEntity, SignalEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: entity_platform.AddEntitiesCallback,
) -> None:
    """Set up nature remo appliances from a config entry."""
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
        await self.signal_entity.send_signal()
