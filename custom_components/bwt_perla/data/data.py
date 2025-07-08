from abc import ABC, abstractmethod
from datetime import datetime

class ApiData(ABC):
    @abstractmethod
    def current_flow(self) -> int: pass

    @abstractmethod
    def total_output(self) -> int: pass

    @abstractmethod
    def hardness_in(self) -> int: pass

    @abstractmethod
    def customer_service(self) -> datetime: pass

    @abstractmethod
    def regenerativ_level(self) -> int: pass

    @abstractmethod
    def day_output(self) -> int: pass

    @abstractmethod
    def capacity_1(self) -> int: pass

    @abstractmethod
    def last_regeneration_1(self) -> datetime: pass