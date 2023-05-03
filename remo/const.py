"""Constants for the nature_remo integration."""
from homeassistant.exceptions import HomeAssistantError
DOMAIN = "remo"
class NetworkError(HomeAssistantError):
    """Error to indicate we cannot connect."""
class AuthError(HomeAssistantError):
    """Error to indicate there is invalid auth."""
