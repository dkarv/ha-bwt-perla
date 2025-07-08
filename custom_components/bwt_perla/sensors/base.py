
from datetime import datetime

from bwt_api.api import treated_to_blended
from bwt_api.data import BwtStatus

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfVolume,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..coordinator import BwtCoordinator

_FAUCET = "mdi:faucet"
_WATER = "mdi:water"
_WARNING = "mdi:alert-circle"
_ERROR = "mdi:alert-decagram"
_WATER_CHECK = "mdi:water-check"
_HOLIDAY = "mdi:location-exit"
_UNKNOWN = "mdi:help-circle"

class BwtEntity(CoordinatorEntity[BwtCoordinator]):
    """General bwt entity with common properties."""

    def __init__(
        self,
        coordinator: BwtCoordinator,
        device_info: DeviceInfo,
        entry_id: str,
        key: str,
    ) -> None:
        """Initialize the common properties."""
        super().__init__(coordinator)
        self._attr_device_info = device_info
        self._attr_translation_key = key
        self._attr_has_entity_name = True
        self.entity_id = f"sensor.${DOMAIN}_${key}"
        self._attr_unique_id = entry_id + "_" + key


class TotalOutputSensor(BwtEntity, SensorEntity):
    """Total water [liter] that passed through the output."""

    _attr_icon = _WATER
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, device_info, entry_id) -> None:
        """Initialize the sensor with the common coordinator."""
        super().__init__(coordinator, device_info, entry_id, "total_output")
        self._attr_native_value = coordinator.data.total_output()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.coordinator.data.total_output()
        self.async_write_ha_state()


class CurrentFlowSensor(BwtEntity, SensorEntity):
    """Current flow per hour."""

    _attr_native_unit_of_measurement = UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = _FAUCET
    suggested_display_precision = 3

    def __init__(self, coordinator, device_info, entry_id) -> None:
        """Initialize the sensor with the common coordinator."""
        super().__init__(coordinator, device_info, entry_id, "current_flow")
        self._attr_native_value = coordinator.data.current_flow() / 1000.0

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # HA only has m3 / h, we get the values in l/h
        self._attr_native_value = self.coordinator.data.current_flow() / 1000.0
        self.async_write_ha_state()


class ErrorSensor(BwtEntity, SensorEntity):
    """Errors reported by the device."""

    _attr_icon = _ERROR

    def __init__(self, coordinator, device_info, entry_id) -> None:
        """Initialize the sensor with the common coordinator."""
        super().__init__(coordinator, device_info, entry_id, "errors")
        values = [x.name for x in self.coordinator.data.errors() if x.is_fatal()]
        self._attr_native_value = ",".join(values)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        values = [x.name for x in self.coordinator.data.errors() if x.is_fatal()]
        self._attr_native_value = ",".join(values)
        self.async_write_ha_state()


class WarningSensor(BwtEntity, SensorEntity):
    """Warnings reported by the device."""

    _attr_icon = _WARNING

    def __init__(self, coordinator, device_info, entry_id) -> None:
        """Initialize the sensor with the common coordinator."""
        super().__init__(coordinator, device_info, entry_id, "warnings")
        values = [x.name for x in self.coordinator.data.errors() if not x.is_fatal()]
        self._attr_native_value = ",".join(values)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        values = [x.name for x in self.coordinator.data.errors() if not x.is_fatal()]
        self._attr_native_value = ",".join(values)
        self.async_write_ha_state()


class SimpleSensor(BwtEntity, SensorEntity):
    """Simplest sensor with least configuration options."""

    def __init__(
        self,
        coordinator: BwtCoordinator,
        device_info: DeviceInfo,
        entry_id: str,
        key: str,
        extract,
        icon: str,
    ) -> None:
        """Initialize the sensor with the common coordinator."""
        super().__init__(coordinator, device_info, entry_id, key)
        self._attr_icon = icon
        self._extract = extract
        self._attr_native_value = self._extract(self.coordinator.data)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self._extract(self.coordinator.data)
        self.async_write_ha_state()


class DeviceClassSensor(SimpleSensor):
    """Basic sensor specifying a device class."""

    def __init__(
        self,
        coordinator: BwtCoordinator,
        device_info: DeviceInfo,
        entry_id: str,
        key: str,
        extract,
        device_class: SensorDeviceClass,
        icon: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_info, entry_id, key, extract, icon)
        self._attr_device_class = device_class


class UnitSensor(SimpleSensor):
    """Sensor specifying a unit."""

    def __init__(
        self,
        coordinator: BwtCoordinator,
        device_info: DeviceInfo,
        entry_id: str,
        key: str,
        extract,
        unit: str,
        icon: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_info, entry_id, key, extract, icon)
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = SensorStateClass.MEASUREMENT


class StateSensor(BwtEntity, SensorEntity):
    """State of the machine."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(BwtStatus.__members__)
    _attr_icon = _WATER_CHECK

    def __init__(self, coordinator, device_info: DeviceInfo, entry_id: str) -> None:
        """Initialize the sensor with the common coordinator."""
        super().__init__(coordinator, device_info, entry_id, "state")
        self._attr_native_value = self.coordinator.data.state().name

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.coordinator.data.state().name
        self.async_write_ha_state()


class HolidayModeSensor(BwtEntity, BinarySensorEntity):
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


class HolidayStartSensor(BwtEntity, SensorEntity):
    """Future start of holiday mode if active."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = _HOLIDAY

    def __init__(self, coordinator, device_info: DeviceInfo, entry_id: str) -> None:
        """Initialize the sensor with the common coordinator."""
        super().__init__(coordinator, device_info, entry_id, "holiday_mode_start")
        holiday_mode = self.coordinator.data.holiday_mode()
        if holiday_mode > 1:
            self._attr_native_value = datetime.fromtimestamp(
                holiday_mode
            )
        else:
            self._attr_native_value = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        holiday_mode = self.coordinator.data.holiday_mode()
        if holiday_mode > 1:
            self._attr_native_value = datetime.fromtimestamp(
                holiday_mode
            )
        else:
            self._attr_native_value = None
        self.async_write_ha_state()


class CalculatedWaterSensor(BwtEntity, SensorEntity):
    """Sensor calculating blended water from treated water."""

    def __init__(
        self,
        coordinator,
        device_info: DeviceInfo,
        entry_id: str,
        key: str,
        extract,
        icon: str,
    ) -> None:
        """Initialize the sensor with the common coordinator."""
        super().__init__(coordinator, device_info, entry_id, key)
        self._attr_native_unit_of_measurement = UnitOfVolume.LITERS
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_device_class = SensorDeviceClass.WATER
        self._attr_icon = icon
        self._extract = extract
        self.suggested_display_precision = 0
        self._attr_native_value = self._extract(self.coordinator.data)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self._extract(self.coordinator.data)
        self.async_write_ha_state()



class UnknownSensor(BwtEntity, SensorEntity):
    """Unknown sensor for debugging."""

    def __init__(
        self,
        coordinator: BwtCoordinator,
        device_info: DeviceInfo,
        entry_id: str,
        index: int,
    ) -> None:
        """Initialize the sensor with the common coordinator."""
        super().__init__(coordinator, device_info, entry_id, f"silk_register_{index}")
        self._index = index
        self._attr_icon = _UNKNOWN
        self._attr_native_value = coordinator.data.get_register(index)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.coordinator.data.get_register(self._index)
        self.async_write_ha_state()
        