"""Resolving which remote buttons switch a light on and off.

The config flow asks the user to pick the two buttons; the light platform reads
that choice back.  Both go through here so they agree on the fallback used for
a light the user was never asked about — one added to the Nature app after the
integration was set up, or an entry that predates the question.
"""

from __future__ import annotations

from typing import Any

from .const import (
    BUTTON_OFF,
    BUTTON_ON,
    BUTTON_ONOFF,
    CONF_LIGHTS,
    CONF_OFF_BUTTON,
    CONF_ON_BUTTON,
)
from .models import ApplianceResponse


def button_choices(appliance: ApplianceResponse) -> dict[str, str]:
    """Return the light's buttons as a mapping of name to human-readable label."""
    if appliance.light is None:
        return {}
    return {
        button.name: button.label or button.name
        for button in appliance.light.buttons or []
    }


def default_buttons(names: list[str]) -> tuple[str, str] | None:
    """Guess the (on, off) pair to pre-select, or None if nothing fits.

    A remote exposes either separate on and off buttons or a single toggle; the
    guess prefers the pair so a toggle is never offered where a real pair
    exists.
    """
    if BUTTON_ON in names and BUTTON_OFF in names:
        return (BUTTON_ON, BUTTON_OFF)
    if BUTTON_ONOFF in names:
        return (BUTTON_ONOFF, BUTTON_ONOFF)
    if names:
        return (names[0], names[0])
    return None


def resolve_buttons(
    entry_data: dict[str, Any], appliance: ApplianceResponse
) -> tuple[str, str] | None:
    """Return the (on, off) pair to use for ``appliance``.

    The user's choice wins; a button they picked that the remote no longer
    offers is discarded so a renamed or re-paired light falls back to the guess
    rather than sending a name the API would reject.
    """
    choices = button_choices(appliance)
    configured = (entry_data.get(CONF_LIGHTS) or {}).get(appliance.id)
    if configured is not None:
        on_button = configured.get(CONF_ON_BUTTON)
        off_button = configured.get(CONF_OFF_BUTTON)
        if on_button in choices and off_button in choices:
            return (on_button, off_button)
    return default_buttons(list(choices))
