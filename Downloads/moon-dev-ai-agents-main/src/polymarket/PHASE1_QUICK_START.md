# 🚀 Phase 1 Quick Start - DigitalOcean Deployment

## TL;DR - Deploy in 5 Minutes

```bash
# On your DigitalOcean droplet:
ssh root@your-droplet-ip

# Create user
adduser polymarket
usermod -aG sudo polymarket
su - polymarket

# Clone & deploy
git clone https://github.com/yourusername/polymarket-bot.git
cd polymarket-bot/src/polymarket
./deploy.sh

# Start bot
sudo systemctl start polymarket-bot

# Monitor
sudo journalctl -u polymarket-bot -f
```

---

## 📊 Key Metrics You'll See

### 1. **Baseline Progress** (Most Important)
```
Target: 100% (20 snapshots per market)
Timeline: 1-2 weeks
Location: logs/activity_YYYYMMDD.log

Example:
  baseline_completion_pct: 41.5%
  markets_ready_for_detection: 156
  estimated_days_to_completion: 6.2 days
```

### 2. **Market Coverage**
```
Target: 418+ HFT targets
Location: logs/activity_YYYYMMDD.log

Example:
  total_markets: 499
  high_volume_count: 297
  target_range_count: 121
```

### 3. **Volume Anomalies** (Watch Closely!)
```
Location: logs/alerts.log

Example:
  Volume increase detected: will-fed-cut-rates-dec
  spike_ratio: 2.8x
  status: APPROACHING THRESHOLD
```

### 4. **System Health**
```
Target: >99% uptime, <1% errors
Location: logs/daily_reports/

Example:
  uptime_pct: 99.8
  avg_cycle_duration: 3.2s
  api_error_rate: 0.12%
```

---

## 🎯 Daily Monitoring Commands

### Morning Check (30 seconds)
```bash
# 1. Bot status
sudo systemctl status polymarket-bot

# 2. Latest progress
tail -20 ~/polymarket-bot/src/polymarket/logs/activity_*.log | grep "baseline_completion"

# 3. Any alerts?
tail -10 ~/polymarket-bot/src/polymarket/logs/alerts.log

# 4. Generate dashboard
cd ~/polymarket-bot/src/polymarket
./monitor.sh
```

### View Dashboard
```bash
# Start web server
cd ~/polymarket-bot/src/polymarket
python3 -m http.server 8080

# Open in browser:
# http://your-droplet-ip:8080/dashboard.html
```

---

## 📈 What Logs Tell You

### Good Signs ✅
```
[INFO] Baseline collection progress
  baseline_completion_pct: 75.0%  ← Progressing nicely
  markets_ready_for_detection: 380  ← Most markets ready
  estimated_days_to_completion: 2.1 days  ← Almost done

[INFO] Market scan complete
  total_markets: 499  ← All markets tracked
  total_volume_24h: $142,567,890  ← Healthy volume

[INFO] System health: uptime_pct: 99.8  ← Stable
```

### Warning Signs ⚠️
```
[ALERT] Volume increase detected
  spike_ratio: 2.8x  ← Watch this market!
  status: APPROACHING THRESHOLD  ← Might spike soon

[ERROR] API request failed  ← Occasional is OK
  (If frequent, check network)

baseline_completion_pct: 15.0%  ← After 1 week
  (Should be ~50% after 1 week)
```

### Bad Signs ❌
```
[ALERT] Bot is DOWN!  ← Immediate action needed

[ERROR] API error rate: 15.2%  ← Too high

baseline_completion_pct: 5.0%  ← After 3 days
  (Should be ~15% after 3 days)
```

---

## 🔍 File Structure

```
polymarket/
├── logs/
│   ├── activity_20251024.log      ← Human-readable log
│   ├── metrics_20251024.jsonl     ← Structured data
│   ├── alerts.log                 ← Important events
│   ├── bot_stdout.log             ← System output
│   ├── bot_stderr.log             ← Errors
│   └── daily_reports/
│       └── report_2025-10-24.json ← Daily summary
├── data/
│   └── volume_history/
│       └── volume_history.json    ← Baseline data
├── dashboard.html                  ← Monitoring dashboard
└── .env                            ← Configuration
```

---

## 📊 Expected Timeline

### Week 1
```
Day 1:  Baseline: 5-10%   | Markets Ready: 50-100
Day 2:  Baseline: 10-15%  | Markets Ready: 100-150
Day 3:  Baseline: 15-20%  | Markets Ready: 150-200
Day 7:  Baseline: 35-50%  | Markets Ready: 300-350
```

### Week 2
```
Day 8:  Baseline: 40-55%  | Markets Ready: 350-380
Day 10: Baseline: 50-65%  | Markets Ready: 380-400
Day 14: Baseline: 70-100% | Markets Ready: 400-418

✅ READY FOR PHASE 2
```

---

## 🚨 Alert Thresholds

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| Baseline Progress (Week 1) | 35-50% | 20-35% | <20% |
| Baseline Progress (Week 2) | 70-100% | 50-70% | <50% |
| Uptime | >99% | 95-99% | <95% |
| Error Rate | <1% | 1-5% | >5% |
| Cycle Duration | <5s | 5-10s | >10s |
| Volume Spikes Approaching | Good! | Monitor | Trade Soon! |

---

## 💡 Pro Tips

### 1. **Check Logs Locations First**
```bash
# Find your logs
ls -lh ~/polymarket-bot/src/polymarket/logs/

# Watch live activity
tail -f ~/polymarket-bot/src/polymarket/logs/activity_*.log
```

### 2. **Use Dashboard for Quick Overview**
```bash
# Generate dashboard every 5 mins (auto via cron)
# Just open: http://your-droplet-ip:8080/dashboard.html
```

### 3. **Monitor Disk Space**
```bash
# Check weekly
du -sh ~/polymarket-bot/src/polymarket/logs/
df -h

# Clean old logs if needed (after backing up)
cd ~/polymarket-bot/src/polymarket/logs/
tar -czf archive_$(date +%Y%m%d).tar.gz activity_202510*.log
rm activity_202510*.log
```

### 4. **Track Volume Anomalies**
```bash
# These are your future trades!
grep "APPROACHING THRESHOLD" logs/alerts.log

# Watch specific market
grep "will-fed-cut-rates" logs/metrics_*.jsonl | tail -20
```

### 5. **Daily Report Analysis**
```bash
# View latest report
cat $(ls -t logs/daily_reports/*.json | head -1) | jq .

# Track progress over time
for report in logs/daily_reports/*.json; do
  echo -n "$(basename $report): "
  jq -r '.baseline_completion_pct' $report
done
```

---

## 🎯 Success Checklist

After **2 weeks** you should have:

- [ ] **Baseline 100% complete** (20 snapshots/market)
- [ ] **418 markets ready** for spike detection
- [ ] **>99% uptime** (stable operation)
- [ ] **<1% error rate** (healthy API)
- [ ] **Volume anomalies detected** (patterns identified)
- [ ] **Daily reports generated** (all 14 days)
- [ ] **Dashboard accessible** (monitoring working)

---

## 🆘 Quick Troubleshooting

### Bot Not Starting
```bash
# Check logs
sudo journalctl -u polymarket-bot -n 50

# Test manually
cd ~/polymarket-bot/src/polymarket
source venv/bin/activate
python3 volume_spike_bot.py
```

### No Baseline Progress
```bash
# Check data directory
ls -lh data/volume_history/

# Verify API access
curl -I https://gamma-api.polymarket.com/markets

# Check for errors
grep "ERROR" logs/bot_stderr.log | tail -20
```

### Dashboard Not Loading
```bash
# Regenerate
cd ~/polymarket-bot/src/polymarket
source venv/bin/activate
python3 dashboard.py

# Start server
python3 -m http.server 8080
```

---

## 📞 Commands Cheat Sheet

```bash
# Start/Stop/Restart
sudo systemctl start polymarket-bot
sudo systemctl stop polymarket-bot
sudo systemctl restart polymarket-bot

# Status
sudo systemctl status polymarket-bot

# Live logs
sudo journalctl -u polymarket-bot -f
tail -f logs/activity_*.log

# Check progress
tail -50 logs/activity_*.log | grep "baseline_completion_pct"

# View latest report
cat $(ls -t logs/daily_reports/*.json | head -1) | jq .

# Generate dashboard
./monitor.sh

# View alerts
tail -50 logs/alerts.log

# Check disk
df -h
du -sh logs/
```

---

## 🎉 Next Steps After Phase 1

Once baseline reaches **100%**:

1. **Review Performance**
   - Analyze detected anomalies
   - Validate signal calculations
   - Check false positive rate

2. **Prepare for Phase 2**
   - Implement WebSocket (30x faster)
   - Add multi-timeframe analysis
   - Integrate order book depth

3. **Test Paper Trading**
   - Verify trades execute correctly
   - Track simulated P&L
   - Optimize position sizing

4. **Plan Live Trading** (Optional)
   - Fund wallet with small amount
   - Test with minimal positions
   - Scale gradually based on results

---

**Remember**: Phase 1 is all about **reliable data collection**. Patience now = profitable trades later! 🚀

**Need Help?**
- Check logs first: `logs/alerts.log`
- View daily reports: `logs/daily_reports/`
- Monitor dashboard: `http://your-droplet-ip:8080/dashboard.html`
