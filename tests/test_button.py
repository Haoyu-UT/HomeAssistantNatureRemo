"""Tests for sending a signal with a button."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.nature_remo.button import ApplianceEntity
from custom_components.nature_remo.const import Appliance, NetworkError


async def test_a_failed_send_reaches_the_caller() -> None:
    """A signal that was not sent must not look like a successful press."""

    async def fail() -> None:
        raise NetworkError("unreachable")

    button = ApplianceEntity(
        Appliance("ir-1", "TV", []), SimpleNamespace(send_signal=fail)
    )
    with pytest.raises(NetworkError):
        await button.async_press()
