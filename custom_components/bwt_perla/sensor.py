"""BWT Sensors."""

from bwt_api.api import BwtApi
from bwt_api.bwt import BwtModel
from bwt_api.exception import WrongCodeException

from homeassistant.components.sensor import (
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfMass,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BwtCoordinator
from .sensors.base import *

_GLASS = "mdi:cup-water"
_COUNTER = "mdi:counter"
_WRENCH_CLOCK = "mdi:wrench-clock"
_WRENCH_PERSON = "mdi:account-wrench"
_WATER_PLUS = "mdi:water-plus"
_WATER_MINUS = "mdi:water-minus"
_PERCENTAGE = "mdi:percent"
_DAYS_LEFT = "mdi:sort-numeric-descending-variant"
_MASS = "mdi:weight"
_TIME = "mdi:calendar-clock"
_DAY = "mdi:calendar-today"
_MONTH = "mdi:calendar-month"
_YEAR = "mdi:calendar-blank-multiple"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up bwt sensors from config entry."""
    my_api = hass.data[DOMAIN][config_entry.entry_id]
    model = BwtModel.PERLA_LOCAL_API if isinstance(
        my_api, BwtApi) else BwtModel.PERLA_SILK
    coordinator = BwtCoordinator(hass, my_api, model)

    try:
        await coordinator.async_config_entry_first_refresh()
    except WrongCodeException as e:
        raise ConfigEntryAuthFailed from e

    model_suffix = coordinator.get_model_suffix()
    device_info = DeviceInfo(
        configuration_url=None,
        connections=set(),
        entry_type=None,
        hw_version=None,
        identifiers={(DOMAIN, config_entry.entry_id)},
        manufacturer="BWT",
        model=f'Perla {model_suffix}',
        name=config_entry.title,
        serial_number=None,
        suggested_area=None,
        sw_version=coordinator.get_firmware_version(),
        via_device=None,
    )

    entities = [
        TotalOutputSensor(coordinator, device_info, config_entry.entry_id),
        SimpleSensor(
            coordinator,
            device_info,
            config_entry.entry_id,
            "hardness_in",
            lambda data: data.hardness_in(),
            _WATER_PLUS,
        ),
        UnitSensor(
            coordinator,
            device_info,
            config_entry.entry_id,
            "regenerativ_level",
            lambda data: data.regenerativ_level(),
            PERCENTAGE,
            _PERCENTAGE,
        ),
        CalculatedWaterSensor(
            coordinator,
            device_info,
            config_entry.entry_id,
            "day_output",
            lambda data: data.day_output(),
            _DAY,
        ),
        CurrentFlowSensor(coordinator, device_info, config_entry.entry_id),
        UnitSensor(
            coordinator,
            device_info,
            config_entry.entry_id,
            "capacity_1",
            lambda data: data.capacity_1(),
            UnitOfVolume.LITERS,
            _GLASS,
        ),
        SimpleSensor(
            coordinator,
            device_info,
            config_entry.entry_id,
            "counter_regeneration_1",
            lambda data: data.regeneration_count_1(),
            _COUNTER,
        ),
    ]

    if model == BwtModel.PERLA_LOCAL_API:
        entities.append(
            ErrorSensor(coordinator, device_info, config_entry.entry_id)
        )
        entities.append(
            WarningSensor(coordinator, device_info, config_entry.entry_id)
        )
        entities.append(
            SimpleSensor(
                coordinator,
                device_info,
                config_entry.entry_id,
                "hardness_out",
                lambda data: data.hardness_out(),
                _WATER_MINUS,
            )
        )
        entities.append(
            DeviceClassSensor(
                coordinator,
                device_info,
                config_entry.entry_id,
                "technician_service",
                lambda data: data.service_technician(),
                SensorDeviceClass.TIMESTAMP,
                _WRENCH_PERSON,
            )
        )
        entities.append(
            StateSensor(coordinator, device_info, config_entry.entry_id)
        )
        entities.append(
            UnitSensor(
                coordinator,
                device_info,
                config_entry.entry_id,
                "regenerativ_days",
                lambda data: data.regenerativ_days(),
                UnitOfTime.DAYS,
                _DAYS_LEFT,
            )
        )
        entities.append(
            UnitSensor(
                coordinator,
                device_info,
                config_entry.entry_id,
                "regenerativ_mass",
                lambda data: data.regenerativ_total(),
                UnitOfMass.GRAMS,
                _MASS,
            )
        )
        entities.append(
            HolidayModeSensor(coordinator, device_info, config_entry.entry_id)
        )
        entities.append(
            HolidayStartSensor(coordinator, device_info,
                               config_entry.entry_id),
        )
        entities.append(
            CalculatedWaterSensor(
                coordinator,
                device_info,
                config_entry.entry_id,
                "month_output",
                lambda data: data.month_output(),
                _MONTH,
            )
        )
        entities.append(
            CalculatedWaterSensor(
                coordinator,
                device_info,
                config_entry.entry_id,
                "year_output",
                lambda data: data.year_output(),
                _YEAR,
            )
        )
        entities.append(
            DeviceClassSensor(
                coordinator,
                device_info,
                config_entry.entry_id,
               "customer_service",
                lambda data: data.customer_service(),
                SensorDeviceClass.TIMESTAMP,
                _WRENCH_CLOCK,
            )
        )
        if coordinator.data.columns() == 2:
            entities.append(UnitSensor(
                coordinator,
                device_info,
                config_entry.entry_id,
                "capacity_2",
                lambda data: data.capacity_2(),
                UnitOfVolume.LITERS,
                _GLASS,
            ))
            entities.append(DeviceClassSensor(
                coordinator,
                device_info,
                config_entry.entry_id,
                "last_regeneration_1",
                lambda data: data.last_regeneration_1(),
                SensorDeviceClass.TIMESTAMP,
                _TIME,
            ))
            entities.append(DeviceClassSensor(
                coordinator,
                device_info,
                config_entry.entry_id,
                "last_regeneration_2",
                lambda data: data.last_regeneration_2(),
                SensorDeviceClass.TIMESTAMP,
                _TIME,
            ))
            entities.append(SimpleSensor(
                coordinator,
                device_info,
                config_entry.entry_id,
                "counter_regeneration_2",
                lambda data: data.regeneration_count_2(),
                _COUNTER,
            ))

    elif model == BwtModel.PERLA_SILK:
        entities.append(
            DeviceClassSensor(
                coordinator,
                device_info,
                config_entry.entry_id,
               "next_customer_service",
                lambda data: data.next_customer_service(),
                SensorDeviceClass.TIMESTAMP,
                _WRENCH_CLOCK,
            )
        )
        entities.append(
            SimpleSensor(
                coordinator,
                device_info,
                config_entry.entry_id,
                "days_in_service",
                lambda data: data.days_in_service(),
                _COUNTER,
            )
        )
        entities.append(
            SimpleSensor(
                coordinator,
                device_info,
                config_entry.entry_id,
                "warranty_end",
                lambda data: data.warranty_end(),
                _WRENCH_PERSON,
            )
        )
        for index in [0, 1, 5, 6, 9, 12, 20, 21, 22, 24, 29, 32, 33, 35, 36, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47]:
            entities.append(
                UnknownSensor(
                    coordinator,
                    device_info,
                    config_entry.entry_id,
                    index
                )
            )

    async_add_entities(entities)

