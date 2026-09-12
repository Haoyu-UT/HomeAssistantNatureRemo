"""Tests for reading an air conditioner off an appliance response."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from conftest import decode
import pytest

from custom_components.nature_remo.climate import (
    AirConditioner,
    extract_ac_properties,
    extract_last_settings,
)
from custom_components.nature_remo.models import ApplianceResponse
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import UnitOfTemperature


@pytest.fixture(name="aircon")
def aircon_fixture(appliances_payload: list[dict[str, Any]]) -> ApplianceResponse:
    """The air conditioner from the recorded appliance list."""
    return decode(
        ApplianceResponse,
        next(item for item in appliances_payload if item["type"] == "AC"),
    )


def test_extract_last_settings(aircon: ApplianceResponse) -> None:
    """The last settings reported by the API become an ACStatus."""
    status = extract_last_settings(aircon.settings)
    assert status.power == "off"  # the recorded button is "power-off"
    assert status.mode is HVACMode.COOL
    assert status.target_temperature == 28.0
    assert status.fan_mode == "auto"
    assert status.temperature_unit is UnitOfTemperature.CELSIUS
    assert str(status.swingmodepair) == "⥮5"
    assert status.timestamp.tzinfo is not None


def test_extract_last_settings_without_a_temperature() -> None:
    """Fan-only modes report an empty temperature, which reads as 0.0."""
    settings = decode(
        ApplianceResponse,
        {
            "id": "ac-0000-0001",
            "type": "AC",
            "nickname": "AC",
            "image": "ico_ac_1",
            "model": None,
            "signals": [],
            "settings": {
                "temp": "",
                "temp_unit": "c",
                "mode": "blow",
                "vol": "auto",
                "dir": "",
                "dirh": "",
                "button": "",
                "updated_at": "2026-09-12T04:00:00Z",
            },
        },
    ).settings
    status = extract_last_settings(settings)
    assert status.power == "on"
    assert status.target_temperature == 0.0


def test_extract_ac_properties(aircon: ApplianceResponse) -> None:
    """An appliance response becomes the AC description the entity is built on."""
    data = extract_ac_properties(aircon, sensors=[])
    assert data.id == "ac-0000-0001"
    assert data.name == "Living Room AC @ Living Room Remo"
    assert data.temperature_unit is UnitOfTemperature.CELSIUS
    assert sorted(data.modes) == sorted(
        [
            HVACMode.OFF,
            HVACMode.FAN_ONLY,
            HVACMode.COOL,
            HVACMode.DRY,
            HVACMode.HEAT,
        ]
    )
    # The sensors list is empty, so no sensor is bound to the AC.
    assert data.temperature_sensor is None
    assert data.humidity_sensor is None


def test_extract_ac_properties_reads_the_temperature_range(
    aircon: ApplianceResponse,
) -> None:
    """Temperatures are sorted, with the step derived from the reported list."""
    cool = extract_ac_properties(aircon, sensors=[]).modes[HVACMode.COOL]
    assert cool.temps_float == sorted(cool.temps_float)
    assert cool.low_temp == min(cool.temps_float)
    assert cool.high_temp == max(cool.temps_float)
    assert cool.step == 0.5


def test_extract_ac_properties_handles_a_mode_without_temperatures(
    aircon: ApplianceResponse,
) -> None:
    """The recorded fan-only mode offers a single empty temperature."""
    fan_only = extract_ac_properties(aircon, sensors=[]).modes[HVACMode.FAN_ONLY]
    assert fan_only.temps_str == [""]
    assert fan_only.temps_float == [0.0]


def test_aircon_params_reproduces_the_target_state(
    aircon: ApplianceResponse,
) -> None:
    """The request body is built from the per-mode targets the entity remembers.

    Called unbound on a stand-in so the body can be checked without starting
    Home Assistant; this is the payload that would reach a real appliance.
    """
    data = extract_ac_properties(aircon, sensors=[])
    cool = data.modes[HVACMode.COOL]
    entity = SimpleNamespace(
        data=data,
        hvac_mode=HVACMode.COOL,
        last_hvac_mode=HVACMode.COOL,
        mode_target_temp_idx={HVACMode.COOL: 0},
        mode_target_fan_mode={HVACMode.COOL: "2"},
        mode_target_swingmodepair={HVACMode.COOL: cool.swingmodespairs[0]},
    )
    params = AirConditioner.aircon_params(entity)
    assert params.button == ""  # empty means powered on
    assert params.operation_mode == "cool"
    assert params.temperature == cool.temps_str[0]
    assert params.temperature_unit == "c"
    assert params.air_volume == "2"
    assert params.air_direction == cool.swingmodespairs[0].v
    assert params.air_direction_h == cool.swingmodespairs[0].h
    assert params.extra is None


def test_aircon_params_powers_off_with_the_fixed_button(
    aircon: ApplianceResponse,
) -> None:
    """Turning off sends power-off while still describing the last mode."""
    data = extract_ac_properties(aircon, sensors=[])
    cool = data.modes[HVACMode.COOL]
    entity = SimpleNamespace(
        data=data,
        hvac_mode=HVACMode.OFF,
        last_hvac_mode=HVACMode.COOL,
        mode_target_temp_idx={HVACMode.COOL: 0},
        mode_target_fan_mode={HVACMode.COOL: "auto"},
        mode_target_swingmodepair={HVACMode.COOL: cool.swingmodespairs[0]},
    )
    assert AirConditioner.aircon_params(entity).button == "power-off"
