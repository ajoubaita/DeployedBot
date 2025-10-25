# 🚀 Quick Reference Card

## Server Info
- **IP**: 159.65.180.152
- **SSH**: `ssh -i ~/.ssh/polymarket_deploy root@159.65.180.152`
- **User**: polymarket
- **Location**: /home/polymarket/polymarket/

---

## Essential Commands

### Check Status
```bash
ssh -i ~/.ssh/polymarket_deploy root@159.65.180.152 'systemctl status polymarket-bot'
```

### View Live Activity
```bash
ssh -i ~/.ssh/polymarket_deploy root@159.65.180.152 'tail -f /home/polymarket/polymarket/logs/bot_stdout.log'
```

### Restart Bot
```bash
ssh -i ~/.ssh/polymarket_deploy root@159.65.180.152 'systemctl restart polymarket-bot'
```

### Check Health
```bash
ssh -i ~/.ssh/polymarket_deploy root@159.65.180.152 'systemctl status polymarket-bot && tail -20 /home/polymarket/polymarket/logs/bot_stdout.log'
```

---

## What to Expect

### Phase 1 (Current): Baseline Collection
- **Duration**: 1-2 weeks
- **Goal**: Collect 20 volume snapshots per market
- **Markets**: 499 total (418 HFT targets)
- **Scans**: Every 30 seconds
- **Mode**: Paper trading (no real money)

### Daily Progress
- Day 1: 5-10% complete
- Day 7: 35-50% complete
- Day 14: 70-100% complete ✅

---

## Key Files

### Logs
- `/home/polymarket/polymarket/logs/bot_stdout.log` - Main output
- `/home/polymarket/polymarket/logs/bot_stderr.log` - Errors

### Data
- `/home/polymarket/polymarket/data/volume_history/volume_history.json` - Baseline
- `/home/polymarket/polymarket/data/paper_trades.json` - Simulated trades

---

## Monitoring Checklist

### Daily (30 seconds)
- [ ] Bot running? `systemctl status polymarket-bot`
- [ ] No errors? `tail /home/polymarket/polymarket/logs/bot_stderr.log`
- [ ] Markets scanned? `grep "markets found" /home/polymarket/polymarket/logs/bot_stdout.log | tail -1`

### Weekly (5 minutes)
- [ ] Volume history growing? `ls -lh /home/polymarket/polymarket/data/volume_history/`
- [ ] Any spikes detected? `grep "spikes detected" /home/polymarket/polymarket/logs/bot_stdout.log`
- [ ] Disk space OK? `ssh -i ~/.ssh/polymarket_deploy root@159.65.180.152 'df -h'`

---

## Current Status

**Deployed**: October 25, 2025
**Running**: ✅ Yes
**Markets**: 499 (418 HFT targets)
**Mode**: Paper Trading
**Next Milestone**: 50% baseline (Week 1-2)

---

## Emergency Commands

### Bot Crashed
```bash
ssh -i ~/.ssh/polymarket_deploy root@159.65.180.152 'journalctl -u polymarket-bot -n 100'
ssh -i ~/.ssh/polymarket_deploy root@159.65.180.152 'systemctl restart polymarket-bot'
```

### Out of Memory
```bash
ssh -i ~/.ssh/polymarket_deploy root@159.65.180.152 'free -h && systemctl restart polymarket-bot'
```

### Disk Full
```bash
ssh -i ~/.ssh/polymarket_deploy root@159.65.180.152 'df -h && find /home/polymarket/polymarket/logs -name "*.log" -mtime +30 -delete'
```

---

## Resources

- **Full Guide**: DEPLOYMENT_COMPLETE.md
- **Deployment Steps**: DEPLOYMENT_GUIDE.md
- **Phase 1 Details**: PHASE1_QUICK_START.md
- **Strategy Docs**: VOLUME_SPIKE_STRATEGY.md

---

**Remember**: Paper trading only. No real money at risk! 🎓
