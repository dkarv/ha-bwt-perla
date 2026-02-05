"""The BWT Perla integration."""

import logging

from bwt_api.api import BwtApi, BwtSilkApi
from bwt_api.exception import BwtException

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_CODE, CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity_registry import async_migrate_entries
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BWT Perla from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    try:
        if CONF_CODE in entry.data:
            api = BwtApi(entry.data["host"], entry.data["code"])
            await api.get_current_data()
        else:
            api = BwtSilkApi(entry.data["host"])
            await api.get_registers()
    except Exception as e:
        _LOGGER.exception("Error setting up Bwt API")
        await api.close()
        raise ConfigEntryNotReady from e

    hass.data[DOMAIN][entry.entry_id] = api

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        api = hass.data[DOMAIN].pop(entry.entry_id)
        await api.close()

    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", entry.version)

    # Add entry id to unique id in order to allow multiple devices
    if entry.version == 1:

        @callback
        def update_unique_id(entity_entry):
            """Update unique ID of entity entry."""
            return {"new_unique_id": entry.entry_id + "_" + entity_entry.unique_id}

        await async_migrate_entries(hass, entry.entry_id, update_unique_id)
        hass.config_entries.async_update_entry(entry, version=2)

    # Fix entity ids
    if entry.version == 2:
        # Remove dollar signs from entity IDs for entities created by this config entry
        registry = er.async_get(hass)

        for entity in list(registry.entities.values()):
            # Only operate on entities that belong to this config entry
            if entity.config_entry_id != entry.entry_id:
                continue

            if "$" not in entity.entity_id:
                continue

            new_entity_id = entity.entity_id.replace("$", "")
            try:
                registry.async_update_entity(entity.entity_id, new_entity_id=new_entity_id)
                _LOGGER.info("Renamed entity %s -> %s", entity.entity_id, new_entity_id)
            except ValueError as exc:
                _LOGGER.warning(
                    "Could not rename entity %s -> %s: %s",
                    entity.entity_id,
                    new_entity_id,
                    exc,
                )
        
        hass.config_entries.async_update_entry(entry, version=3)

    _LOGGER.info("Migration to version %s successful", entry.version)

    return True
