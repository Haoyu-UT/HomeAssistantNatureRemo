"""Tests for the electricity meter."""

from __future__ import annotations

import copy
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from conftest import decode
import pytest

from custom_components.nature_remo.const import EPC_ITEMS, Appliances
from custom_components.nature_remo.models import ApplianceResponse
from custom_components.nature_remo.sensor import PowerEnergyMeter

MAC = "aa:bb:cc:dd:ee:01"
CONSUMED_ENERGY_EPC = 224


@pytest.fixture(name="reading")
def reading_fixture(appliances_payload: list[dict[str, Any]]) -> Any:
    """Build the recorded meter reporting a given cumulative count."""
    payload = next(
        item for item in appliances_payload if item["type"] == "EL_SMART_METER"
    )

    def build(count: int) -> ApplianceResponse:
        reported = copy.deepcopy(payload)
        for item in reported["smart_meter"]["echonetlite_properties"]:
            if item["epc"] == CONSUMED_ENERGY_EPC:
                item["val"] = str(count)
        return decode(ApplianceResponse, reported)

    return build


@pytest.fixture(name="meter")
def meter_fixture(reading: Any) -> PowerEnergyMeter:
    """A consumed-energy meter with its state writes recorded."""
    coordinator = SimpleNamespace(data=None)
    meter = PowerEnergyMeter(
        EPC_ITEMS.comsumed_energy, coordinator, MAC, "Meter", reading(1000)
    )
    meter.hass = SimpleNamespace()
    meter.writes = []
    meter.async_write_ha_state = lambda: meter.writes.append(meter.native_value)
    return meter


def report(meter: PowerEnergyMeter, appliance: ApplianceResponse) -> None:
    """Make the coordinator deliver a new reading."""
    meter.coordinator.data = Appliances(
        ac=[], light=[], power_energy_meter=[appliance], others=[]
    )
    meter._handle_coordinator_update()


def test_a_rising_count_is_published_at_once(
    meter: PowerEnergyMeter, reading: Any
) -> None:
    """An ordinary update has nothing to wait for."""
    report(meter, reading(1001))
    assert meter.native_value == pytest.approx(100.1)
    assert meter.writes == [meter.native_value]


def test_a_counter_reset_does_not_block_the_event_loop(
    meter: PowerEnergyMeter, reading: Any
) -> None:
    """The maximum goes out first, and the new count follows on a timer.

    This runs on the event loop, so sleeping here would stop Home Assistant.
    """
    with (
        patch("time.sleep") as sleep,
        patch(
            "custom_components.nature_remo.sensor.async_call_later", create=True
        ) as call_later,
    ):
        report(meter, reading(5))
    sleep.assert_not_called()
    assert set(meter.writes) == {meter.max_value}

    _, delay, publish = call_later.call_args.args
    assert delay == 1.0
    publish(None)
    assert meter.native_value == pytest.approx(0.5)
    assert meter.writes[-1] == meter.native_value
