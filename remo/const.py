"""Constants for the nature_remo integration."""
import collections

from homeassistant.exceptions import HomeAssistantError

DOMAIN = "remo"


class NetworkError(HomeAssistantError):
    """Error to indicate we cannot connect."""


class AuthError(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class NoSignalError(HomeAssistantError):
    """Error to indicate the appliance has no signal binded."""


Api = collections.namedtuple("Api", ("url", "method"))
GeneralAppliance = collections.namedtuple("GeneralAppliance", ("id", "name", "signals"))
Signal = collections.namedtuple("Signal", ("id", "name"))