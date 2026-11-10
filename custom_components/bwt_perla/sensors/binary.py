"""BWT binary sensor entities."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory

from ..coordinator import BwtCoordinator
from .base import BwtEntity

_HOLIDAY = "mdi:location-exit"


class BwtBinaryEntity(BwtEntity, BinarySensorEntity):
    """Common base of all BWT binary sensors."""

    _entity_domain = "binary_sensor"


class SimpleBinarySensor(BwtBinaryEntity):
    """Simple binary sensor with extract function."""

    def __init__(
        self,
        coordinator: BwtCoordinator,
        device_info: DeviceInfo,
        entry_id: str,
        key: str,
        extract,
        icon: str,
        *,
        entity_category: EntityCategory | None = None,
    ) -> None:
        """Initialize the binary sensor with the common coordinator."""
        super().__init__(
            coordinator, device_info, entry_id, key, entity_category=entity_category
        )
        self._attr_icon = icon
        self._extract = extract
        self._attr_is_on = self._extract(self.coordinator.data)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_on = self._extract(self.coordinator.data)
        self.async_write_ha_state()


class HolidayModeSensor(BwtBinaryEntity):
    """Current holiday mode state."""

    _attr_icon = _HOLIDAY

    def __init__(self, coordinator, device_info: DeviceInfo, entry_id: str) -> None:
        """Initialize the sensor with the common coordinator."""
        super().__init__(coordinator, device_info, entry_id, "holiday_mode")
        self._attr_is_on = self.coordinator.data.holiday_mode() == 1

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_on = self.coordinator.data.holiday_mode() == 1
        self.async_write_ha_state()
