"""Communication with the Nature API.

Every endpoint, request body and response type here mirrors the API's OpenAPI
specification; the wire types themselves live in the generated models module.
See script/generate_models.py.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import functools
import logging
from typing import Any

from pydantic import TypeAdapter, ValidationError
import requests
from requests.adapters import HTTPAdapter, Retry

from .const import Appliances, AuthError, DecodeError, NetworkError, SensorData
from .models import (
    AirConParams,
    AirconSettingsResponse,
    ApplianceResponse,
    ApplianceResponses,
    DeviceResponse,
    DeviceResponses,
    LightParams,
    LightState,
    UserResponse,
)
from .util import debugger_is_active

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://api.nature.global"
TIMEOUT = 5


@dataclass(frozen=True)
class Endpoint:
    """An operation of the Nature API, as named by its specification."""

    method: str
    path: str
    response: Any

    def url(self, **path_params: str) -> str:
        return BASE_URL + self.path.format(**path_params)


GET_USER = Endpoint("get", "/1/users/me", UserResponse)
GET_DEVICES = Endpoint("get", "/1/devices", DeviceResponses)
GET_APPLIANCES = Endpoint("get", "/1/appliances", ApplianceResponses)
SEND_SIGNAL = Endpoint("post", "/1/signals/{signalid}/send", None)
SET_AIRCON_SETTINGS = Endpoint(
    "post", "/1/appliances/{applianceid}/aircon_settings", AirconSettingsResponse
)
SET_LIGHT = Endpoint("post", "/1/appliances/{applianceid}/light", LightState)


@functools.cache
def _adapter(annotation: Any) -> TypeAdapter:
    """Return the validator for a wire type, built once per type.

    Building a TypeAdapter compiles a schema, so the cache matters: the polling
    loop decodes the appliance list on every update.
    """
    return TypeAdapter(annotation)


def _decode(endpoint: Endpoint, payload: Any) -> Any:
    """Build the type ``endpoint`` declares out of a decoded JSON payload.

    Keys the specification does not mention are ignored rather than rejected,
    which is pydantic's default and what this API needs: it serves fields absent
    from its own spec (``revision`` on an appliance, for one) and gains more over
    time.
    """
    try:
        return _adapter(endpoint.response).validate_python(payload)
    except ValidationError as err:
        raise DecodeError(
            f"{endpoint.path} served a payload its specification does not describe"
        ) from err


def _form_body(params: Any) -> dict[str, str]:
    """Flatten a request-parameter model into form fields, omitting unset ones."""
    return _adapter(type(params)).dump_python(params, exclude_none=True)


def group_appliances(appliances: list[ApplianceResponse]) -> Appliances:
    """Group appliances by the capability each platform needs.

    Grouping follows the sub-object the API fills in rather than the ``type``
    string, because that sub-object is what a platform actually reads.  An
    appliance may carry a null ``aircon`` key alongside a populated ``light``
    one, so the check has to be for a decoded value and not for a present key.
    """
    groups = Appliances(ac=[], light=[], power_energy_meter=[], others=[])
    for appliance in appliances:
        if appliance.aircon is not None:
            groups.ac.append(appliance)
        elif appliance.light is not None:
            groups.light.append(appliance)
        elif appliance.smart_meter is not None:
            groups.power_energy_meter.append(appliance)
        elif appliance.signals:
            groups.others.append(appliance)
        else:
            _LOGGER.debug(
                "Ignoring appliance %s of type %s: nothing to control",
                appliance.id,
                appliance.type,
            )
    return groups


def blocking_get(session: requests.Session, url: str):
    """A blocking version of requests.get()."""
    return session.get(url=url, timeout=TIMEOUT)


def blocking_post(session: requests.Session, url: str, data: dict):
    """A blocking version of requests.post()."""
    return session.post(url=url, data=data, timeout=TIMEOUT)


class RemoAPI:
    """Class providing communication with the Nature API."""

    def __init__(self, token: str) -> None:
        """Initialize."""
        self.token = token
        self.session = requests.Session()
        self.session.mount(
            "https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1))
        )
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    async def _request(
        self,
        endpoint: Endpoint,
        path_params: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
    ):
        """Call ``endpoint`` and validate its response into the declared type."""
        loop = asyncio.get_running_loop()
        url = endpoint.url(**(path_params or {}))
        try:
            if endpoint.method == "get":
                response = await loop.run_in_executor(
                    None, blocking_get, self.session, url
                )
            else:
                # Every POST in the spec takes application/x-www-form-urlencoded,
                # which is what requests sends for a dict passed as `data`.
                response = await loop.run_in_executor(
                    None, blocking_post, self.session, url, data or {}
                )
        except Exception as err:
            raise NetworkError from err
        if response.status_code == 401:
            raise AuthError
        if response.status_code != 200:
            raise NetworkError(f"HTTP response status code {response.status_code}")
        if endpoint.response is None:
            return None
        return _decode(endpoint, response.json())

    async def _get(self, endpoint: Endpoint):
        """Call a GET endpoint, or answer from the local mocks when debugging."""
        if debugger_is_active():
            try:
                from .test import mock_responses  # noqa: PLC0415
            except ImportError:
                pass
            else:
                return _decode(endpoint, mock_responses[endpoint])
        result = await self._request(endpoint)
        _LOGGER.debug("%s gives the following response: %s", endpoint.path, result)
        return result

    async def _post(
        self, endpoint: Endpoint, path_params: dict[str, str], params: Any = None
    ):
        """Call a POST endpoint; returns None when a debugger suppresses sending."""
        data = _form_body(params) if params is not None else {}
        if debugger_is_active():
            try:
                from .test import mock_responses  # noqa: PLC0415, F401
            except ImportError:
                pass
            else:
                _LOGGER.debug(
                    "Posting to %s with data %s", endpoint.url(**path_params), data
                )
                return None
        return await self._request(endpoint, path_params, data)

    async def fetch_user(self) -> UserResponse:
        """GET /1/users/me."""
        return await self._get(GET_USER)

    async def fetch_devices(self) -> list[DeviceResponse]:
        """GET /1/devices."""
        return await self._get(GET_DEVICES) or []

    async def fetch_appliances(self) -> list[ApplianceResponse]:
        """GET /1/appliances."""
        return await self._get(GET_APPLIANCES) or []

    async def send_signal(self, signal_id: str) -> None:
        """POST /1/signals/{signalid}/send."""
        await self._post(SEND_SIGNAL, {"signalid": signal_id})

    async def set_aircon_settings(
        self, appliance_id: str, params: AirConParams
    ) -> AirconSettingsResponse | None:
        """POST /1/appliances/{applianceid}/aircon_settings."""
        _LOGGER.debug("Setting aircon %s to %s", appliance_id, params)
        return await self._post(
            SET_AIRCON_SETTINGS, {"applianceid": appliance_id}, params
        )

    async def set_light(self, appliance_id: str, button: str) -> LightState | None:
        """POST /1/appliances/{applianceid}/light."""
        return await self._post(
            SET_LIGHT, {"applianceid": appliance_id}, LightParams(button=button)
        )

    async def fetch_grouped_appliances(self) -> Appliances:
        """Fetch all appliances, grouped by capability."""
        return group_appliances(await self.fetch_appliances())

    async def fetch_sensor_data(self) -> dict[str, SensorData]:
        """Fetch sensor readings of every Remo device, keyed by MAC address."""
        data = {}
        for device in await self.fetch_devices():
            events = device.newest_events or {}
            if not events:
                continue
            data[device.mac_address] = SensorData(
                temperature=events["te"].val if "te" in events else None,
                humidity=events["hu"].val if "hu" in events else None,
                illuminance=events["il"].val if "il" in events else None,
                movement=events["mo"].created_at if "mo" in events else None,
            )
        return data

    async def fetch_device_names(self) -> dict[str, str]:
        """Fetch the name of every Remo device, keyed by MAC address."""
        return {
            device.mac_address: device.name for device in await self.fetch_devices()
        }

    async def authenticate(self) -> bool:
        """Test whether we can authenticate with the API."""
        return await self.fetch_user() is not None
