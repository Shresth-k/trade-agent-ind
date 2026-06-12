from datetime import date, datetime, time, timezone

import pytest

from model_trader.markets import (
    INDIA_TZ,
    AssetClass,
    ExchangeSegment,
    IndianInstrument,
    MarketSession,
    NSECalendar,
    OptionType,
)


def test_nse_session_accepts_aware_utc_timestamp():
    calendar = NSECalendar()
    moment = datetime(2026, 6, 12, 4, 0, tzinfo=timezone.utc)  # 09:30 IST, Friday

    assert calendar.is_open(moment)
    assert calendar.to_exchange_time(moment).tzinfo == INDIA_TZ


def test_nse_session_rejects_weekends_holidays_and_naive_timestamps():
    holiday = date(2026, 6, 15)
    calendar = NSECalendar(holidays={holiday})

    assert not calendar.is_open(datetime(2026, 6, 13, 10, 0, tzinfo=INDIA_TZ))
    assert not calendar.is_open(datetime(2026, 6, 15, 10, 0, tzinfo=INDIA_TZ))
    with pytest.raises(ValueError, match="timezone-aware"):
        calendar.is_open(datetime(2026, 6, 12, 10, 0))


def test_special_session_overrides_weekend():
    special_day = date(2026, 11, 8)
    calendar = NSECalendar(
        special_sessions={special_day: MarketSession(time(18, 0), time(19, 0))}
    )

    assert calendar.is_open(datetime(2026, 11, 8, 18, 30, tzinfo=INDIA_TZ))
    assert not calendar.is_open(datetime(2026, 11, 8, 17, 59, tzinfo=INDIA_TZ))


def test_no_entry_cutoff_is_separate_from_market_close():
    calendar = NSECalendar()
    moment = datetime(2026, 6, 12, 15, 1, tzinfo=INDIA_TZ)

    assert calendar.is_open(moment)
    assert not calendar.can_enter(moment, no_entry_after=time(15, 0))


def test_option_contract_requires_complete_metadata():
    option = IndianInstrument(
        symbol="NIFTY26JUN25000CE",
        exchange_segment=ExchangeSegment.NSE_FNO,
        asset_class=AssetClass.OPTION,
        underlying="NIFTY",
        expiry=date(2026, 6, 25),
        strike=25000,
        option_type=OptionType.CALL,
        lot_size=75,
        tick_size=0.05,
    )

    assert option.is_derivative

    with pytest.raises(ValueError, match="options require"):
        IndianInstrument(
            symbol="NIFTY_OPTION",
            exchange_segment=ExchangeSegment.NSE_FNO,
            asset_class=AssetClass.OPTION,
        )
