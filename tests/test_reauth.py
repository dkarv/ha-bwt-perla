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

from custom_components.bwt_perla import async_migrate_entry
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
    coordinator = BwtCoordinator(hass, _entry(), api, BwtModel.PERLA_LOCAL_API)
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_coordinator_other_bwt_error_is_update_failed(hass):
    """Other BwtExceptions keep being reported as UpdateFailed."""
    api = MagicMock()
    api.get_current_data = AsyncMock(side_effect=BwtException("down"))
    coordinator = BwtCoordinator(hass, _entry(), api, BwtModel.PERLA_LOCAL_API)
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_setup_and_unload_use_runtime_data(hass):
    """The coordinator lives in entry.runtime_data and unload closes the api."""
    entry = _entry()
    entry.add_to_hass(hass)

    data = MagicMock()
    api = MagicMock()
    api.get_current_data = AsyncMock(return_value=data)
    api.close = AsyncMock()
    with patch("custom_components.bwt_perla.BwtApi", return_value=api), patch(
        "custom_components.bwt_perla.coordinator.LocalApiData"
    ) as data_cls:
        data_cls.return_value.current_flow.return_value = 0
        with patch.object(
            hass.config_entries, "async_forward_entry_setups", AsyncMock()
        ), patch.object(
            hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True)
        ):
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
            assert entry.state is ConfigEntryState.LOADED
            coordinator = entry.runtime_data
            assert isinstance(coordinator, BwtCoordinator)
            assert coordinator.config_entry is entry
            assert coordinator.model is BwtModel.PERLA_LOCAL_API
            assert DOMAIN not in hass.data

            assert await hass.config_entries.async_unload(entry.entry_id)
            api.close.assert_awaited_once()


async def test_migration_backfills_unique_id(hass):
    """Entries created before unique ids existed get one derived from the host."""
    entry = _entry()
    entry.add_to_hass(hass)
    assert entry.unique_id is None
    assert entry.minor_version == 1

    assert await async_migrate_entry(hass, entry)

    assert entry.unique_id == "192.168.1.50"
    assert entry.minor_version == 2


async def test_migration_skips_unique_id_on_collision(hass):
    """A second entry for the same host keeps no unique id instead of erroring."""
    first = _entry()
    first.add_to_hass(hass)
    second = _entry()
    second.add_to_hass(hass)

    assert await async_migrate_entry(hass, first)
    assert await async_migrate_entry(hass, second)

    assert first.unique_id == "192.168.1.50"
    assert second.unique_id is None
    assert second.minor_version == 2


async def test_smartdos_requests_run_sequentially(hass):
    """The six SmartDos requests are issued one after another, never overlapping."""
    import asyncio

    active = 0
    max_active = 0
    calls = []

    def make(name):
        async def fetch():
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            calls.append(name)
            await asyncio.sleep(0)
            active -= 1
            return MagicMock()

        return fetch

    names = [
        "get_device_info",
        "get_configuration",
        "get_remaining_capacity",
        "get_treated_water",
        "get_substance_dosage",
        "get_wifi_info",
    ]
    api = MagicMock()
    for name in names:
        setattr(api, name, make(name))
    coordinator = BwtCoordinator(hass, _entry(), api, BwtModel.SMART_DOS)
    with patch("custom_components.bwt_perla.coordinator.SmartDosApiData") as data_cls:
        data_cls.return_value.current_flow.return_value = 0
        await coordinator._async_update_data()
    assert calls == names
    assert max_active == 1


async def test_setup_closes_api_when_platform_setup_fails(hass):
    """A failing platform forward must not leak the api session."""
    entry = _entry()
    entry.add_to_hass(hass)
    api = MagicMock()
    api.get_current_data = AsyncMock(return_value=MagicMock())
    api.close = AsyncMock()
    with (
        patch("custom_components.bwt_perla.BwtApi", return_value=api),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            AsyncMock(side_effect=RuntimeError("boom")),
        ),
        patch("custom_components.bwt_perla.coordinator.LocalApiData"),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
    api.close.assert_awaited()
