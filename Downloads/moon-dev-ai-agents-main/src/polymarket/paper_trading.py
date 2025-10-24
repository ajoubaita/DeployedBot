"""
Polymarket Paper Trading System

Simulates trades without real money to validate the arbitrage system.
Tracks simulated P&L, win rate, and performance metrics.

Usage:
    python3 paper_trading.py

Features:
- Simulated order execution
- Position tracking
- P&L calculation
- Performance analytics
- Trade history logging
"""
import json
import time
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import os

try:
    from polymarket.gamma_client import GammaClient
    from polymarket.clob_client import ClobClient
except ImportError:
    from gamma_client import GammaClient
    from clob_client import ClobClient


@dataclass
class SimulatedTrade:
    """Represents a simulated trade."""
    trade_id: str
    timestamp: datetime
    market_id: str
    market_slug: str
    outcome: str
    entry_price: float
    position_size: float
    shares: float
    expected_payout: float
    expected_profit: float
    costs: float
    status: str  # 'open', 'closed', 'cancelled'
    exit_price: Optional[float] = None
    actual_payout: Optional[float] = None
    actual_profit: Optional[float] = None
    roi_percent: float = 0.0
    certainty_score: float = 0.0
    reasoning: str = ""


@dataclass
class TradingSession:
    """Tracks an entire paper trading session."""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    starting_balance: float = 10000.0
    current_balance: float = 10000.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit: float = 0.0
    total_costs: float = 0.0
    open_positions: List[SimulatedTrade] = None
    closed_positions: List[SimulatedTrade] = None

    def __post_init__(self):
        if self.open_positions is None:
            self.open_positions = []
        if self.closed_positions is None:
            self.closed_positions = []


class PaperTradingEngine:
    """
    Paper trading engine that simulates trade execution.
    """

    def __init__(self, starting_balance: float = 10000.0, log_file: str = None):
        """
        Initialize paper trading engine.

        Args:
            starting_balance: Starting USDC balance
            log_file: Path to save trade history (default: data/paper_trades.json)
        """
        self.session = TradingSession(
            session_id=f"paper_{int(time.time())}",
            start_time=datetime.now(),
            starting_balance=starting_balance,
            current_balance=starting_balance
        )

        # Set up logging
        if log_file is None:
            log_dir = os.path.join(os.path.dirname(__file__), 'data')
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'paper_trades.json')

        self.log_file = log_file

        print(f"{'='*70}")
        print(f"PAPER TRADING ENGINE INITIALIZED")
        print(f"{'='*70}")
        print(f"Session ID: {self.session.session_id}")
        print(f"Starting Balance: ${self.session.starting_balance:,.2f}")
        print(f"Trade Log: {self.log_file}")
        print(f"{'='*70}\n")

    def can_trade(self, position_size: float) -> bool:
        """
        Check if we have enough balance to execute trade.

        Args:
            position_size: Position size in USDC

        Returns:
            True if we can afford the trade
        """
        # Account for existing open positions
        open_exposure = sum(t.position_size for t in self.session.open_positions)
        available = self.session.current_balance - open_exposure

        return available >= position_size

    def execute_trade(self, market_id: str, market_slug: str, outcome: str,
                     entry_price: float, position_size: float, expected_roi: float,
                     confidence: float, reasoning: str) -> Optional[SimulatedTrade]:
        """
        Execute a simulated trade (volume spike compatible).

        Args:
            market_id: Market identifier
            market_slug: Human-readable market name
            outcome: YES/NO
            entry_price: Entry price for position
            position_size: Size in USDC
            expected_roi: Expected return on investment percentage
            confidence: Confidence score (0-100)
            reasoning: Why we're taking this trade

        Returns:
            SimulatedTrade if successful, None if insufficient balance
        """
        if not self.can_trade(position_size):
            print(f"  ✗ Insufficient balance for ${position_size:,.2f} trade")
            return None

        # Calculate shares and expected profit
        shares = position_size / entry_price
        expected_profit = position_size * (expected_roi / 100)
        costs = position_size * 0.02  # 2% vig

        # Create simulated trade
        trade = SimulatedTrade(
            trade_id=f"paper_{int(time.time())}_{len(self.session.open_positions) + 1}",
            timestamp=datetime.now(),
            market_id=market_id,
            market_slug=market_slug,
            outcome=outcome,
            entry_price=entry_price,
            position_size=position_size,
            shares=shares,
            expected_payout=shares * 1.0,  # Assume resolves to $1
            expected_profit=expected_profit - costs,
            costs=costs,
            status='open',
            roi_percent=expected_roi,
            certainty_score=confidence / 100.0,
            reasoning=reasoning
        )

        # Add to open positions
        self.session.open_positions.append(trade)
        self.session.total_trades += 1

        print(f"\n{'='*70}")
        print(f"📝 SIMULATED TRADE ENTRY")
        print(f"{'='*70}")
        print(f"Trade ID: {trade.trade_id}")
        print(f"Market: {trade.market_slug[:60]}")
        print(f"Outcome: {trade.outcome}")
        print(f"Entry Price: ${trade.entry_price:.3f}")
        print(f"Position Size: ${trade.position_size:,.2f}")
        print(f"Shares: {trade.shares:,.2f}")
        print(f"Expected Profit: ${trade.expected_profit:,.2f}")
        print(f"Expected ROI: {trade.roi_percent:.1f}%")
        print(f"Confidence: {trade.certainty_score * 100:.0f}%")
        print(f"Reasoning: {trade.reasoning}")
        print(f"{'='*70}\n")

        # Save trade log
        self._save_log()

        return trade

    def simulate_trade_exit(self, trade: SimulatedTrade, exit_price: float = 1.0, reason: str = "Market resolved"):
        """
        Simulate closing a trade.

        Args:
            trade: The trade to close
            exit_price: Exit price (default 1.0 for resolved markets)
            reason: Reason for closing
        """
        # Calculate actual payout
        actual_payout = trade.shares * exit_price
        actual_profit = actual_payout - trade.position_size - trade.costs

        # Update trade
        trade.exit_price = exit_price
        trade.actual_payout = actual_payout
        trade.actual_profit = actual_profit
        trade.status = 'closed'

        # Update session stats
        self.session.current_balance += actual_profit
        self.session.total_profit += actual_profit
        self.session.total_costs += trade.costs

        if actual_profit > 0:
            self.session.winning_trades += 1
        else:
            self.session.losing_trades += 1

        # Move to closed positions
        self.session.open_positions.remove(trade)
        self.session.closed_positions.append(trade)

        print(f"\n{'='*70}")
        print(f"✅ SIMULATED TRADE EXIT")
        print(f"{'='*70}")
        print(f"Trade ID: {trade.trade_id}")
        print(f"Market: {trade.market_slug[:60]}")
        print(f"Exit Price: ${exit_price:.3f}")
        print(f"Actual Payout: ${actual_payout:,.2f}")
        print(f"Actual Profit: ${actual_profit:,.2f}")
        print(f"ROI: {(actual_profit / trade.position_size) * 100:.1f}%")
        print(f"Reason: {reason}")
        print(f"\nUpdated Balance: ${self.session.current_balance:,.2f}")
        print(f"Session P&L: ${self.session.total_profit:,.2f}")
        print(f"{'='*70}\n")

        # Save trade log
        self._save_log()

    def simulate_auto_resolve(self):
        """
        Automatically resolve open positions based on certainty.

        For paper trading, we assume certain outcomes (certainty >= 0.95) resolve
        to the expected outcome (price = 1.0), while uncertain outcomes may vary.
        """
        if not self.session.open_positions:
            return

        print(f"\n{'='*70}")
        print(f"AUTO-RESOLVING OPEN POSITIONS")
        print(f"{'='*70}\n")

        # Simulate resolution for high-certainty trades
        for trade in list(self.session.open_positions):
            if trade.certainty_score >= 0.95:
                # High certainty = resolves as expected
                self.simulate_trade_exit(trade, exit_price=1.0, reason="Certain outcome resolved")
            else:
                # Lower certainty = might not resolve favorably
                # Simulate with 70% success rate
                import random
                if random.random() < 0.70:
                    self.simulate_trade_exit(trade, exit_price=1.0, reason="Trade won (simulated)")
                else:
                    self.simulate_trade_exit(trade, exit_price=0.0, reason="Trade lost (simulated)")

    def get_performance_summary(self) -> Dict:
        """
        Get performance summary statistics.

        Returns:
            Dict with performance metrics
        """
        total_trades = self.session.winning_trades + self.session.losing_trades
        win_rate = (self.session.winning_trades / total_trades * 100) if total_trades > 0 else 0

        avg_profit = (self.session.total_profit / total_trades) if total_trades > 0 else 0

        roi = ((self.session.current_balance - self.session.starting_balance) /
               self.session.starting_balance * 100)

        return {
            'session_id': self.session.session_id,
            'starting_balance': self.session.starting_balance,
            'current_balance': self.session.current_balance,
            'total_profit': self.session.total_profit,
            'total_costs': self.session.total_costs,
            'total_trades': total_trades,
            'open_trades': len(self.session.open_positions),
            'winning_trades': self.session.winning_trades,
            'losing_trades': self.session.losing_trades,
            'win_rate': win_rate,
            'avg_profit_per_trade': avg_profit,
            'session_roi': roi,
            'duration': (datetime.now() - self.session.start_time).total_seconds()
        }

    def print_performance(self):
        """Print performance summary."""
        stats = self.get_performance_summary()

        print(f"\n{'='*70}")
        print(f"PERFORMANCE SUMMARY")
        print(f"{'='*70}")
        print(f"Session ID: {stats['session_id']}")
        print(f"Duration: {stats['duration']/60:.1f} minutes")
        print(f"\nBalance:")
        print(f"  Starting: ${stats['starting_balance']:,.2f}")
        print(f"  Current:  ${stats['current_balance']:,.2f}")
        print(f"  P&L:      ${stats['total_profit']:,.2f}")
        print(f"  ROI:      {stats['session_roi']:.1f}%")
        print(f"\nTrades:")
        print(f"  Total:    {stats['total_trades']}")
        print(f"  Open:     {stats['open_trades']}")
        print(f"  Winners:  {stats['winning_trades']}")
        print(f"  Losers:   {stats['losing_trades']}")
        print(f"  Win Rate: {stats['win_rate']:.1f}%")
        print(f"\nProfitability:")
        print(f"  Total Profit: ${stats['total_profit']:,.2f}")
        print(f"  Total Costs:  ${stats['total_costs']:,.2f}")
        print(f"  Avg Profit:   ${stats['avg_profit_per_trade']:,.2f}")
        print(f"{'='*70}\n")

    def _save_log(self):
        """Save trade log to file."""
        try:
            # Convert to JSON-serializable format
            log_data = {
                'session': {
                    'session_id': self.session.session_id,
                    'start_time': self.session.start_time.isoformat(),
                    'starting_balance': self.session.starting_balance,
                    'current_balance': self.session.current_balance,
                    'total_trades': self.session.total_trades,
                    'winning_trades': self.session.winning_trades,
                    'losing_trades': self.session.losing_trades,
                    'total_profit': self.session.total_profit,
                },
                'open_positions': [self._trade_to_dict(t) for t in self.session.open_positions],
                'closed_positions': [self._trade_to_dict(t) for t in self.session.closed_positions]
            }

            with open(self.log_file, 'w') as f:
                json.dump(log_data, f, indent=2)

        except Exception as e:
            print(f"Warning: Could not save trade log: {e}")

    def _trade_to_dict(self, trade: SimulatedTrade) -> Dict:
        """Convert trade to dict for JSON serialization."""
        d = asdict(trade)
        d['timestamp'] = trade.timestamp.isoformat()
        return d


