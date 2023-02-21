
import asyncio
from datetime import datetime
from typing import List, Optional, Tuple

from async_lru import alru_cache
from async_property import async_cached_property
from brownie import Contract
from dank_mids.brownie_patch import patch_contract
from eth_typing import ChecksumAddress
from semantic_version import Version

from ysubs.plan import Plan
from ysubs.utils.asynchronous import await_if_sync
from ysubs.utils.dank_mids import dank_w3
from ysubs.utils.signatures import get_msg_signer


class Subscriber:
    def __init__(self, address: ChecksumAddress, asynchronous: bool = False) -> None:
        self.asynchronous = asynchronous
        self.contract = patch_contract(Contract(address), dank_w3)
    
    @await_if_sync
    @async_cached_property
    async def version(self) -> Version:
        return Version(await self.contract.API_VERSION.coroutine())
    
    @await_if_sync
    @alru_cache(maxsize=None)
    async def get_plan(self, plan_id: int) -> Optional[Plan]:
        if plan_id > 0:
            return Plan(await self.contract.plans.coroutine(plan_id))
    
    @await_if_sync
    async def get_plans(self) -> List[Plan]:
        num_plans = await self.contract.num_plans.coroutine()
        return await asyncio.gather(*[self.get_plan(plan_id) for plan_id in range(1, num_plans)])

    @await_if_sync
    async def check_subscription(self, signature: str) -> Tuple[Optional[Plan], datetime]:
        plan_id, ends_at = await self.contract.active_plan.coroutine(get_msg_signer(signature))
        plan = await self.get_plan(plan_id)
        return plan, datetime.fromtimestamp(ends_at)
