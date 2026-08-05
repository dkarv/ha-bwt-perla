from typing import Optional, Mapping, List

from .data import ApiData
from bwt_api.data import (
    ConfigurationResponse,
    DeviceInfoResponse,
    RemainingCapacityResponse,
    SubstanceDosageResponse,
    TreatedWaterResponse,
    WifiResponse,
    SmartDosStatus,
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
        remaining_capacity: Mapping[int, RemainingCapacityResponse],
        treated_water: Mapping[int, TreatedWaterResponse],
        substance_dosage: SubstanceDosageResponse,
        wifi_info: WifiResponse,
    ) -> None:
        self._device_info = device_info
        self._configuration = configuration
        # Extract the first capacity entry from the mapping (typically channel 1)
        self._remaining_capacity = next(iter(remaining_capacity.values()))
        # Extract the first treated water entry from the mapping (typically channel 1)
        self._treated_water = next(iter(treated_water.values()))
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

    def hardware_version(self) -> Optional[str]:
        # Support several possible attribute names from the API
        return getattr(self._device_info, "hw_rev", None) or getattr(self._device_info, "hw_version", None) or getattr(self._device_info, "hardware_revision", None)

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

    def wifi_rssi(self) -> Optional[str]:
        # Use average RSSI if available, otherwise raw RSSI
        rssi_avg = getattr(self._wifi_info, "rssiAvg", None)
        if rssi_avg is not None:
            return str(rssi_avg)
        return getattr(self._wifi_info, "rssi", None)

    def mac_address(self) -> Optional[str]:
        # MAC address is in WiFi info
        return getattr(self._wifi_info, "mac", None)

    def substance_dosage(self) -> float:
        return self._substance_dosage.dosed_mineral

    def dosing_total(self) -> Optional[float]:
        # Some API variants may expose a total dosed value; fall back to the dosed_mineral
        return getattr(self._substance_dosage, "total_dosed", None) or getattr(self._substance_dosage, "dosed_total", None) or self._substance_dosage.dosed_mineral

    def buzzer(self) -> Optional[bool]:
        return self._configuration.buzzer_en

    def aqa_watch(self) -> Optional[bool]:
        return self._configuration.aqa_watch_en

    def aqa_max_flow(self) -> Optional[bool]:
        return self._configuration.aqa_max_flow_en

    def aqa_max_volume(self) -> Optional[bool]:
        return self._configuration.aqa_volume_en

    def errors(self) -> List[SmartDosStatus]:
        """Return list of SmartDos state errors/warnings, excluding normal OK state (2001)."""
        # Get active states from device info, filter out the OK state (2001)
        active_states = self._device_info.active_states or []
        return [state for state in active_states if not state.is_normal() ]
