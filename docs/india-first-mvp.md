# India-First MVP

The first product is a paper-only intraday research and validation system for
NIFTY. It is not an autonomous options bot.

## Research question

Can rules repeatedly taught by an Indian intraday trader be converted into a
small deterministic strategy that remains useful after realistic costs and on
unseen market periods?

## Initial scope

- Underlying signal: NIFTY spot or front-month futures
- Context timeframe: 15-minute
- Trigger timeframe: 5-minute
- Execution model: paper trade an ATM or one-step ITM option
- Maximum trades: two per session
- Strategy family: opening range or previous-day level breakout and retest
- Inputs: YouTube transcripts first; X posts and articles later

Signals come from the underlying because option premiums are also affected by
implied volatility, time decay, strike selection, spread, and expiry. Contract
selection is a separate execution concern.

## Acceptance gates

A content-derived rule can reach scanner code only when it:

1. Has source evidence and a stable locator such as a video timestamp.
2. Is deterministic enough to express as pass/fail logic.
3. Has been reviewed by a human.
4. Has a stated invalidation condition.
5. Can be tested without future data.

The strategy can reach live paper monitoring only after:

1. Unit tests cover indicators, session rules, and position sizing.
2. Backtests include fees, slippage, spreads, and conservative same-bar fills.
3. Results are reported separately for development and unseen periods.
4. A random or naive baseline is included.
5. Daily loss, trade-count, and market-hours guards are enforced.

## Planned vertical slices

1. Research provenance: normalized sources, citations, deduplication, reviewed rules.
2. Indian market model: instruments, exchange calendar, sessions, tick and lot sizes.
3. Data layer: historical adapter plus cache and data-quality validation.
4. Strategy: one NIFTY opening-range or previous-day-level setup.
5. Realistic backtest: costs, fills, walk-forward split, baseline comparison.
6. Paper monitor: option selection, audit ledger, risk mandate, kill switch.

Live order routing is deliberately outside the MVP.

## Exchange assumptions

NSE currently publishes a normal equity and equity-derivatives session of
09:15-15:30 Asia/Kolkata. Holiday and Muhurat sessions are not hardcoded; they
must be loaded from the current exchange calendar so a stale package release
cannot silently trade on the wrong schedule.
