"""Tests for how a light switches with the buttons chosen during setup."""

from __future__ import annotations

import pytest

from custom_components.nature_remo.light import RemoLight


class FakeAPI:
    """Records the buttons that would have been sent."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def set_light(self, appliance_id: str, button: str) -> None:
        self.sent.append((appliance_id, button))


@pytest.fixture(name="api")
def api_fixture() -> FakeAPI:
    """An API that records instead of sending."""
    return FakeAPI()


def make_light(api: FakeAPI, on_button: str, off_button: str) -> RemoLight:
    """Build a light entity switched by the given pair of buttons."""
    return RemoLight("light-1", "Test Light", on_button, off_button, api)


def test_separate_buttons_are_not_toggle_only(api: FakeAPI) -> None:
    """Two different buttons mean on and off are independently reachable."""
    assert make_light(api, "on", "off").toggle_only is False


def test_one_button_for_both_is_toggle_only(api: FakeAPI) -> None:
    """The same button for both is what makes a light toggle-only."""
    assert make_light(api, "onoff", "onoff").toggle_only is True


async def test_separate_buttons_turn_on_sends_the_on_button(api: FakeAPI) -> None:
    """With a real on button, turning on sends it directly."""
    light = make_light(api, "on", "off")
    await light.async_turn_on()
    assert api.sent == [("light-1", "on")]
    assert light.is_on is True


async def test_separate_buttons_turn_on_is_idempotent(api: FakeAPI) -> None:
    """Turning on an already-on light still sends the on button, not off."""
    light = make_light(api, "on", "off")
    await light.async_turn_on()
    await light.async_turn_on()
    assert api.sent == [("light-1", "on"), ("light-1", "on")]
    assert light.is_on is True


async def test_separate_buttons_turn_off_sends_the_off_button(api: FakeAPI) -> None:
    """With a real off button, turning off sends it directly."""
    light = make_light(api, "on", "off")
    await light.async_turn_on()
    await light.async_turn_off()
    assert api.sent[-1] == ("light-1", "off")
    assert light.is_on is False


async def test_separate_buttons_turn_off_is_idempotent(api: FakeAPI) -> None:
    """Turning off an already-off light still sends the off button."""
    light = make_light(api, "on", "off")
    await light.async_turn_off()
    await light.async_turn_off()
    assert api.sent == [("light-1", "off"), ("light-1", "off")]
    assert light.is_on is False


async def test_separate_buttons_toggle_alternates(api: FakeAPI) -> None:
    """Toggling alternates between the two buttons."""
    light = make_light(api, "on", "off")
    await light.async_toggle()
    await light.async_toggle()
    await light.async_toggle()
    assert api.sent == [
        ("light-1", "on"),
        ("light-1", "off"),
        ("light-1", "on"),
    ]


async def test_toggle_only_light_always_sends_the_one_button(api: FakeAPI) -> None:
    """A single-button remote sends that button whatever was asked for."""
    light = make_light(api, "onoff", "onoff")
    await light.async_turn_on()
    await light.async_turn_off()
    await light.async_toggle()
    assert api.sent == [
        ("light-1", "onoff"),
        ("light-1", "onoff"),
        ("light-1", "onoff"),
    ]


async def test_toggle_only_light_turn_on_assumes_it_is_off(api: FakeAPI) -> None:
    """Turning on takes the real state to be off, so the state ends up on.

    A lone toggle button carries no state, so this is the documented
    assumption rather than something the remote can confirm.
    """
    light = make_light(api, "onoff", "onoff")
    await light.async_turn_on()
    assert light.is_on is True
    await light.async_turn_on()
    assert light.is_on is True


async def test_toggle_only_light_turn_off_assumes_it_is_on(api: FakeAPI) -> None:
    """The mirror assumption: turning off leaves the state off."""
    light = make_light(api, "onoff", "onoff")
    await light.async_turn_off()
    assert light.is_on is False
    await light.async_turn_off()
    assert light.is_on is False


async def test_any_button_pair_may_be_chosen(api: FakeAPI) -> None:
    """The chosen buttons need not be the remote's own on and off."""
    light = make_light(api, "on-favorite", "night")
    await light.async_turn_on()
    await light.async_turn_off()
    assert api.sent == [
        ("light-1", "on-favorite"),
        ("light-1", "night"),
    ]


def test_unique_id_is_unchanged_by_the_button_choice(api: FakeAPI) -> None:
    """Existing entities must keep their id when buttons are reconfigured."""
    assert make_light(api, "on", "off").unique_id == "Test Light @ light-1"
    assert make_light(api, "onoff", "onoff").unique_id == "Test Light @ light-1"
