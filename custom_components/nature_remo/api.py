"""File for communication with nature remo"""
import asyncio
import logging

import requests
from requests.adapters import HTTPAdapter, Retry

from .const import (
    HVAC_MODE_REVERSE_MAP,
    Api,
    Appliances,
    AuthError,
    NetworkError,
    SensorData,
)
from .util import debugger_is_active

_LOGGER = logging.getLogger(__name__)


def blocking_get(session: requests.Session, url: str):
    """A blocking vesion of requests.get()"""
    return session.get(url=url, timeout=5)


def blocking_post(session: requests.Session, url: str, data: dict):
    """A blocking vesion of requests.post()"""
    return session.post(url=url, data=data, timeout=5)


class RemoAPI:
    """Class providing communication with nature remo"""

    def __init__(self, token: str) -> None:
        """Initialize."""
        self.token = token
        self.base_url = "https://api.nature.global/"
        self.apis = {
            "user": Api("1/users/me", "get"),
            "devices": Api("1/devices", "get"),
            "appliances": Api("1/appliances", "get"),
            "sendir": Api("1/signals/{}/send", "post"),
            "setac": Api("1/appliances/{}/aircon_settings", "post"),
            "setlight": Api("1/appliances/{}/light", "post"),
        }
        self.session = requests.Session()
        self.session.mount(
            "https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1))
        )
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    async def get(self, api: Api):
        """An async vesion of requests.get()"""
        loop = asyncio.get_running_loop()
        url = self.base_url + api.url
        if debugger_is_active():
            try:
                from .test import mock_responses

                return mock_responses[api]
            except ImportError:
                pass
        try:
            response = await loop.run_in_executor(None, blocking_get, self.session, url)
        except Exception as err:
            raise NetworkError from err
        else:
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise AuthError
            else:
                raise NetworkError(f"HTTP response status code {response.status_code}")

    async def post(self, api: Api, params: list[str], data: dict):
        """An async vesion of requests.post()"""
        loop = asyncio.get_running_loop()
        url = self.base_url + api.url.format(*params)
        if debugger_is_active():
            try:
                from .test import mock_responses

                _LOGGER.debug("Posting to %s with data %s", url, str(data))
                return None
            except ImportError:
                pass
        try:
            response = await loop.run_in_executor(None, blocking_post, self.session, url, data)
        except Exception as err:
            raise NetworkError from err
        else:
            if response.status_code == 200:
                return response.json()
            else:
                raise NetworkError

    async def fecth_sensor_data(self) -> dict[str, SensorData]:
        """Fetch sensor data from all remo devices"""
        data = {}
        response = await self.get(self.apis["devices"])
        for device_response in response:
            if "newest_events" in device_response:
                event = device_response["newest_events"]
                temperature = event["te"]["val"] if "te" in event else None
                humidity = event["hu"]["val"] if "hu" in event else None
                illuminance = event["il"]["val"] if "il" in event else None
                movement = event["mo"]["created_at"] if "mo" in event else None
                mac = device_response["mac_address"]
                data[mac] = SensorData(temperature, humidity, illuminance, movement)
        return data

    async def fetch_device_name(self) -> dict[str, str]:
        """Fetch device name for all remo devices"""
        data = {}
        remote_api = self.apis["devices"]
        response = await self.get(remote_api)
        _LOGGER.debug(
            f"{self.base_url}{remote_api.url} gives the following response: %s",
            str(response),
        )
        for device_response in response:
            mac = device_response["mac_address"]
            name = device_response["name"]
            data[mac] = name
        return data

    async def fetch_appliance(self) -> Appliances:
        """Fetch all registered appliances"""
        ac_list, light_list, electricity_meter_list, others_list = [], [], [], []
        remote_api = self.apis["appliances"]
        response = await self.get(remote_api)
        _LOGGER.debug(
            f"{self.base_url}{remote_api.url} gives the following response: %s",
            str(response),
        )
        for appliance_response in response:
            properties = {k: v for k, v in appliance_response.items() if v}
            if "aircon" in properties:
                ac_list.append(properties)
            elif "light" in properties:
                light_list.append(properties)
            elif "smart_meter" in properties:
                electricity_meter_list.append(properties)
            elif "signals" in properties:
                others_list.append(properties)
        return Appliances(ac_list, light_list, electricity_meter_list, others_list)

    async def send_ir_signal(self, signal_id: str):
        """Send ir signal"""
        return await self.post(self.apis["sendir"], [signal_id], {})

    async def send_ac_signal(self, ac):
        """Control AC using information from AirConditioner object"""
        data = {
            "button": "power-off" if ac.hvac_mode == "off" else "",
            "air_direction": ac.mode_target_swingmodepair[ac.last_hvac_mode].v,
            "air_direction_h": ac.mode_target_swingmodepair[ac.last_hvac_mode].h,
            "operation_mode": HVAC_MODE_REVERSE_MAP[ac.last_hvac_mode],
            "temperature": ac.data.modes[ac.last_hvac_mode].temps_str[
                ac.mode_target_temp_idx[ac.last_hvac_mode]
            ],
            "air_volume": ac.mode_target_fan_mode[ac.last_hvac_mode],
            "temperature_unit": "c",
        }
        _LOGGER.debug(data)
        return await self.post(self.apis["setac"], [ac.data.id], data)

    async def send_light_signal(self, app_id: str, button: str):
        """Press button on given light"""
        return await self.post(self.apis["setlight"], [app_id], {"button": button})

    async def authenticate(self) -> bool:
        """Test if we can authenticate with the host"""
        remote_api = self.apis["user"]
        response = await self.get(remote_api)
        _LOGGER.debug(
            f"{self.base_url}{remote_api.url} gives the following response: %s",
            str(response),
        )
        return response is not None
