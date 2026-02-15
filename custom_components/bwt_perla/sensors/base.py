
from datetime import datetime

import logging

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
from homeassistant.helpers import translation

from ..util import truncate_value

from ..const import DOMAIN
from ..coordinator import BwtCoordinator

_LOGGER = logging.getLogger(__name__)

_FAUCET = "mdi:faucet"
_WATER = "mdi:water"
_WARNING = "mdi:alert-circle"
_ERROR = "mdi:alert-decagram"
_WATER_CHECK = "mdi:water-check"
_HOLIDAY = "mdi:location-exit"
_UNKNOWN = "mdi:help-circle"

# Error code translations
# English translations
_ERROR_TRANSLATIONS_EN = {
    "UNKNOWN": "Unknown error",
    "OFFLINE_MOTOR_1": "Motor 1 offline",
    "OFFLINE_MOTOR_2": "Motor 2 offline",
    "OFFLINE_MOTOR_BLEND": "Blend motor offline",
    "REGENERATIV_20": "Regeneration salt level < 20%",
    "OVERCURRENT_MOTOR_1": "Overcurrent motor 1",
    "OVERCURRENT_MOTOR_2": "Overcurrent motor 2",
    "OVERCURRENT_MOTOR_3": "Overcurrent motor 3",
    "OVERCURRENT_VALVE": "Overcurrent valve",
    "STOP_VOLUME": "Stop volume",
    "STOP_SENSOR": "Stop sensor",
    "CONSTANT_FLOW": "Constant flow",
    "LOW_PRESSURE": "Low pressure",
    "PISTON_POSITION": "Piston position",
    "ELECTRONIC": "Electronic",
    "INSUFFICIENT_REGENERATIV": "Insufficient regeneration salt",
    "STOP_WIRELESS_SENSOR": "Stop wireless sensor",
    "REGENERATIV_0": "Regeneration salt empty",
    "MAINTENANCE_CUSTOMER": "Routine maintenance due",
    "INSPECTION_CUSTOMER": "Customer inspection required",
    "MAINTENANCE_SERVICE": "Technician maintenance due",
    "MINERALS_LOW": "Minerals low",
    "MINERALS_0": "Minerals empty",
    "OVERCURRENT_VALVE_1": "Overcurrent valve 1",
    "OVERCURRENT_VALVE_2": "Overcurrent valve 2",
    "OVERCURRENT_DOSING": "Overcurrent dosing",
    "OVERCURRENT_VALVE_BALL": "Overcurrent ball valve",
    "METER_NOT_COUNTING": "Water meter not counting",
    "REGENERATION_DRAIN": "Regeneration drain issue",
    "INIT_PCB_0": "PCB initialization 0",
    "INIT_PCB_1": "PCB initialization 1",
    "POSITION_MOTOR_1": "Motor 1 position",
    "POSITION_MOTOR_2": "Motor 2 position",
    "CONDUCTIVITY_HIGH": "Conductivity too high",
    "CONDUCTIVITY_LIMIT_1": "Conductivity limit 1 exceeded",
    "CONDUCTIVITY_LIMIT_2": "Conductivity limit 2 exceeded",
    "CONDUCTIVITY_LIMIT_WATER": "Water conductivity limit exceeded",
    "NO_FUNCTION": "No function",
    "TEMPERATURE_DISCONNECTED": "Temperature sensor disconnected",
    "TEMPERATURE_HIGH": "Temperature too high",
    "OFFLINE_VALVE_BALL": "Ball valve offline",
    "EXTERNAL_FILTER_CHANGE": "External filter change required",
    "BRINE_UNSATURATED": "Brine unsaturated",
    "DOSING_FAULT": "Dosing fault",
}

# German translations
_ERROR_TRANSLATIONS_DE = {
    "UNKNOWN": "Unbekannter Fehler",
    "OFFLINE_MOTOR_1": "Motor 1 offline",
    "OFFLINE_MOTOR_2": "Motor 2 offline",
    "OFFLINE_MOTOR_BLEND": "Mischmotor offline",
    "REGENERATIV_20": "Regeneriersalz-Stand < 20%",
    "OVERCURRENT_MOTOR_1": "Überstrom Motor 1",
    "OVERCURRENT_MOTOR_2": "Überstrom Motor 2",
    "OVERCURRENT_MOTOR_3": "Überstrom Motor 3",
    "OVERCURRENT_VALVE": "Überstrom Ventil",
    "STOP_VOLUME": "Volumen-Stopp",
    "STOP_SENSOR": "Sensor-Stopp",
    "CONSTANT_FLOW": "Konstanter Durchfluss",
    "LOW_PRESSURE": "Niedriger Druck",
    "PISTON_POSITION": "Kolbenposition",
    "ELECTRONIC": "Elektronik",
    "INSUFFICIENT_REGENERATIV": "Unzureichendes Regeneriersalz",
    "STOP_WIRELESS_SENSOR": "Funk-Sensor-Stopp",
    "REGENERATIV_0": "Regeneriersalz leer",
    "MAINTENANCE_CUSTOMER": "Planmäßige Wartung fällig",
    "INSPECTION_CUSTOMER": "Kundeninspektion erforderlich",
    "MAINTENANCE_SERVICE": "Technikerwartung fällig",
    "MINERALS_LOW": "Mineralien niedrig",
    "MINERALS_0": "Mineralien leer",
    "OVERCURRENT_VALVE_1": "Überstrom Ventil 1",
    "OVERCURRENT_VALVE_2": "Überstrom Ventil 2",
    "OVERCURRENT_DOSING": "Überstrom Dosierung",
    "OVERCURRENT_VALVE_BALL": "Überstrom Kugelventil",
    "METER_NOT_COUNTING": "Wasserzähler zählt nicht",
    "REGENERATION_DRAIN": "Regenerationsabfluss-Problem",
    "INIT_PCB_0": "Leiterplatten-Initialisierung 0",
    "INIT_PCB_1": "Leiterplatten-Initialisierung 1",
    "POSITION_MOTOR_1": "Position Motor 1",
    "POSITION_MOTOR_2": "Position Motor 2",
    "CONDUCTIVITY_HIGH": "Leitfähigkeit zu hoch",
    "CONDUCTIVITY_LIMIT_1": "Leitfähigkeitsgrenze 1 überschritten",
    "CONDUCTIVITY_LIMIT_2": "Leitfähigkeitsgrenze 2 überschritten",
    "CONDUCTIVITY_LIMIT_WATER": "Wasser-Leitfähigkeitsgrenze überschritten",
    "NO_FUNCTION": "Keine Funktion",
    "TEMPERATURE_DISCONNECTED": "Temperatursensor getrennt",
    "TEMPERATURE_HIGH": "Temperatur zu hoch",
    "OFFLINE_VALVE_BALL": "Kugelventil offline",
    "EXTERNAL_FILTER_CHANGE": "Externer Filterwechsel erforderlich",
    "BRINE_UNSATURATED": "Sole ungesättigt",
    "DOSING_FAULT": "Dosierfehler",
}

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
        self.entity_id = f"sensor.{DOMAIN}_{key}"
        self._attr_unique_id = entry_id + "_" + key


class TranslatableErrorMixin:
    """Mixin for entities that need to translate error codes.

    This mixin provides translation functionality for entities that display
    multiple error/warning codes using hardcoded translation dictionaries.
    """

    def _translate_code(self, code_name: str) -> str:
        """Translate an error/warning code to the user's language."""
        # Get the user's language from hass config
        language = self.hass.config.language if hasattr(self, 'hass') else 'en'
        
        # Select the appropriate translation dictionary
        if language.startswith('de'):
            translations = _ERROR_TRANSLATIONS_DE
        else:
            translations = _ERROR_TRANSLATIONS_EN
        
        # Return translation or fallback to code name
        return translations.get(code_name, code_name)


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
        self._attr_suggested_display_precision = 0

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.coordinator.data.total_output()
        self.async_write_ha_state()


class CurrentFlowSensor(BwtEntity, SensorEntity):
    """Current flow per hour."""

    _attr_native_unit_of_measurement = UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.VOLUME_FLOW_RATE
    _attr_icon = _FAUCET

    def __init__(self, coordinator, device_info, entry_id) -> None:
        """Initialize the sensor with the common coordinator."""
        super().__init__(coordinator, device_info, entry_id, "current_flow")
        self._attr_native_value = coordinator.data.current_flow() / 1000.0
        self._attr_suggested_display_precision = 3

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # HA only has m3 / h, we get the values in l/h
        self._attr_native_value = self.coordinator.data.current_flow() / 1000.0
        self.async_write_ha_state()


class ErrorSensor(TranslatableErrorMixin, BwtEntity, SensorEntity):
    """Errors reported by the device."""

    _attr_icon = _ERROR

    def __init__(self, coordinator, device_info, entry_id) -> None:
        """Initialize the sensor with the common coordinator."""
        super().__init__(coordinator, device_info, entry_id, "errors")
        self._update_values(self._get_errors())

    def _get_errors(self):
        """Get the current list of fatal errors."""
        return [x for x in self.coordinator.data.errors() if x.is_fatal()]

    def _update_values(self, errors) -> None:
        """Update error values with translations."""
        raw_values = [x.name for x in errors]
        # Store raw values as extra attributes for automation
        self._attr_extra_state_attributes = {"error_codes": raw_values}

        # Translate error names for display
        if errors:
            translated = [self._translate_code(x.name) for x in errors]
            # Join translated parts and ensure it does not exceed 255 chars
            joined = ", ".join(translated)
            self._attr_native_value = truncate_value(joined, 255)
        else:
            self._attr_native_value = ""

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_values(self._get_errors())
        self.async_write_ha_state()


class WarningSensor(TranslatableErrorMixin, BwtEntity, SensorEntity):
    """Warnings reported by the device."""

    _attr_icon = _WARNING

    def __init__(self, coordinator, device_info, entry_id) -> None:
        """Initialize the sensor with the common coordinator."""
        super().__init__(coordinator, device_info, entry_id, "warnings")
        self._update_values(self._get_warnings())

    def _get_warnings(self):
        """Get the current list of non-fatal warnings."""
        return [x for x in self.coordinator.data.errors() if not x.is_fatal()]

    def _update_values(self, warnings) -> None:
        """Update warning values with translations."""
        raw_values = [x.name for x in warnings]
        # Store raw values as extra attributes for automation
        self._attr_extra_state_attributes = {"warning_codes": raw_values}

        # Translate warning names for display
        if warnings:
            translated = [self._translate_code(x.name) for x in warnings]
            # Join translated parts and ensure it does not exceed 255 chars
            joined = ", ".join(translated)
            self._attr_native_value = truncate_value(joined, 255)
        else:
            self._attr_native_value = ""

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_values(self._get_warnings())
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
        display_precision: int | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_info, entry_id, key, extract, icon)
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = display_precision


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
        
