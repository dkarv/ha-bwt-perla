from typing import Optional

from .data import ApiData
from bwt_api.data import (
    ConfigurationResponse,
    DeviceInfoResponse,
    RemainingCapacityResponse,
    SubstanceDosageResponse,
    TreatedWaterResponse,
    WifiResponse,
)


class SmartDosApiData(ApiData):
    """Data class for BWT SmartDos API data."""
    _device_info: DeviceInfoResponse
    _configuration: ConfigurationResponse
    _remaining_capacity: RemainingCapacityResponse
    _treated_water: TreatedWaterResponse
    _substance_dosage: SubstanceDosageResponse
    _wifi_info: WifiResponse

    def __init__(
        self,
        device_info: DeviceInfoResponse,
        configuration: ConfigurationResponse,
        remaining_capacity: RemainingCapacityResponse,
        treated_water: TreatedWaterResponse,
        substance_dosage: SubstanceDosageResponse,
        wifi_info: WifiResponse,
    ) -> None:
        self._device_info = device_info
        self._configuration = configuration
        self._remaining_capacity = remaining_capacity
        self._treated_water = treated_water
        self._substance_dosage = substance_dosage
        self._wifi_info = wifi_info

    def current_flow(self) -> int:
        return 0

    def total_output(self) -> int:
        return int(self._treated_water.total_flow / 1000.0)

    def hardness_in(self) -> int:
        return 0

    def regenerativ_level(self) -> int:
        return 0

    def day_output(self) -> int:
        return 0

    def capacity_1(self) -> Optional[int]:
        if self._remaining_capacity.rem_capacity is None:
            return None
        return int(self._remaining_capacity.rem_capacity / 1000.0)

    def regeneration_count_1(self) -> int:
        return 0

    def firmware_version(self) -> str:
        return self._device_info.fw_rev

    def product_code(self) -> str:
        return self._device_info.product_code

    def device_state(self) -> str:
        if self._device_info.dev_state is None:
            return "UNKNOWN"
        return self._device_info.dev_state.name

    def active_states(self) -> str:
        return ", ".join(
            state.name if state is not None else "UNKNOWN"
            for state in self._device_info.active_states
        )

    def comm_date(self) -> str:
        return self._device_info.comm_date

    def dosing_rate(self) -> float:
        return self._configuration.dosing_rate

    def remaining_capacity_pct(self) -> float:
        return self._remaining_capacity.rem_capacity_pct

    def remaining_capacity_days(self) -> int:
        return self._remaining_capacity.rem_capacity_days

    def wifi_ssid(self) -> str:
        return self._wifi_info.ssid

    def wifi_rssi(self) -> int:
        return self._wifi_info.rssi

    def substance_dosage(self) -> float:
        return self._substance_dosage.dosed_mineral
