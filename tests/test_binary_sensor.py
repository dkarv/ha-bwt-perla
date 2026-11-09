"""Tests for the binary_sensor platform and the sensor -> binary_sensor migration."""
from unittest.mock import AsyncMock, MagicMock, patch

from bwt_api.bwt import BwtModel
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_CODE, EntityCategory
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bwt_perla.const import DOMAIN

from .test_entity_model import (
    HOST,
    _local_response,
    _smartdos_api,
    _setup,
    _setup_local,
)

SMARTDOS_KEYS = ("buzzer", "aqa_watch", "aqa_max_flow", "aqa_max_volume")


async def test_local_holiday_mode_is_binary_sensor(hass):
    entry = await _setup_local(hass)
    registry = er.async_get(hass)
    uid = f"{entry.entry_id}_holiday_mode"
    assert registry.async_get_entity_id("sensor", DOMAIN, uid) is None
    entity_id = registry.async_get_entity_id("binary_sensor", DOMAIN, uid)
    assert entity_id == "binary_sensor.bwt_perla_holiday_mode"
    # Holiday mode only "starts in the future" -> not active yet.
    assert hass.states.get(entity_id).state == "off"


async def test_smartdos_binary_sensors(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, version=4, title="BWT", unique_id=HOST,
        data={"host": HOST, "model": BwtModel.SMART_DOS.name},
    )
    await _setup(hass, entry, "BwtSmartDosApi", _smartdos_api())
    registry = er.async_get(hass)
    for key in SMARTDOS_KEYS:
        uid = f"{entry.entry_id}_{key}"
        assert registry.async_get_entity_id("sensor", DOMAIN, uid) is None
        entity_id = registry.async_get_entity_id("binary_sensor", DOMAIN, uid)
        assert entity_id == f"binary_sensor.bwt_perla_{key}"
        assert registry.async_get(entity_id).entity_category is EntityCategory.DIAGNOSTIC


def _old_entry(model, version=3, **extra):
    return MockConfigEntry(
        domain=DOMAIN, version=version, title="BWT", unique_id=HOST,
        data={"host": HOST, "model": model.name, **extra},
    )


async def test_migration_moves_registry_entries(hass):
    entry = _old_entry(BwtModel.PERLA_LOCAL_API, **{CONF_CODE: "c"})
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    uid = f"{entry.entry_id}_holiday_mode"
    old = registry.async_get_or_create(
        "sensor", DOMAIN, uid, config_entry=entry,
        suggested_object_id="bwt_perla_holiday_mode",
        translation_key="holiday_mode", has_entity_name=True,
    )
    registry.async_update_entity(
        old.entity_id, name="Away", icon="mdi:beach", area_id=None,
        disabled_by=None, labels={"lbl"},
    )
    # An unrelated sensor must be left alone.
    other_uid = f"{entry.entry_id}_holiday_mode_start"
    registry.async_get_or_create(
        "sensor", DOMAIN, other_uid, config_entry=entry,
        suggested_object_id="bwt_perla_holiday_mode_start",
    )

    api = MagicMock()
    api.close = AsyncMock()
    api.get_current_data = AsyncMock(return_value=_local_response())
    await _setup(hass, entry, "BwtApi", api)

    assert entry.version == 4
    assert registry.async_get_entity_id("sensor", DOMAIN, uid) is None
    new_id = registry.async_get_entity_id("binary_sensor", DOMAIN, uid)
    assert new_id == "binary_sensor.bwt_perla_holiday_mode"
    new = registry.async_get(new_id)
    assert new.unique_id == uid
    assert new.name == "Away"
    assert new.icon == "mdi:beach"
    assert new.labels == {"lbl"}
    assert new.config_entry_id == entry.entry_id
    # Untouched sensor stays a sensor, no duplicates anywhere.
    assert registry.async_get_entity_id("sensor", DOMAIN, other_uid)
    ids = [e.entity_id for e in registry.entities.values() if e.platform == DOMAIN]
    assert len(ids) == len(set(ids))
    uids = [e.unique_id for e in registry.entities.values() if e.platform == DOMAIN]
    assert uids.count(uid) == 1
    assert hass.states.get("sensor.bwt_perla_holiday_mode") is None
    assert hass.states.get(new_id) is not None


async def test_migration_keeps_user_disabled_state(hass):
    entry = _old_entry(BwtModel.SMART_DOS)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    uid = f"{entry.entry_id}_buzzer"
    old = registry.async_get_or_create(
        "sensor", DOMAIN, uid, config_entry=entry,
        suggested_object_id="bwt_perla_buzzer",
    )
    registry.async_update_entity(
        old.entity_id, disabled_by=er.RegistryEntryDisabler.USER
    )
    await _setup(hass, entry, "BwtSmartDosApi", _smartdos_api())
    new = registry.async_get("binary_sensor.bwt_perla_buzzer")
    assert new.disabled_by is er.RegistryEntryDisabler.USER
    assert hass.states.get("binary_sensor.bwt_perla_buzzer") is None


async def test_migration_is_idempotent_for_fresh_entries(hass):
    """A v3 entry without old sensor entries (new install) migrates cleanly."""
    entry = _old_entry(BwtModel.SMART_DOS)
    await _setup(hass, entry, "BwtSmartDosApi", _smartdos_api())
    assert entry.version == 4
    assert entry.state is ConfigEntryState.LOADED
    registry = er.async_get(hass)
    for key in SMARTDOS_KEYS:
        assert registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_{key}"
        )
