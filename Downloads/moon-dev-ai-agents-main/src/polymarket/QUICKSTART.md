# Polymarket API Quick Start Guide

## Installation

```bash
cd /Users/adamoubaita/Downloads/moon-dev-ai-agents-main/src

# Install dependencies
pip install requests

# Optional: for WebSocket support
pip install websocket-client
```

## Quick Test

```bash
# Run the working demo
python3 polymarket/examples/demo_working.py

# Run comprehensive tests
python3 polymarket/examples/test_specific_markets.py

# Run real-world examples
python3 polymarket/examples/test_realworld_usage.py
```

## Basic Usage

### Get Market Data

```python
from polymarket import GammaClient

gamma = GammaClient()

# Get open markets
markets = gamma.get_markets(limit=50, closed=False)

# Filter for active, high-liquidity markets
active = gamma.filter_markets(
    active_only=True,
    open_only=True,
    min_liquidity=10000
)

# Show results
for m in active[:5]:
    print(f"{m['slug']}: ${m.get('volume', 0):,.2f}")
```

### Get Current Prices

```python
from polymarket import ClobClient

clob = ClobClient()

# Get all markets with prices (RECOMMENDED METHOD)
markets = clob.get_simplified_markets()

# Filter for active trading
active = [m for m in markets if m.get('accepting_orders')]

# Show prices
for m in active[:5]:
    print(f"\nMarket: {m.get('question', 'Unknown')}")
    for token in m.get('tokens', []):
        print(f"  {token['outcome']}: ${token['price']:.3f}")
```

### Combined: Metadata + Prices

```python
from polymarket import GammaClient, ClobClient

gamma = GammaClient()
clob = ClobClient()

# Get high-volume markets
gamma_markets = gamma.filter_markets(
    open_only=True,
    min_liquidity=1000
)

# Get current prices
clob_markets = clob.get_simplified_markets()
clob_by_condition = {m['condition_id']: m for m in clob_markets}

# Match and display
for gm in gamma_markets[:10]:
    cond_id = gm.get('condition_id')
    if cond_id and cond_id in clob_by_condition:
        cm = clob_by_condition[cond_id]

        print(f"\n{gm['slug']}")
        print(f"  Volume: ${gm.get('volume', 0):,.2f}")

        for token in cm.get('tokens', []):
            print(f"  {token['outcome']}: ${token['price']:.3f}")
```

## Common Use Cases

### Find High-Volume Trading Opportunities

```python
gamma = GammaClient()

markets = gamma.filter_markets(
    active_only=True,
    open_only=True,
    min_liquidity=10000,
    limit=100
)

# Filter by volume
high_volume = [m for m in markets if m.get('volume', 0) > 100000]

# Sort by volume
sorted_markets = sorted(
    high_volume,
    key=lambda x: float(x.get('volume', 0)),
    reverse=True
)

for m in sorted_markets[:5]:
    print(f"{m['slug']}: ${m['volume']:,.2f}")
```

### Monitor Specific Topics

```python
gamma = GammaClient()

# Get all open markets
markets = gamma.get_markets(limit=200, closed=False)

# Search for election markets
election_markets = [
    m for m in markets
    if 'election' in m.get('slug', '').lower()
]

print(f"Found {len(election_markets)} election markets")
```

### Track Market Sentiment

```python
clob = ClobClient()

markets = clob.get_simplified_markets()

# Analyze binary markets
total_yes = 0
total_no = 0
count = 0

for m in markets:
    tokens = m.get('tokens', [])
    if len(tokens) == 2:
        for t in tokens:
            outcome = t.get('outcome', '').lower()
            if 'yes' in outcome:
                total_yes += t.get('price', 0)
                count += 1
            elif 'no' in outcome:
                total_no += t.get('price', 0)

if count > 0:
    print(f"Average Yes sentiment: {total_yes/count:.3f}")
    print(f"Average No sentiment: {total_no/count:.3f}")
```

## Important Notes

1. **Use `get_simplified_markets()` for prices** - The legacy `/price` endpoint has limited availability

2. **Some markets lack `condition_id`** - Filter these out when matching Gamma and CLOB data

3. **Read-only by design** - These clients cannot place trades (enforced by runtime guardrails)

4. **Rate limiting** - No built-in rate limiting; add delays if making many requests

## Troubleshooting

### "Invalid token id" errors

This is expected for the legacy `/price` endpoint. Use `get_simplified_markets()` instead.

### Markets not matching between APIs

Some markets have `condition_id: None`. Filter these out:

```python
valid_markets = [m for m in markets if m.get('condition_id')]
```

### Empty question fields

CLOB simplified markets sometimes have empty questions. Use Gamma API for metadata.

## Next Steps

- Read the full documentation: `CLAUDE.md`
- View test results: `TEST_RESULTS.md`
- Run example scripts in `examples/` directory
- Check the official docs: https://docs.polymarket.com

## Support

For issues with these clients, check:
1. Test results in `TEST_RESULTS.md`
2. Code examples in `examples/` directory
3. Full documentation in `CLAUDE.md`
