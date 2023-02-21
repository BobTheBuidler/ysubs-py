import asyncio
from datetime import datetime
from typing import Dict, Iterable, List, Tuple

from eth_typing import ChecksumAddress

from ysubs.plan import Plan
from ysubs.subscriber import Subscriber
from ysubs.utils.asynchronous import await_if_sync


class ySubs:
    def __init__(self, addresses: Iterable[ChecksumAddress], asynchronous: bool = False) -> None:
        """
        addresses: an iterable of addresses for Subscriber contracts that you have deployed for your program
        """
        self.asynchronous = asynchronous
        self.subscribers = [Subscriber(address, asynchronous=True) for address in addresses]
    
    @await_if_sync
    async def check_subscription(self, signature: str) -> List[Tuple[Plan, datetime]]:
        """
        Returns all active subscriptions for the user who signed 'signature'
        """
        results = await asyncio.gather(*[subscriber.check_subscription(signature) for subscriber in self.subscribers])
        active_plans = [plan for plan in results if plan]
        return active_plans
    
    @await_if_sync
    async def get_plans(self) -> Dict[Subscriber, List[Plan]]:
        """
        Returns all Plans defined on each Subscriber.
        """
        plans = await asyncio.gather(*[subscriber.get_plans() for subscriber in self.subscribers])
        return dict(zip(self.subscribers, plans))
