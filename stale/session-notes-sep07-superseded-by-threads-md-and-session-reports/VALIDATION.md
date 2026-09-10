# BEAR Algorithm Validation vs Literature

## 1. Overextended / Reversal — NEEDS FIX

### What I used
- `rev_8w > 0.10` (10% return threshold) and `mom_7d > 0.03` (3%)
- These are arbitrary thresholds with no academic basis

### What the literature says
- **Kiefer & Nowotny (2026)**: 8-week formation window is optimal. Sharpe 0.96 base, 1.37 for high-vol. Strategy: short winners, buy losers. VALIDATED.
- **CoinQuant (2026)**: Mean reversion is regime-dependent. Bull: +16.3%, Bear: -40.6%. Need trend filter. Bollinger k=2.0 (z-score threshold) is standard.
- **Avellaneda & Lee (2010)**: Z-score / BB reversion Sharpe 2.5-3.2 in bull regimes.

### Fix
Replace arbitrary % thresholds with z-score:
```python
# Instead of: rev_8w > 0.10
# Use: z-score of 8w return > 2.0 (2 standard deviations above mean)
z_score = (return_8w - mean_8w) / std_8w
is_overextended = z_score > 2.0
```
This is the Bollinger Band approach validated by CoinQuant.

## 2. Squeeze Detection — NEEDS FIX

### What I used
- Drawdown + pump from 30d low + volume spike
- This measures "what happened" not "what's happening now"

### What the literature says
- **Global games model (arXiv 2024)**: Volatility threshold σ* = 1.8%/hour triggers coordinated arbitrageur withdrawal. OI collapses 65% during Terra crash.
- **OI reconciliation (arXiv 2310.14973)**: OI is systematically misquoted on some exchanges. Use with caution.

### Fix
Squeeze = OI declining + volatility spike + funding extreme:
```python
squeeze_score = (
    oi_change_24h < -20%  # OI collapsing
    + hourly_vol > 1.8%    # above global-games threshold
    + funding < -0.0001    # shorts paying = crowded
)
```

## 3. Dogshit — NEEDS FIX

### What I used
- Category (meme/other) + low price + negative funding
- Too simple, doesn't capture actual garbage

### What the literature says
- **MELT (2026)**: 36.5% of token supply held by coordinated insider accounts. TVL drops and trading idleness are key signals.
- **ME2F (2025)**: Fragility = Volatility Dynamics + Whale Dominance + Sentiment Amplification
- **Catching the Rug (2026)**: XGBoost predicts rug pulls within 5 minutes using TVL/idle features.
- **CoinCLIP (2025)**: Viability = community engagement + visual quality + listing on DEX

### Fix
Add on-chain signals:
```python
dogshit_score = (
    insider_concentration * 0.25  # % held by top 10 wallets
    + tvl_decline_30d * 0.20      # TVL dropping
    + idle_ratio * 0.15           # % of time with no trades
    + meme_category * 0.15        # if meme coin
    + low_volume * 0.15           # nobody cares
    + negative_funding * 0.10     # market consensus
)
```
Currently we don't have on-chain data. Keep category-based for now but add validation notes.

## 4. Funding — VALIDATED

### What I used
- `funding_hourly * 24 * 365` (annualized)
- Correct for Hyperliquid hourly funding

### What the literature says
- **Lau (2026)**: Naive delta-neutral funding carry ~7% excess on HL. ML refinements don't improve.
- VALIDATED. Simple is better.

## 5. Regime Filter — MISSING

### What the literature says
- **CoinQuant (2026)**: Mean reversion loses 40% in bear markets without trend filter.
- **Corbet & Katsiampa (2020)**: BTC reversion is asymmetric — negative moves revert faster.

### Fix
Add BTC regime filter:
```python
btc_above_200sma = btc_price > btc_200sma
if not btc_above_200sma:
    # Bear market — reduce short scores (mean reversion unreliable)
    total_score *= 0.7
```

## Summary of Required Changes

| Algorithm | Current | Literature-Based | Priority |
|-----------|---------|-----------------|----------|
| Overextended | Arbitrary 10%/3% | Z-score > 2.0 (Bollinger) | HIGH |
| Squeeze | Drawdown + pump | OI decline + vol spike + funding | HIGH |
| Dogshit | Category + price | On-chain: insider, TVL, idle | MEDIUM |
| Funding | ✅ Correct | annualized hourly | VALIDATED |
| Regime filter | Missing | BTC vs 200SMA | HIGH |
