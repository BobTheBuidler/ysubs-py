
import asyncio
from time import time
from typing import TYPE_CHECKING, Literal, Optional

from brownie.convert.datatypes import EthAddress
from pony.orm import Database, PrimaryKey, Required, db_session, select

from ysubs import _config
from ysubs.utils.time import *

if TYPE_CHECKING:
    from ysubs.subscription import Subscription

db = Database()

class User(db.Entity):
    _table_ = "users"
    
    user_id = PrimaryKey(int, auto=True)
    address = Required(str, unique=True)
    
    @classmethod
    async def get_or_create_entity(cls, address: EthAddress) -> "User":
        return await asyncio.get_event_loop().run_in_executor(None, cls._get_or_create_entity, address)
    
    @classmethod
    async def get_user_id(cls, address: EthAddress) -> int:
        return await asyncio.get_event_loop().run_in_executor(None, cls._get_user_id, address)
    
    @db_session
    @classmethod
    def _get_or_create_entity(cls, address: EthAddress) -> "User":
        user = cls.get(address=address)
        if user is None:
            user = cls(address=address)
        return user

    @db_session
    @classmethod
    def _get_user_id(cls, address: EthAddress) -> int:
        return cls._get_or_create_entity(address).user_id


class UserRequest(db.Entity):
    _table_ = "user_requests"
    
    uid = PrimaryKey(int, auto=True)
    user = Required(User, index=True)
    timestamp = Required(float)
    
    @classmethod
    async def clear_stale_for(cls, address: EthAddress, t: Optional[float] = None) -> None:
        return await asyncio.get_event_loop().run_in_executor(None, cls.__clear_stale_for, address, t)
    
    @classmethod
    async def count_this_day(cls, address: EthAddress) -> int:
        return await asyncio.get_event_loop().run_in_executor(None, cls.__count_this_day, address)
    
    @classmethod
    async def count_this_minute(cls, address: EthAddress) -> int:
        return await asyncio.get_event_loop().run_in_executor(None, cls.__count_this_minute, address)
    
    @classmethod
    async def next(cls, subscription: "Subscription") -> int:
        next = min(await asyncio.gather(cls._time_til_next(subscription, "minute"), cls._time_til_next(subscription, "day")))
        return next if next > 0 else 0
    
    @classmethod
    async def record_request(cls, address: EthAddress) -> None:
        return await asyncio.get_event_loop().run_in_executor(None, cls.__record_request, address)
    
    @classmethod
    async def _time_til_next(cls, subscription: "Subscription", limiter: Literal["minute", "day"]) -> float:
        return await asyncio.get_event_loop().run_in_executor(None, cls.__time_til_next.__get__(cls, type), subscription, limiter)
    
    @db_session
    @classmethod
    def __clear_stale_for(cls, address: EthAddress, t: Optional[float] = None) -> None:
        select(r for r in cls if r.user.address == address and (t or time()) - r.timestamp >= ONE_DAY).delete(bulk=True)
        
    @db_session
    @classmethod
    def __count_this_day(cls, address: EthAddress) -> int:
        cls.__clear_stale_for(address)
        return select(r for r in cls if r.user.address == address).count()
    
    @db_session
    @classmethod
    def __count_this_minute(cls, address: EthAddress) -> int:
        return select(r for r in cls if r.user.address == address and time() - r.timestamp < ONE_MINUTE).count()
    
    @db_session
    @classmethod
    def __record_request(cls, address: EthAddress) -> None:
        cls(user=User._get_or_create_entity(address), timestamp=time())
        
    @db_session
    @classmethod
    def __time_til_next(cls, subscription: "Subscription", limiter: Literal["minute", "day"]) -> float:
        t = time()
        if limiter == "minute":
            if cls.__count_this_minute(subscription.user) < subscription.plan.requests_per_minute:
                return 0
            next = ONE_MINUTE - (t - min(r.timestamp for r in cls if r.user.address == subscription.user and t - r.timestamp < ONE_MINUTE))
        elif limiter == "day":
            cls.__clear_stale_for(subscription.user)
            next = ONE_DAY - (t - min(r.timestamp for r in cls if r.user.address == subscription.user))
        else:
            raise NotImplementedError(limiter)
        return next if next > 0 else 0

db.bind(provider='sqlite', filename=_config.DB_PATH, create_db=True)