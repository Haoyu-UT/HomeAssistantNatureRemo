"""File defining temperature sensor"""
import datetime
import logging
import time

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    LIGHT_LUX,
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .api import RemoAPI
from .const import (
    DOMAIN,
    ENERGY_UNIT_COEFFICIENT_MAP,
    EPC_ITEM_NAME_MAP,
    EPC_ITEM_VALUE_MAP,
    EPC_ITEMS,
    EPC_VALUE_ITEM_MAP,
    Appliances,
    SensorData,
)

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
        if (val := sensor_data.illuminance) is not None:
            sensors.append(IlluminanceSensor(coordinator, mac, device_name, val))
        if (val := sensor_data.movement) is not None:
            sensors.append(MovementSensor(coordinator, mac, device_name, val))
    appliances: Appliances = hass.data[DOMAIN][entry.entry_id]["appliances"]
    coordinator = ApplianceCoordinator(hass, api)
    hass.data[DOMAIN][entry.entry_id]["appliance_coordinator"] = coordinator
    for properties in appliances.power_energy_meter:
        mac = properties["device"]["mac_address"]
        device_name = device_name_dic[mac]
        epc_items = {
            EPC_VALUE_ITEM_MAP[p["epc"]]
            for p in properties["smart_meter"]["echonetlite_properties"]
        }
        target_epc_items = {
            EPC_ITEMS.power,
            EPC_ITEMS.comsumed_energy,
            EPC_ITEMS.generated_energy,
        }
        for epc_item in target_epc_items & epc_items:
            sensors.append(
                PowerEnergyMeter(epc_item, coordinator, mac, device_name, properties)
            )
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

    @staticmethod
    def timestamp_to_datetime(timestamp: str):
        return datetime.datetime.fromisoformat(timestamp[:-1] + "+00:00")

    def __init__(self, coordinator, mac, name, init_val) -> None:
        # this step sets self.coordinator
        super().__init__(coordinator)
        self.mac = mac
        self._attr_unique_id = f"Movement Sensor @ {mac}"
        self._attr_name = f"Movement Sensor @ {name}"
        self._attr_native_value = self.timestamp_to_datetime(init_val)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        time_str = self.coordinator.data[self.mac].movement
        self._attr_native_value = self.timestamp_to_datetime(time_str)
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


class PowerEnergyMeter(CoordinatorEntity, SensorEntity):
    """Class providing electricity or power meter function"""

    _attr_has_entity_name = True
    _attr_should_poll = True
    _attr_device_info = {}
    _attr_native_value = 0.0

    @staticmethod
    def get_raw_value(properties: dict, epc_item: EPC_ITEMS):
        return next(
            int(p["val"])
            for p in properties["smart_meter"]["echonetlite_properties"]
            if p["epc"] == EPC_ITEM_VALUE_MAP[epc_item]
        )

    def __init__(self, epc_item, coordinator, mac, name, init_properties) -> None:
        # this step sets self.coordinator
        super().__init__(coordinator)
        self.epc_item = epc_item
        self.epc_value = EPC_ITEM_VALUE_MAP[epc_item]
        self.epc_name = EPC_ITEM_NAME_MAP[epc_item]
        self.mac = mac
        self._attr_unique_id = f"{self.epc_name} @ {mac}"
        self._attr_name = f"{self.epc_name} @ {name}"
        if epc_item == EPC_ITEMS.power:
            self._attr_unit_of_measurement = UnitOfPower.WATT
            self._attr_native_unit_of_measurement = UnitOfPower.WATT
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_state_class = SensorStateClass.MEASUREMENT
        else:
            self._attr_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
            self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            energy_coefficient = self.get_raw_value(
                init_properties, EPC_ITEMS.energy_coefficient
            )
            energy_unit_coefficient = ENERGY_UNIT_COEFFICIENT_MAP[
                self.get_raw_value(init_properties, EPC_ITEMS.energy_unit)
            ]
            energy_max_digits = self.get_raw_value(
                init_properties, EPC_ITEMS.energy_max_digits
            )
            self.coefficient = float(energy_coefficient * energy_unit_coefficient)
            self.max_value = float(self.coefficient * int("9" * energy_max_digits))

        self.update_state(init_properties)

    def update_state(self, properties: dict):
        raw_val = self.get_raw_value(properties, self.epc_item)
        if self.epc_item == EPC_ITEMS.power:
            self._attr_native_value = raw_val
        else:
            value = float(self.coefficient * raw_val)
            if value < self._attr_native_value:
                # reseted since last update
                self._attr_native_value = self.max_value
                self.async_write_ha_state()
                time.sleep(1.0)
            self._attr_native_value = value

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        properties = next(
            p
            for p in self.coordinator.data.power_energy_meter
            if p["device"]["mac_address"] == self.mac
        )
        self.update_state(properties)
        self.async_write_ha_state()
