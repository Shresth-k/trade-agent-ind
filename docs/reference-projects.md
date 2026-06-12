# Reference Projects

This project learns from the following MIT-licensed repositories without
copying their full product surface.

## HKUDS/Vibe-Trading

Useful patterns:

- Normalized loader interfaces instead of one-off data scripts
- Paper/read-only broker guards for connectors without a structural sandbox
- Explicit trading mandates, pre-trade risk gates, kill switches, and audit ledgers
- Data caching with staleness rules
- Out-of-sample checks and random controls for strategy evaluation

Not adopted for the MVP:

- Multi-agent swarms
- General-purpose chat and web application
- Large alpha catalogue
- Live autonomous broker execution

## mvanhorn/last30days-skill

Useful patterns:

- Parallel research across source types
- Source deduplication
- Recency and relevance metadata
- Grounded summaries with citations
- Keeping collection separate from synthesis

Not adopted for the MVP:

- Broad social research unrelated to a selected trader or setup
- Engagement counts as evidence that a strategy is profitable

## Attribution policy

Ideas and public interfaces may be reimplemented locally. If source code is
copied or substantially adapted, its original copyright and MIT notice must
be retained in the relevant file and in the project notice.
