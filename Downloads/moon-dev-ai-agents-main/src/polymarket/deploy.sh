#!/bin/bash
#
# Quick Deploy Script for Polymarket Bot on DigitalOcean
#
# Usage: ./deploy.sh
#

set -e  # Exit on error

echo "============================================"
echo "  Polymarket Bot Deployment Script"
echo "============================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect if running on remote server or local
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
else
    OS="Unknown"
fi

echo -e "${GREEN}Detected OS: $OS${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Please do not run as root. Run as regular user with sudo access.${NC}"
    exit 1
fi

# Step 1: Install system dependencies
echo -e "${YELLOW}[1/7] Installing system dependencies...${NC}"
if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y python3.11 python3.11-venv python3-pip git htop tmux jq bc
else
    echo -e "${RED}apt-get not found. Please install dependencies manually.${NC}"
    exit 1
fi

# Step 2: Setup Python environment
echo -e "${YELLOW}[2/7] Setting up Python environment...${NC}"
if [ ! -d "venv" ]; then
    python3.11 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install requests websocket-client python-dotenv

# Step 3: Create directory structure
echo -e "${YELLOW}[3/7] Creating directory structure...${NC}"
mkdir -p logs
mkdir -p logs/daily_reports
mkdir -p data/volume_history

# Step 4: Create .env file if doesn't exist
echo -e "${YELLOW}[4/7] Configuring environment...${NC}"
if [ ! -f .env ]; then
    cat > .env << EOF
# Trading Mode (KEEP AS true FOR PHASE 1)
PAPER_TRADING=true

# Volume Spike Thresholds
MIN_SPIKE_RATIO=3.0
MIN_VOLUME_USD=50000
MAX_HOURS_TO_DEADLINE=72

# Logging
LOG_LEVEL=INFO
EOF
    echo -e "${GREEN}Created .env file${NC}"
else
    echo -e "${GREEN}.env file already exists${NC}"
fi

# Step 5: Setup systemd service
echo -e "${YELLOW}[5/7] Setting up systemd service...${NC}"

SERVICE_FILE="/etc/systemd/system/polymarket-bot.service"
CURRENT_DIR=$(pwd)
USER=$(whoami)

sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=Polymarket Volume Spike Trading Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$CURRENT_DIR
Environment="PATH=$CURRENT_DIR/venv/bin"
ExecStart=$CURRENT_DIR/venv/bin/python3 -u volume_spike_bot.py
Restart=always
RestartSec=10
StandardOutput=append:$CURRENT_DIR/logs/bot_stdout.log
StandardError=append:$CURRENT_DIR/logs/bot_stderr.log

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}Systemd service created${NC}"

# Reload systemd
sudo systemctl daemon-reload
sudo systemctl enable polymarket-bot

# Step 6: Setup log rotation
echo -e "${YELLOW}[6/7] Setting up log rotation...${NC}"

sudo tee /etc/logrotate.d/polymarket-bot > /dev/null << EOF
$CURRENT_DIR/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 $USER $USER
    sharedscripts
    postrotate
        systemctl reload polymarket-bot > /dev/null 2>&1 || true
    endscript
}

$CURRENT_DIR/logs/*.jsonl {
    daily
    rotate 60
    compress
    delaycompress
    notifempty
    create 0644 $USER $USER
}
EOF

echo -e "${GREEN}Log rotation configured${NC}"

# Step 7: Setup monitoring cron job
echo -e "${YELLOW}[7/7] Setting up monitoring...${NC}"

# Create monitoring script
cat > monitor.sh << 'EOF'
#!/bin/bash

LOG_DIR="$(dirname "$0")/logs"
ALERT_LOG="$LOG_DIR/alerts.log"

# Check if bot is running
if ! systemctl is-active --quiet polymarket-bot; then
    echo "[$(date)] ALERT: Bot is DOWN!" >> $ALERT_LOG
    systemctl restart polymarket-bot
fi

# Generate dashboard
cd "$(dirname "$0")"
source venv/bin/activate
python3 dashboard.py > /dev/null 2>&1
EOF

chmod +x monitor.sh

# Add to crontab (every 5 minutes)
(crontab -l 2>/dev/null | grep -v "monitor.sh"; echo "*/5 * * * * $(pwd)/monitor.sh") | crontab -

echo -e "${GREEN}Monitoring configured (runs every 5 minutes)${NC}"

# Summary
echo ""
echo "============================================"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo "============================================"
echo ""
echo "📊 Bot Status:"
echo "  Service: polymarket-bot"
echo "  Status: Enabled (not started yet)"
echo ""
echo "🚀 To Start:"
echo "  sudo systemctl start polymarket-bot"
echo ""
echo "📈 To Monitor:"
echo "  sudo systemctl status polymarket-bot"
echo "  sudo journalctl -u polymarket-bot -f"
echo "  tail -f logs/activity_*.log"
echo ""
echo "📊 Dashboard:"
echo "  ./monitor.sh  # Generate dashboard"
echo "  python3 -m http.server 8080"
echo "  Open: http://$(hostname -I | awk '{print $1}'):8080/dashboard.html"
echo ""
echo "⚙️  Configuration:"
echo "  Edit .env file to change settings"
echo ""
echo "🔍 Important Files:"
echo "  Logs: logs/"
echo "  Daily Reports: logs/daily_reports/"
echo "  Volume Data: data/volume_history/"
echo ""
echo -e "${YELLOW}⚠️  REMEMBER: This is Phase 1 (Baseline Collection)${NC}"
echo "  - Bot will run in PAPER TRADING mode"
echo "  - No real money will be used"
echo "  - It will collect baseline data for 1-2 weeks"
echo "  - Check logs daily for progress"
echo ""
echo "Ready to start? Run:"
echo -e "${GREEN}sudo systemctl start polymarket-bot${NC}"
echo ""
