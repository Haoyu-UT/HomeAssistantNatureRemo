"""File for controling air conditioners"""
import datetime
import logging
from typing import Any, Optional

import voluptuous as vol

import homeassistant.components.climate as Climate
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import RemoAPI
from .const import (
    AC,
    DOMAIN,
    MODE_ACTION_MAP,
    MODE_MAP,
    ACStatus,
    Appliances,
    ModeSpec,
    UnexpectedAC,
)
from .sensor import ApplianceCoordinator, HumiditySensor, TemperatureSensor

_LOGGER = logging.getLogger(__name__)


def extract_last_settings(settings: dict) -> ACStatus:
    """Extract last ACStatus from json"""
    return ACStatus(
        "off" if settings["button"] == "power-off" else "on",
        settings["dir"],
        settings["dirh"],
        MODE_MAP[settings["mode"]],
        float(settings["temp"]),
        UnitOfTemperature.CELSIUS,
        settings["vol"],
        datetime.datetime.fromisoformat(settings["updated_at"][:-1] + "+00:00"),
    )


def extract_ac_properties(properties: dict, sensors: list) -> AC:
    """Extract AC properties from json"""
    assert properties["aircon"]["tempUnit"] == "c"
    assert "power-off" in properties["aircon"]["range"]["fixedButtons"]
    temperature_unit = UnitOfTemperature.CELSIUS
    ac_name, remo_name = properties["nickname"], properties["device"]["name"]
    name = f"{ac_name} @ {remo_name}"
    ac_id = properties["id"]
    remo_mac = properties["device"]["mac_address"]
    temperature_sensor: Optional[TemperatureSensor] = next(
        (
            sensor
            for sensor in sensors
            if isinstance(sensor, TemperatureSensor) and sensor.mac == remo_mac
        ),
        None,
    )
    humidity_sensor: Optional[HumiditySensor] = next(
        (
            sensor
            for sensor in sensors
            if isinstance(sensor, HumiditySensor) and sensor.mac == remo_mac
        ),
        None,
    )
    ac_properties = properties["aircon"]["range"]["modes"]
    feature_flag = (
        Climate.const.ClimateEntityFeature.TARGET_TEMPERATURE
        | Climate.const.ClimateEntityFeature.FAN_MODE
    )
    modes = {Climate.const.HVACMode.OFF: ModeSpec(None, None, None, None, [], [])}
    for mode, mode_properties in ac_properties.items():
        if mode in MODE_MAP:
            swing = list(filter(bool, mode_properties["dir"]))
            swing_h = list(filter(bool, mode_properties["dirh"]))
            fan_modes = list(filter(bool, mode_properties["vol"]))
            if swing or swing_h:
                feature_flag |= Climate.const.ClimateEntityFeature.SWING_MODE
            temps = sorted(map(int, mode_properties["temp"]))
            # assert temps is continuous and the step is 1
            assert all(temps[i + 1] - 1 == temps[i] for i in range(len(temps) - 1))
            modes[MODE_MAP[mode]] = ModeSpec(
                float(min(temps)), float(max(temps)), 1.0, fan_modes, swing, swing_h
            )
        else:
            _LOGGER.warning(
                "Unknown AC mode %s; please contact the project maintainer", mode
            )
    last_status = extract_last_settings(properties["settings"])
    return AC(
        ac_id,
        name,
        temperature_unit,
        Climate.const.ClimateEntityFeature(feature_flag),
        temperature_sensor,
        humidity_sensor,
        last_status,
        modes,
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up nature remo sensors from a config entry."""
    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_TURN_ON, {}, AirConditioner.async_turn_on.__name__
    )
    platform.async_register_entity_service(
        SERVICE_TURN_OFF, {}, AirConditioner.async_turn_off.__name__
    )
    platform.async_register_entity_service(
        Climate.const.SERVICE_SET_HVAC_MODE,
        {
            vol.Required(Climate.const.ATTR_HVAC_MODE): vol.Coerce(
                Climate.const.HVACMode
            )
        },
        AirConditioner.async_set_hvac_mode.__name__,
    )
    platform.async_register_entity_service(
        Climate.const.SERVICE_SET_TEMPERATURE,
        Climate.SET_TEMPERATURE_SCHEMA,
        Climate.async_service_temperature_set,
        [Climate.const.ClimateEntityFeature.TARGET_TEMPERATURE],
    )
    platform.async_register_entity_service(
        Climate.const.SERVICE_SET_FAN_MODE,
        {vol.Required(Climate.const.ATTR_FAN_MODE): cv.string},
        AirConditioner.async_set_fan_mode.__name__,
        [Climate.ClimateEntityFeature.FAN_MODE],
    )
    platform.async_register_entity_service(
        Climate.const.SERVICE_SET_SWING_MODE,
        {vol.Required(Climate.const.ATTR_SWING_MODE): cv.string},
        AirConditioner.async_set_swing_mode.__name__,
        [Climate.ClimateEntityFeature.SWING_MODE],
    )
    entities = []
    store = hass.data[DOMAIN][entry.entry_id]
    api: RemoAPI = store["api"]
    sensors = store["sensors"]
    appliances: Appliances = store["appliances"]
    coordinator: ApplianceCoordinator = store["appliance_coordinator"]
    for properties in appliances.ac:
        try:
            data = extract_ac_properties(properties, sensors)
        except Exception as err:
            _LOGGER.critical(
                "Unexpected AC configuration; please contact the project maintainer"
            )
            raise UnexpectedAC from err
        else:
            entities.append(AirConditioner(data, api, coordinator))
    async_add_entities(entities)


class AirConditioner(CoordinatorEntity, Climate.ClimateEntity):
    """Class providing air conditioner control"""

    _attr_has_entity_name = True
    last_update_timestamp: datetime.datetime
    last_hvac_mode: Climate.const.HVACMode
    mode_min_temp: float
    mode_max_temp: float
    mode_target_temp: dict[str, float]
    mode_target_fan_mode: dict[str, str]
    mode_target_swing_mode: dict[str, str]

    def recover_status_from_ac_status(self, status: ACStatus):
        """Recover status from ACStatus"""
        self.last_hvac_mode = status.mode
        self._attr_hvac_mode = (
            Climate.const.HVACMode.OFF if status.power == "off" else status.mode
        )
        self._attr_hvac_action = MODE_ACTION_MAP[self.hvac_mode]
        self._attr_fan_mode = status.fan_mode
        self.mode_target_fan_mode[status.mode] = status.fan_mode
        self._attr_swing_mode = status.swing
        self.mode_target_swing_mode[status.mode] = status.swing
        self.last_update_timestamp = status.timestamp
        self._attr_fan_modes = self.data.modes[status.mode].fan_modes
        self.mode_min_temp = self.data.modes[status.mode].low_temp
        self.mode_max_temp = self.data.modes[status.mode].high_temp
        self.mode_target_temp[status.mode] = status.target_temperature
        self._attr_target_temperature = status.target_temperature
        self._attr_target_temperature_step = self.data.modes[status.mode].step
        self._attr_swing_modes = self.data.modes[status.mode].swing_modes

    def __init__(
        self, data: AC, api: RemoAPI, coordinator: ApplianceCoordinator
    ) -> None:
        # this step sets self.coordinator
        super().__init__(coordinator)
        self.data = data
        self.api = api
        self._attr_name = data.name
        self._attr_unique_id = f"{data.name} @ {data.id}"
        self._attr_temperature_unit = data.temperature_unit
        self._attr_supported_features = data.feature_flag
        self._attr_hvac_modes = sorted(data.modes.keys())
        self.mode_target_temp = {
            mode: float(
                round((data.modes[mode].low_temp + data.modes[mode].high_temp) / 2)
            )
            for mode in self.hvac_modes
            if mode != Climate.const.HVACMode.OFF
        }
        self.mode_target_fan_mode = {
            mode: data.modes[mode].fan_modes[0]
            for mode in self.hvac_modes
            if mode != Climate.const.HVACMode.OFF
        }
        self.mode_target_swing_mode = {
            mode: data.modes[mode].swing_modes[0]
            for mode in self.hvac_modes
            if mode != Climate.const.HVACMode.OFF
        }
        if data.temperature_sensor is not None:
            self._attr_current_temperature = data.temperature_sensor.native_value
        if data.humidity_sensor is not None:
            self._attr_current_humidity = data.humidity_sensor.native_value
        self.recover_status_from_ac_status(data.last_status)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        properties = next(
            ac for ac in self.coordinator.data.ac if ac["id"] == self.data.id
        )
        fetched_status = extract_last_settings(properties["settings"])
        if fetched_status.timestamp > self.last_update_timestamp:
            self.recover_status_from_ac_status(fetched_status)
        if self.data.temperature_sensor is not None:
            self._attr_current_temperature = self.data.temperature_sensor.native_value
        if self.data.humidity_sensor is not None:
            self._attr_current_humidity = self.data.humidity_sensor.native_value
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        self._attr_hvac_mode = self.last_hvac_mode
        self._attr_target_temperature = self.mode_target_temp[self.hvac_mode]
        self._attr_fan_mode = self.mode_target_fan_mode[self.hvac_mode]
        self._attr_swing_mode = self.mode_target_swing_mode[self.hvac_mode]
        self._attr_hvac_action = MODE_ACTION_MAP[self.hvac_mode]
        await self.api.send_ac_signal(self)
        self.last_update_timestamp = datetime.datetime.now(datetime.timezone.utc)
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        self._attr_hvac_mode = Climate.const.HVACMode.OFF
        self._attr_hvac_action = MODE_ACTION_MAP[self.hvac_mode]
        await self.api.send_ac_signal(self)
        self.last_update_timestamp = datetime.datetime.now(datetime.timezone.utc)
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: Climate.const.HVACMode) -> None:
        if hvac_mode == Climate.const.HVACMode.OFF:
            await self.async_turn_off()
        elif hvac_mode != self.hvac_mode and hvac_mode in self.hvac_modes:
            self.last_hvac_mode = self._attr_hvac_mode = hvac_mode
            self._attr_hvac_action = MODE_ACTION_MAP[hvac_mode]
            self._attr_fan_mode = self.mode_target_fan_mode[hvac_mode]
            self._attr_fan_modes = self.data.modes[hvac_mode].fan_modes
            self.mode_min_temp = self.data.modes[hvac_mode].low_temp
            self.mode_max_temp = self.data.modes[hvac_mode].high_temp
            self._attr_target_temperature = self.mode_target_temp[hvac_mode]
            self._attr_target_temperature_step = self.data.modes[hvac_mode].step
            self._attr_swing_mode = self.mode_target_swing_mode[hvac_mode]
            self._attr_swing_modes = self.data.modes[hvac_mode].swing_modes
            await self.api.send_ac_signal(self)
            self.last_update_timestamp = datetime.datetime.now(datetime.timezone.utc)
            self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs["temperature"]
        new_temp = min(self.mode_max_temp, max(self.mode_min_temp, temperature))
        if round(new_temp) != round(self.target_temperature):
            self._attr_target_temperature = new_temp
            self.mode_target_temp[self.hvac_mode] = new_temp
            await self.api.send_ac_signal(self)
            self.last_update_timestamp = datetime.datetime.now(datetime.timezone.utc)
            self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        if fan_mode != self.fan_mode and fan_mode in self.fan_modes:
            self._attr_fan_mode = fan_mode
            self.mode_target_fan_mode[self.hvac_mode] = fan_mode
            await self.api.send_ac_signal(self)
            self.last_update_timestamp = datetime.datetime.now(datetime.timezone.utc)
            self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        if swing_mode != self.swing_mode and swing_mode in self.swing_modes:
            self._attr_swing_mode = swing_mode
            self.mode_target_swing_mode[self.hvac_mode] = swing_mode
            await self.api.send_ac_signal(self)
            self.last_update_timestamp = datetime.datetime.now(datetime.timezone.utc)
            self.async_write_ha_state()
