"""Tests for entity state classes, categories, units and translated names."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from bwt_api.bwt import BwtModel
from bwt_api.data import (
    BwtStatus,
    ConfigurationResponse,
    CurrentResponse,
    DeviceInfoResponse,
    Hardness,
    RemainingCapacityResponse,
    SmartDosStatus,
    SubstanceDosageResponse,
    TreatedWaterResponse,
    WifiResponse,
)
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_CODE, CONF_HOST, EntityCategory
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bwt_perla.const import DOMAIN

HOST = "192.168.1.50"
MAC = "aa:bb:cc:dd:ee:ff"
SSID = "MyHomeWifi"
HOLIDAY_EPOCH = 1_900_000_000


def _entry(model: BwtModel, **extra):
    data = {CONF_HOST: HOST, "model": model.name, **extra}
    return MockConfigEntry(domain=DOMAIN, version=3, title="BWT", data=data)


def _local_response(holiday_mode: int = HOLIDAY_EPOCH) -> CurrentResponse:
    now = datetime(2026, 1, 1, 12, 0, 0)
    return CurrentResponse(
        errors=[],
        blended_total=1000,
        capacity_1=100_000,
        capacity_2=100_000,
        current_flow=0,
        dosing_total=5,
        firmware_version="2.0",
        in_hardness=Hardness(0, 20, 0, 0),
        out_hardness=Hardness(0, 5, 0, 0),
        holiday_mode=holiday_mode,
        regeneration_last_1=now,
        regeneration_last_2=now,
        service_customer=now,
        service_technician=now,
        out_of_service=0,
        regeneration_count_1=3,
        regeneration_count_2=4,
        regeneration_count=7,
        regenerativ_level=50,
        regenerativ_days=10,
        regenerativ_total=1234,
        state=BwtStatus.OK,
        treated_day=10,
        treated_month=100,
        treated_year=1000,
        columns=2,
    )


def _smartdos_api():
    api = MagicMock()
    api.close = AsyncMock()
    api.get_device_info = AsyncMock(
        return_value=DeviceInfoResponse(
            fw_rev="1.0",
            hw_rev="A",
            product_code="X",
            uptime=1,
            operating_time=1,
            dev_state=SmartDosStatus.STANDBY,
            active_states=[],
            comm_date="2026-01-01",
            device_id="id",
            device_type="t",
            device_variant="v",
            total_flow=1000,
            total_dosed=10,
        )
    )
    api.get_configuration = AsyncMock(
        return_value=ConfigurationResponse(
            buzzer_en=True,
            dosing_rate=1.0,
            aqa_volume_en=False,
            aqa_watch_en=False,
            aqa_max_flow_en=False,
            aqa_volume_val=0,
            volume_per_stroke=0,
            pouch_empty_timeout=0,
            pouch_not_empty_timeout=0,
            aqa_watch_val=0,
            aqa_max_flow_val=0,
            rest_server_en=True,
        )
    )
    api.get_remaining_capacity = AsyncMock(
        return_value={1: RemainingCapacityResponse(5000, 50.0, 20, 0)}
    )
    api.get_treated_water = AsyncMock(
        return_value={1: TreatedWaterResponse(2_000_000, 0)}
    )
    api.get_substance_dosage = AsyncMock(return_value=SubstanceDosageResponse(12.5))
    api.get_wifi_info = AsyncMock(
        return_value=WifiResponse(
            ssid=SSID,
            rssi=-70,
            rssiAvg="-65",
            rssiSig="3",
            dhcp=True,
            ip="10.0.0.5",
            sn=None,
            sg=None,
            pDns=None,
            sDns=None,
            mac=MAC,
        )
    )
    return api


def _silk_api():
    api = MagicMock()
    api.close = AsyncMock()
    api.get_registers = AsyncMock(return_value=[1] * 50)
    api.get_status = AsyncMock(return_value={"version": "1.2", "gitver": 3})
    return api


async def _setup(hass, entry, api_name, api):
    entry.add_to_hass(hass)
    with patch(f"custom_components.bwt_perla.{api_name}", return_value=api):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED


async def _setup_local(hass, holiday_mode=HOLIDAY_EPOCH):
    api = MagicMock()
    api.close = AsyncMock()
    api.get_current_data = AsyncMock(return_value=_local_response(holiday_mode))
    entry = _entry(BwtModel.PERLA_LOCAL_API, **{CONF_CODE: "secret-code"})
    await _setup(hass, entry, "BwtApi", api)
    return entry


def _reg(hass, entry, key):
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_{key}"
    )
    assert entity_id, key
    return registry.async_get(entity_id)


def _sensor_attrs(hass, entry, key):
    reg = _reg(hass, entry, key)
    return reg, hass.states.get(reg.entity_id)


async def test_local_state_classes(hass):
    entry = await _setup_local(hass)
    total = {
        "regenerativ_mass": SensorStateClass.TOTAL_INCREASING,
        "dosing_total": SensorStateClass.TOTAL_INCREASING,
        "counter_regeneration_1": SensorStateClass.TOTAL_INCREASING,
        "counter_regeneration_2": SensorStateClass.TOTAL_INCREASING,
        "regenerativ_days": SensorStateClass.MEASUREMENT,
        "regenerativ_level": SensorStateClass.MEASUREMENT,
        "capacity_1": SensorStateClass.MEASUREMENT,
    }
    for key, expected in total.items():
        _, state = _sensor_attrs(hass, entry, key)
        assert state.attributes.get("state_class") == expected, key


async def test_entity_ids_unchanged(hass):
    entry = await _setup_local(hass)
    assert (
        _reg(hass, entry, "regenerativ_mass").entity_id
        == "sensor.bwt_perla_regenerativ_mass"
    )


async def test_smartdos_categories_and_rssi(hass):
    api = _smartdos_api()
    entry = _entry(BwtModel.SMART_DOS)
    await _setup(hass, entry, "BwtSmartDosApi", api)

    for key in (
        "wifi_ssid",
        "wifi_rssi",
        "mac_address",
        "buzzer",
        "aqa_watch",
        "aqa_max_flow",
        "aqa_max_volume",
    ):
        reg = _reg(hass, entry, key)
        assert reg.entity_category is EntityCategory.DIAGNOSTIC, key
        assert reg.disabled_by is None, key

    reg, state = _sensor_attrs(hass, entry, "wifi_rssi")
    assert state.state == "-65.0"
    assert state.attributes["device_class"] == SensorDeviceClass.SIGNAL_STRENGTH
    assert state.attributes["unit_of_measurement"] == "dBm"
    assert state.attributes["state_class"] == SensorStateClass.MEASUREMENT

    _, state = _sensor_attrs(hass, entry, "dosing_total")
    assert state.attributes["state_class"] == SensorStateClass.TOTAL_INCREASING
    _, state = _sensor_attrs(hass, entry, "remaining_capacity_days")
    assert state.attributes["state_class"] == SensorStateClass.MEASUREMENT
    _, state = _sensor_attrs(hass, entry, "remaining_capacity_pct")
    assert state.attributes["state_class"] == SensorStateClass.MEASUREMENT


async def test_smartdos_rssi_falls_back_to_raw(hass):
    api = _smartdos_api()
    api.get_wifi_info = AsyncMock(
        return_value=WifiResponse(
            ssid=SSID,
            rssi=-70,
            rssiAvg="n/a",
            rssiSig="",
            dhcp=True,
            ip=None,
            sn=None,
            sg=None,
            pDns=None,
            sDns=None,
            mac=MAC,
        )
    )
    entry = _entry(BwtModel.SMART_DOS)
    await _setup(hass, entry, "BwtSmartDosApi", api)
    _, state = _sensor_attrs(hass, entry, "wifi_rssi")
    assert state.state == "-70.0"


async def test_smartdos_device_model_has_no_perla_prefix(hass):
    from homeassistant.helpers import device_registry as dr

    entry = _entry(BwtModel.SMART_DOS)
    await _setup(hass, entry, "BwtSmartDosApi", _smartdos_api())
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    assert device.model == "SmartDos"


async def test_silk_categories_and_state_classes(hass):
    entry = _entry(BwtModel.PERLA_SILK)
    await _setup(hass, entry, "BwtSilkApi", _silk_api())

    reg = _reg(hass, entry, "firmware_version")
    assert reg.entity_category is EntityCategory.DIAGNOSTIC
    assert reg.disabled_by is er.RegistryEntryDisabler.INTEGRATION

    raw = _reg(hass, entry, "silk_register_5")
    assert raw.entity_category is EntityCategory.DIAGNOSTIC
    assert raw.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert raw.original_name == "Device ranking"
    # Reserved registers get distinct translated names (and thus entity ids).
    names = {
        _reg(hass, entry, f"silk_register_{i}").original_name
        for i in (1, 36, 37, 44, 45, 46)
    }
    assert names == {f"Reserved {n}" for n in range(1, 7)}

    for key in (
        "fill_duration",
        "dwell_duration",
        "brine_duration",
        "backwash_duration",
        "rinse_duration",
    ):
        reg, state = _sensor_attrs(hass, entry, key)
        assert reg.entity_category is None
        assert state.attributes["state_class"] == SensorStateClass.MEASUREMENT, key

    _, state = _sensor_attrs(hass, entry, "salt_remaining_kg")
    assert state.attributes["state_class"] == SensorStateClass.MEASUREMENT
