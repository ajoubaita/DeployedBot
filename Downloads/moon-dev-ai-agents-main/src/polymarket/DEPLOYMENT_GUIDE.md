# 🚀 DigitalOcean Deployment Guide - Phase 1

## Pre-Deployment Checklist

- [ ] DigitalOcean droplet created (recommend: 2GB RAM, Ubuntu 22.04)
- [ ] SSH access configured
- [ ] Domain/subdomain setup (optional, for monitoring dashboard)
- [ ] Backup strategy planned

---

## 📦 Step 1: Initial Server Setup

```bash
# SSH into your droplet
ssh root@your-droplet-ip

# Update system
apt update && apt upgrade -y

# Install Python 3.11+
apt install python3.11 python3.11-venv python3-pip git -y

# Install monitoring tools
apt install htop tmux -y

# Create polymarket user (security best practice)
adduser polymarket
usermod -aG sudo polymarket

# Switch to polymarket user
su - polymarket
```

---

## 📥 Step 2: Deploy Bot Code

```bash
# Clone repository
cd ~
git clone https://github.com/yourusername/polymarket-bot.git
cd polymarket-bot/src

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install requests websocket-client python-dotenv

# Create necessary directories
mkdir -p polymarket/logs
mkdir -p polymarket/data/volume_history
mkdir -p polymarket/data/daily_reports
```

---

## ⚙️ Step 3: Configuration

```bash
# Create .env file (if needed for future live trading)
cd ~/polymarket-bot/src/polymarket
nano .env
```

Add (keep PAPER_TRADING=true for Phase 1):
```env
# Trading Mode
PAPER_TRADING=true

# Volume Spike Thresholds
MIN_SPIKE_RATIO=3.0
MIN_VOLUME_USD=50000
MAX_HOURS_TO_DEADLINE=72

# Logging
LOG_LEVEL=INFO
```

---

## 🔄 Step 4: Setup Systemd Service

Create systemd service for automatic restart:

```bash
sudo nano /etc/systemd/system/polymarket-bot.service
```

Add:
```ini
[Unit]
Description=Polymarket Volume Spike Trading Bot
After=network.target

[Service]
Type=simple
User=polymarket
WorkingDirectory=/home/polymarket/polymarket-bot/src
Environment="PATH=/home/polymarket/polymarket-bot/src/venv/bin"
ExecStart=/home/polymarket/polymarket-bot/src/venv/bin/python3 -u polymarket/volume_spike_bot.py
Restart=always
RestartSec=10
StandardOutput=append:/home/polymarket/polymarket-bot/src/polymarket/logs/bot_stdout.log
StandardError=append:/home/polymarket/polymarket-bot/src/polymarket/logs/bot_stderr.log

[Install]
WantedBy=multi-user.target
```

Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable polymarket-bot
sudo systemctl start polymarket-bot

# Check status
sudo systemctl status polymarket-bot

# View live logs
sudo journalctl -u polymarket-bot -f
```

---

## 📊 Step 5: Setup Log Rotation

Prevent logs from filling disk:

```bash
sudo nano /etc/logrotate.d/polymarket-bot
```

Add:
```
/home/polymarket/polymarket-bot/src/polymarket/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 polymarket polymarket
    sharedscripts
    postrotate
        systemctl reload polymarket-bot > /dev/null 2>&1 || true
    endscript
}

/home/polymarket/polymarket-bot/src/polymarket/logs/*.jsonl {
    daily
    rotate 60
    compress
    delaycompress
    notifempty
    create 0644 polymarket polymarket
}
```

---

## 🔍 Step 6: Monitoring & Alerts

### Option A: Simple Email Alerts

Install mailutils:
```bash
sudo apt install mailutils -y
```

Create monitoring script:
```bash
nano ~/monitor.sh
```

Add:
```bash
#!/bin/bash

LOG_FILE="/home/polymarket/polymarket-bot/src/polymarket/logs/alerts.log"
EMAIL="your-email@example.com"

# Check if bot is running
if ! systemctl is-active --quiet polymarket-bot; then
    echo "Polymarket bot is DOWN!" | mail -s "ALERT: Bot Down" $EMAIL
fi

# Check for errors in last hour
ERROR_COUNT=$(grep -c "ERROR" <(tail -n 1000 $LOG_FILE))
if [ $ERROR_COUNT -gt 10 ]; then
    echo "High error rate detected: $ERROR_COUNT errors" | mail -s "ALERT: High Error Rate" $EMAIL
fi

# Check baseline progress
LATEST_REPORT=$(ls -t /home/polymarket/polymarket-bot/src/polymarket/logs/daily_reports/*.json | head -1)
if [ -f "$LATEST_REPORT" ]; then
    COMPLETION=$(jq '.baseline_completion_pct' $LATEST_REPORT)
    if (( $(echo "$COMPLETION >= 100" | bc -l) )); then
        echo "Baseline collection complete! Ready for live trading." | mail -s "SUCCESS: Baseline Complete" $EMAIL
    fi
fi
```

Make executable and add to cron:
```bash
chmod +x ~/monitor.sh

# Run every hour
crontab -e
# Add: 0 * * * * /home/polymarket/monitor.sh
```

### Option B: Advanced Monitoring Dashboard

Create web dashboard:
```bash
nano ~/polymarket-bot/src/polymarket/dashboard.py
```

(See dashboard.py file below)

---

## 📈 Step 7: Daily Checks (What to Monitor)

### Every Morning:
```bash
# 1. Check bot status
systemctl status polymarket-bot

# 2. View latest daily report
cat $(ls -t ~/polymarket-bot/src/polymarket/logs/daily_reports/*.json | head -1) | jq

# 3. Check baseline progress
tail -50 ~/polymarket-bot/src/polymarket/logs/activity_*.log | grep "baseline"

# 4. Check for alerts
tail -50 ~/polymarket-bot/src/polymarket/logs/alerts.log

# 5. Monitor disk usage
df -h

# 6. Check memory usage
free -h
```

### Weekly:
```bash
# Review volume trends
grep "total_volume_24h" ~/polymarket-bot/src/polymarket/logs/metrics_*.jsonl | tail -100

# Check for potential spikes
grep "APPROACHING THRESHOLD" ~/polymarket-bot/src/polymarket/logs/alerts.log

# Analyze top markets
# (manual analysis of daily reports)
```

---

## 🎯 Key Metrics to Track (Phase 1)

### 1. **Baseline Collection Progress**
- **Target**: 100% completion (20 snapshots per market)
- **Timeline**: 1-2 weeks
- **Log location**: `logs/activity_YYYYMMDD.log`
- **Search for**: `"baseline_completion_pct"`

**Example log entry**:
```
2025-10-24 18:30:45 [INFO] Baseline collection progress
  avg_snapshots_per_market: 8.3
  baseline_completion_pct: 41.5%
  markets_ready_for_detection: 156
  estimated_days_to_completion: 6.2 days
```

### 2. **Market Coverage**
- **Target**: 418+ HFT targets consistently tracked
- **Log location**: `logs/activity_YYYYMMDD.log`
- **Search for**: `"Market scan complete"`

**Example log entry**:
```
2025-10-24 18:30:45 [INFO] Market scan complete
  total_markets: 499
  high_volume_count: 297
  target_range_count: 121
  total_volume_24h: $142,567,890
```

### 3. **Volume Anomalies**
- **Target**: Detect pre-spike patterns
- **Log location**: `logs/alerts.log`
- **Search for**: `"APPROACHING THRESHOLD"`

**Example log entry**:
```
2025-10-24 18:31:22 [ALERT] Volume increase detected: will-fed-cut-rates-dec
  spike_ratio: 2.8x
  status: APPROACHING THRESHOLD
```

### 4. **System Health**
- **Uptime target**: >99%
- **API error rate**: <1%
- **Cycle duration**: <5 seconds
- **Log location**: Daily reports JSON

**Example metrics**:
```json
{
  "uptime_pct": 99.8,
  "avg_cycle_duration": 3.2,
  "api_error_rate": 0.12
}
```

### 5. **Data Quality**
- **Snapshot consistency**: All markets should gain ~1 snapshot/hour
- **Volume data freshness**: No stale data >4 hours
- **Log location**: `logs/metrics_YYYYMMDD.jsonl`

---

## 🚨 Alert Thresholds

Configure alerts for these events:

| Event | Threshold | Priority | Action |
|-------|-----------|----------|--------|
| Bot Down | Service inactive | **CRITICAL** | Immediate restart |
| High Error Rate | >10 errors/hour | **HIGH** | Check API status |
| Baseline Milestone | 25%, 50%, 75%, 100% | **INFO** | Celebrate progress |
| Volume Spike Approaching | 2.5x-2.9x spike | **MEDIUM** | Monitor closely |
| Volume Spike Detected | 3.0x+ spike | **HIGH** | Ready for Phase 2 |
| Disk Usage | >80% full | **MEDIUM** | Clean old logs |
| Memory Usage | >90% | **HIGH** | Investigate leak |

---

## 📁 Log File Structure

```
logs/
├── activity_20251024.log          # Human-readable activity log
├── metrics_20251024.jsonl          # Structured metrics (JSON lines)
├── alerts.log                       # Important events only
├── bot_stdout.log                   # Systemd stdout
├── bot_stderr.log                   # Systemd stderr
└── daily_reports/
    ├── report_2025-10-24.json
    ├── report_2025-10-25.json
    └── ...
```

---

## 🔧 Troubleshooting

### Bot won't start
```bash
# Check logs
sudo journalctl -u polymarket-bot -n 100

# Test manually
cd ~/polymarket-bot/src
source venv/bin/activate
python3 polymarket/volume_spike_bot.py
```

### High memory usage
```bash
# Check process
ps aux | grep python

# Restart service
sudo systemctl restart polymarket-bot
```

### API errors
```bash
# Check connectivity
ping gamma-api.polymarket.com

# Check rate limits
grep "429" logs/bot_stderr.log
```

### Missing data
```bash
# Verify volume history
ls -lh polymarket/data/volume_history/

# Check file permissions
ls -la polymarket/data/
```

---

## 🎯 Success Criteria for Phase 1

After **2 weeks** of continuous operation, you should have:

✅ **Baseline Complete**
- 20 snapshots per market (100% completion)
- 418+ markets ready for spike detection

✅ **System Stable**
- >99% uptime
- <1% error rate
- Consistent cycle performance

✅ **Data Quality**
- No gaps in volume history
- All markets tracked consistently
- Anomalies detected and logged

✅ **Ready for Phase 2**
- First volume spikes detected
- Pattern recognition working
- Signal strength calculation validated

---

## 📞 Support Commands

```bash
# Restart bot
sudo systemctl restart polymarket-bot

# View live logs
sudo journalctl -u polymarket-bot -f

# Check baseline progress
tail -100 logs/activity_*.log | grep "baseline_completion_pct"

# Generate manual report
cd ~/polymarket-bot/src
source venv/bin/activate
python3 -c "from polymarket.production_logger import ProductionLogger; logger = ProductionLogger(); report = logger.generate_daily_report(); logger.print_daily_summary(report)"

# Check disk space
du -sh logs/
df -h

# Archive old logs
tar -czf logs_archive_$(date +%Y%m%d).tar.gz logs/*.log
rm logs/activity_202510*.log  # Clean old activity logs
```

---

## 🚀 Next Steps After Phase 1

Once baseline is complete (100%):

1. Review daily reports for patterns
2. Analyze detected anomalies
3. Validate signal strength calculations
4. Prepare for Phase 2 optimizations:
   - WebSocket integration
   - Multi-timeframe analysis
   - Order book depth
5. Test paper trading with real spike detections
6. Plan live trading deployment (if desired)

---

**Remember**: Phase 1 is about **data collection**, not trading. The goal is to build a robust baseline so Phase 2 can make informed trading decisions!
