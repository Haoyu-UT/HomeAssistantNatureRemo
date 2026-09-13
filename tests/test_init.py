"""Tests for the integration setup."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.nature_remo import current_old_unique_ids, migrated_unique_id
from custom_components.nature_remo.const import Appliances


@pytest.mark.parametrize(
    ("domain", "unique_id", "expected"),
    [
        ("light", "Living Light @ light-1", "light-1"),
        ("climate", "Bedroom AC @ Remo mini @ ac-1", "ac-1"),
        ("light", "Me @ Home @ light-1", "light-1"),
        # Already migrated.
        ("light", "light-1", None),
        ("climate", "ac-1", None),
        # Other platforms never had the nickname in their unique_id.
        ("select", "Signals @ tv-1", None),
        ("button", "Send Signal @ tv-1", None),
        ("sensor", "Temperature Sensor @ aa:bb:cc", None),
    ],
)
def test_migrated_unique_id(domain: str, unique_id: str, expected: str | None) -> None:
    """Only nicknamed light and climate ids are rewritten, to the appliance id."""
    assert migrated_unique_id(domain, unique_id) == expected


def test_current_old_unique_ids() -> None:
    """The old ids are rebuilt from today's names, as the platforms made them."""
    appliances = Appliances(
        ac=[
            SimpleNamespace(
                id="ac-1", nickname="AC", device=SimpleNamespace(name="Remo")
            )
        ],
        light=[SimpleNamespace(id="light-1", nickname="Light")],
        power_energy_meter=[],
        others=[],
    )
    assert current_old_unique_ids(appliances) == {
        "AC @ Remo @ ac-1",
        "Light @ light-1",
    }
