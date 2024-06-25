"""File for controling air conditioners"""
import asyncio
import copy
import datetime
import itertools
import logging
from typing import Any, Optional

import voluptuous as vol

import homeassistant.components.climate as Climate
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform, restore_state
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import RemoAPI
from .const import (
    AC,
    DOMAIN,
    HVAC_MODE_ACTION_MAP,
    HVAC_MODE_MAP,
    ACStatus,
    Appliances,
    ModeSpec,
    SwingModePair,
    UnexpectedAC,
)
from .sensor import ApplianceCoordinator, HumiditySensor, TemperatureSensor

_LOGGER = logging.getLogger(__name__)


def extract_last_settings(settings: dict) -> ACStatus:
    """Extract last ACStatus from json"""
    try:
        temp = float(settings["temp"])
    except ValueError:
        temp = 0.0
    return ACStatus(
        "off" if settings["button"] == "power-off" else "on",
        SwingModePair(v=settings["dir"], h=settings["dirh"]),
        HVAC_MODE_MAP[settings["mode"]],
        temp,
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
        | Climate.const.ClimateEntityFeature.SWING_MODE
        | Climate.const.ClimateEntityFeature.TURN_OFF
        | Climate.const.ClimateEntityFeature.TURN_ON
    )
    modes = {
        Climate.const.HVACMode.OFF: ModeSpec(
            None, None, None, None, None, None, None, None, None
        )
    }
    for mode, mode_properties in ac_properties.items():
        if mode in HVAC_MODE_MAP:
            swings = mode_properties["dir"]
            swings_h = mode_properties["dirh"]
            swingmodepairs = [
                SwingModePair(*p) for p in itertools.product(swings, swings_h)
            ]
            fan_modes = mode_properties["vol"]
            assert len(mode_properties["temp"]) >= 1
            if len(mode_properties["temp"]) == 1:
                # the case where no adjustable temps are provided
                try:
                    temps_str = mode_properties["temp"]
                    temps_float = [float(temps_str[0])]
                    modes[HVAC_MODE_MAP[mode]] = ModeSpec(
                        temps_str,
                        temps_float,
                        temps_float[0],
                        temps_float[0],
                        None,
                        fan_modes,
                        swings,
                        swings_h,
                        swingmodepairs,
                    )
                except ValueError:
                    assert temps_str[0] == ""
                    modes[HVAC_MODE_MAP[mode]] = ModeSpec(
                        [""],
                        [0.0],
                        0.0,
                        0.0,
                        1.0,
                        fan_modes,
                        swings,
                        swings_h,
                        swingmodepairs,
                    )
            else:
                # the normal case where temps are provided and >= 2
                temps_sorted = sorted((float(t), t) for t in mode_properties["temp"])
                temps_float = [temp_float for temp_float, temp_str in temps_sorted]
                temps_str = [temp_str for temp_float, temp_str in temps_sorted]
                # assert temps are equally stepped, and the step is larger than 0.01
                step_str = f"{temps_float[1]-temps_float[0]:.2f}"
                step_float = float(step_str)
                assert abs(step_float - (temps_float[1] - temps_float[0])) <= 1e-3
                assert all(
                    f"{b-a:.2f}" == step_str
                    for a, b in zip(temps_float[:-1], temps_float[1:])
                )
                modes[HVAC_MODE_MAP[mode]] = ModeSpec(
                    temps_str,
                    temps_float,
                    min(temps_float),
                    max(temps_float),
                    step_float,
                    fan_modes,
                    swings,
                    swings_h,
                    swingmodepairs,
                )
        else:
            _LOGGER.warning(
                "Unknown AC mode %s; please contact the project maintainer", mode
            )
    try:
        last_status = extract_last_settings(properties["settings"])
    except:
        last_status = None
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


class AirConditioner(
    restore_state.RestoreEntity, CoordinatorEntity, Climate.ClimateEntity
):
    """Class providing air conditioner control"""

    _enable_turn_on_off_backwards_compatibility = False
    _attr_has_entity_name = True
    last_update_timestamp: datetime.datetime
    last_hvac_mode: Climate.const.HVACMode
    mode_target_temp_idx: dict[str, int]
    mode_target_fan_mode: dict[str, str]
    mode_target_swingmodepair: dict[str, SwingModePair]

    @property
    def extra_restore_state_data(self) -> restore_state.ExtraStoredData:
        data = {
            "mode_target_fan_mode": self.mode_target_fan_mode,
            "mode_target_temp_idx": self.mode_target_temp_idx,
            "mode_target_swingmodepair": {
                k: [v.v, v.h] for k, v in self.mode_target_swingmodepair.items()
            },
        }
        return restore_state.RestoredExtraData(data)

    def recover_status_from_ac_status(self, status: ACStatus):
        """Recover status from ACStatus"""
        self.last_update_timestamp = status.timestamp
        self.last_hvac_mode = status.mode
        self._attr_hvac_mode = (
            Climate.const.HVACMode.OFF if status.power == "off" else status.mode
        )
        # set attributes of last hvac mode
        modespec: ModeSpec = self.data.modes[status.mode]
        self.mode_target_fan_mode[status.mode] = status.fan_mode
        self.mode_target_swingmodepair[status.mode] = status.swingmodepair
        self.mode_target_temp_idx[status.mode] = modespec.temps_float.index(
            status.target_temperature
        )
        # set attributes of current hvac mode
        modespec: ModeSpec = self.data.modes[self.hvac_mode]
        self._attr_hvac_action = HVAC_MODE_ACTION_MAP[self.hvac_mode]
        self._attr_fan_modes = modespec.fan_modes
        self._attr_target_temperature_low = modespec.low_temp
        self._attr_target_temperature_high = modespec.high_temp
        self._attr_target_temperature_step = modespec.step
        if status.power == "on":
            self._attr_fan_mode = status.fan_mode
            self._attr_swing_mode = str(status.swingmodepair)
            self._attr_target_temperature = status.target_temperature
            self._attr_swing_modes = list(map(str, modespec.swingmodespairs))
            self._attr_min_temp = min(modespec.temps_float)
            self._attr_max_temp = max(modespec.temps_float)
        elif status.power == "off":
            self._attr_fan_mode = None
            self._attr_swing_mode = None
            self._attr_swing_modes = None
            self._attr_target_temperature = 0.0
            self._attr_min_temp = 0.0
            self._attr_max_temp = 0.0

    def __init__(
        self, data: AC, api: RemoAPI, coordinator: ApplianceCoordinator
    ) -> None:
        # this step sets self.coordinator
        _LOGGER.debug("parsed AC modes: %s", str(data.modes))
        super().__init__(coordinator)
        self.data = data
        self.api = api
        self._attr_name = data.name
        self._attr_unique_id = f"{data.name} @ {data.id}"
        self._attr_temperature_unit = data.temperature_unit
        self._attr_supported_features = data.feature_flag
        self._attr_hvac_modes = sorted(data.modes.keys())
        self.mode_target_temp_idx = {
            mode: len(data.modes[mode].temps_float) // 2
            for mode in self.hvac_modes
            if mode != Climate.const.HVACMode.OFF
        }
        self.mode_target_fan_mode = {
            mode: data.modes[mode].fan_modes[0]
            for mode in self.hvac_modes
            if mode != Climate.const.HVACMode.OFF
        }
        self.mode_target_swingmodepair = {
            mode: data.modes[mode].swingmodespairs[0]
            for mode in self.hvac_modes
            if mode != Climate.const.HVACMode.OFF
        }
        if data.temperature_sensor is not None:
            self._attr_current_temperature = data.temperature_sensor.native_value
        if data.humidity_sensor is not None:
            self._attr_current_humidity = data.humidity_sensor.native_value
        # recover from last settings if possible
        if data.last_status is not None:

            def f(task):
                mode = data.last_status.mode
                if (extra_data := task.result()) is not None:
                    extra_data = copy.deepcopy(extra_data.as_dict())
                    for dic in extra_data.values():
                        dic.pop(mode, None)
                    self.mode_target_fan_mode.update(extra_data["mode_target_fan_mode"])
                    self.mode_target_temp_idx.update(extra_data["mode_target_temp_idx"])
                    self.mode_target_swingmodepair.update(
                        {
                            k: SwingModePair(*v)
                            for k, v in extra_data["mode_target_swingmodepair"].items()
                        }
                    )

            loop = asyncio.get_running_loop()
            task = loop.create_task(self.async_get_last_extra_data())
            task.add_done_callback(f)
            self.recover_status_from_ac_status(data.last_status)
        else:
            self._attr_hvac_mode = Climate.const.HVACMode.OFF
            self._attr_hvac_action = HVAC_MODE_ACTION_MAP[self.hvac_mode]
            self.last_hvac_mode = next(
                mode for mode in self.hvac_modes if mode != Climate.const.HVACMode.OFF
            )
            self._attr_target_temperature = 0.0
            self._attr_min_temp = 0.0
            self._attr_max_temp = 0.0
            self.last_update_timestamp = datetime.datetime.now(datetime.timezone.utc)

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
        await self.async_set_hvac_mode(self.last_hvac_mode)

    async def async_turn_off(self) -> None:
        self._attr_hvac_mode = Climate.const.HVACMode.OFF
        self._attr_hvac_action = HVAC_MODE_ACTION_MAP[self.hvac_mode]
        self._attr_target_temperature = 0.0
        self._attr_min_temp = 0.0
        self._attr_max_temp = 0.0
        await self.api.send_ac_signal(self)
        self.last_update_timestamp = datetime.datetime.now(datetime.timezone.utc)
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: Climate.const.HVACMode) -> None:
        if hvac_mode == Climate.const.HVACMode.OFF:
            await self.async_turn_off()
        elif hvac_mode != self.hvac_mode and hvac_mode in self.hvac_modes:
            modespec: ModeSpec = self.data.modes[hvac_mode]
            self.last_hvac_mode = self._attr_hvac_mode = hvac_mode
            self._attr_hvac_action = HVAC_MODE_ACTION_MAP[hvac_mode]
            self._attr_fan_modes = modespec.fan_modes
            self._attr_target_temperature_low = modespec.low_temp
            self._attr_target_temperature_high = modespec.high_temp
            self._attr_target_temperature_step = modespec.step
            self._attr_min_temp = min(modespec.temps_float)
            self._attr_max_temp = max(modespec.temps_float)
            self._attr_swing_modes = list(map(str, modespec.swingmodespairs))
            self._attr_fan_mode = self.mode_target_fan_mode[hvac_mode]
            self._attr_target_temperature = modespec.temps_float[
                self.mode_target_temp_idx[hvac_mode]
            ]
            self._attr_swing_mode = str(self.mode_target_swingmodepair[hvac_mode])
            await self.api.send_ac_signal(self)
            self.last_update_timestamp = datetime.datetime.now(datetime.timezone.utc)
            self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if self.hvac_mode == Climate.const.HVACMode.OFF:
            return
        temperature = kwargs["temperature"]
        cur_modespec: ModeSpec = self.data.modes[self.hvac_mode]
        mode_min_temp, mode_max_temp = cur_modespec.low_temp, cur_modespec.high_temp
        mode_temps_float = cur_modespec.temps_float
        new_temp = min(mode_max_temp, max(mode_min_temp, temperature))
        # mode_temps_str = cur_modespec.temps_str
        new_temp_idx = min(
            range(len(mode_temps_float)),
            key=lambda i: abs(mode_temps_float[i] - new_temp),
        )
        new_temp = mode_temps_float[new_temp_idx]
        if new_temp != self.target_temperature:
            self._attr_target_temperature = new_temp
            self.mode_target_temp_idx[self.hvac_mode] = new_temp_idx
            await self.api.send_ac_signal(self)
            self.last_update_timestamp = datetime.datetime.now(datetime.timezone.utc)
            self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        if self.hvac_mode == Climate.const.HVACMode.OFF:
            return
        if fan_mode != self.fan_mode and fan_mode in self.fan_modes:
            self._attr_fan_mode = fan_mode
            self.mode_target_fan_mode[self.hvac_mode] = fan_mode
            await self.api.send_ac_signal(self)
            self.last_update_timestamp = datetime.datetime.now(datetime.timezone.utc)
            self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        if self.hvac_mode == Climate.const.HVACMode.OFF:
            return
        if swing_mode != self.swing_mode and swing_mode in self.swing_modes:
            modespec: ModeSpec = self.data.modes[self.hvac_mode]
            self._attr_swing_mode = swing_mode
            self.mode_target_swingmodepair[self.hvac_mode] = next(
                p for p in modespec.swingmodespairs if str(p) == swing_mode
            )
            await self.api.send_ac_signal(self)
            self.last_update_timestamp = datetime.datetime.now(datetime.timezone.utc)
            self.async_write_ha_state()
