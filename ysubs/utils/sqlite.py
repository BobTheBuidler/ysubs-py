from asyncio import gather, get_event_loop
from time import time
from typing import TYPE_CHECKING, Literal, Optional

from brownie.convert.datatypes import EthAddress
from pony.orm import Database, PrimaryKey, Required, Set, db_session, select

from ysubs import _config
from ysubs.utils.time import ONE_DAY, ONE_MINUTE

if TYPE_CHECKING:
    from ysubs.subscription import Subscription

db = Database()


@db_session
def _get_or_create_user(address: EthAddress) -> "User":
    user = User.get(address=address)
    if user is None:
        user = User(address=address)
    return user


@db_session
def _get_user_id(address: EthAddress) -> int:
    return _get_or_create_user(address).user_id


class User(db.Entity):
    _table_ = "users"

    user_id = PrimaryKey(int, auto=True)
    address = Required(str, unique=True)
    requests = Set("UserRequest")

    @classmethod
    async def get_or_create_entity(cls, address: EthAddress) -> "User":
        return await get_event_loop().run_in_executor(None, _get_or_create_user, address)

    @classmethod
    async def get_user_id(cls, address: EthAddress) -> int:
        return await get_event_loop().run_in_executor(None, _get_user_id, address)


@db_session
def _clear_stale_for(address: EthAddress, t: Optional[float] = None) -> None:
    select(
        r
        for r in UserRequest
        if r.user.address == address and (t or time()) - r.timestamp >= ONE_DAY
    ).delete(bulk=True)


@db_session
def _time_til_next(subscription: "Subscription", limiter: Literal["minute", "day"]) -> float:
    t = time()
    if limiter == "minute":
        if _count_this_minute(subscription.user) < subscription.plan.requests_per_minute:
            return 0
        least_recent = select(
            r.timestamp
            for r in UserRequest
            if r.user.address == subscription.user and t - r.timestamp < ONE_MINUTE
        ).min()
        next = 0 if least_recent is None else ONE_MINUTE - (t - least_recent)
    elif limiter == "day":
        _clear_stale_for(subscription.user)
        least_recent = select(
            r.timestamp for r in UserRequest if r.user.address == subscription.user
        ).min()
        next = 0 if least_recent is None else ONE_DAY - (t - least_recent)
    else:
        raise NotImplementedError(limiter)
    return next if next > 0 else 0


@db_session
def _count_this_day(address: EthAddress) -> int:
    _clear_stale_for(address)
    return select(r for r in UserRequest if r.user.address == address).count()


@db_session
def _count_this_minute(address: EthAddress) -> int:
    return select(
        r for r in UserRequest if r.user.address == address and time() - r.timestamp < ONE_MINUTE
    ).count()


@db_session
def _record_request(address: EthAddress) -> None:
    UserRequest(user=_get_or_create_user(address), timestamp=time())


class UserRequest(db.Entity):
    _table_ = "user_requests"

    uid = PrimaryKey(int, auto=True)
    user = Required(User, index=True, reverse="requests")
    timestamp = Required(float)

    @classmethod
    async def clear_stale_for(cls, address: EthAddress, t: Optional[float] = None) -> None:
        return await get_event_loop().run_in_executor(None, _clear_stale_for, address, t)

    @classmethod
    async def count_this_day(cls, address: EthAddress) -> int:
        return await get_event_loop().run_in_executor(None, _count_this_day, address)

    @classmethod
    async def count_this_minute(cls, address: EthAddress) -> int:
        return await get_event_loop().run_in_executor(None, _count_this_minute, address)

    @classmethod
    async def next(cls, subscription: "Subscription") -> int:
        next = min(
            await gather(
                *[UserRequest._time_til_next(subscription, period) for period in ["minute", "day"]]
            )
        )
        return next if next > 0 else 0

    @classmethod
    async def record_request(cls, address: EthAddress) -> None:
        return await get_event_loop().run_in_executor(None, _record_request, address)

    @classmethod
    async def _time_til_next(
        cls, subscription: "Subscription", limiter: Literal["minute", "day"]
    ) -> float:
        return await get_event_loop().run_in_executor(None, _time_til_next, subscription, limiter)


db.bind(provider="sqlite", filename=_config.DB_PATH, create_db=True)
db.generate_mapping(create_tables=True)
