"""Tests that a rejected login code triggers reauth."""
from unittest.mock import AsyncMock, MagicMock, patch

from bwt_api.bwt import BwtModel
from bwt_api.exception import BwtException, WrongCodeException
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_CODE, CONF_HOST
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bwt_perla.const import DOMAIN
from custom_components.bwt_perla.coordinator import BwtCoordinator


def _entry():
    return MockConfigEntry(
        domain=DOMAIN,
        version=3,
        title="BWT Perla One",
        data={
            CONF_HOST: "192.168.1.50",
            CONF_CODE: "bad",
            "model": BwtModel.PERLA_LOCAL_API.name,
        },
    )


def test_wrong_code_is_a_bwt_exception():
    """Guards the ordering of the except clauses in the coordinator."""
    assert issubclass(WrongCodeException, BwtException)


async def test_setup_wrong_code_starts_reauth(hass):
    """WrongCodeException in the setup probe puts the entry in setup_error and starts reauth."""
    entry = _entry()
    entry.add_to_hass(hass)

    api = MagicMock()
    api.get_current_data = AsyncMock(side_effect=WrongCodeException("bad"))
    api.close = AsyncMock()
    with patch("custom_components.bwt_perla.BwtApi", return_value=api):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
    api.close.assert_awaited_once()
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [f["context"]["source"] for f in flows] == ["reauth"]


async def test_setup_other_error_is_retried(hass):
    """Other connection errors still lead to setup retry, not reauth."""
    entry = _entry()
    entry.add_to_hass(hass)

    api = MagicMock()
    api.get_current_data = AsyncMock(side_effect=BwtException("down"))
    api.close = AsyncMock()
    with patch("custom_components.bwt_perla.BwtApi", return_value=api):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert not hass.config_entries.flow.async_progress_by_handler(DOMAIN)


async def test_coordinator_wrong_code_raises_auth_failed(hass):
    """WrongCodeException during an update is not wrapped into UpdateFailed."""
    api = MagicMock()
    api.get_current_data = AsyncMock(side_effect=WrongCodeException("bad"))
    coordinator = BwtCoordinator(hass, api, BwtModel.PERLA_LOCAL_API)
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_coordinator_other_bwt_error_is_update_failed(hass):
    """Other BwtExceptions keep being reported as UpdateFailed."""
    api = MagicMock()
    api.get_current_data = AsyncMock(side_effect=BwtException("down"))
    coordinator = BwtCoordinator(hass, api, BwtModel.PERLA_LOCAL_API)
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
