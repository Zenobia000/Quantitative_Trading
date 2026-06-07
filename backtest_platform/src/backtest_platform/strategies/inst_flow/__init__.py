"""Institutional-flow factor — a new edge family (non-momentum).

Cross-sectional factor that follows 三大法人 (foreign / trust / dealer) net buying:
rank stocks by trailing institutional net-buy *intensity* (net-buy normalized by
trading volume, so it is comparable across stock sizes), go long the top fraction,
rebalance. A flow/sentiment edge orthogonal to price-momentum — Taiwan's
retail-heavy market makes institutional (esp. foreign) flow informative.

Uses FREE FinMind ``institutional_flows`` (already ingested); reuses momentum's
tested rebalance / cost / vol-target mechanics so only the *signal* differs.
"""
