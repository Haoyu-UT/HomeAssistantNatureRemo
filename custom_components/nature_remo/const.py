"""Constants for the nature_remo integration."""
import collections
from enum import Enum

import homeassistant.components.climate as Climate
from homeassistant.exceptions import HomeAssistantError

DOMAIN = "nature_remo"


class NetworkError(HomeAssistantError):
    """Error to indicate we cannot connect."""


class AuthError(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class NoSignalError(HomeAssistantError):
    """Error to indicate the appliance has no signal binded."""


class UnexpectedAC(HomeAssistantError):
    """Error to indicate the AC has an expected configuration."""


class UnexpectedLight(HomeAssistantError):
    """Error to indicate the light has an expected configuration."""


class SwingModePair:
    """Class storing vertical and horizontal swing modes."""

    def __init__(self, v, h):
        self.v = v
        self.h = h

    def __str__(self) -> str:
        first_part = f"⥮{self.v}" if self.v else ""
        second_part = f"⇋{self.h}" if self.h else ""
        if first_part and second_part:
            return f"{first_part}, {second_part}"
        else:
            return (list(filter(bool, [first_part, second_part])) + [""])[0]


Api = collections.namedtuple("Api", ("url", "method"))
Appliance = collections.namedtuple("GeneralAppliance", ("id", "name", "signals"))
Signal = collections.namedtuple("Signal", ("id", "name"))
SensorData = collections.namedtuple(
    "SensorData", ("temperature", "humidity", "illuminance", "movement")
)
Appliances = collections.namedtuple(
    "Appliances", ("ac", "light", "power_energy_meter", "others")
)
AC = collections.namedtuple(
    "AC",
    (
        "id",
        "name",
        "temperature_unit",
        "feature_flag",
        "temperature_sensor",
        "humidity_sensor",
        "last_status",
        "modes",
    ),
)
ModeSpec = collections.namedtuple(
    "ModeSpec",
    (
        "temps_str",
        "temps_float",
        "low_temp",
        "high_temp",
        "step",
        "fan_modes",
        "swing_modes",
        "swing_h_modes",
        "swingmodespairs",
    ),
)
ACStatus = collections.namedtuple(
    "ACStatus",
    (
        "power",
        "swingmodepair",
        "mode",
        "target_temperature",
        "temperature_unit",
        "fan_mode",
        "timestamp",
    ),
)
HVAC_MODE_MAP = {
    "cool": Climate.const.HVACMode.COOL,
    "warm": Climate.const.HVACMode.HEAT,
    "dry": Climate.const.HVACMode.DRY,
    "auto": Climate.const.HVACMode.AUTO,
    "blow": Climate.const.HVACMode.FAN_ONLY,
}
HVAC_MODE_REVERSE_MAP = {v: k for k, v in HVAC_MODE_MAP.items()}
HVAC_MODE_ACTION_MAP = {
    Climate.const.HVACMode.COOL: Climate.const.HVACAction.COOLING,
    Climate.const.HVACMode.HEAT: Climate.const.HVACAction.HEATING,
    Climate.const.HVACMode.DRY: Climate.const.HVACAction.DRYING,
    Climate.const.HVACMode.AUTO: Climate.const.HVACAction.IDLE,
    Climate.const.HVACMode.FAN_ONLY: Climate.const.HVACAction.FAN,
    Climate.const.HVACMode.OFF: Climate.const.HVACAction.OFF,
}
EPC_ITEMS = Enum(
    "EPC_ITEMS",
    [
        "power",
        "comsumed_energy",
        "generated_energy",
        "energy_max_digits",
        "energy_coefficient",
        "energy_unit",
    ],
)
EPC_ITEM_NAME_MAP = {
    EPC_ITEMS.power: "Power",
    EPC_ITEMS.comsumed_energy: "Consumed energy",
    EPC_ITEMS.generated_energy: "Generated energy",
    EPC_ITEMS.energy_max_digits: "Max digits",
    EPC_ITEMS.energy_coefficient: "Energy coefficient",
    EPC_ITEMS.energy_unit: "Energy unit",
}
EPC_ITEM_VALUE_MAP = {
    EPC_ITEMS.power: 231,
    EPC_ITEMS.comsumed_energy: 224,
    EPC_ITEMS.generated_energy: 227,
    EPC_ITEMS.energy_max_digits: 215,
    EPC_ITEMS.energy_coefficient: 211,
    EPC_ITEMS.energy_unit: 225,
}
EPC_VALUE_ITEM_MAP = {v: k for k, v in EPC_ITEM_VALUE_MAP.items()}
ENERGY_UNIT_COEFFICIENT_MAP = {
    0x00: 1.0,
    0x01: 0.1,
    0x02: 0.01,
    0x03: 0.001,
    0x04: 0.0001,
    0x0A: 10.0,
    0x0B: 100.0,
    0x0C: 1000.0,
    0x0D: 10000.0,
}
