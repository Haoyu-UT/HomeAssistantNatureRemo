"""File defining temperature sensor"""
import datetime
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

from .api import RemoAPI
from .const import DOMAIN, Appliances, SensorData

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
    hass.data[DOMAIN][entry.entry_id]["sensor_coordinator"] = coordinator
    for mac, sensor_data in sensor_data_dic.items():
        device_name = device_name_dic[mac]
        if (val := sensor_data.temperature) is not None:
            sensors.append(TemperatureSensor(coordinator, mac, device_name, val))
        if (val := sensor_data.humidity) is not None:
            sensors.append(HumiditySensor(coordinator, mac, device_name, val))
        if val := sensor_data.illuminance is not None:
            sensors.append(IlluminanceSensor(coordinator, mac, device_name, val))
        if (val := sensor_data.movement) is not None:
            sensors.append(MovementSensor(coordinator, mac, device_name, val))
    appliances: Appliances = hass.data[DOMAIN][entry.entry_id]["appliances"]
    coordinator = ApplianceCoordinator(hass, api)
    hass.data[DOMAIN][entry.entry_id]["appliance_coordinator"] = coordinator
    if appliances.electricitymeter:
        for properties in appliances.electricitymeter:
            unique_id, name = properties["id"], properties["nickname"]
            sensors.append(ElectricityMeter(coordinator, unique_id, name))
    hass.data[DOMAIN][entry.entry_id]["sensors"] = sensors
    async_add_entities(sensors)


class SensorCoordinator(DataUpdateCoordinator):
    """Coordinator for polling Remo sensor data"""

    def __init__(self, hass: HomeAssistant, api: RemoAPI) -> None:
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name="Remo API Coordinator for sensors",
            update_interval=datetime.timedelta(seconds=60),
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

    def __init__(self, coordinator, mac, name, init_val) -> None:
        # this step sets self.coordinator
        super().__init__(coordinator)
        self.mac = mac
        self._attr_unique_id = f"Temperature Sensor @ {mac}"
        self._attr_name = f"Temperature Sensor @ {name}"
        self._attr_native_value = init_val

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

    def __init__(self, coordinator, mac, name, init_val) -> None:
        # this step sets self.coordinator
        super().__init__(coordinator)
        self.mac = mac
        self._attr_unique_id = f"Humidity Sensor @ {mac}"
        self._attr_name = f"Humidity Sensor @ {name}"
        self._attr_native_value = init_val

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

    def __init__(self, coordinator, mac, name, init_val) -> None:
        # this step sets self.coordinator
        super().__init__(coordinator)
        self.mac = mac
        self._attr_unique_id = f"Illuminance Sensor @ {mac}"
        self._attr_name = f"Illuminance Sensor @ {name}"
        self._attr_native_value = init_val

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

    def __init__(self, coordinator, mac, name, init_val) -> None:
        # this step sets self.coordinator
        super().__init__(coordinator)
        self.mac = mac
        self._attr_unique_id = f"Movement Sensor @ {mac}"
        self._attr_name = f"Movement Sensor @ {name}"
        self._attr_native_value = init_val

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        time_str = self.coordinator.data[self.mac].movement
        self._attr_native_value = datetime.datetime.fromisoformat(
            time_str[:-1] + "+00:00"
        )
        self.async_write_ha_state()


class ApplianceCoordinator(DataUpdateCoordinator):
    """Coordinator for polling appliance data"""

    def __init__(self, hass: HomeAssistant, api: RemoAPI) -> None:
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name="Remo API Coordinator for appliances",
            update_interval=datetime.timedelta(seconds=60),
            update_method=self.api.fetch_appliance,
        )


class ElectricityMeter(CoordinatorEntity, SensorEntity):
    """Class providing electricity meter function"""

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
            for p in self.coordinator.data.electricitymeter
            if p["id"] == self._attr_unique_id
        )
        value = next(
            int(p["val"])
            for p in properties["smart_meter"]["echonetlite_properties"]
            if p["epc"] == 231
        )
        self._attr_native_value = value
        self.async_write_ha_state()
