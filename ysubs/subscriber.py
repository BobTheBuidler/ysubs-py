
import asyncio
from datetime import datetime
from typing import List, Optional, Tuple

import a_sync
from a_sync import ASyncGenericBase
from brownie import Contract
from dank_mids.brownie_patch import patch_contract
from eth_typing import ChecksumAddress
from semantic_version import Version

from ysubs import _config
from ysubs.plan import Plan
from ysubs.utils.dank_mids import dank_w3
from ysubs.utils.signatures import get_msg_signer


class Subscriber(ASyncGenericBase):
    def __init__(self, address: ChecksumAddress, asynchronous: bool = False) -> None:
        self.asynchronous = asynchronous
        self.contract = patch_contract(Contract(address), dank_w3)
    
    @a_sync.aka.cached_property
    async def version(self) -> Version:
        return Version(await self.contract.API_VERSION.coroutine())
    
    @a_sync.a_sync(cache_type='memory')
    async def get_plan(self, plan_id: int) -> Optional[Plan]:
        if plan_id > 0:
            return Plan(await self.contract.plans.coroutine(plan_id))
    
    @a_sync.a_sync(ram_cache_ttl=_config.VALIDATION_INTERVAL)
    async def get_plans(self) -> List[Plan]:
        num_plans = await self.contract.num_plans.coroutine()
        return await asyncio.gather(*[self.get_plan(plan_id, sync=False) for plan_id in range(1, num_plans)])

    @a_sync.a_sync(ram_cache_ttl=_config.VALIDATION_INTERVAL)
    async def check_subscription(self, signature: str) -> Tuple[Optional[Plan], datetime]:
        plan_id, ends_at = await self.contract.active_plan.coroutine(get_msg_signer(signature))
        plan = await self.get_plan(plan_id, sync=False)
        return plan, datetime.fromtimestamp(ends_at)
