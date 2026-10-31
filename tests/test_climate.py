"""Tests for reading an air conditioner off an appliance response."""

from __future__ import annotations

import copy
from functools import partial
from types import SimpleNamespace
from typing import Any

from conftest import decode
import pytest

from custom_components.nature_remo.climate import (
    AirConditioner,
    extract_ac_properties,
    extract_last_settings,
)
from custom_components.nature_remo.const import NetworkError
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


class FakeAPI:
    """Records the settings that would have been sent, or fails to send them."""

    def __init__(self) -> None:
        self.sent: list[Any] = []
        self.error: Exception | None = None

    async def set_aircon_settings(self, appliance_id: str, params: Any) -> None:
        if self.error is not None:
            raise self.error
        self.sent.append(params)


def another(options: list[Any], current: Any) -> Any:
    """Pick an option a command would have to act on."""
    return next(option for option in options if option != current)


# Each entry settles on its value once, so that a retry repeats the same command.
COMMANDS = {
    "turn_off": lambda ac: ac.async_turn_off,
    "hvac_mode": lambda ac: partial(ac.async_set_hvac_mode, HVACMode.HEAT),
    "temperature": lambda ac: partial(
        ac.async_set_temperature,
        temperature=another(
            ac.data.modes[ac.hvac_mode].temps_float, ac.target_temperature
        ),
    ),
    "fan_mode": lambda ac: partial(
        ac.async_set_fan_mode, another(ac.fan_modes, ac.fan_mode)
    ),
    "swing_mode": lambda ac: partial(
        ac.async_set_swing_mode, another(ac.swing_modes, ac.swing_mode)
    ),
}


def target_state(ac: AirConditioner) -> dict[str, Any]:
    """Everything a command may change, spelled out independently of the code."""
    return copy.deepcopy(
        {
            "hvac_mode": ac.hvac_mode,
            "hvac_action": ac.hvac_action,
            "last_hvac_mode": ac.last_hvac_mode,
            "target_temperature": ac.target_temperature,
            "target_temperature_low": ac.target_temperature_low,
            "target_temperature_high": ac.target_temperature_high,
            "target_temperature_step": ac.target_temperature_step,
            "min_temp": ac.min_temp,
            "max_temp": ac.max_temp,
            "fan_mode": ac.fan_mode,
            "fan_modes": ac.fan_modes,
            "swing_mode": ac.swing_mode,
            "swing_modes": ac.swing_modes,
            "mode_target_temp_idx": ac.mode_target_temp_idx,
            "mode_target_fan_mode": ac.mode_target_fan_mode,
            "mode_target_swingmodepair": {
                mode: str(pair) for mode, pair in ac.mode_target_swingmodepair.items()
            },
        }
    )


@pytest.fixture(name="api")
def api_fixture() -> FakeAPI:
    """An API that records instead of sending."""
    return FakeAPI()


@pytest.fixture(name="ac")
async def ac_fixture(aircon: ApplianceResponse, api: FakeAPI) -> AirConditioner:
    """An air conditioner already running, with its state writes recorded."""
    data = extract_ac_properties(aircon, sensors=[])._replace(last_status=None)
    ac = AirConditioner(data, api, SimpleNamespace(data=None))
    ac.writes = []
    ac.async_write_ha_state = lambda: ac.writes.append(None)
    await ac.async_set_hvac_mode(HVACMode.COOL)
    api.sent.clear()
    ac.writes.clear()
    return ac


@pytest.mark.parametrize("prepare", COMMANDS.values(), ids=COMMANDS)
async def test_a_failed_command_leaves_the_state_alone(
    ac: AirConditioner, api: FakeAPI, prepare: Any
) -> None:
    """A setting that never reached the API must not be taken for applied.

    The next poll writes the state regardless, and the API's unchanged timestamp
    would not correct it, so anything left behind here reaches the user.
    """
    before = target_state(ac)
    command = prepare(ac)
    api.error = NetworkError("unreachable")
    with pytest.raises(NetworkError):
        await command()
    assert target_state(ac) == before
    assert ac.writes == []


@pytest.mark.parametrize("prepare", COMMANDS.values(), ids=COMMANDS)
async def test_a_failed_command_can_be_retried(
    ac: AirConditioner, api: FakeAPI, prepare: Any
) -> None:
    """A retry is sent, rather than taken for a change that is already applied."""
    command = prepare(ac)
    api.error = NetworkError("unreachable")
    with pytest.raises(NetworkError):
        await command()
    api.error = None
    await command()
    assert len(api.sent) == 1
    assert len(ac.writes) == 1


async def test_a_failed_first_command_leaves_the_state_alone(
    aircon: ApplianceResponse, api: FakeAPI
) -> None:
    """Rolling back also works from the state an entity starts in."""
    data = extract_ac_properties(aircon, sensors=[])._replace(last_status=None)
    ac = AirConditioner(data, api, SimpleNamespace(data=None))
    api.error = NetworkError("unreachable")
    with pytest.raises(NetworkError):
        await ac.async_set_hvac_mode(HVACMode.COOL)
    assert ac.hvac_mode is HVACMode.OFF
    assert ac.target_temperature == 0.0
    assert ac.max_temp == 0.0


async def test_settings_are_ignored_while_off(
    ac: AirConditioner, api: FakeAPI
) -> None:
    """With the AC off there is nothing to send, which is not a failure."""
    await ac.async_turn_off()
    api.sent.clear()
    before = target_state(ac)
    await ac.async_set_fan_mode("anything")
    await ac.async_set_swing_mode("anything")
    assert api.sent == []
    assert target_state(ac) == before
