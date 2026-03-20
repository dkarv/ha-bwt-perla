"""Coordinator to fetch the data once for all sensors."""

import asyncio
from datetime import timedelta
import json
import logging

from bwt_api.bwt import BwtModel
from bwt_api.exception import BwtException

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .data.data import ApiData
from .data.local import LocalApiData
from .data.silk import SilkApiData

_LOGGER = logging.getLogger(__name__)

_UPDATE_INTERVAL_MIN = 1
_UPDATE_INTERVAL_MAX = 30


class BwtCoordinator(DataUpdateCoordinator[ApiData]):
    """Bwt coordinator."""
    model: BwtModel

    def __init__(self, hass: HomeAssistant, api, model: BwtModel) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="My sensor",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=_UPDATE_INTERVAL_MAX),
        )
        self.my_api = api
        self.model = model

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        # Note: asyncio.TimeoutError and aiohttp.ClientError are already
        # handled by the data update coordinator. However, bwt_api raises
        # its own BwtException hierarchy (not derived from aiohttp.ClientError)
        # and the device may return empty responses that cause JSONDecodeError.
        # Both must be caught here to avoid unhandled tracebacks.
        try:
            async with asyncio.timeout(10):
                if self.model == BwtModel.PERLA_LOCAL_API:
                    new_values = LocalApiData(await self.my_api.get_current_data())
                elif self.model == BwtModel.PERLA_SILK:
                    new_values = SilkApiData(await self.my_api.get_registers())
                else:
                    raise UpdateFailed(
                        f"Unsupported API type: {type(self.my_api)}"
                    )
        except (BwtException, json.JSONDecodeError) as err:
            raise UpdateFailed(
                f"Error communicating with BWT device: {err}"
            ) from err
        self.update_interval = calculate_update_interval(
            self.update_interval, new_values.current_flow()
        )
        return new_values

    def get_model_suffix(self) -> str:
        """Get the model suffix based on the number of columns."""
        if self.model == BwtModel.PERLA_LOCAL_API:
            if self.data.columns() == 2:
                return "Duplex"
            return "One"
        return "Silk"

    def get_firmware_version(self) -> str:
        """Get the firmware version."""
        if self.model == BwtModel.PERLA_LOCAL_API:
            return self.data.firmware_version()
        return "Unknown"


def calculate_update_interval(current_interval: timedelta | None, current_flow: int):
    """Calculate the new update interval, based on the old one and the current flow."""

    if current_flow > 0:
        return timedelta(seconds=_UPDATE_INTERVAL_MIN)
    if current_interval is None:
        return timedelta(seconds=_UPDATE_INTERVAL_MAX)
    if current_interval.seconds >= _UPDATE_INTERVAL_MAX:
        return current_interval
    # Increase the interval to max step by step if there is no flow at the moment
    return timedelta(seconds=min(_UPDATE_INTERVAL_MAX, current_interval.seconds * 2))
