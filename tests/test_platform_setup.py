"""Tests for setting up each platform from the recorded appliance list.

A platform that fails here creates none of its entities, which no test of a
single entity would notice. Setup must also leave service registration to Home
Assistant: registering them here reaches into internals that move between
releases.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

from conftest import decode
import pytest

from custom_components.nature_remo import button, climate, light, select
from custom_components.nature_remo.api import group_appliances
from custom_components.nature_remo.button import ApplianceEntity
from custom_components.nature_remo.climate import AirConditioner
from custom_components.nature_remo.const import DOMAIN
from custom_components.nature_remo.light import RemoLight
from custom_components.nature_remo.models import ApplianceResponse
from custom_components.nature_remo.select import LightSignalEntity, SignalEntity

ENTRY_ID = "entry-0001"


@pytest.fixture(name="platform")
def platform_fixture() -> Iterator[MagicMock]:
    """Stand in for the entity platform a setup would run inside."""
    with patch(
        "homeassistant.helpers.entity_platform.async_get_current_platform"
    ) as get_platform:
        yield get_platform.return_value


@pytest.fixture(name="hass")
def hass_fixture(appliances_payload: list[dict[str, Any]]) -> SimpleNamespace:
    """A hass whose store holds what __init__ and sensor.py put there."""
    appliances = [decode(ApplianceResponse, item) for item in appliances_payload]
    return SimpleNamespace(
        data={
            DOMAIN: {
                ENTRY_ID: {
                    "api": object(),
                    "appliances": group_appliances(appliances),
                    "appliance_coordinator": SimpleNamespace(data=None),
                    "sensors": [],
                }
            }
        }
    )


async def set_up(module: ModuleType, hass: SimpleNamespace) -> list[Any]:
    """Run a platform's setup and return the entities it added."""
    added: list[Any] = []
    entry = SimpleNamespace(entry_id=ENTRY_ID, data={})
    await module.async_setup_entry(hass, entry, added.extend)
    return added


async def test_climate_setup_adds_the_air_conditioner(
    hass: SimpleNamespace, platform: MagicMock
) -> None:
    """The climate platform comes up and creates its entity."""
    entities = await set_up(climate, hass)
    assert [type(entity) for entity in entities] == [AirConditioner]
    platform.async_register_entity_service.assert_not_called()


async def test_light_setup_adds_the_lights(
    hass: SimpleNamespace, platform: MagicMock
) -> None:
    """The light platform comes up and creates an entity per light."""
    entities = await set_up(light, hass)
    assert [type(entity) for entity in entities] == [RemoLight, RemoLight]
    platform.async_register_entity_service.assert_not_called()


async def test_select_setup_adds_the_signal_selects(
    hass: SimpleNamespace, platform: MagicMock
) -> None:
    """The select platform covers general appliances and lights."""
    entities = await set_up(select, hass)
    assert [type(entity) for entity in entities] == [
        SignalEntity,
        LightSignalEntity,
        LightSignalEntity,
    ]
    platform.async_register_entity_service.assert_not_called()


async def test_button_setup_adds_a_button_per_select(
    hass: SimpleNamespace, platform: MagicMock
) -> None:
    """Buttons pair with the selects, which are set up first."""
    selects = await set_up(select, hass)
    entities = await set_up(button, hass)
    assert [type(entity) for entity in entities] == [ApplianceEntity] * len(selects)
    assert [entity.signal_entity for entity in entities] == selects
    platform.async_register_entity_service.assert_not_called()
