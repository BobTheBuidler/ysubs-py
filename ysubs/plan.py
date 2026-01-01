from typing import Optional


class Plan:
    def __init__(
        self,
        price: int,
        rate_limit_per_minute: int,
        rate_limit_per_day: int,
        time_interval: str,
        is_active: bool,
        name: Optional[str] = None,  # Not all subscribers support names.
    ) -> None:
        self.name = name
        self.price = price
        self.requests_per_day = rate_limit_per_day
        self.requests_per_minute = rate_limit_per_minute
        self.seconds_per_request = rate_limit_per_minute / 60

    def __repr__(self) -> str:
        return f"<Plan {self.name}>" if self.name else f"<Unnamed Plan>"


class FreeTrial(Plan):
    def __init__(self, rate_limit_per_minute: int):
        if not rate_limit_per_minute > 0:
            raise ValueError(
                f"'rate_limit_per_minute' must be a positive integer. You passed {rate_limit_per_minute}"
            )
        super().__init__(
            name="Free Trial",
            price=0,
            rate_limit_per_minute=rate_limit_per_minute,
            rate_limit_per_day=rate_limit_per_minute * 60 * 24,
            time_interval="Not Implemented",
            is_active=True,
        )
