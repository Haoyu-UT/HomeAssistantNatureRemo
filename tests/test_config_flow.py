"""Tests for the config flow, in particular the light button step."""

from __future__ import annotations

from typing import Any

from conftest import decode
import pytest

from custom_components.nature_remo import config_flow as config_flow_module
from custom_components.nature_remo.api import group_appliances
from custom_components.nature_remo.config_flow import ConfigFlow
from custom_components.nature_remo.const import (
    CONF_LIGHTS,
    CONF_OFF_BUTTON,
    CONF_ON_BUTTON,
    CONF_POLLING_INTERVAL_POWER_METER,
    CONF_POLLING_INTERVAL_SENSOR,
    CONF_TEST_BUTTON,
    CONF_TOKEN,
    AuthError,
    NetworkError,
)
from custom_components.nature_remo.models import ApplianceResponse, ApplianceResponses

USER_INPUT = {
    CONF_TOKEN: "test-token",
    CONF_POLLING_INTERVAL_SENSOR: 60,
    CONF_POLLING_INTERVAL_POWER_METER: 60,
}


@pytest.fixture(name="lights")
def lights_fixture(appliances_payload: list[dict[str, Any]]) -> list[ApplianceResponse]:
    """The lights of the recorded appliance list.

    The first offers separate on and off buttons, the second only a toggle.
    """
    return group_appliances(decode(ApplianceResponses, appliances_payload)).light


@pytest.fixture(name="answer_with")
def answer_with_fixture(monkeypatch: pytest.MonkeyPatch):
    """Replace token validation, so no request is made."""

    def install(result: list[ApplianceResponse] | Exception):
        async def validate_input(data: dict[str, Any]) -> list[ApplianceResponse]:
            if isinstance(result, Exception):
                raise result
            return result

        monkeypatch.setattr(config_flow_module, "validate_input", validate_input)

    return install


class FakeRemo:
    """Stands in for RemoAPI in the flow, recording the buttons sent."""

    def __init__(self, token: str) -> None:
        self.token = token
        self.sent: list[tuple[str, str]] = []
        self.error: Exception | None = None

    async def set_light(self, appliance_id: str, button: str) -> None:
        if self.error is not None:
            raise self.error
        self.sent.append((appliance_id, button))


@pytest.fixture(name="remo")
def remo_fixture(monkeypatch: pytest.MonkeyPatch) -> FakeRemo:
    """Replace the API client the flow builds, so no button is really sent."""
    remo = FakeRemo("test-token")
    monkeypatch.setattr(config_flow_module, "RemoAPI", lambda token: remo)
    return remo


def schema_defaults(result: dict[str, Any]) -> dict[str, Any]:
    """Read the pre-selected value of each field in a shown form.

    Markers are inspected by duck typing: Home Assistant substitutes its own
    implementation of voluptuous, so an isinstance check against the package
    this module could import would not hold.
    """
    defaults = {}
    for marker in result["data_schema"].schema:
        default = getattr(marker, "default", None)
        if callable(default):
            defaults[str(marker)] = default()
    return defaults


def schema_options(result: dict[str, Any], key: str) -> list[str]:
    """Read the values a field offers in a shown form."""
    selector = next(
        validator
        for marker, validator in result["data_schema"].schema.items()
        if str(marker) == key
    )
    return [option["value"] for option in selector.config["options"]]


async def test_full_flow_asks_about_every_light(
    answer_with, lights: list[ApplianceResponse]
) -> None:
    """Each light gets its own form, and the answers land in the entry."""
    answer_with(lights)
    flow = ConfigFlow()

    first = await flow.async_step_user(USER_INPUT)
    assert first["type"] == "form"
    assert first["step_id"] == "light"
    assert first["description_placeholders"] == {
        "name": "Living Room Light",
        "current": "1",
        "total": "2",
    }

    second = await flow.async_step_light({CONF_ON_BUTTON: "on", CONF_OFF_BUTTON: "off"})
    assert second["step_id"] == "light"
    assert second["description_placeholders"]["name"] == "Hallway Light"

    result = await flow.async_step_light(
        {CONF_ON_BUTTON: "onoff", CONF_OFF_BUTTON: "onoff"}
    )
    assert result["type"] == "create_entry"
    assert result["title"] == "Nature Remo"
    assert result["data"] == {
        **USER_INPUT,
        CONF_LIGHTS: {
            "light-0000-0001": {CONF_ON_BUTTON: "on", CONF_OFF_BUTTON: "off"},
            "light-0000-0002": {CONF_ON_BUTTON: "onoff", CONF_OFF_BUTTON: "onoff"},
        },
    }


async def test_the_same_button_may_be_chosen_for_both(
    answer_with, lights: list[ApplianceResponse]
) -> None:
    """Choosing one button twice is accepted; it makes the light toggle-only."""
    answer_with(lights[:1])
    flow = ConfigFlow()
    await flow.async_step_user(USER_INPUT)
    result = await flow.async_step_light(
        {CONF_ON_BUTTON: "night", CONF_OFF_BUTTON: "night"}
    )
    assert result["data"][CONF_LIGHTS] == {
        "light-0000-0001": {CONF_ON_BUTTON: "night", CONF_OFF_BUTTON: "night"}
    }


async def test_the_form_offers_every_button_of_that_light(
    answer_with, lights: list[ApplianceResponse]
) -> None:
    """Both fields offer the full button list of the light being configured."""
    answer_with(lights)
    flow = ConfigFlow()
    result = await flow.async_step_user(USER_INPUT)
    expected = [
        "on",
        "off",
        "on-100",
        "on-favorite",
        "night",
        "bright-up",
        "bright-down",
        "colortemp-down",
        "colortemp-up",
    ]
    assert schema_options(result, CONF_ON_BUTTON) == expected
    assert schema_options(result, CONF_OFF_BUTTON) == expected


async def test_the_form_preselects_the_separate_pair(
    answer_with, lights: list[ApplianceResponse]
) -> None:
    """A light with real on and off buttons has them pre-selected."""
    answer_with(lights[:1])
    flow = ConfigFlow()
    result = await flow.async_step_user(USER_INPUT)
    assert schema_defaults(result) == {
        CONF_ON_BUTTON: "on",
        CONF_OFF_BUTTON: "off",
    }


async def test_the_form_preselects_a_lone_toggle_for_both(
    answer_with, lights: list[ApplianceResponse]
) -> None:
    """A light with only a toggle has it pre-selected for both fields."""
    answer_with(lights[1:])
    flow = ConfigFlow()
    result = await flow.async_step_user(USER_INPUT)
    assert schema_defaults(result) == {
        CONF_ON_BUTTON: "onoff",
        CONF_OFF_BUTTON: "onoff",
    }


async def test_trying_a_button_sends_it_and_shows_the_form_again(
    answer_with, remo: FakeRemo, lights: list[ApplianceResponse]
) -> None:
    """A button in the test field is sent, and the same light is asked again."""
    answer_with(lights)
    flow = ConfigFlow()
    await flow.async_step_user(USER_INPUT)

    result = await flow.async_step_light(
        {CONF_ON_BUTTON: "on-100", CONF_OFF_BUTTON: "night", CONF_TEST_BUTTON: "night"}
    )
    assert remo.sent == [("light-0000-0001", "night")]
    assert result["type"] == "form"
    assert result["step_id"] == "light"
    assert result["errors"] == {}
    assert result["description_placeholders"]["name"] == "Living Room Light"
    # The picks survive, and the test field is empty so the next submit saves.
    assert schema_defaults(result) == {
        CONF_ON_BUTTON: "on-100",
        CONF_OFF_BUTTON: "night",
    }
    assert schema_options(result, CONF_TEST_BUTTON) == schema_options(
        result, CONF_ON_BUTTON
    )

    result = await flow.async_step_light(
        {CONF_ON_BUTTON: "on-100", CONF_OFF_BUTTON: "night"}
    )
    assert result["description_placeholders"]["name"] == "Hallway Light"
    assert flow._data[CONF_LIGHTS] == {
        "light-0000-0001": {CONF_ON_BUTTON: "on-100", CONF_OFF_BUTTON: "night"}
    }
    assert remo.sent == [("light-0000-0001", "night")]


async def test_the_flow_sends_with_the_entered_token(
    answer_with, monkeypatch: pytest.MonkeyPatch, lights: list[ApplianceResponse]
) -> None:
    """The client used for trying buttons is built from the validated token."""
    tokens: list[str] = []

    def build(token: str) -> FakeRemo:
        tokens.append(token)
        return FakeRemo(token)

    monkeypatch.setattr(config_flow_module, "RemoAPI", build)
    answer_with(lights)
    await ConfigFlow().async_step_user(USER_INPUT)
    assert tokens == ["test-token"]


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        pytest.param(NetworkError(), "send_failed", id="network"),
        pytest.param(AuthError(), "invalid_token", id="auth"),
        pytest.param(RuntimeError("boom"), "unknown", id="unexpected"),
    ],
)
async def test_a_failed_send_is_reported_on_the_form(
    answer_with,
    remo: FakeRemo,
    lights: list[ApplianceResponse],
    error: Exception,
    expected: str,
) -> None:
    """A button that cannot be sent shows an error but keeps the flow going."""
    answer_with(lights[1:])
    flow = ConfigFlow()
    await flow.async_step_user(USER_INPUT)
    remo.error = error

    result = await flow.async_step_light(
        {CONF_ON_BUTTON: "onoff", CONF_OFF_BUTTON: "onoff", CONF_TEST_BUTTON: "onoff"}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "light"
    assert result["errors"] == {"base": expected}
    assert schema_defaults(result) == {
        CONF_ON_BUTTON: "onoff",
        CONF_OFF_BUTTON: "onoff",
    }


async def test_flow_without_lights_creates_the_entry_directly(answer_with) -> None:
    """With nothing to ask about, setup finishes at the first step."""
    answer_with([])
    flow = ConfigFlow()
    result = await flow.async_step_user(USER_INPUT)
    assert result["type"] == "create_entry"
    assert result["data"] == {**USER_INPUT, CONF_LIGHTS: {}}


async def test_a_light_without_buttons_is_not_asked_about(
    answer_with, appliances_payload: list[dict[str, Any]]
) -> None:
    """A light offering no button cannot be switched, so it is skipped."""
    payload = dict(appliances_payload[0])
    payload["light"] = {"buttons": None}
    answer_with([decode(ApplianceResponse, payload)])
    flow = ConfigFlow()
    result = await flow.async_step_user(USER_INPUT)
    assert result["type"] == "create_entry"
    assert result["data"][CONF_LIGHTS] == {}


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        pytest.param(NetworkError(), "network_error", id="network"),
        pytest.param(AuthError(), "invalid_token", id="auth"),
        pytest.param(RuntimeError("boom"), "unknown", id="unexpected"),
    ],
)
async def test_the_first_step_reports_validation_errors(
    answer_with, error: Exception, expected: str
) -> None:
    """A token that cannot be validated re-shows the first step with an error."""
    answer_with(error)
    flow = ConfigFlow()
    result = await flow.async_step_user(USER_INPUT)
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": expected}


async def test_the_first_step_is_shown_without_input(answer_with) -> None:
    """Opening the flow shows the token form."""
    answer_with([])
    result = await ConfigFlow().async_step_user()
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}
