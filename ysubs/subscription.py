import asyncio
from typing import List

from ysubs.exceptions import TooManyRequests
from ysubs.plan import Plan
from ysubs.utils.pg import UserRequest
from ysubs.utils.time import *


class Subscription:
    def __init__(self, user_wallet: str, plan: Plan) -> None:
        self.user = user_wallet
        self.plan = plan
    
    def __repr__(self) -> str:
        return f"<Subscription {self.user} {self.plan}>"
    
    async def __aenter__(self):
        if time_to_next := await UserRequest.next(self):
            raise TooManyRequests(time_to_next)
        asyncio.create_task(UserRequest.record_request(self.user))
    
    def __aexit__(self, *_):
        pass

class SubscriptionsLimiter:
    def __init__(self, subscriptions: List[Subscription]) -> None:
        self.subscriptions = subscriptions
    
    async def __aenter__(self) -> None:
        """We will enter this object before each request a user makes."""
        for subscription in self.subscriptions:
            try:
                async with subscription:
                    return
            except TooManyRequests:
                pass
        next = min(await asyncio.gather(*[UserRequest.next(subscription) for subscription in self.subscriptions]))
        if next <= 0: # potential race condition
            return
        raise TooManyRequests(next)
    
    def __exit__(self, *_) -> None:
        # NOTE: exiting a Subscription does nothing so we don't need to do that here.
        pass