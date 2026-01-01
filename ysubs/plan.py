from typing import Final, Optional, final


class Plan:
    def __init__(
        self,
        price: int,
        rate_limit_per_minute: int,
        rate_limit_per_day: int,
        time_interval: str,
        is_active: bool,
        # NOTE Not all subscribers support names.
        name: Optional[str] = None,
    ) -> None:
        self.name: Final = name
        self.price: Final = price
        self.requests_per_day: Final = rate_limit_per_day
        self.requests_per_minute: Final = rate_limit_per_minute
        self.seconds_per_request: Final = rate_limit_per_minute / 60

    def __repr__(self) -> str:
        return f"<Plan {self.name}>" if self.name else f"<Unnamed Plan>"


@final
class FreeTrial(Plan):
    def __init__(self, rate_limit_per_minute: int) -> None:
        if not rate_limit_per_minute > 0:
            err = f"'rate_limit_per_minute' must be a positive integer. You passed {rate_limit_per_minute}"
            raise ValueError(err)
        super().__init__(
            name="Free Trial",
            price=0,
            rate_limit_per_minute=rate_limit_per_minute,
            rate_limit_per_day=rate_limit_per_minute * 60 * 24,
            time_interval="Not Implemented",
            is_active=True,
        )
