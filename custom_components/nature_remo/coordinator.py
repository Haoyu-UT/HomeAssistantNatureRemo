"""Polling coordinators for the nature_remo integration.

Both are created during config entry setup rather than by a platform: the
platforms are set up concurrently, so one cannot rely on a coordinator another
has built.
"""

from __future__ import annotations

import datetime
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import RemoAPI

_LOGGER = logging.getLogger(__name__)


class SensorCoordinator(DataUpdateCoordinator):
    """Coordinator for polling Remo sensor data"""

    def __init__(self, hass: HomeAssistant, api: RemoAPI, update_interval: int) -> None:
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name="Remo API Coordinator for sensors",
            update_interval=datetime.timedelta(seconds=update_interval),
            update_method=self.api.fetch_sensor_data,
        )


class ApplianceCoordinator(DataUpdateCoordinator):
    """Coordinator for polling appliance data.

    Drives the power meter sensors, and is also how a change made outside Home
    Assistant reaches an entity: the API offers no push channel, so an air
    conditioner's settings and a light's reported power are only ever noticed
    on the next poll.
    """

    def __init__(self, hass: HomeAssistant, api: RemoAPI, update_interval: int) -> None:
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name="Remo API Coordinator for appliances",
            update_interval=datetime.timedelta(seconds=update_interval),
            update_method=self.api.fetch_grouped_appliances,
        )
