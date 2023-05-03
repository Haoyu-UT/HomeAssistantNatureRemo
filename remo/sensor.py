"""File defining temperature sensor"""
from datetime import timedelta
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .api import RemoAPI, SensorData
from .const import DOMAIN, AuthError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up nature_remo from a config entry."""
    devices = []
    api = hass.data[DOMAIN][entry.entry_id]
    sensor_data_dic: dict[str, SensorData] = await api.fecth_sensor_data()
    coordinator = MyCoordinator(hass, api)
    for mac, sensor_data in sensor_data_dic.items():
        if sensor_data.temperature:
            devices.append(TemperatureSensor(coordinator, mac))
    async_add_entities(devices)


class MyCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass: HomeAssistant, api: RemoAPI) -> None:
        """Initialize my coordinator."""
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name="Remo Temperature Sensor",
            update_interval=timedelta(seconds=60),
            update_method=self.api.fecth_sensor_data,
        )

class TemperatureSensor(CoordinatorEntity, SensorEntity):
    """Class providing sensor function"""

    _attr_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_has_entity_name = True
    _attr_name = "Remo Temperature Sensor"
    _attr_should_poll = True
    _attr_device_info = {}

    def __init__(self, coordinator, mac) -> None:
        # this step sets self.coordinator
        super().__init__(coordinator)
        self._attr_unique_id = mac

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.coordinator.data[self._attr_unique_id].temperature
        self.async_write_ha_state()
