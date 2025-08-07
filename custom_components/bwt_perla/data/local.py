from bwt_api.data import CurrentResponse
from bwt_api.api import treated_to_blended 
from .data import ApiData
from datetime import datetime


class LocalApiData(ApiData):
    """Data class for local API data."""
    _data: CurrentResponse

    def __init__(self, data: CurrentResponse) -> None:
        """Initialize the LocalApiData with the provided data."""
        self._data = data
    
    def columns(self) -> int:
        return self._data.columns
    
    def firmware_version(self) -> str:
        return self._data.firmware_version

    def total_output(self) -> int:
        return self._data.blended_total

    def hardness_in(self) -> int:
        return self._data.in_hardness.dH

    def customer_service(self) -> datetime:
        return self._data.service_customer.astimezone()

    def regenerativ_level(self) -> int:
        return self._data.regenerativ_level

    def day_output(self) -> int:
        return treated_to_blended(self._data.treated_day, self._data.in_hardness.dH, self._data.out_hardness.dH)

    def capacity_1(self) -> int:
        return self._data.capacity_1 / (self._data.in_hardness.dH - self._data.out_hardness.dH) / 1000.0

    def capacity_2(self) -> int:
        return self._data.capacity_2 / (self._data.in_hardness.dH - self._data.out_hardness.dH) / 1000.0

    def last_regeneration_1(self) -> datetime:
        return self._data.regeneration_last_1.astimezone()
    
    def last_regeneration_2(self) -> datetime:
        return self._data.regeneration_last_2.astimezone()

    def current_flow(self) -> int:
        return self._data.current_flow
    
    def errors(self):
        return self._data.errors
    
    def hardness_out(self) -> int:
        return self._data.out_hardness.dH
    
    def technician_service(self) -> int:
        return self._data.service_technician.astimezone()
    
    def state(self) -> int:
        return self._data.state
    
    def holiday_mode(self):
        return self._data.holiday_mode
    
    def service_technician(self):
        return self._data.service_technician.astimezone()
    
    def regenerativ_days(self):
        return self._data.regenerativ_days
    
    def regenerativ_total(self):
        return self._data.regenerativ_total
    
    def month_output(self):
        return treated_to_blended(self._data.treated_month, self._data.in_hardness.dH, self._data.out_hardness.dH)
    
    def year_output(self):
        return treated_to_blended(self._data.treated_year, self._data.in_hardness.dH, self._data.out_hardness.dH)
    
    def regeneration_count_1(self):
        return self._data.regeneration_count_1
    
    def regeneration_count_2(self):
        return self._data.regeneration_count_2
    
    def dosing_total(self):
        return self._data.dosing_total
