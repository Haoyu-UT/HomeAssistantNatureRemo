"""Tests for the Nature API client.

Nothing here touches the network: the two blocking transport functions are
replaced with a recorder, so the tests assert on the request that would have
been sent and on how a canned response is decoded.
"""

from __future__ import annotations

from typing import Any

from conftest import decode
import pytest

from custom_components.nature_remo import api as api_module
from custom_components.nature_remo.api import RemoAPI, group_appliances
from custom_components.nature_remo.const import AuthError, DecodeError, NetworkError
from custom_components.nature_remo.models import (
    AirConParams,
    ApplianceResponse,
    ApplianceResponses,
)


class FakeResponse:
    """The subset of requests.Response that the client reads."""

    def __init__(self, status_code: int = 200, payload: Any = None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


class Recorder:
    """Captures the requests the client makes and replays canned responses."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.response = FakeResponse()
        self.error: Exception | None = None

    def get(self, session: Any, url: str) -> FakeResponse:
        self.calls.append({"method": "get", "url": url})
        if self.error is not None:
            raise self.error
        return self.response

    def post(self, session: Any, url: str, data: dict) -> FakeResponse:
        self.calls.append({"method": "post", "url": url, "data": data})
        if self.error is not None:
            raise self.error
        return self.response


@pytest.fixture(name="recorder")
def recorder_fixture(monkeypatch: pytest.MonkeyPatch) -> Recorder:
    """Install the recorder in place of the blocking transport."""
    recorder = Recorder()
    monkeypatch.setattr(api_module, "blocking_get", recorder.get)
    monkeypatch.setattr(api_module, "blocking_post", recorder.post)
    # Under a tracing test runner this would otherwise divert to local mocks.
    monkeypatch.setattr(api_module, "debugger_is_active", lambda: False)
    return recorder


@pytest.fixture(name="client")
def client_fixture() -> RemoAPI:
    """A client with a placeholder token; no request ever leaves the process."""
    return RemoAPI("test-token")


def test_token_is_sent_as_a_bearer_header(client: RemoAPI) -> None:
    """The API authenticates with a bearer token."""
    assert client.session.headers["Authorization"] == "Bearer test-token"


async def test_fetch_user(
    client: RemoAPI, recorder: Recorder, user_payload: dict[str, Any]
) -> None:
    """GET /1/users/me decodes into a UserResponse."""
    recorder.response = FakeResponse(payload=user_payload)
    user = await client.fetch_user()
    assert recorder.calls == [
        {"method": "get", "url": "https://api.nature.global/1/users/me"}
    ]
    assert user.nickname == "tester"


async def test_authenticate(
    client: RemoAPI, recorder: Recorder, user_payload: dict[str, Any]
) -> None:
    """A decodable /1/users/me response means the token works."""
    recorder.response = FakeResponse(payload=user_payload)
    assert await client.authenticate() is True


async def test_fetch_appliances(
    client: RemoAPI, recorder: Recorder, appliances_payload: list[dict[str, Any]]
) -> None:
    """GET /1/appliances decodes into typed appliances."""
    recorder.response = FakeResponse(payload=appliances_payload)
    appliances = await client.fetch_appliances()
    assert recorder.calls[0]["url"] == "https://api.nature.global/1/appliances"
    assert [appliance.type for appliance in appliances] == [
        "LIGHT",
        "AC",
        "LIGHT",
        "EL_SMART_METER",
        "IR",
    ]


async def test_fetch_appliances_handles_null_body(
    client: RemoAPI, recorder: Recorder
) -> None:
    """The array is nullable in the spec, so null must read as no appliances."""
    recorder.response = FakeResponse(payload=None)
    assert await client.fetch_appliances() == []


async def test_fetch_sensor_data(
    client: RemoAPI, recorder: Recorder, devices_payload: list[dict[str, Any]]
) -> None:
    """Sensor readings are keyed by MAC, with absent sensors left as None."""
    recorder.response = FakeResponse(payload=devices_payload)
    data = await client.fetch_sensor_data()
    assert sorted(data) == ["aa:bb:cc:dd:ee:01", "aa:bb:cc:dd:ee:02"]
    living_room = data["aa:bb:cc:dd:ee:01"]
    assert living_room.temperature == 26.5
    assert living_room.humidity == 55
    assert living_room.illuminance == 120.5
    assert living_room.movement == "2026-09-12T03:59:00Z"
    bedroom = data["aa:bb:cc:dd:ee:02"]
    assert bedroom.temperature == 24
    assert bedroom.humidity is None
    assert bedroom.illuminance is None
    assert bedroom.movement is None


async def test_fetch_device_names(
    client: RemoAPI, recorder: Recorder, devices_payload: list[dict[str, Any]]
) -> None:
    """Device names are keyed by MAC."""
    recorder.response = FakeResponse(payload=devices_payload)
    assert await client.fetch_device_names() == {
        "aa:bb:cc:dd:ee:01": "Living Room Remo",
        "aa:bb:cc:dd:ee:02": "Bedroom Remo",
    }


async def test_send_signal_posts_to_the_signal_path(
    client: RemoAPI, recorder: Recorder
) -> None:
    """Sending an IR signal posts an empty body to the signal's send path."""
    await client.send_signal("signal-0001")
    assert recorder.calls == [
        {
            "method": "post",
            "url": "https://api.nature.global/1/signals/signal-0001/send",
            "data": {},
        }
    ]


async def test_set_light_posts_the_button_name(
    client: RemoAPI, recorder: Recorder
) -> None:
    """Setting a light posts the button name as a form field."""
    recorder.response = FakeResponse(
        payload={"brightness": "100", "power": "on", "last_button": "on"}
    )
    state = await client.set_light("light-0000-0001", "on")
    assert recorder.calls == [
        {
            "method": "post",
            "url": "https://api.nature.global/1/appliances/light-0000-0001/light",
            "data": {"button": "on"},
        }
    ]
    assert state.power == "on"


async def test_set_aircon_settings_posts_the_form_body(
    client: RemoAPI, recorder: Recorder, appliances_payload: list[dict[str, Any]]
) -> None:
    """Aircon settings are posted as the flat form body the spec describes."""
    recorder.response = FakeResponse(payload=appliances_payload[1]["settings"])
    params = AirConParams(
        air_direction="1",
        air_direction_h="",
        air_volume="auto",
        button="",
        operation_mode="cool",
        temperature="26",
        temperature_unit="c",
    )
    settings = await client.set_aircon_settings("ac-0000-0001", params)
    call = recorder.calls[0]
    assert call["url"] == (
        "https://api.nature.global/1/appliances/ac-0000-0001/aircon_settings"
    )
    assert call["data"] == {
        "air_direction": "1",
        "air_direction_h": "",
        "air_volume": "auto",
        "button": "",
        "operation_mode": "cool",
        "temperature": "26",
        "temperature_unit": "c",
    }
    assert settings.mode == "cool"


async def test_unusable_payload_raises_decode_error(
    client: RemoAPI, recorder: Recorder
) -> None:
    """A 200 whose body contradicts the specification is reported, not returned."""
    recorder.response = FakeResponse(payload={"id": "user-0000-0001"})
    with pytest.raises(DecodeError, match="/1/users/me"):
        await client.fetch_user()


async def test_unauthorized_raises_auth_error(
    client: RemoAPI, recorder: Recorder
) -> None:
    """A rejected token is reported as an auth failure, not a network one."""
    recorder.response = FakeResponse(status_code=401)
    with pytest.raises(AuthError):
        await client.fetch_user()


@pytest.mark.parametrize("status_code", [429, 500], ids=["rate_limited", "server"])
async def test_unexpected_status_raises_network_error(
    client: RemoAPI, recorder: Recorder, status_code: int
) -> None:
    """Any other unexpected status is a network error."""
    recorder.response = FakeResponse(status_code=status_code)
    with pytest.raises(NetworkError):
        await client.fetch_user()


async def test_transport_failure_raises_network_error(
    client: RemoAPI, recorder: Recorder
) -> None:
    """A transport-level failure surfaces as a network error."""
    recorder.error = OSError("connection reset")
    with pytest.raises(NetworkError):
        await client.fetch_user()


def test_group_appliances(appliances_payload: list[dict[str, Any]]) -> None:
    """Appliances are grouped by the capability each platform needs."""
    groups = group_appliances(decode(ApplianceResponses, appliances_payload))
    assert [appliance.id for appliance in groups.ac] == ["ac-0000-0001"]
    assert [appliance.id for appliance in groups.light] == [
        "light-0000-0001",
        "light-0000-0002",
    ]
    assert [appliance.id for appliance in groups.power_energy_meter] == [
        "meter-0000-0001"
    ]
    assert [appliance.id for appliance in groups.others] == ["ir-0000-0001"]


def test_group_appliances_ignores_a_light_with_a_null_aircon(
    appliances_payload: list[dict[str, Any]],
) -> None:
    """A null aircon key beside a populated light must not read as an AC.

    Real responses carry both keys on a light, which is why grouping tests the
    decoded value rather than the presence of the key.
    """
    payload = appliances_payload[0]
    assert "aircon" in payload and payload["aircon"] is None
    groups = group_appliances([decode(ApplianceResponse, payload)])
    assert not groups.ac
    assert [appliance.id for appliance in groups.light] == ["light-0000-0001"]


def test_group_appliances_skips_uncontrollable_appliances() -> None:
    """An appliance with no supported sub-object and no signals is skipped."""
    appliance = decode(
        ApplianceResponse,
        {
            "id": "lock-0000-0001",
            "type": "QRIO_LOCK",
            "nickname": "Front Door",
            "image": "ico_lock",
            "model": None,
            "signals": [],
        },
    )
    groups = group_appliances([appliance])
    assert groups == ([], [], [], [])
