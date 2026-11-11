"""Tests for diagnostics redaction."""

from dataclasses import replace
from unittest.mock import AsyncMock

from bwt_api.bwt import BwtModel
from homeassistant.const import CONF_CODE, CONF_HOST
from homeassistant.helpers.json import json_dumps

from custom_components.bwt_perla.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .test_entity_model import (
    HOST,
    MAC,
    SSID,
    _entry,
    _setup,
    _setup_local,
    _silk_api,
    _smartdos_api,
)


async def test_diagnostics_redacts_sensitive_data(hass):
    entry = await _setup_local(hass)
    diag = await async_get_config_entry_diagnostics(hass, entry)
    # Must be serialisable the way HA serialises diagnostics downloads.
    text = json_dumps(diag)
    for secret in ("secret-code", HOST):
        assert secret not in text
    assert diag["entry"]["data"][CONF_CODE] == "**REDACTED**"
    assert diag["entry"]["data"][CONF_HOST] == "**REDACTED**"
    assert diag["model"] == "PERLA_LOCAL_API"
    assert diag["data"]["data"]["firmware_version"] == "2.0"


async def test_diagnostics_smartdos_redacts_wifi(hass):
    api = _smartdos_api()
    info = await api.get_device_info()
    api.get_device_info = AsyncMock(
        return_value=replace(info, device_id="SECRET-DEVICE-ID")
    )
    entry = _entry(BwtModel.SMART_DOS)
    await _setup(hass, entry, "BwtSmartDosApi", api)
    diag = await async_get_config_entry_diagnostics(hass, entry)
    text = json_dumps(diag)
    for secret in (SSID, MAC, "10.0.0.5", HOST, "SECRET-DEVICE-ID"):
        assert secret not in text
    assert diag["data"]["device_info"]["device_id"] == "**REDACTED**"
    assert diag["data"]["wifi_info"]["rssiAvg"] == "-65"


async def test_diagnostics_silk_drops_unknown_status_fields(hass):
    api = _silk_api()
    api.get_status = AsyncMock(
        return_value={
            "version": "1.2",
            "gitver": 3,
            "productCode": "SILK",
            "hostname": "bwt-silk-secret-host",
            "wifi": {"ssid": SSID, "bssid": MAC},
            "deviceId": "SECRET-DEVICE-ID",
        }
    )
    entry = _entry(BwtModel.PERLA_SILK)
    await _setup(hass, entry, "BwtSilkApi", api)
    diag = await async_get_config_entry_diagnostics(hass, entry)
    text = json_dumps(diag)
    for secret in ("secret-host", SSID, MAC, "SECRET-DEVICE-ID", HOST):
        assert secret not in text
    assert diag["data"]["status"] == {
        "version": "1.2",
        "gitver": 3,
        "productCode": "SILK",
    }


async def test_diagnostics_silk_data_shape_tripwire(hass):
    """Tripwire for newly added attributes on the Silk data object.

    Diagnostics export every attribute of the data object, so a new one (for
    example from a future register sensor) fails here and must be reviewed for
    sensitive content and redacted if needed. This does not guarantee anything
    about what the real device puts into its registers.
    """
    entry = _entry(BwtModel.PERLA_SILK)
    await _setup(hass, entry, "BwtSilkApi", _silk_api())
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert set(diag["data"]) == {"registers", "status"}
    assert diag["data"]["registers"]
    assert all(
        isinstance(value, int) and not isinstance(value, bool)
        for value in diag["data"]["registers"]
    )


async def test_diagnostics_without_runtime_data(hass):
    """A config entry whose setup failed still yields redacted diagnostics."""
    entry = _entry(BwtModel.PERLA_LOCAL_API, **{CONF_CODE: "secret-code"})
    entry.add_to_hass(hass)
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["model"] == BwtModel.PERLA_LOCAL_API.name
    text = json_dumps(diag)
    assert "secret-code" not in text
    assert HOST not in text
