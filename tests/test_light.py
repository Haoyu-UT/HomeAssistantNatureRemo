"""Tests for the light entity.

Covers both how a light is switched with the buttons chosen during setup, and
how a change made outside Home Assistant — a press of the physical remote, the
Nature app, or another client — is picked up from the appliance poll.
"""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import Any

from conftest import decode
import pytest

from custom_components.nature_remo.const import Appliances
from custom_components.nature_remo.light import COMMAND_SETTLE_TIME, RemoLight
from custom_components.nature_remo.models import ApplianceResponse
import homeassistant.util.dt as dt_util

LIGHT_ID = "light-1"


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


def make_appliance(
    power: str | None = None,
    last_button: str = "",
    light_id: str = LIGHT_ID,
    with_light: bool = True,
) -> ApplianceResponse:
    """Build a light appliance reporting the given power state."""
    state = (
        None
        if power is None
        else {"power": power, "brightness": "100", "last_button": last_button}
    )
    payload: dict[str, Any] = {
        "id": light_id,
        "type": "LIGHT",
        "nickname": "Test Light",
        "image": "ico_light",
        "model": None,
        "signals": [],
    }
    if with_light:
        payload["light"] = {
            "buttons": [{"name": "on", "image": "ico", "label": "ON"}],
            "state": state,
        }
    return decode(ApplianceResponse, payload)


def make_light(
    api: FakeAPI,
    on_button: str,
    off_button: str,
    appliance: ApplianceResponse | None = None,
) -> tuple[RemoLight, list[None], SimpleNamespace]:
    """Build a light entity, its recorded state writes, and its coordinator."""
    coordinator = SimpleNamespace(data=None, last_update_success=True)
    light = RemoLight(
        appliance if appliance is not None else make_appliance(),
        on_button,
        off_button,
        api,
        coordinator,
    )
    writes: list[None] = []
    light.async_write_ha_state = lambda: writes.append(None)
    return light, writes, coordinator


def report(coordinator: SimpleNamespace, *appliances: ApplianceResponse) -> None:
    """Make the coordinator report the given appliances on its next update."""
    coordinator.data = Appliances(
        ac=[], light=list(appliances), power_energy_meter=[], others=[]
    )


async def test_separate_buttons_turn_on_sends_the_on_button(api: FakeAPI) -> None:
    """With a real on button, turning on sends it directly."""
    light, _, _ = make_light(api, "on", "off")
    await light.async_turn_on()
    assert api.sent == [(LIGHT_ID, "on")]
    assert light.is_on is True


async def test_separate_buttons_turn_on_is_idempotent(api: FakeAPI) -> None:
    """Turning on an already-on light still sends the on button, not off."""
    light, _, _ = make_light(api, "on", "off")
    await light.async_turn_on()
    await light.async_turn_on()
    assert api.sent == [(LIGHT_ID, "on"), (LIGHT_ID, "on")]
    assert light.is_on is True


async def test_separate_buttons_turn_off_sends_the_off_button(api: FakeAPI) -> None:
    """With a real off button, turning off sends it directly."""
    light, _, _ = make_light(api, "on", "off")
    await light.async_turn_on()
    await light.async_turn_off()
    assert api.sent[-1] == (LIGHT_ID, "off")
    assert light.is_on is False


async def test_separate_buttons_toggle_alternates(api: FakeAPI) -> None:
    """Toggling alternates between the two buttons."""
    light, _, _ = make_light(api, "on", "off")
    await light.async_toggle()
    await light.async_toggle()
    await light.async_toggle()
    assert api.sent == [
        (LIGHT_ID, "on"),
        (LIGHT_ID, "off"),
        (LIGHT_ID, "on"),
    ]


async def test_toggle_only_light_always_sends_the_one_button(api: FakeAPI) -> None:
    """A single-button remote sends that button whatever was asked for."""
    light, _, _ = make_light(api, "onoff", "onoff")
    await light.async_turn_on()
    await light.async_turn_off()
    await light.async_toggle()
    assert api.sent == [
        (LIGHT_ID, "onoff"),
        (LIGHT_ID, "onoff"),
        (LIGHT_ID, "onoff"),
    ]


async def test_toggle_only_light_turn_on_assumes_it_is_off(api: FakeAPI) -> None:
    """Turning on takes the real state to be off, so the state ends up on."""
    light, _, _ = make_light(api, "onoff", "onoff")
    await light.async_turn_on()
    assert light.is_on is True
    await light.async_turn_on()
    assert light.is_on is True


async def test_toggle_only_light_turn_off_assumes_it_is_on(api: FakeAPI) -> None:
    """The mirror assumption: turning off leaves the state off."""
    light, _, _ = make_light(api, "onoff", "onoff")
    await light.async_turn_off()
    assert light.is_on is False
    await light.async_turn_off()
    assert light.is_on is False


async def test_any_button_pair_may_be_chosen(api: FakeAPI) -> None:
    """The chosen buttons need not be the remote's own on and off."""
    light, _, _ = make_light(api, "on-favorite", "night")
    await light.async_turn_on()
    await light.async_turn_off()
    assert api.sent == [
        (LIGHT_ID, "on-favorite"),
        (LIGHT_ID, "night"),
    ]


@pytest.mark.parametrize(
    ("on_button", "off_button"),
    [
        pytest.param("on", "off", id="separate_buttons"),
        pytest.param("onoff", "onoff", id="toggle_only"),
    ],
)
async def test_every_command_writes_the_new_state(
    api: FakeAPI, on_button: str, off_button: str
) -> None:
    """A coordinator entity is not polled, so a command must write its state.

    Nothing else would: Home Assistant only writes after a service call for
    entities that poll, and the next report finds the state already matching.
    """
    light, writes, _ = make_light(api, on_button, off_button)
    await light.async_turn_on()
    assert len(writes) == 1
    await light.async_turn_off()
    assert len(writes) == 2
    await light.async_toggle()
    assert len(writes) == 3


async def test_a_failed_command_leaves_the_state_alone(api: FakeAPI) -> None:
    """A button that never reached the API must not flip the state."""

    async def fail(appliance_id: str, button: str) -> None:
        raise RuntimeError("unreachable")

    light, writes, _ = make_light(api, "on", "off")
    light.api.set_light = fail
    with pytest.raises(RuntimeError):
        await light.async_turn_on()
    assert light.is_on is False
    assert writes == []


def test_unique_id_is_unchanged_by_the_button_choice(api: FakeAPI) -> None:
    """Existing entities must keep their id when buttons are reconfigured."""
    assert make_light(api, "on", "off")[0].unique_id == "light-1"
    assert make_light(api, "onoff", "onoff")[0].unique_id == "light-1"


@pytest.mark.parametrize(
    ("power", "expected"),
    [
        pytest.param("on", True, id="reported_on"),
        pytest.param("off", False, id="reported_off"),
        # Neither an absent state nor an unknown power tells us anything, so
        # the entity keeps its default rather than guessing.
        pytest.param(None, False, id="no_state_reported"),
        pytest.param("", False, id="unknown_power"),
    ],
)
def test_initial_state_comes_from_the_report(
    api: FakeAPI, power: str | None, expected: bool
) -> None:
    """Setup seeds the state from what the API already knows."""
    light, _, _ = make_light(api, "on", "off", make_appliance(power=power))
    assert light.is_on is expected


def test_a_change_made_elsewhere_is_picked_up(api: FakeAPI) -> None:
    """A press of the physical remote reaches the entity through the poll."""
    light, writes, coordinator = make_light(
        api, "on", "off", make_appliance(power="off")
    )
    assert light.is_on is False
    report(coordinator, make_appliance(power="on", last_button="on"))
    light._handle_coordinator_update()
    assert light.is_on is True
    assert len(writes) == 1


def test_an_unchanged_report_writes_no_state(api: FakeAPI) -> None:
    """A poll that confirms what we already believe costs nothing."""
    light, writes, coordinator = make_light(
        api, "on", "off", make_appliance(power="on")
    )
    report(coordinator, make_appliance(power="on", last_button="on"))
    light._handle_coordinator_update()
    assert light.is_on is True
    assert writes == []


async def test_a_report_predating_our_command_is_ignored(api: FakeAPI) -> None:
    """A poll in flight when a command is sent must not undo it.

    LightState has no timestamp, so this is the case a timestamp comparison
    would otherwise have caught.
    """
    light, writes, coordinator = make_light(
        api, "on", "off", make_appliance(power="off")
    )
    await light.async_turn_on()
    assert light.is_on is True
    writes.clear()
    # The response was captured before the command landed.
    report(coordinator, make_appliance(power="off", last_button=""))
    light._handle_coordinator_update()
    assert light.is_on is True
    assert writes == []


async def test_the_settle_window_ends_when_the_button_is_echoed(
    api: FakeAPI,
) -> None:
    """Once the API echoes our button, its report is current and is trusted."""
    light, _, coordinator = make_light(api, "on", "off", make_appliance(power="off"))
    await light.async_turn_on()
    # The light was already on, so the remote's on button changed nothing.
    report(coordinator, make_appliance(power="off", last_button="on"))
    light._handle_coordinator_update()
    assert light.is_on is False


async def test_the_settle_window_expires(api: FakeAPI) -> None:
    """After the window, reports are trusted even without an echo."""
    light, _, coordinator = make_light(api, "on", "off", make_appliance(power="off"))
    await light.async_turn_on()
    light._command_sent_at = (
        dt_util.utcnow() - COMMAND_SETTLE_TIME - datetime.timedelta(seconds=1)
    )
    report(coordinator, make_appliance(power="off", last_button=""))
    light._handle_coordinator_update()
    assert light.is_on is False


def test_a_report_for_another_light_is_ignored(api: FakeAPI) -> None:
    """Each entity only reads the appliance it belongs to."""
    light, writes, coordinator = make_light(
        api, "on", "off", make_appliance(power="off")
    )
    report(coordinator, make_appliance(power="on", light_id="light-2"))
    light._handle_coordinator_update()
    assert light.is_on is False
    assert writes == []


def test_a_light_missing_from_the_report_is_ignored(api: FakeAPI) -> None:
    """An appliance removed in the Nature app must not raise."""
    light, writes, coordinator = make_light(
        api, "on", "off", make_appliance(power="on")
    )
    report(coordinator)
    light._handle_coordinator_update()
    assert light.is_on is True
    assert writes == []


def test_a_report_without_a_light_object_is_ignored(api: FakeAPI) -> None:
    """A light that stops reporting its sub-object must not raise."""
    light, writes, coordinator = make_light(
        api, "on", "off", make_appliance(power="on")
    )
    report(coordinator, make_appliance(with_light=False))
    light._handle_coordinator_update()
    assert light.is_on is True
    assert writes == []


async def test_toggle_follows_a_change_made_elsewhere(api: FakeAPI) -> None:
    """Toggling acts on the reported state, not on a drifting local guess.

    This is what the poll buys a toggle-only light: before, turning the light
    on by its own remote left Home Assistant believing it was off, so the next
    toggle sent a command that turned it on again.
    """
    light, _, coordinator = make_light(
        api, "onoff", "onoff", make_appliance(power="off")
    )
    report(coordinator, make_appliance(power="on", last_button="onoff"))
    light._handle_coordinator_update()
    assert light.is_on is True

    await light.async_toggle()
    assert light.is_on is False
    assert api.sent == [(LIGHT_ID, "onoff")]
