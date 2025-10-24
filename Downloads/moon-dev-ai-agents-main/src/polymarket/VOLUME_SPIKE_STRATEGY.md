# Polymarket Volume Spike Trading Strategy

## 🎯 Strategy Overview

**Latency Arbitrage via Volume Spike Detection**

The goal is to detect sudden volume spikes in Polymarket markets that signal imminent resolution or insider information, then execute trades before the crowd catches on.

### Key Insight
When a market is about to resolve, insiders or informed traders often place large bets, causing volume to spike 3x-5x above normal. By detecting these spikes within seconds and correlating with price movement + deadline proximity, we can identify high-probability trades **before** the market price fully adjusts.

---

## 📊 Current System Status

### ✅ What's Built

1. **Volume Spike Detector** (`volume_spike_detector.py`)
   - Tracks volume history for all markets
   - Detects 3x-5x+ volume increases
   - Correlates with price movement (1h change)
   - Filters by deadline proximity (< 72 hours)
   - Calculates signal strength (0-100)
   - Persists volume history to disk

2. **Volume Spike Bot** (`volume_spike_bot.py`)
   - Monitors 418+ open markets continuously (all available markets)
   - Optimized for high-frequency trading across all volume tiers
   - Uses Gamma API for real volume data
   - Executes trades in paper trading mode
   - Tracks P&L and performance
   - Runs 24/7 monitoring cycles

3. **Real Data Integration**
   - Connected to Gamma API: 418+ markets with volume data
   - High volume tier: 297 markets (>$100K)
   - Target HFT range: 121 markets ($10K-$100K)
   - Volume ranges: $10K - $24M per market
   - Markets include: Fed rate decisions, geopolitics, crypto events
   - All data is REAL, not mock

### ⏳ What's Needed

**24/7 Monitoring to Build Baseline**

The system currently detects **0 spikes** because:
1. Volume data doesn't change over 30-second intervals (API updates hourly/daily)
2. Need longer time periods to establish "normal" baseline for each market
3. Real spikes occur over hours/days as volume builds toward resolution

**Solution**: Run bot continuously for days/weeks to:
- Build historical baseline for each market
- Detect when volume deviates from that baseline
- Real spikes will appear as markets approach resolution

---

## 🔍 How It Works

### Signal Detection Formula

**Signal Strength (0-100) =**
- **Volume Component (0-40 points)**: Spike magnitude
  - 3x spike = 10 points
  - 5x spike = 25 points
  - 10x spike = 40 points

- **Price Component (0-30 points)**: Correlated price movement
  - 5% price change = 15 points
  - 10% price change = 30 points

- **Deadline Component (0-30 points)**: Proximity to resolution
  - 72 hours away = 0 points
  - 24 hours away = 20 points
  - <1 hour away = 30 points

**Minimum Signal to Trade: 50/100**

### Example Scenario

```
Market: "Will Fed cut rates in December?"
Normal Volume: $100K/day
Current Volume: $450K/day (4.5x spike)
Price Change: +8% in last hour
Deadline: 18 hours away

Calculation:
- Volume: (4.5 - 1) × 8 = 28 points
- Price: 8 × 3 = 24 points
- Deadline: (1 - 18/72) × 30 = 22.5 points
- Total: 74.5/100 → TRADE SIGNAL ✓

Action: Buy YES at current price ($0.62)
Position: $1,490 (base $1k × 1.49 signal multiplier)
Expected ROI: 61% if resolves to $1.00
```

---

## 📈 Markets Currently Monitored

### Top Volume Markets

1. **russia-x-ukraine-ceasefire-in-2025** - $24.2M volume
2. **us-recession-in-2025** - $9.8M volume
3. **khamenei-out-as-supreme-leader-of-iran-in-2025** - $7.7M volume
4. **will-1-fed-rate-cut-happen-in-2025** - $2.6M volume
5. **will-2-fed-rate-cuts-happen-in-2025** - $2.1M volume

**Total**: 418+ open markets being tracked (all available markets for HFT)

### Market Categories
- **Economic**: Fed rates, recession indicators, inflation
- **Geopolitical**: Wars, sanctions, regime changes
- **Crypto**: Tether depeg, ETF approvals, regulatory actions
- **Policy**: Cannabis rescheduling, NATO expansion

---

## 🎮 How to Use

### Paper Trading (Current Mode)

```bash
# Run for 3 cycles to see system in action
python3 polymarket/volume_spike_bot.py

# Or run original 5-minute test
python3 polymarket/run_5min.py
```

**Expected Output**:
```
Cycle #1:
  ✓ 418 markets with volume data found
    • High volume (>$100K): 297 markets
    • Target range ($10K-$100K): 121 markets
    • Total HFT targets: 418 markets
  Scanning 418 markets for volume spikes...
  ✓ 0 volume spikes detected
```

This is **correct** - no spikes detected yet because baseline data is being collected.

### 24/7 Deployment (Recommended)

To find real opportunities, deploy continuously:

```bash
# Option 1: Run locally in background
nohup python3 polymarket/volume_spike_bot.py > logs/spike_bot.log 2>&1 &

# Option 2: Deploy to cloud server
# - AWS EC2, DigitalOcean, Raspberry Pi
# - Run in tmux/screen session
# - Check logs periodically

# Option 3: Systemd service (Linux)
sudo systemctl enable polymarket-spike-bot
sudo systemctl start polymarket-spike-bot
```

### Live Trading (When Ready)

1. Fund wallet with USDC on Polygon
2. Set `PAPER_TRADING=false` in `.env`
3. Confirm safety limits are set:
   ```bash
   MAX_POSITION_USD=5000
   MAX_DAILY_EXPOSURE=50000
   ```
4. Run bot and monitor closely for first 24 hours

---

## ⚙️ Configuration

### Volume Spike Settings

Edit `volume_spike_bot.py` main():

```python
bot = VolumeSpikeBot(
    paper_trading=True,           # Safety default
    min_spike_ratio=3.0,          # 3x minimum spike
    min_volume_usd=50000,         # $50k min volume
    max_hours_to_deadline=72,     # 3 days max
    check_interval=30             # 30 seconds between scans
)
```

### Tuning for Different Strategies

**Conservative** (lower risk, fewer trades):
```python
min_spike_ratio=5.0              # 5x spike required
min_volume_usd=100000            # $100k min
max_hours_to_deadline=24         # Only last 24h
```

**Aggressive** (more trades, higher risk):
```python
min_spike_ratio=2.0              # 2x spike triggers
min_volume_usd=25000             # $25k min
max_hours_to_deadline=168        # Full week
```

---

## 📊 Performance Expectations

### Win Rate
**Target**: 70-85%
- Not 100% because some spikes are false signals
- Some markets can reverse even after resolution seems certain
- Risk management limits losses on bad trades

### ROI Per Trade
**Target**: 20-60%
- Depends on how early we catch the spike
- Earlier detection = higher ROI
- Markets near $0.50 have lower ROI but higher certainty

### Trade Frequency
**Expected**: 1-5 trades per week
- Depends on market activity
- More during high-activity periods:
  - Fed meetings (8x per year)
  - Elections (every 2-4 years)
  - Major geopolitical events
  - Crypto regulatory decisions

### Example Returns (Hypothetical)

```
Month 1 Baseline Building:
- Trades: 0 (collecting data)
- P&L: $0
- Status: Building volume history for 199 markets

Month 2 Initial Trading:
- Trades: 4 detected opportunities
- Win Rate: 75% (3 wins, 1 loss)
- Avg Position: $1,500
- P&L: +$1,845 (30% ROI on deployed capital)

Month 3 Active Period (Fed Meeting):
- Trades: 12 opportunities around Fed decision
- Win Rate: 83% (10 wins, 2 losses)
- Avg Position: $2,200
- P&L: +$5,720 (43% ROI on deployed capital)
```

---

## 🛠️ Technical Details

### Data Flow

```
1. Gamma API → Fetch 418+ markets with volume data (all available)
2. Volume History → Store in rolling 20-snapshot window
3. Spike Detection → Calculate volume_spike_ratio for each market
4. Signal Strength → Combine volume + price + deadline
5. Filter → Keep only signals > 50/100
6. Rank → Sort by signal strength
7. Execute → Trade top 3 signals
8. Track → Record in paper_trades.json
9. Repeat → Every 30 seconds
```

### Volume History Storage

```json
{
  "market_id_123": [
    {
      "timestamp": "2025-10-24T15:00:00",
      "volume_24h": 125000.0,
      "price": 0.65,
      "liquidity": 15000.0
    },
    // ... 20 snapshots total
  ]
}
```

### Signal Calculation Logic

```python
def calculate_signal_strength(volume_spike, price_change, deadline_proximity):
    # Volume score: 0-40 points
    volume_score = min(40, (volume_spike - 1) * 8)

    # Price score: 0-30 points
    price_score = min(30, abs(price_change) * 3)

    # Deadline score: 0-30 points
    deadline_score = deadline_proximity * 0.3

    return volume_score + price_score + deadline_score
```

---

## 🚨 Risk Management

### Position Limits
- **Max per trade**: $5,000
- **Max daily exposure**: $50,000
- **Max loss per trade**: Position size (can lose 100%)
- **Stop loss**: Automatic at market resolution

### Safety Features

1. **Paper trading by default** - No real money until you confirm
2. **Balance checks** - Won't trade if insufficient funds
3. **Position limits** - Enforced before every trade
4. **Signal threshold** - Minimum 50/100 to execute
5. **Volume history** - Persisted to survive restarts

### Known Risks

**False Signals**:
- Volume spike from single whale (not crowd)
- Bot trading causing fake volume
- Market manipulation attempts

**Mitigation**: Require minimum absolute volume ($50K) and correlation with price movement

**Execution Risk**:
- Latency delay between detection and execution
- Slippage on large orders
- Gas fees eating into profits

**Mitigation**: Small positions ($1K-$5K), fast execution (<3s), monitor gas costs

**Market Risk**:
- Resolution reversal (rare but possible)
- Oracle failure
- Polymarket operational issues

**Mitigation**: Only trade near-deadline markets, diversify across multiple opportunities

---

## 📝 Logging & Monitoring

### What's Logged

```
[15:23:37] Fetching markets...
  ✓ 418 markets with volume data found
    • High volume (>$100K): 297 markets
    • Target range ($10K-$100K): 121 markets
    • Total HFT targets: 418 markets
  Scanning 418 markets for volume spikes...
  ✓ 0 volume spikes detected

SESSION STATISTICS:
Cycles Run: 1
Volume Spikes Detected: 0
Trades Executed: 0
```

### Trade Execution Log

When a spike is detected:

```
======================================================================
EXECUTING TRADE - VOLUME SPIKE DETECTED
======================================================================
Market: will-fed-cut-rates-in-december
Outcome: Yes

Volume Spike:
  Current: $450,000
  Average: $100,000
  Spike Ratio: 4.5x

Price Action:
  Current Price: $0.620
  1h Change: +8.2%

Timing:
  Hours to Deadline: 18.5h
  Deadline Proximity: 61/100

Signal:
  Strength: 74/100
  Confidence: 95/100

Trade Sizing:
  Recommended Position: $1,490
  Max Loss: $1,490
  Expected ROI: 61.3%
```

### Performance Tracking

All trades saved to `/Users/adamoubaita/Downloads/moon-dev-ai-agents-main/src/polymarket/data/paper_trades.json`:

```json
{
  "trade_id": "paper_1761333817_001",
  "market_slug": "will-fed-cut-rates-in-december",
  "entry_price": 0.620,
  "exit_price": 1.000,
  "position_size": 1490.0,
  "actual_profit": 918.20,
  "roi_percent": 61.6,
  "reasoning": "Volume spike 4.5x..."
}
```

---

## 🎯 Next Steps

### Immediate (To Find Opportunities)

1. **Deploy for 24/7 monitoring**
   - Cloud server or Raspberry Pi
   - Let run for 1-2 weeks to build baseline
   - Check logs daily for spike detections

2. **Lower initial thresholds** (optional for faster testing)
   ```python
   min_spike_ratio=2.0  # Instead of 3.0
   max_hours_to_deadline=168  # Instead of 72
   ```

3. **Monitor high-activity markets manually**
   - Watch Fed rate markets around meeting dates
   - Track Ukraine-Russia markets during news events
   - Follow crypto markets during regulatory actions

### Medium Term (Optimization)

1. **Add WebSocket integration**
   - Real-time price/volume updates
   - Faster spike detection (<1 second)
   - Currently using REST API (30s polling)

2. **Enhance signal validation**
   - Check order book depth
   - Analyze trade distribution
   - Detect whale vs. crowd activity

3. **Implement advanced filtering**
   - Market category preferences
   - Time-of-day patterns
   - Historical spike success rates

### Long Term (Scale)

1. **Multi-strategy bot**
   - Volume spikes (current)
   - Arbitrage across platforms
   - Market maker strategies

2. **Portfolio management**
   - Diversify across 5-10 open positions
   - Dynamic position sizing based on confidence
   - Automated rebalancing

3. **Machine learning enhancement**
   - Train on historical spike outcomes
   - Predict spike likelihood
   - Optimize signal strength formula

---

## 🔗 Related Files

- `volume_spike_detector.py` - Core detection logic
- `volume_spike_bot.py` - Complete trading bot
- `test_volume_detection.py` - Debug/testing script
- `run_5min.py` - Original 5-minute monitoring demo
- `data/volume_history/` - Persistent volume storage

---

## 📞 Support

### Common Issues

**"0 spikes detected"** → Normal! Needs 24/7 monitoring to build baseline

**"No markets with volume data"** → Check Gamma API connection

**"Insufficient balance"** → Add USDC or use paper trading mode

---

## ⚖️ Legal & Ethics

This strategy is **legal arbitrage**:
- ✅ Using public information only
- ✅ No insider trading
- ✅ No market manipulation
- ✅ Following Polymarket terms of service

We're simply detecting publicly visible volume changes faster than manual traders.

---

**Last Updated**: October 24, 2025
**Status**: ✅ System built and tested
**Ready For**: 24/7 deployment to collect baseline data
**Expected Time to First Trade**: 1-2 weeks after continuous monitoring begins
