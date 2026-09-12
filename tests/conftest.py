"""Shared test fixtures.

These tests never reach the network: every response is loaded from
tests/fixtures, which was recorded from the API and then anonymised.
"""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any

from pydantic import TypeAdapter
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def decode(annotation: Any, payload: Any) -> Any:
    """Validate a payload against a wire type, the way the client does.

    The client goes through api._decode, which adds only the mapping of a
    pydantic failure onto DecodeError; tests that start from a recorded payload
    want the validation alone.
    """
    return TypeAdapter(annotation).validate_python(payload)


def load_fixture(name: str) -> Any:
    """Read a recorded API payload."""
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture(name="appliances_payload")
def appliances_payload_fixture() -> list[dict[str, Any]]:
    """The payload of GET /1/appliances."""
    return load_fixture("appliances")


@pytest.fixture(name="devices_payload")
def devices_payload_fixture() -> list[dict[str, Any]]:
    """The payload of GET /1/devices."""
    return load_fixture("devices")


@pytest.fixture(name="user_payload")
def user_payload_fixture() -> dict[str, Any]:
    """The payload of GET /1/users/me."""
    return load_fixture("users_me")
