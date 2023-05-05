"""File defining temperature sensor"""
from datetime import timedelta
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import LIGHT_LUX, PERCENTAGE, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .api import Appliances, RemoAPI, SensorData
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up nature remo sensors from a config entry."""
    sensors = []
    api: RemoAPI = hass.data[DOMAIN][entry.entry_id]["api"]
    sensor_data_dic: dict[str, SensorData] = await api.fecth_sensor_data()
    device_name_dic: dict[str, str] = await api.fetch_device_name()
    coordinator = SensorCoordinator(hass, api)
    for mac, sensor_data in sensor_data_dic.items():
        if sensor_data.temperature is not None:
            sensors.append(TemperatureSensor(coordinator, mac, device_name_dic[mac]))
        if sensor_data.humidity is not None:
            sensors.append(HumiditySensor(coordinator, mac, device_name_dic[mac]))
        if sensor_data.illuminance is not None:
            sensors.append(IlluminanceSensor(coordinator, mac, device_name_dic[mac]))
        if sensor_data.movement is not None:
            sensors.append(MovementSensor(coordinator, mac, device_name_dic[mac]))
    appliances: Appliances = await api.fetch_appliance()
    if appliances.powermeter:
        coordinator = PowerMeterCoordinator(hass, api)
        for properties in appliances.powermeter:
            unique_id, name = properties["id"], properties["nickname"]
            sensors.append(PowerMeter(coordinator, unique_id, name))
    async_add_entities(sensors)


class SensorCoordinator(DataUpdateCoordinator):
    """Coordinator for polling Remo sensor data"""

    def __init__(self, hass: HomeAssistant, api: RemoAPI) -> None:
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name="Remo API Coordinator",
            update_interval=timedelta(seconds=60),
            update_method=self.api.fecth_sensor_data,
        )


class TemperatureSensor(CoordinatorEntity, SensorEntity):
    """Class providing temperature sensor function"""

    _attr_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_has_entity_name = True
    _attr_should_poll = True
    _attr_device_info = {}
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, mac, name) -> None:
        # this step sets self.coordinator
        super().__init__(coordinator)
        self.mac = mac
        self._attr_unique_id = f"Temperature Sensor @ {mac}"
        self._attr_name = f"Temperature Sensor @ {name}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.coordinator.data[self.mac].temperature
        self.async_write_ha_state()


class HumiditySensor(CoordinatorEntity, SensorEntity):
    """Class providing humidity sensor function"""

    _attr_unit_of_measurement = PERCENTAGE
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_has_entity_name = True
    _attr_should_poll = True
    _attr_device_info = {}
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, mac, name) -> None:
        # this step sets self.coordinator
        super().__init__(coordinator)
        self.mac = mac
        self._attr_unique_id = f"Humidity Sensor @ {mac}"
        self._attr_name = f"Humidity Sensor @ {name}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.coordinator.data[self.mac].humidity
        self.async_write_ha_state()


class IlluminanceSensor(CoordinatorEntity, SensorEntity):
    """Class providing illuminance sensor function"""

    _attr_unit_of_measurement = LIGHT_LUX
    _attr_native_unit_of_measurement = LIGHT_LUX
    _attr_has_entity_name = True
    _attr_should_poll = True
    _attr_device_info = {}
    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, mac, name) -> None:
        # this step sets self.coordinator
        super().__init__(coordinator)
        self.mac = mac
        self._attr_unique_id = f"Illuminance Sensor @ {mac}"
        self._attr_name = f"Illuminance Sensor @ {name}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.coordinator.data[self.mac].illuminance
        self.async_write_ha_state()


class MovementSensor(CoordinatorEntity, SensorEntity):
    """Class providing movement sensor function"""

    _attr_has_entity_name = True
    _attr_should_poll = True
    _attr_device_info = {}
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, mac, name) -> None:
        # this step sets self.coordinator
        super().__init__(coordinator)
        self.mac = mac
        self._attr_unique_id = f"Movement Sensor @ {mac}"
        self._attr_name = f"Movement Sensor @ {name}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.coordinator.data[self.mac].movement
        self.async_write_ha_state()


class PowerMeterCoordinator(DataUpdateCoordinator):
    """Coordinator for polling power meter data"""

    def __init__(self, hass: HomeAssistant, api: RemoAPI) -> None:
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name="Remo API Coordinator for Power Meter",
            update_interval=timedelta(seconds=60),
            update_method=self.api.fetch_appliance,
        )


class PowerMeter(CoordinatorEntity, SensorEntity):
    """Class providing power meter function"""

    _attr_unit_of_measurement = UnitOfPower.WATT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_has_entity_name = True
    _attr_should_poll = True
    _attr_device_info = {}
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, unique_id, name) -> None:
        # this step sets self.coordinator
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._attr_name = name

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        properties = next(
            p
            for p in self.coordinator.data.powermeter
            if p["id"] == self._attr_unique_id
        )
        value = next(
            int(p["val"])
            for p in properties["smart_meter"]["echonetlite_properties"]
            if p["epc"] == 231
        )
        self._attr_native_value = value
        self.async_write_ha_state()
