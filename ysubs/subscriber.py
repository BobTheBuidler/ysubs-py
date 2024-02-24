
import asyncio
from datetime import datetime, timezone
from typing import List, Optional

import a_sync
import dank_mids
from eth_typing import ChecksumAddress
from semantic_version import Version

from ysubs import _config
from ysubs.plan import Plan
from ysubs.subscription import Subscription
from ysubs.utils import sentry, dank_mids


class Subscriber(a_sync.ASyncGenericBase):
    def __init__(self, address: ChecksumAddress, asynchronous: bool = False) -> None:
        self.asynchronous = asynchronous
        try:
            self.contract = dank_mids.Contract(address)
        except ValueError:
            self.contract = dank_mids.Contract.from_explorer(address)
    
    @a_sync.aka.cached_property
    @sentry.trace
    async def version(self) -> Version:
        return Version(await self.contract.API_VERSION.coroutine())
    
    @a_sync.aka.property
    @sentry.trace
    async def plan_count(self) -> int:
        return await self.contract.plan_count.coroutine()
    
    @a_sync.aka.property
    @sentry.trace
    async def active_plan_ids(self) -> List[int]:
        return list(range(1, await self.__plan_count__(sync=False) + 1))
    
    @a_sync.a_sync(cache_type='memory')
    @sentry.trace
    async def get_plan(self, plan_id: int) -> Optional[Plan]:
        if plan_id > 0:
            details = await self.contract.get_plan.coroutine(plan_id)
            return Plan(**details.dict())
        raise ValueError(f"{plan_id} is not a valid plan_id.")
    
    @a_sync.a_sync(ram_cache_ttl=_config.VALIDATION_INTERVAL)
    @sentry.trace
    async def get_all_plans(self) -> List[Plan]:
        return await asyncio.gather(*[self.get_plan(plan_id, sync=False) for plan_id in await self.__active_plan_ids__(sync=False)])
    
    @a_sync.a_sync(cache_type='memory')
    @sentry.trace
    async def get_subscription(self, signer: str, plan_id: int) -> Subscription:
        return Subscription(signer, await self.get_plan(plan_id))
    
    @sentry.trace
    async def get_active_subscriptions(self, signer: str) -> List[Subscription]:
        plan_ids = await self.__active_plan_ids__(sync=False)
        ends = await asyncio.gather(*[self.contract.subscription_end.coroutine(i, signer) for i in plan_ids])
        now = datetime.now(tz=timezone.utc)
        return await asyncio.gather(*[self.get_subscription(signer, id) for end, id in zip(ends, plan_ids) if end and datetime.fromtimestamp(end, tz=timezone.utc) > now])
