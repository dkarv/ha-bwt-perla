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

    def current_flow(self) -> int | None:
        raw = self.get_register(CURRENT_FLOW_RATE)
        return None if raw is None else raw * 60  # raw → L/h

    def total_output(self) -> int | None:
        raw = self.get_register(TOTAL_WATER_SERVED)
        return None if raw is None else raw * 100

    def hardness_in(self):
        return self.get_register(WATER_HARDNESS)

    def next_customer_service(self) -> datetime | None:
        service_days = self.get_register(DAYS_UNTIL_SERVICE)
        if service_days is None:
            return None
        return (datetime.now().astimezone() + timedelta(days=service_days)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    def regenerativ_level(self) -> int | None:
        cap = self.get_register(REGENERATIV_CAPACITY)
        rem = self.get_register(REGENERATIV_REMAINING)
        if cap is None or rem is None or cap <= 0:
            return None
        return int(rem / cap * 100)

    def day_output(self) -> int | None:
        return self.get_register(DAILY_WATER_USAGE)

    def capacity_1(self) -> int | None:
        return self.get_register(REMAINING_CAPACITY)

    def days_in_service(self) -> int | None:
        return self.get_register(DAYS_IN_SERVICE)

    def warranty_end(self) -> datetime | None:
        warranty_days = self.get_register(WARRANTY_DAYS_REMAINING)
        if warranty_days is None:
            return None
        return (datetime.now().astimezone() + timedelta(days=warranty_days)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    def regeneration_count_1(self) -> int | None:
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

    def get_register(self, index: int) -> int | None:
        if index < 0 or index >= len(self._registers):
            return None
        return self._registers[index]

    def get_flag(self, index: int) -> bool | None:
        """Boolean register; negative values (e.g. -1) mean not set."""
        raw = self.get_register(index)
        return None if raw is None or raw < 0 else raw != 0


# Softener register addresses (== params[] indices).
# Names from firmware settings table @ 0x86880 (stride 0x2c: name + reg index)
# + TwinValues / community for telemetry registers not in that table.
SALT_TYPE = 0
CURRENT_HOUR = 2
CURRENT_MINUTE = 3
WATER_HARDNESS = 4  # ppm CaCO3
DEVICE_RANKING = 5
MODEL_CODE = 6
LAST_REGENERATION_HOUR = 7  # firmware: RechargeTime
LAST_REGENERATION_MINUTE = 8
DUPLEX_SETTING = 11
BASE_MODEL_NUMBER = 12
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
SERVICE_REMINDER_MODE = 33
DAYS_UNTIL_SERVICE = 34
RECHARGE_ALGORITHM = 35
DAY_OF_WEEK = 38
ALLOW_CHANGING_SALT_TYPE = 39
ALLOW_CHANGING_REGEN_TIME = 40
RESIN_CAPACITY = 41
DAILY_WATER_USAGE = 42

# Device settings with a known meaning (see silk.md). Their units and value
# mappings are not documented, so they are exposed as plain numbers.
SETTING_REGISTERS: dict[str, int] = {
    "salt_type": SALT_TYPE,
    "device_ranking": DEVICE_RANKING,
    "model_code": MODEL_CODE,
    "duplex_setting": DUPLEX_SETTING,
    "base_model_number": BASE_MODEL_NUMBER,
    "hardness_units": HARDNESS_UNITS,
    "turbine_pulses_per_liter": TURBINE_PULSES_PER_LITER,
    "recharge_interval": RECHARGE_INTERVAL,
    "capacity_scale_factor": CAPACITY_SCALE_FACTOR,
    "salt_alarm_mode": SALT_ALARM_MODE,
    "salt_per_regeneration": SALT_PER_REGEN,
    "service_reminder_mode": SERVICE_REMINDER_MODE,
    "recharge_algorithm": RECHARGE_ALGORITHM,
    "day_of_week": DAY_OF_WEEK,
    "resin_capacity": RESIN_CAPACITY,
}

# Boolean device settings.
FLAG_REGISTERS: dict[str, int] = {
    "allow_salt_type_change": ALLOW_CHANGING_SALT_TYPE,
    "allow_regen_time_change": ALLOW_CHANGING_REGEN_TIME,
}

# Registers whose meaning is unknown (reserved or unidentified). They stay
# raw silk_register_<index> diagnostic entities, disabled by default.
UNKNOWN_REGISTER_INDEXES = [1, 9, 10, 36, 37, 44, 45, 46, 47]
