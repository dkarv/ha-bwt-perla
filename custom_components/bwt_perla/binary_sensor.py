"""BWT binary sensors."""

from bwt_api.bwt import BwtModel
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import BwtConfigEntry
from .data.silk import FLAG_REGISTERS
from .sensors.base import build_device_info
from .sensors.binary import HolidayModeSensor, SimpleBinarySensor

_UNKNOWN = "mdi:help-circle"
_SETTING = "mdi:cog-outline"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BwtConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up bwt binary sensors from config entry."""
    coordinator = config_entry.runtime_data
    model = coordinator.model
    device_info = build_device_info(coordinator, config_entry)
    entry_id = config_entry.entry_id

    entities = []
    if model == BwtModel.PERLA_LOCAL_API:
        entities.append(HolidayModeSensor(coordinator, device_info, entry_id))
    elif model == BwtModel.SMART_DOS:
        for key, extract in (
            ("buzzer", lambda data: data.buzzer()),
            ("aqa_watch", lambda data: data.aqa_watch()),
            ("aqa_max_flow", lambda data: data.aqa_max_flow()),
            ("aqa_max_volume", lambda data: data.aqa_max_volume()),
        ):
            entities.append(
                SimpleBinarySensor(
                    coordinator,
                    device_info,
                    entry_id,
                    key,
                    extract,
                    _UNKNOWN,
                    entity_category=EntityCategory.DIAGNOSTIC,
                )
            )

    elif model == BwtModel.PERLA_SILK:
        for key, index in FLAG_REGISTERS.items():
            entities.append(
                SimpleBinarySensor(
                    coordinator,
                    device_info,
                    entry_id,
                    key,
                    lambda data, index=index: data.get_flag(index),
                    _SETTING,
                    entity_category=EntityCategory.DIAGNOSTIC,
                )
            )

    async_add_entities(entities)
