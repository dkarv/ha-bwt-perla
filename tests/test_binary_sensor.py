"""Tests for the binary_sensor platform and the sensor -> binary_sensor migration."""

from unittest.mock import AsyncMock, MagicMock

from bwt_api.bwt import BwtModel
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_CODE, EntityCategory
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bwt_perla import async_migrate_entry
from custom_components.bwt_perla.const import DOMAIN

from .test_entity_model import (
    HOST,
    _local_response,
    _setup,
    _setup_local,
    _silk_api,
    _smartdos_api,
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
        domain=DOMAIN,
        version=3,
        minor_version=3,
        title="BWT",
        data={"host": HOST, "model": BwtModel.SMART_DOS.name},
    )
    await _setup(hass, entry, "BwtSmartDosApi", _smartdos_api())
    registry = er.async_get(hass)
    for key in SMARTDOS_KEYS:
        uid = f"{entry.entry_id}_{key}"
        assert registry.async_get_entity_id("sensor", DOMAIN, uid) is None
        entity_id = registry.async_get_entity_id("binary_sensor", DOMAIN, uid)
        assert entity_id == f"binary_sensor.bwt_perla_{key}"
        assert (
            registry.async_get(entity_id).entity_category is EntityCategory.DIAGNOSTIC
        )


def _old_entry(model, version=3, minor_version=2, **extra):
    """An entry as written before the binary_sensor platform existed."""
    return MockConfigEntry(
        domain=DOMAIN,
        version=version,
        minor_version=minor_version,
        title="BWT",
        data={"host": HOST, "model": model.name, **extra},
    )


def _old_sensor(registry, entry, key, object_id=None, **kwargs):
    """Register a former sensor.* binary sensor."""
    return registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_{key}",
        config_entry=entry,
        suggested_object_id=object_id or f"bwt_perla_{key}",
        translation_key=key,
        has_entity_name=True,
        **kwargs,
    )


def _local_api():
    api = MagicMock()
    api.close = AsyncMock()
    api.get_current_data = AsyncMock(return_value=_local_response())
    return api


def _issues(hass):
    return [i for i in ir.async_get(hass).issues.values() if i.domain == DOMAIN]


async def test_migration_moves_registry_entries(hass):
    entry = _old_entry(BwtModel.PERLA_LOCAL_API, **{CONF_CODE: "c"})
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    uid = f"{entry.entry_id}_holiday_mode"
    old = _old_sensor(registry, entry, "holiday_mode")
    registry.async_update_entity(
        old.entity_id,
        name="Away",
        icon="mdi:beach",
        labels={"lbl"},
        aliases={"vacation"},
    )
    # An unrelated sensor must be left alone.
    other_uid = f"{entry.entry_id}_holiday_mode_start"
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        other_uid,
        config_entry=entry,
        suggested_object_id="bwt_perla_holiday_mode_start",
    )

    await _setup(hass, entry, "BwtApi", _local_api())

    assert (entry.version, entry.minor_version) == (3, 3)
    assert registry.async_get_entity_id("sensor", DOMAIN, uid) is None
    new_id = registry.async_get_entity_id("binary_sensor", DOMAIN, uid)
    assert new_id == "binary_sensor.bwt_perla_holiday_mode"
    new = registry.async_get(new_id)
    assert new.unique_id == uid
    assert new.name == "Away"
    assert new.icon == "mdi:beach"
    assert new.labels == {"lbl"}
    assert new.aliases == {"vacation"}
    assert new.config_entry_id == entry.entry_id
    # Untouched sensor stays a sensor, no duplicates anywhere.
    assert registry.async_get_entity_id("sensor", DOMAIN, other_uid)
    uids = [e.unique_id for e in registry.entities.values() if e.platform == DOMAIN]
    assert uids.count(uid) == 1
    assert hass.states.get("sensor.bwt_perla_holiday_mode") is None
    assert hass.states.get(new_id) is not None


async def test_migration_keeps_user_disabled_state(hass):
    entry = _old_entry(BwtModel.SMART_DOS)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    old = _old_sensor(registry, entry, "buzzer")
    registry.async_update_entity(
        old.entity_id, disabled_by=er.RegistryEntryDisabler.USER
    )
    await _setup(hass, entry, "BwtSmartDosApi", _smartdos_api())
    new = registry.async_get("binary_sensor.bwt_perla_buzzer")
    assert new.disabled_by is er.RegistryEntryDisabler.USER
    assert hass.states.get("binary_sensor.bwt_perla_buzzer") is None


async def test_migration_keeps_custom_entity_id(hass):
    """A user-renamed entity id keeps its slug in the new domain."""
    entry = _old_entry(BwtModel.SMART_DOS)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    old = _old_sensor(registry, entry, "buzzer")
    registry.async_update_entity(old.entity_id, new_entity_id="sensor.kitchen_beeper")
    await _setup(hass, entry, "BwtSmartDosApi", _smartdos_api())
    uid = f"{entry.entry_id}_buzzer"
    assert registry.async_get_entity_id("binary_sensor", DOMAIN, uid) == (
        "binary_sensor.kitchen_beeper"
    )
    assert registry.async_get_entity_id("sensor", DOMAIN, uid) is None
    (issue,) = _issues(hass)
    assert (
        "`sensor.kitchen_beeper` -> `binary_sensor.kitchen_beeper`"
        in (issue.translation_placeholders["entities"])
    )


async def test_migration_keeps_hidden_area_options_and_device(hass):
    entry = _old_entry(BwtModel.SMART_DOS)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    area = ar.async_get(hass).async_create("Utility room")
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "dev")}
    )
    old = _old_sensor(registry, entry, "buzzer", device_id=device.id)
    registry.async_update_entity(
        old.entity_id,
        hidden_by=er.RegistryEntryHider.USER,
        area_id=area.id,
        categories={"scope": "cat"},
        device_class="problem",
    )
    registry.async_update_entity_options(
        old.entity_id, "conversation", {"should_expose": True}
    )
    registry.async_update_entity_options(old.entity_id, "binary_sensor", {"foo": "bar"})

    # Migrate directly: setup would re-attach the entity to the integration's own device.
    assert await async_migrate_entry(hass, entry)

    new = registry.async_get("binary_sensor.bwt_perla_buzzer")
    assert new.hidden_by is er.RegistryEntryHider.USER
    assert new.area_id == area.id
    assert new.device_id == device.id
    assert new.categories == {"scope": "cat"}
    assert new.device_class == "problem"
    assert new.options["conversation"] == {"should_expose": True}
    assert new.options["binary_sensor"] == {"foo": "bar"}


async def test_migration_when_old_and_new_entries_both_exist(hass):
    """An interrupted earlier run left both entries: keep the new, drop the old."""
    entry = _old_entry(BwtModel.SMART_DOS)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    uid = f"{entry.entry_id}_buzzer"
    _old_sensor(registry, entry, "buzzer")
    new = registry.async_get_or_create(
        "binary_sensor",
        DOMAIN,
        uid,
        config_entry=entry,
        suggested_object_id="bwt_perla_buzzer",
        translation_key="buzzer",
    )
    registry.async_update_entity(new.entity_id, name="Keep me")

    await _setup(hass, entry, "BwtSmartDosApi", _smartdos_api())

    assert registry.async_get_entity_id("sensor", DOMAIN, uid) is None
    assert registry.async_get(new.entity_id).name == "Keep me"
    uids = [e.unique_id for e in registry.entities.values() if e.platform == DOMAIN]
    assert uids.count(uid) == 1


async def test_migration_creates_issue_only_when_something_moved(hass):
    moved_entry = _old_entry(BwtModel.SMART_DOS)
    moved_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    _old_sensor(registry, moved_entry, "buzzer")
    _old_sensor(registry, moved_entry, "aqa_watch")
    fresh_entry = _old_entry(BwtModel.SMART_DOS)
    fresh_entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, moved_entry)
    assert await async_migrate_entry(hass, fresh_entry)

    (issue,) = _issues(hass)
    assert issue.issue_id == f"binary_sensors_moved_{moved_entry.entry_id}"
    assert issue.translation_key == "binary_sensors_moved"
    assert issue.is_fixable is False
    assert issue.severity is ir.IssueSeverity.WARNING
    listed = issue.translation_placeholders["entities"]
    assert "`sensor.bwt_perla_buzzer` -> `binary_sensor.bwt_perla_buzzer`" in listed
    assert "aqa_watch" in listed


async def test_migration_without_old_entities_creates_no_issue(hass):
    """A v3 entry without old sensor entries (new install) migrates cleanly."""
    entry = _old_entry(BwtModel.SMART_DOS)
    await _setup(hass, entry, "BwtSmartDosApi", _smartdos_api())
    assert (entry.version, entry.minor_version) == (3, 3)
    assert entry.state is ConfigEntryState.LOADED
    assert _issues(hass) == []
    registry = er.async_get(hass)
    for key in SMARTDOS_KEYS:
        assert registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_{key}"
        )


async def test_migration_is_idempotent(hass):
    entry = _old_entry(BwtModel.SMART_DOS)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    _old_sensor(registry, entry, "buzzer")

    assert await async_migrate_entry(hass, entry)
    snapshot = sorted(e.entity_id for e in registry.entities.values())
    issue_ids = [i.issue_id for i in _issues(hass)]
    # Forcing a re-run (e.g. minor version reset to 2) changes nothing and adds nothing.
    hass.config_entries.async_update_entry(entry, minor_version=2)
    assert await async_migrate_entry(hass, entry)

    assert sorted(e.entity_id for e in registry.entities.values()) == snapshot
    assert [i.issue_id for i in _issues(hass)] == issue_ids
    assert (entry.version, entry.minor_version) == (3, 3)


async def test_full_migration_chain_from_version_1(hass):
    """v1 entry: unique ids re-keyed, sensors moved."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        title="BWT",
        data={"host": "Bwt.Local", "model": BwtModel.SMART_DOS.name},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    # v1 unique ids had no entry id prefix.
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "buzzer",
        config_entry=entry,
        suggested_object_id="bwt_perla_buzzer",
    )
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "total",
        config_entry=entry,
        suggested_object_id="bwt_perla_total",
    )

    assert await async_migrate_entry(hass, entry)

    assert (entry.version, entry.minor_version) == (3, 3)
    assert (
        registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_buzzer"
        )
        == "binary_sensor.bwt_perla_buzzer"
    )
    assert (
        registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_total")
        == "sensor.bwt_perla_total"
    )
    assert len(_issues(hass)) == 1


async def test_migration_from_version_2(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        title="BWT",
        data={"host": HOST, "model": BwtModel.SMART_DOS.name},
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    _old_sensor(registry, entry, "aqa_max_flow")

    assert await async_migrate_entry(hass, entry)

    assert (entry.version, entry.minor_version) == (3, 3)
    assert registry.async_get_entity_id(
        "binary_sensor", DOMAIN, f"{entry.entry_id}_aqa_max_flow"
    )


async def test_removing_entry_deletes_repair_issue(hass):
    entry = _old_entry(BwtModel.SMART_DOS)
    entry.add_to_hass(hass)
    other = _old_entry(BwtModel.SMART_DOS)
    other.add_to_hass(hass)
    registry = er.async_get(hass)
    _old_sensor(registry, entry, "buzzer")
    _old_sensor(registry, other, "buzzer")
    assert await async_migrate_entry(hass, entry)
    assert await async_migrate_entry(hass, other)
    assert len(_issues(hass)) == 2

    await hass.config_entries.async_remove(entry.entry_id)

    assert [i.issue_id for i in _issues(hass)] == [
        f"binary_sensors_moved_{other.entry_id}"
    ]


async def test_silk_flags_are_binary_sensors(hass):
    entry = _old_entry(BwtModel.PERLA_SILK, minor_version=3)
    await _setup(hass, entry, "BwtSilkApi", _silk_api())
    registry = er.async_get(hass)
    for key in ("allow_salt_type_change", "allow_regen_time_change"):
        uid = f"{entry.entry_id}_{key}"
        assert registry.async_get_entity_id("sensor", DOMAIN, uid) is None
        assert registry.async_get_entity_id("binary_sensor", DOMAIN, uid) == (
            f"binary_sensor.bwt_perla_{key}"
        )


async def test_silk_flag_register_migrates_through_3_2_and_3_3(hass):
    """A raw silk_register_39 sensor is re-keyed (3.2), then moved (3.3)."""
    entry = _old_entry(BwtModel.PERLA_SILK, minor_version=1)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_silk_register_39",
        config_entry=entry,
        suggested_object_id="bwt_perla_silk_register_39",
    )

    assert await async_migrate_entry(hass, entry)

    assert (entry.version, entry.minor_version) == (3, 3)
    uid = f"{entry.entry_id}_allow_salt_type_change"
    assert registry.async_get_entity_id("sensor", DOMAIN, uid) is None
    assert registry.async_get_entity_id("binary_sensor", DOMAIN, uid) == (
        "binary_sensor.bwt_perla_silk_register_39"
    )
    (issue,) = _issues(hass)
    assert (
        "`sensor.bwt_perla_silk_register_39` -> `binary_sensor.bwt_perla_silk_register_39`"
        in issue.translation_placeholders["entities"]
    )
