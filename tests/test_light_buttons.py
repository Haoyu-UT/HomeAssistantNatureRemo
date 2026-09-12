"""Tests for resolving a light's on and off buttons."""

from __future__ import annotations

from typing import Any

from conftest import decode
import pytest

from custom_components.nature_remo.const import (
    CONF_LIGHTS,
    CONF_OFF_BUTTON,
    CONF_ON_BUTTON,
)
from custom_components.nature_remo.light_buttons import (
    button_choices,
    default_buttons,
    resolve_buttons,
)
from custom_components.nature_remo.models import ApplianceResponse


def make_light(light_id: str, button_names: list[str] | None) -> ApplianceResponse:
    """Build a light appliance offering the named buttons."""
    buttons = (
        None
        if button_names is None
        else [
            {"name": name, "image": "ico", "label": name.upper()}
            for name in button_names
        ]
    )
    return decode(
        ApplianceResponse,
        {
            "id": light_id,
            "type": "LIGHT",
            "nickname": "Test Light",
            "image": "ico_light",
            "model": None,
            "signals": [],
            "light": {"buttons": buttons},
        },
    )


def test_button_choices_uses_the_api_label(
    appliances_payload: list[dict[str, Any]],
) -> None:
    """Buttons are offered under the label the API gives them."""
    light = decode(ApplianceResponse, appliances_payload[0])
    choices = button_choices(light)
    assert choices["on"] == "ON"
    assert choices["bright-up"] == "Bright"


def test_button_choices_falls_back_to_the_button_name() -> None:
    """A button with a blank label is offered under its own name."""
    light = decode(
        ApplianceResponse,
        {
            "id": "light-1",
            "type": "LIGHT",
            "nickname": "Test Light",
            "image": "ico_light",
            "model": None,
            "signals": [],
            "light": {"buttons": [{"name": "on", "image": "ico", "label": ""}]},
        },
    )
    assert button_choices(light) == {"on": "on"}


def test_button_choices_of_a_light_without_buttons() -> None:
    """A null button array yields no choices."""
    assert button_choices(make_light("light-1", None)) == {}


@pytest.mark.parametrize(
    ("names", "expected"),
    [
        pytest.param(["on", "off", "night"], ("on", "off"), id="separate_pair"),
        pytest.param(["onoff", "bright-up"], ("onoff", "onoff"), id="single_toggle"),
        # A remote offering both is preferred as a pair, never as a toggle.
        pytest.param(["onoff", "on", "off"], ("on", "off"), id="pair_wins"),
        pytest.param(["night"], ("night", "night"), id="only_other_buttons"),
        pytest.param([], None, id="no_buttons"),
    ],
)
def test_default_buttons(names: list[str], expected: tuple[str, str] | None) -> None:
    """The pre-selected pair is guessed from the buttons on offer."""
    assert default_buttons(names) == expected


def test_resolve_buttons_prefers_the_configured_pair() -> None:
    """The choice made during setup wins over the guess."""
    light = make_light("light-1", ["on", "off", "night"])
    entry_data = {
        CONF_LIGHTS: {
            "light-1": {CONF_ON_BUTTON: "night", CONF_OFF_BUTTON: "off"},
        }
    }
    assert resolve_buttons(entry_data, light) == ("night", "off")


def test_resolve_buttons_allows_the_same_button_twice() -> None:
    """Choosing one button for both is what makes a light toggle-only."""
    light = make_light("light-1", ["on", "off", "onoff"])
    entry_data = {
        CONF_LIGHTS: {
            "light-1": {CONF_ON_BUTTON: "onoff", CONF_OFF_BUTTON: "onoff"},
        }
    }
    assert resolve_buttons(entry_data, light) == ("onoff", "onoff")


def test_resolve_buttons_falls_back_for_an_unconfigured_light() -> None:
    """A light added after setup was never asked about."""
    light = make_light("light-2", ["on", "off"])
    entry_data = {
        CONF_LIGHTS: {"light-1": {CONF_ON_BUTTON: "on", CONF_OFF_BUTTON: "off"}}
    }
    assert resolve_buttons(entry_data, light) == ("on", "off")


def test_resolve_buttons_falls_back_for_an_entry_without_the_key() -> None:
    """Entries predating the question carry no lights key at all."""
    light = make_light("light-1", ["onoff"])
    assert resolve_buttons({}, light) == ("onoff", "onoff")


def test_resolve_buttons_discards_a_button_the_remote_dropped() -> None:
    """A stale choice is discarded rather than sent to the API."""
    light = make_light("light-1", ["on", "off"])
    entry_data = {
        CONF_LIGHTS: {
            "light-1": {CONF_ON_BUTTON: "on-favorite", CONF_OFF_BUTTON: "off"},
        }
    }
    assert resolve_buttons(entry_data, light) == ("on", "off")


def test_resolve_buttons_of_a_light_without_buttons() -> None:
    """A light with no buttons cannot be switched at all."""
    assert resolve_buttons({}, make_light("light-1", None)) is None
