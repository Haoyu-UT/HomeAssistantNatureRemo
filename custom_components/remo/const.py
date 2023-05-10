"""Constants for the nature_remo integration."""
import collections

import homeassistant.components.climate as Climate
from homeassistant.exceptions import HomeAssistantError

DOMAIN = "remo"


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


Api = collections.namedtuple("Api", ("url", "method"))
Appliance = collections.namedtuple("GeneralAppliance", ("id", "name", "signals"))
Signal = collections.namedtuple("Signal", ("id", "name"))
SensorData = collections.namedtuple(
    "SensorData", ("temperature", "humidity", "illuminance", "movement")
)
Appliances = collections.namedtuple(
    "Appliances", ("ac", "light", "electricitymeter", "others")
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
    ("low_temp", "high_temp", "step", "fan_modes", "swing_modes", "swing_h_modes"),
)
ACStatus = collections.namedtuple(
    "ACStatus",
    (
        "power",
        "swing",
        "swing_h",
        "mode",
        "target_temperature",
        "temperature_unit",
        "fan_mode",
        "timestamp",
    ),
)
MODE_MAP = {
    "cool": Climate.const.HVACMode.COOL,
    "warm": Climate.const.HVACMode.HEAT,
    "dry": Climate.const.HVACMode.DRY,
    "auto": Climate.const.HVACMode.AUTO,
    "blow": Climate.const.HVACMode.FAN_ONLY,
}
MODE_REVERSE_MAP = {v: k for k, v in MODE_MAP.items()}
MODE_ACTION_MAP = {
    Climate.const.HVACMode.COOL: Climate.const.HVACAction.COOLING,
    Climate.const.HVACMode.HEAT: Climate.const.HVACAction.HEATING,
    Climate.const.HVACMode.DRY: Climate.const.HVACAction.DRYING,
    Climate.const.HVACMode.AUTO: Climate.const.HVACAction.IDLE,
    Climate.const.HVACMode.FAN_ONLY: Climate.const.HVACAction.FAN,
    Climate.const.HVACMode.OFF: Climate.const.HVACAction.OFF,
}
