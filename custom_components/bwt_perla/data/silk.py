from .data import ApiData
from datetime import datetime, timedelta
import logging

_LOGGER = logging.getLogger(__name__)

class SilkApiData(ApiData):
    """Data class for BWT Perla Silk API data."""
    _registers: list[int]

    def __init__(self, registers: list[int]) -> None:
        """Initialize the SilkApiData with a list of registers."""
        self._registers = registers
    
    def current_flow(self) -> int:
        return self.get_register(CURRENT_FLOW_RATE) * 60 # l/m -> l/h

    def total_output(self) -> int:
        return self.get_register(TOTAL_WATER_SERVED) * 100

    def hardness_in(self):
        return self.get_register(WATER_HARDNESS)

    def next_customer_service(self) -> int:
        service_days = self.get_register(DAYS_UNTIL_SERVICE)
        return (datetime.now().astimezone() + timedelta(days=service_days)).replace(hour = 0, minute = 0, second = 0, microsecond = 0)

    def regenerativ_level(self) -> int:
        return int(self.get_register(REGENERATIV_REMAINING) / self.get_register(REGENERATIV_CAPACITY) * 100)
    
    def day_output(self) -> int:
        return self.get_register(DAILY_WATER_USAGE)
    
    def capacity_1(self) -> int:
        return self.get_register(REMAINING_CAPACITY)
    
    def days_in_service(self) -> int:
        return self.get_register(DAYS_IN_SERVICE)
    
    def warranty_end(self) -> datetime:
        warranty_days = self.get_register(WARRANTY_DAYS_REMAINING)
        return (datetime.now().astimezone() + timedelta(days=warranty_days)).replace(hour = 0, minute = 0, second = 0, microsecond = 0)
    
    def regeneration_count_1(self) -> int:
        return self.get_register(TOTAL_NUMBER_OF_RECHARGES)

    def get_register(self, index: int) -> int | None:
        if index < 0 or index >= len(self._registers):
            return None
        return self._registers[index]

CURRENT_HOUR = 2 # useless
CURRENT_MINUTE = 3 # useless

WATER_HARDNESS = 4 # ppm

LAST_REGENERATION_HOUR = 7 # last_regeneration_1
LAST_REGENERATION_MINUTE = 8 # last_regeneration_1

BASE_MODEL_NUMBER = 10 # Probably useless?
DUPLEX_SETTING = 11 # Probably useless?

TURBINE_PULSES_PER_LITER = 13 # Probably useless?
AVG_WATER_SERVED_PER_DAY = 14 # Probably useless? HA will have better statistics
TOTAL_WATER_SERVED = 15 # total_output
CURRENT_FLOW_RATE = 16 # current_flow
DAYS_IN_SERVICE = 17 # days_in_service
WARRANTY_DAYS_REMAINING = 18 # warranty_days_remaining
TOTAL_NUMBER_OF_RECHARGES = 19 # regeneration_count_1

REMAINING_CAPACITY = 23 # capacity_1

DWELL_DURATION = 25 # [min] useless
BRINE_DURATION = 26 # [min] useless
ALLOW_CHANGING_SALT_TYPE = 27 # [bool] useless
ALLOW_CHANGING_REGEN_TIME = 28 # [bool] useless

REGENERATIV_CAPACITY = 30 # 31/30 = salt %
REGENERATIV_REMAINING = 31 # 31/30 = salt %

DAYS_UNTIL_SERVICE = 34 # next_customer_service

DAILY_WATER_USAGE = 42 # day_output
