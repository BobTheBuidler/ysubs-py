
from typing import Optional


class Plan:
    def __init__(
        self,
        price: int,
        rate_limit: int,
        time_interval: str,
        is_active: bool,
        name: Optional[str] = None,  # Not all subscribers support names.
    ) -> None:
        self.name = name
        self.price = price
        self.requests_per_minute = rate_limit
        self.seconds_per_request = rate_limit / 60
    
    def __repr__(self) -> str:
        return f"<Plan {self.name}>" if self.name else f"<Unnamed Plan>"
