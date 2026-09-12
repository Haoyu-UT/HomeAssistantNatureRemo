"""Tests that the generated models describe what the API actually serves.

The decoding itself is pydantic's and is not retested here.  What is worth
pinning is that the models still match payloads recorded from the API, and that
the parts of the specification this integration leans on -- the tagged unions,
the nullable arrays, the tolerance for undeclared fields -- survive a
regeneration of models.py.
"""

from __future__ import annotations

from typing import Any

from conftest import decode
from pydantic import ValidationError
import pytest

from custom_components.nature_remo import models


def test_decode_user(user_payload: dict[str, Any]) -> None:
    """A response with only its required fields decodes."""
    user = decode(models.UserResponse, user_payload)
    assert user.id == "user-0000-0001"
    assert user.nickname == "tester"
    assert user.country is None


def test_decode_devices(devices_payload: list[dict[str, Any]]) -> None:
    """Sensor events decode into a mapping of typed values."""
    devices = decode(models.DeviceResponses, devices_payload)
    assert [device.name for device in devices] == [
        "Living Room Remo",
        "Bedroom Remo",
    ]
    events = devices[0].newest_events
    assert sorted(events) == ["hu", "il", "mo", "te"]
    assert events["te"].val == 26.5
    assert events["mo"].created_at == "2026-09-12T03:59:00Z"
    # A Remo mini reports temperature alone.
    assert sorted(devices[1].newest_events) == ["te"]


def test_decode_appliances(appliances_payload: list[dict[str, Any]]) -> None:
    """Each appliance decodes with only its own sub-object populated."""
    appliances = decode(models.ApplianceResponses, appliances_payload)
    by_id = {appliance.id: appliance for appliance in appliances}

    light = by_id["light-0000-0001"]
    assert light.type == "LIGHT"
    assert [button.name for button in light.light.buttons][:2] == ["on", "off"]
    assert light.light.state.power == "on"
    # The payload carries an explicitly null "aircon" alongside the light.
    assert light.aircon is None

    aircon = by_id["ac-0000-0001"]
    assert aircon.aircon.tempUnit == "c"
    assert aircon.aircon.range.fixedButtons == ["power-off"]
    assert sorted(aircon.aircon.range.modes) == ["blow", "cool", "dry", "warm"]
    assert aircon.aircon.range.modes["cool"].vol == ["1", "2", "3", "4", "auto"]
    assert aircon.settings.mode == "cool"
    assert aircon.light is None

    meter = by_id["meter-0000-0001"]
    assert [p.epc for p in meter.smart_meter.echonetlite_properties] == [
        231,
        224,
        215,
        211,
        225,
    ]

    assert [signal.name for signal in by_id["ir-0000-0001"].signals] == [
        "Power",
        "Volume Up",
    ]


def test_unknown_fields_are_ignored(
    appliances_payload: list[dict[str, Any]],
) -> None:
    """Fields absent from the spec must not fail the decode.

    The API serves some of these already ("revision" on an appliance) and
    gains more over time, so a strict decode would break on its own schedule.
    """
    payload = dict(appliances_payload[1], revision="0" * 64, brand_new_field=[1, 2])
    assert decode(models.ApplianceResponse, payload).id == "ac-0000-0001"


def test_missing_required_field_raises() -> None:
    """A payload that contradicts the spec is rejected."""
    with pytest.raises(ValidationError, match="nickname"):
        decode(models.UserResponse, {"id": "user-0000-0001"})


def test_wrong_shape_raises() -> None:
    """A scalar where the spec says object is rejected."""
    with pytest.raises(ValidationError):
        decode(models.UserResponse, "not-an-object")


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("relay", models.EVCCStateErrorValueRelay),
        ("meter", models.EVCCStateErrorValueMeter),
        ("memory", models.EVCCStateErrorValueMemory),
    ],
    ids=["relay", "meter", "memory"],
)
def test_tagged_union_uses_discriminator(kind: str, expected: type) -> None:
    """Union variants are told apart by their Literal discriminator."""
    decoded = decode(models.EVCCSelfTestValueUnion, {"kind": kind, "type": "unknown"})
    assert isinstance(decoded, expected)


def test_union_without_a_match_raises() -> None:
    """A union value matching no variant is rejected."""
    with pytest.raises(ValidationError):
        decode(models.EVCCSelfTestValueUnion, {"kind": "nonsense", "type": "unknown"})


def test_integral_json_number_decodes_as_float() -> None:
    """JSON has one number type, so 24 may arrive where a float is specified."""
    value = decode(models.CoreSensorValue, {"val": 24, "created_at": "t"})
    assert isinstance(value.val, float)
    assert value.val == 24.0


def test_required_but_nullable_arrays_accept_null() -> None:
    """The spec marks arrays required and nullable; both must decode.

    Nineteen properties are declared that way, LightResponse.buttons and
    AirConRangeResponse.modes among them.  Generating without --strict-nullable
    drops the nullability and the models then promise a list where the API is
    allowed to send null, so this is the test that fails if that flag is lost.
    """
    assert decode(models.LightResponse, {"buttons": None}).buttons is None
    nulls = {"dir": None, "dirh": None, "temp": None, "vol": None}
    assert decode(models.RangeResponseMode, nulls).temp is None
