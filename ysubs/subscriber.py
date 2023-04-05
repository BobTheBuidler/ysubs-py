
import asyncio
from datetime import datetime
from typing import List, Optional

import a_sync
from a_sync import ASyncGenericBase
from brownie import Contract
from dank_mids.brownie_patch import patch_contract
from eth_typing import ChecksumAddress
from semantic_version import Version

from ysubs import _config
from ysubs.plan import Plan
from ysubs.utils import signatures
from ysubs.utils.dank_mids import dank_w3


class Subscriber(ASyncGenericBase):
    def __init__(self, address: ChecksumAddress, asynchronous: bool = False) -> None:
        self.asynchronous = asynchronous
        try:
            self.contract = patch_contract(Contract(address), dank_w3)
        except ValueError:
            self.contract = patch_contract(Contract.from_explorer(address), dank_w3)
    
    @a_sync.aka.cached_property
    async def version(self) -> Version:
        return Version(await self.contract.API_VERSION.coroutine())
    
    @a_sync.aka.property
    async def num_plans(self) -> int:
        return await self.contract.num_plans.coroutine()
    
    @a_sync.aka.property
    async def active_plan_ids(self) -> List[int]:
        return list(range(1, await self.__num_plans__(sync=False)))
    
    @a_sync.a_sync(cache_type='memory')
    async def get_plan(self, plan_id: int) -> Optional[Plan]:
        if plan_id > 0:
            details = await self.contract.get_plan.coroutine(plan_id)
            return Plan(**details.dict())
        raise ValueError(f"{plan_id} is not a valid plan_id.")
    
    @a_sync.a_sync(ram_cache_ttl=_config.VALIDATION_INTERVAL)
    async def get_all_plans(self) -> List[Plan]:
        return await asyncio.gather(*[self.get_plan(plan_id, sync=False) for plan_id in await self.__active_plan_ids__(sync=False)])
    
    async def get_active_subscriptions(self, signer_or_signature: str) -> List[Plan]:
        plan_ids = await self.__active_plan_ids__(sync=False)
        signer = signatures.get_msg_signer(signer_or_signature)
        ends = await asyncio.gather(*[self.contract.subscription_end.coroutine(i, signer) for i in plan_ids])
        now = datetime.utcnow()
        return [id for end, id in zip(ends, plan_ids) if end and datetime.fromtimestamp(end) > now]
