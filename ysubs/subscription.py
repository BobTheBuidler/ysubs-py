from time import time
from typing import List

from ysubs.exceptions import TooManyRequests
from ysubs.plan import Plan


class Subscription:
    def __init__(self, user_wallet: str, plan: Plan) -> None:
        self.user = user_wallet
        self.plan = plan
        self.checkpoint = 0
    
    def __repr__(self) -> str:
        return f"<Subscription {self.user} {self.plan}>"
    
    def __enter__(self):
        if self.should_rate_limit:
            raise TooManyRequests(self.time_til_next_request)
    
    def __exit__(self, *_):
        pass
    
    @property
    def should_rate_limit(self) -> bool:
        return self.time_since_last_request < self.plan.seconds_per_request
    
    @property
    def time_since_last_request(self) -> float:
        return time() - self.checkpoint
    
    @property
    def time_til_next_request(self) -> float:
        next = self.checkpoint + self.plan.seconds_per_request
        return next if next >= 0 else 0


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