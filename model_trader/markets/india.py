"""Indian market domain types and NSE equity/derivatives session handling."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import Enum
from zoneinfo import ZoneInfo


INDIA_TZ = ZoneInfo("Asia/Kolkata")


class ExchangeSegment(str, Enum):
    NSE_EQ = "NSE_EQ"
    NSE_FNO = "NSE_FNO"
    BSE_EQ = "BSE_EQ"
    BSE_FNO = "BSE_FNO"


class AssetClass(str, Enum):
    INDEX = "index"
    EQUITY = "equity"
    FUTURE = "future"
    OPTION = "option"


class OptionType(str, Enum):
    CALL = "CE"
    PUT = "PE"


@dataclass(frozen=True)
class IndianInstrument:
    """Broker-neutral identity and contract metadata for an Indian instrument."""

    symbol: str
    exchange_segment: ExchangeSegment
    asset_class: AssetClass
    broker_token: str = ""
    underlying: str = ""
    lot_size: int = 1
    tick_size: float = 0.05
    expiry: date | None = None
    strike: float | None = None
    option_type: OptionType | None = None

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol cannot be empty")
        if self.lot_size <= 0:
            raise ValueError("lot_size must be positive")
        if self.tick_size <= 0:
            raise ValueError("tick_size must be positive")

        option_fields = (self.expiry, self.strike, self.option_type)
        if self.asset_class == AssetClass.OPTION:
            if any(value is None for value in option_fields):
                raise ValueError("options require expiry, strike, and option_type")
            if not self.underlying.strip():
                raise ValueError("options require an underlying")
        elif self.strike is not None or self.option_type is not None:
            raise ValueError("strike and option_type are only valid for options")

    @property
    def is_derivative(self) -> bool:
        return self.asset_class in (AssetClass.FUTURE, AssetClass.OPTION)


@dataclass(frozen=True)
class MarketSession:
    open_time: time
    close_time: time

    def contains(self, value: time) -> bool:
        return self.open_time <= value <= self.close_time


NSE_NORMAL_SESSION = MarketSession(open_time=time(9, 15), close_time=time(15, 30))


@dataclass
class NSECalendar:
    """NSE normal session with externally supplied holidays and special sessions.

    Holiday and Muhurat dates change every year, so this class deliberately does
    not hardcode them. Load them from an exchange circular or checked-in data file.
    """

    holidays: set[date] = field(default_factory=set)
    special_sessions: dict[date, MarketSession] = field(default_factory=dict)
    normal_session: MarketSession = NSE_NORMAL_SESSION

    def is_trading_day(self, day: date) -> bool:
        if day in self.special_sessions:
            return True
        return day.weekday() < 5 and day not in self.holidays

    def session_for(self, day: date) -> MarketSession | None:
        if day in self.special_sessions:
            return self.special_sessions[day]
        if self.is_trading_day(day):
            return self.normal_session
        return None

    def is_open(self, moment: datetime) -> bool:
        local = self.to_exchange_time(moment)
        session = self.session_for(local.date())
        return bool(session and session.contains(local.time().replace(tzinfo=None)))

    def can_enter(self, moment: datetime, no_entry_after: time | None = None) -> bool:
        local = self.to_exchange_time(moment)
        if not self.is_open(local):
            return False
        return no_entry_after is None or local.time().replace(tzinfo=None) <= no_entry_after

    @staticmethod
    def to_exchange_time(moment: datetime) -> datetime:
        if moment.tzinfo is None or moment.utcoffset() is None:
            raise ValueError("market timestamps must be timezone-aware")
        return moment.astimezone(INDIA_TZ)
