"""File for communication with nature remo"""
import asyncio
import collections
import logging

import requests

from .const import AuthError

Api = collections.namedtuple("Api", ("url", "method"))
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
        }
        self.header = {"Authorization": f"Bearer {self.token}"}

    async def get(self, api: Api):
        """A async vesion of requests.get()"""
        loop = asyncio.get_running_loop()
        url = self.base_url + api.url
        response = await loop.run_in_executor(None, blocking_get, url, self.header)
        return response.json() if response.status_code == 200 else None

    async def fecth_sensor_data(self) -> dict[str, SensorData]:
        """fetch sensor data from all remo devices"""
        data = {}
        response = await self.get(self.apis["devices"])
        if response is not None:
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
        else:
            raise AuthError

    async def fetch_device_name(self) -> dict[str, str]:
        """fetch device name for all remo devices"""
        data = {}
        response = await self.get(self.apis["devices"])
        if response is not None:
            for device_response in response:
                mac = device_response["mac_address"]
                name = device_response["name"]
                data[mac] = name
            return data
        else:
            raise AuthError

    async def fetch_appliance(self) -> Appliances:
        """fetch all registered appliances"""
        ac_list, light_list, powermeter_list, others_list = [], [], [], []
        response = await self.get(self.apis["appliances"])
        if response is not None:
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
        else:
            raise AuthError

    async def authenticate(self) -> bool:
        """Test if we can authenticate with the host."""
        response = await self.get(self.apis["user"])
        return response is not None
