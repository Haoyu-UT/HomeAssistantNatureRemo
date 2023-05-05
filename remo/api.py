"""File for communication with nature remo"""
import asyncio
import collections
import logging

import requests

from .const import NetworkError, Api

SensorData = collections.namedtuple(
    "SensorData", ("temperature", "humidity", "illuminance", "movement")
)
Appliances = collections.namedtuple(
    "Appliances", ("ac", "light", "powermeter", "others")
)
_LOGGER = logging.getLogger(__name__)


def blocking_get(url, header):
    """A blocking vesion of requests.get()"""
    return requests.get(url=url, headers=header, timeout=1)


def blocking_post(url, header, data):
    """A blocking vesion of requests.post()"""
    return requests.post(url=url, data=data, headers=header, timeout=1)


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
        }
        self.header = {"Authorization": f"Bearer {self.token}"}

    async def get(self, api: Api):
        """An async vesion of requests.get()"""
        loop = asyncio.get_running_loop()
        url = self.base_url + api.url
        try:
            response = await loop.run_in_executor(None, blocking_get, url, self.header)
        except Exception as err:
            raise NetworkError from err
        else:
            if response.status_code == 200:
                return response.json()
            else:
                raise NetworkError

    async def post(self, api: Api, params: list[str], data: dict):
        """An async vesion of requests.post()"""
        loop = asyncio.get_running_loop()
        url = self.base_url + api.url.format(*params)
        try:
            response = await loop.run_in_executor(
                None, blocking_post, url, self.header, data
            )
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
        response = await self.get(self.apis["devices"])
        for device_response in response:
            mac = device_response["mac_address"]
            name = device_response["name"]
            data[mac] = name
        return data

    async def fetch_appliance(self) -> Appliances:
        """Fetch all registered appliances"""
        ac_list, light_list, powermeter_list, others_list = [], [], [], []
        response = await self.get(self.apis["appliances"])

        for appliance_response in response:
            properties = {k: v for k, v in appliance_response.items() if v}
            if "aircon" in properties:
                ac_list.append(properties)
            elif "light" in properties:
                light_list.append(properties)
            elif "smart_meter" in properties:
                if any(
                    p["epc"] == 231
                    for p in properties["smart_meter"]["echonetlite_properties"]
                ):
                    powermeter_list.append(properties)
            else:
                others_list.append(properties)
        return Appliances(ac_list, light_list, powermeter_list, others_list)

    async def send_ir_signal(self, signal_id: str):
        """Send ir signal"""
        return await self.post(self.apis["sendir"], [signal_id], {})

    async def authenticate(self) -> bool:
        """Test if we can authenticate with the host"""
        response = await self.get(self.apis["user"])
        return response is not None
