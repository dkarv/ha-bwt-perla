"""The BWT Perla integration."""

import logging

from bwt_api.api import BwtApi, BwtSilkApi, BwtSmartDosApi
from bwt_api.bwt import BwtModel

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_CODE
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity_registry import async_migrate_entries
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .coordinator import BwtConfigEntry, BwtCoordinator
from .data.silk import FLAG_REGISTERS, SETTING_REGISTERS

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: BwtConfigEntry) -> bool:
    """Set up BWT Perla from a config entry."""

    # Backwards compatibility: older config entries may not have a `model` key.
    model_value = entry.data.get("model")
    if model_value is None:
        # Fall back to previous behaviour: presence of CONF_CODE implied local API,
        # otherwise assume Silk API. Update the config entry for future runs.
        inferred = BwtModel.PERLA_LOCAL_API if CONF_CODE in entry.data else BwtModel.PERLA_SILK
        model_value = inferred.name
        new_data = dict(entry.data)
        new_data["model"] = model_value
        hass.config_entries.async_update_entry(entry, data=new_data)

    lib_logger = _LOGGER.getChild("bwt_api")
    if model_value == BwtModel.PERLA_LOCAL_API.name:
        model = BwtModel.PERLA_LOCAL_API
        api = BwtApi(entry.data["host"], entry.data.get("code"), lib_logger)
    elif model_value == BwtModel.PERLA_SILK.name:
        model = BwtModel.PERLA_SILK
        api = BwtSilkApi(entry.data["host"], lib_logger)
    elif model_value == BwtModel.SMART_DOS.name:
        model = BwtModel.SMART_DOS
        api = BwtSmartDosApi(entry.data["host"], lib_logger)
    else:
        raise ConfigEntryNotReady(f"Unsupported BWT model: {model_value}")

    coordinator = BwtCoordinator(hass, entry, api, model)
    try:
        # Raises ConfigEntryAuthFailed (starting reauth) on a rejected login
        # code and ConfigEntryNotReady on any other failure.
        await coordinator.async_config_entry_first_refresh()
    except Exception as e:
        _LOGGER.debug("Error connecting to BWT device at %s: %s", entry.data["host"], e)
        await api.close()
        raise

    entry.runtime_data = coordinator

    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        await api.close()
        raise

    return True


async def async_unload_entry(hass: HomeAssistant, entry: BwtConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.my_api.close()

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Clean up the persistent repair issue when the config entry is deleted."""
    ir.async_delete_issue(hass, DOMAIN, f"binary_sensors_moved_{entry.entry_id}")


# Entity keys that used to be registered in the sensor domain and now live in the
# binary_sensor domain.
_BINARY_SENSOR_KEYS = (
    "holiday_mode",
    "buzzer",
    "aqa_watch",
    "aqa_max_flow",
    "aqa_max_volume",
    *FLAG_REGISTERS,
)


def _move_binary_sensors(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, str]:
    """Re-register the former sensor.* binary sensors in the binary_sensor domain.

    The registry refuses a domain change on an existing entry
    (``async_update_entity(new_entity_id=...)`` raises "New entity ID should be
    same domain"), and the registry key includes the domain. So the old entry is
    removed and an equivalent one is created with the same unique id and entity id
    slug, carrying over the user's customizations.

    Returns a mapping of old entity id -> new entity id for everything moved.
    """
    registry = er.async_get(hass)
    moved: dict[str, str] = {}
    for key in _BINARY_SENSOR_KEYS:
        unique_id = f"{entry.entry_id}_{key}"
        old_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        if old_id is None:
            continue
        old = registry.async_get(old_id)
        new_id = registry.async_get_entity_id("binary_sensor", DOMAIN, unique_id)
        if new_id is None:
            options = {k: dict(v) for k, v in old.options.items()}
            new_id = registry.async_get_or_create(
                "binary_sensor",
                DOMAIN,
                unique_id,
                config_entry=entry,
                device_id=old.device_id,
                suggested_object_id=old_id.split(".", 1)[1],
                disabled_by=old.disabled_by,
                hidden_by=old.hidden_by,
                get_initial_options=(lambda opts=options: opts) if options else None,
                capabilities=old.capabilities,
                entity_category=old.entity_category,
                has_entity_name=old.has_entity_name,
                original_device_class=old.original_device_class,
                original_icon=old.original_icon,
                original_name=old.original_name,
                supported_features=old.supported_features,
                translation_key=old.translation_key,
                unit_of_measurement=old.unit_of_measurement,
            ).entity_id
            registry.async_update_entity(
                new_id,
                name=old.name,
                icon=old.icon,
                device_class=old.device_class,
                area_id=old.area_id,
                aliases=old.aliases,
                labels=old.labels,
                categories=old.categories,
            )
        # else: a previous, interrupted run already created the new entry; keep it.
        registry.async_remove(old_id)
        moved[old_id] = new_id
        _LOGGER.info("Moved entity %s -> %s", old_id, new_id)
    return moved


def _create_moved_entities_issue(
    hass: HomeAssistant, entry: ConfigEntry, moved: dict[str, str]
) -> None:
    """Tell the user which entity ids changed domain (automations need updating)."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"binary_sensors_moved_{entry.entry_id}",
        is_fixable=False,
        is_persistent=True,
        severity=ir.IssueSeverity.ERROR,
        translation_key="binary_sensors_moved",
        translation_placeholders={
            "title": entry.title,
            "entities": "\n".join(f"- `{o}` -> `{n}`" for o, n in moved.items()),
        },
    )


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

    # 3.2: Silk registers with a known meaning became named sensors. Move their
    # registry entries to the new unique ids so entity ids and history are kept.
    if entry.version == 3 and entry.minor_version < 2:
        renames = {
            f"{entry.entry_id}_silk_register_{index}": f"{entry.entry_id}_{key}"
            for key, index in {**SETTING_REGISTERS, **FLAG_REGISTERS}.items()
        }

        @callback
        def rename_silk_register(entity_entry):
            """Re-key a raw Silk register entity to its named sensor."""
            if new_unique_id := renames.get(entity_entry.unique_id):
                return {"new_unique_id": new_unique_id}
            return None

        await async_migrate_entries(hass, entry.entry_id, rename_silk_register)
        hass.config_entries.async_update_entry(entry, minor_version=2)

    # 3.3: Binary sensors moved from the sensor platform to the binary_sensor platform.
    # The stored data is unchanged, so this is a minor version bump (older
    # versions can still load the entry).
    if entry.version == 3 and entry.minor_version < 3:
        moved = _move_binary_sensors(hass, entry)
        hass.config_entries.async_update_entry(entry, minor_version=3)
        if moved:
            _create_moved_entities_issue(hass, entry, moved)

    _LOGGER.info("Migration to version %s.%s successful", entry.version, entry.minor_version)

    return True
