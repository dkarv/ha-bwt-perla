from .base import BwtEntity
from homeassistant.components.sensor import (
    SensorEntity,
)
from ..const import DOMAIN
from ..util import truncate_value

from homeassistant.core import callback
from homeassistant.helpers import translation

from bwt_api.error import BwtError

_WARNING = "mdi:alert-circle"
_ERROR = "mdi:alert-decagram"

class TranslatableErrorMixin:
    """Mixin for entities that need to translate error codes.

    This mixin provides translation functionality for entities that display
    multiple error/warning codes. It loads translations when the entity is
    added to Home Assistant and provides a method to translate individual codes.

    Attributes:
        _translations: Dictionary of translations loaded from language files.
                      Initialized as None and populated in async_added_to_hass.
    """

    _translations = None

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass, load translations."""
        await super().async_added_to_hass()
        # Load translations for the current language
        self._translations = await translation.async_get_translations(
            self.hass,
            self.hass.config.language,
            "entity_component",
            {DOMAIN},
        )

    def _translate_code(self, code_name: str) -> str:
        """Translate an error/warning code to the user's language."""
        if self._translations is None:
            return code_name

        key = f"component.{DOMAIN}.entity_component._.state.error_{code_name.lower()}"
        return self._translations.get(key, code_name)

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

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass, load translations."""
        await super().async_added_to_hass()
        # Update values with translations now that they're loaded
        self._update_values(self._get_errors())
        self.async_write_ha_state()

    def _update_values(self, errors) -> None:
        """Update error values with translations."""
        raw_values = [x.name for x in errors]
        # Store raw values as extra attributes for automation
        self._attr_extra_state_attributes = {"error_codes": raw_values}

        # Translate error names for display
        translated = [self._translate_code(x.name) for x in errors]
        # Join translated parts and ensure it does not exceed 255 chars
        joined = ", ".join(translated)
        self._attr_native_value = truncate_value(joined, 255)

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

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass, load translations."""
        await super().async_added_to_hass()
        # Update values with translations now that they're loaded
        self._update_values(self._get_warnings())
        self.async_write_ha_state()

    def _update_values(self, warnings) -> None:
        """Update warning values with translations."""
        raw_values = [x.name for x in warnings]
        # Store raw values as extra attributes for automation
        self._attr_extra_state_attributes = {"warning_codes": raw_values}

        # Translate warning names for display
        translated = [self._translate_code(x.name) for x in warnings]
        # Join translated parts and ensure it does not exceed 255 chars
        joined = ", ".join(translated)
        self._attr_native_value = truncate_value(joined, 255)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_values(self._get_warnings())
        self.async_write_ha_state()