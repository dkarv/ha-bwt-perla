"""Diagnostics support for BWT Perla."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_CODE, CONF_HOST
from homeassistant.core import HomeAssistant

from .coordinator import BwtConfigEntry

TO_REDACT = {
    CONF_CODE,
    CONF_HOST,
    "ssid",
    "mac",
    "ip",
    "sn",
    "sg",
    "dns",
    "pDns",
    "sDns",
    "serial_number",
    "wifi_ssid",
    "mac_address",
    "device_id",
}


# The Silk /silk/status payload is not documented and may carry device
# identifiers (hostname, network details, ...). Only the firmware/product
# metadata the integration itself uses is exported; everything else is dropped.
SILK_STATUS_ALLOWED = {"version", "gitver", "productCode"}


def _raw_data(data: Any) -> dict[str, Any]:
    """Collect the raw device payload held by an ApiData object."""
    raw: dict[str, Any] = {}
    for name, value in vars(data).items():
        name = name.removeprefix("_")
        if is_dataclass(value) and not isinstance(value, type):
            value = asdict(value)
        elif isinstance(value, dict):
            value = {
                key: asdict(item)
                if is_dataclass(item) and not isinstance(item, type)
                else item
                for key, item in value.items()
            }
        if name == "status" and isinstance(value, dict):
            value = {k: v for k, v in value.items() if k in SILK_STATUS_ALLOWED}
        raw[name] = value
    return raw


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: BwtConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    redacted_entry = async_redact_data(
        entry.as_dict(), TO_REDACT | {"title", "unique_id"}
    )
    coordinator = getattr(entry, "runtime_data", None)
    if coordinator is None:
        # Setup failed or has not run: still return the entry for the report.
        return {"entry": redacted_entry, "model": entry.data.get("model")}
    return {
        "entry": redacted_entry,
        "model": coordinator.model.name,
        "last_update_success": coordinator.last_update_success,
        "update_interval": str(coordinator.update_interval),
        "data": async_redact_data(_raw_data(coordinator.data), TO_REDACT),
    }
