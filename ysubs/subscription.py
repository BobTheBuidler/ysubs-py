from time import time
from typing import List

from ysubs.exceptions import TooManyRequests
from ysubs.plan import Plan


class Subscription:
    def __init__(self, user_wallet: str, plan: Plan) -> None:
        self.user = user_wallet
        self.plan = plan
        self.requests_this_day = []
        self.requests_this_minute = []
    
    def __repr__(self) -> str:
        return f"<Subscription {self.user} {self.plan}>"
    
    def __enter__(self):
        if self.should_rate_limit:
            raise TooManyRequests(self.time_til_next_request)
        self.__make_request()
    
    def __exit__(self, *_):
        pass
    
    def __clear_stale(self) -> None:
        t = time()
        self.requests_this_minute = [_t for _t in self.requests_this_minute if t - _t > 60]
        self.requests_this_day = [_t for _t in self.requests_this_minute if t - _t > 60 * 60 * 24]
    
    def __make_request(self) -> None:
        t = time()
        self.requests_this_minute.append(t)
        self.requests_this_day.append(t)
    
    @property
    def should_rate_limit(self) -> bool:
        return (self.daily_limit_reached or self.minute_limit_reached) is False
    
    @property
    def time_til_next_request(self) -> float:
        if self.daily_limit_reached:
            return self.requests_this_day[0] + 60 * 60 * 24
        elif self.minute_limit_reached:
            return self.requests_this_minute[0] + 60
        return 0
    
    @property
    def daily_limit_reached(self) -> bool:
        self.__clear_stale()
        return len(self.requests_this_day) > self.plan.requests_per_day
    
    @property
    def minute_limit_reached(self) -> bool:
        self.__clear_stale()
        return len(self.requests_this_minute) > self.plan.requests_per_minute


class SubscriptionsLimiter:
    def __init__(self, subscriptions: List[Subscription]) -> None:
        self.subscriptions = subscriptions
    
    def __enter__(self) -> None:
        """We will enter this object before each request a user makes."""
        for subscription in self.subscriptions:
            try:
                subscription.__enter__()
                return
            except TooManyRequests:
                pass
        raise TooManyRequests(min(subscription.time_til_next_request for subscription in self.subscriptions))
    
    def __exit__(self, *_) -> None:
        # NOTE: exiting a Subscription does nothing so we don't need to do that here.
        pass