"""BWT Perla Silk register / status data."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging

from .data import ApiData


_LOGGER = logging.getLogger(__name__)


class SilkApiData(ApiData):
    """Data class for BWT Perla Silk API data."""

    _registers: list[int]
    _status: dict | None

    def __init__(self, registers: list[int], status: dict | None = None) -> None:
        self._registers = registers
        self._status = status or {}

    def current_flow(self) -> int:
        return self.get_register(CURRENT_FLOW_RATE) * 60  # L/min-ish raw → L/h

    def total_output(self) -> int:
        return self.get_register(TOTAL_WATER_SERVED) * 100

    def hardness_in(self):
        return self.get_register(WATER_HARDNESS)

    def next_customer_service(self) -> datetime:
        service_days = self.get_register(DAYS_UNTIL_SERVICE) or 0
        return (datetime.now().astimezone() + timedelta(days=service_days)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    def regenerativ_level(self) -> int:
        cap = self.get_register(REGENERATIV_CAPACITY) or 0
        rem = self.get_register(REGENERATIV_REMAINING) or 0
        if cap <= 0:
            return 0
        return int(rem / cap * 100)

    def day_output(self) -> int:
        return self.get_register(DAILY_WATER_USAGE)

    def capacity_1(self) -> int:
        return self.get_register(REMAINING_CAPACITY)

    def days_in_service(self) -> int:
        return self.get_register(DAYS_IN_SERVICE)

    def warranty_end(self) -> datetime:
        warranty_days = self.get_register(WARRANTY_DAYS_REMAINING) or 0
        return (datetime.now().astimezone() + timedelta(days=warranty_days)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    def regeneration_count_1(self) -> int:
        return self.get_register(TOTAL_NUMBER_OF_RECHARGES)

    def firmware_version(self) -> str:
        version = self._status.get("version")
        gitver = self._status.get("gitver")
        if version and gitver is not None:
            return f"{version} (git {gitver})"
        if version:
            return str(version)
        return "Unknown"

    def product_code(self) -> str | None:
        return self._status.get("productCode")

    def avg_daily_output(self) -> int | None:
        return self.get_register(AVG_WATER_SERVED_PER_DAY)

    def salt_capacity(self) -> float | None:
        raw = self.get_register(REGENERATIV_CAPACITY)
        return None if raw is None or raw < 0 else raw / 10.0

    def salt_remaining(self) -> float | None:
        raw = self.get_register(REGENERATIV_REMAINING)
        return None if raw is None or raw < 0 else raw / 10.0

    def last_regeneration_time(self) -> str | None:
        hour = self.get_register(LAST_REGENERATION_HOUR)
        minute = self.get_register(LAST_REGENERATION_MINUTE)
        if hour is None or minute is None or hour < 0 or minute < 0:
            return None
        return f"{hour:02d}:{minute:02d}"

    def device_clock(self) -> str | None:
        hour = self.get_register(CURRENT_HOUR)
        minute = self.get_register(CURRENT_MINUTE)
        if hour is None or minute is None or hour < 0 or minute < 0:
            return None
        return f"{hour:02d}:{minute:02d}"

    def get_register(self, index: int) -> int | None:
        if index < 0 or index >= len(self._registers):
            return None
        return self._registers[index]


# Softener register addresses (== params[] indices).
# Names from firmware settings table @ 0x86880 (stride 0x2c: name + reg index)
# + TwinValues / community for telemetry registers not in that table.
CURRENT_HOUR = 2
CURRENT_MINUTE = 3
WATER_HARDNESS = 4  # ppm CaCO3
LAST_REGENERATION_HOUR = 7  # firmware: RechargeTime
LAST_REGENERATION_MINUTE = 8
HARDNESS_UNITS = 13
AVG_WATER_SERVED_PER_DAY = 14
TOTAL_WATER_SERVED = 15  # ×100 → lifetime litres
CURRENT_FLOW_RATE = 16  # ×60 → L/h
DAYS_IN_SERVICE = 17
WARRANTY_DAYS_REMAINING = 18
TOTAL_NUMBER_OF_RECHARGES = 19
TURBINE_PULSES_PER_LITER = 20
RECHARGE_INTERVAL = 21
CAPACITY_SCALE_FACTOR = 22
REMAINING_CAPACITY = 23
FILL_DURATION = 24  # min
DWELL_DURATION = 25  # min
BRINE_DURATION = 26  # min
BACKWASH_DURATION = 27  # min
RINSE_DURATION = 28  # min
SALT_ALARM_MODE = 29
REGENERATIV_CAPACITY = 30  # raw units (÷10 ≈ kg)
REGENERATIV_REMAINING = 31
SALT_PER_REGEN = 32
DAYS_UNTIL_SERVICE = 34
DAY_OF_WEEK = 38
ALLOW_CHANGING_SALT_TYPE = 39
ALLOW_CHANGING_REGEN_TIME = 40
RESIN_CAPACITY = 41
DAILY_WATER_USAGE = 42

# Human-readable map for leftover / debug register entities.
REGISTER_NAMES: dict[int, str] = {
    0: "Salt type",
    1: "Reserved",
    5: "Device ranking",
    6: "Model code",
    9: "Register 9",
    10: "Register 10",
    11: "Duplex setting",
    12: "Base model number",
    13: "Hardness units",
    20: "Turbine pulses per litre",
    21: "Recharge interval",
    22: "Capacity scale factor",
    24: "Fill duration",
    25: "Dwell duration",
    26: "Brine duration",
    27: "Backwash duration",
    28: "Rinse duration",
    29: "Salt alarm mode",
    32: "Salt use per regeneration",
    33: "Service reminder mode",
    35: "Recharge algorithm",
    36: "Reserved",
    37: "Reserved",
    38: "Day of week",
    39: "Allow salt type change",
    40: "Allow regen time change",
    41: "Resin capacity",
    44: "Reserved",
    45: "Reserved",
    46: "Reserved",
    47: "Register 47",
}

# Duration registers (minutes) that have dedicated UnitSensors.
_NAMED_DURATION_INDEXES = {
    FILL_DURATION,
    DWELL_DURATION,
    BRINE_DURATION,
    BACKWASH_DURATION,
    RINSE_DURATION,
}

# Still exposed as raw silk_register_* (not duplicated by named sensors).
UNKNOWN_REGISTER_INDEXES = [
    i for i in REGISTER_NAMES if i not in _NAMED_DURATION_INDEXES
]
