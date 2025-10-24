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
    from polymarket.arbitrage_detector import ArbitrageDetector, ArbitrageOpportunity
    from polymarket.agent_integration import AgentIntegrator
except ImportError:
    from gamma_client import GammaClient
    from clob_client import ClobClient
    from arbitrage_detector import ArbitrageDetector, ArbitrageOpportunity
    from agent_integration import AgentIntegrator


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

    def simulate_trade_entry(self, opportunity: ArbitrageOpportunity) -> Optional[SimulatedTrade]:
        """
        Simulate entering a trade.

        Args:
            opportunity: The arbitrage opportunity

        Returns:
            SimulatedTrade if successful, None if insufficient balance
        """
        if not self.can_trade(opportunity.position_size_usd):
            print(f"  ✗ Insufficient balance for ${opportunity.position_size_usd:,.2f} trade")
            return None

        # Create simulated trade
        trade = SimulatedTrade(
            trade_id=f"trade_{len(self.session.open_positions) + len(self.session.closed_positions) + 1}",
            timestamp=datetime.now(),
            market_id=opportunity.market_id,
            market_slug=opportunity.market_slug,
            outcome=opportunity.outcome,
            entry_price=opportunity.current_price,
            position_size=opportunity.position_size_usd,
            shares=opportunity.position_size_usd / opportunity.current_price,
            expected_payout=opportunity.expected_payout,
            expected_profit=opportunity.net_profit,
            costs=opportunity.vig_cost + opportunity.gas_cost,
            status='open',
            roi_percent=opportunity.roi_percent,
            certainty_score=opportunity.certainty_score,
            reasoning=opportunity.reasoning
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
        print(f"Certainty: {trade.certainty_score * 100:.0f}%")
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


class PaperTradingMonitor:
    """
    Combines arbitrage detection with paper trading execution.
    """

    def __init__(self, starting_balance: float = 10000.0):
        """
        Initialize paper trading monitor.

        Args:
            starting_balance: Starting USDC balance
        """
        self.gamma = GammaClient()
        self.clob = ClobClient()
        self.detector = ArbitrageDetector()
        self.integrator = AgentIntegrator()
        self.engine = PaperTradingEngine(starting_balance=starting_balance)

        self.check_count = 0

    def run_check_cycle(self):
        """Run a single monitoring and trading cycle."""
        self.check_count += 1

        print(f"\n{'='*70}")
        print(f"PAPER TRADING CHECK #{self.check_count} - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*70}\n")

        try:
            # 1. Fetch markets
            print("Fetching markets...")
            clob_markets = self.clob.get_simplified_markets()

            # Filter for open markets
            open_markets = [
                m for m in clob_markets
                if not m.get('closed') and not m.get('archived')
            ]

            print(f"  ✓ Found {len(open_markets)} open markets\n")

            if not open_markets:
                print("No open markets available\n")
                return

            # Limit for performance
            open_markets = open_markets[:50]

            # 2. Scan for opportunities (using mock certainty for now)
            print("Scanning for arbitrage opportunities...")
            opportunities = []

            for market in open_markets:
                tokens = market.get('tokens', [])
                if len(tokens) != 2:
                    continue

                # Add mock data
                market['volume'] = 50000
                market['liquidity'] = 15000
                market['slug'] = market.get('question', 'unknown-market')[:60]

                # Look for extreme prices (potential opportunities)
                for token in tokens:
                    price = token.get('price', 0.5)
                    outcome = token.get('outcome', '')

                    # Only consider if price suggests opportunity
                    if 'yes' in outcome.lower() and 0.50 <= price <= 0.75:
                        # Mock certainty (in production, this comes from event detection)
                        certainty_info = {
                            'type': 'mock',
                            'game_status': 'SIMULATED',
                            'source': 'Paper Trading Test'
                        }

                        opp = self.detector.detect_opportunity(
                            market=market,
                            event_outcome=outcome,
                            event_timestamp=datetime.now(),
                            certainty_info=certainty_info
                        )

                        if opp and opp.roi_percent >= 20:
                            opportunities.append(opp)

            print(f"  ✓ Found {len(opportunities)} potential opportunities\n")

            if not opportunities:
                print("No opportunities meet criteria\n")
                return

            # 3. Validate with AI agents
            print("Validating with AI agents...")
            validated = self.integrator.validate_multiple_opportunities(
                opportunities,
                max_to_approve=3  # Max 3 trades per cycle
            )

            print(f"  ✓ {len(validated)} opportunities approved\n")

            # 4. Execute paper trades
            for v in validated:
                if self.engine.can_trade(v.opportunity.position_size_usd):
                    self.engine.simulate_trade_entry(v.opportunity)
                else:
                    print(f"  ⚠ Skipping trade - insufficient balance")

        except Exception as e:
            print(f"Error in check cycle: {e}")
            import traceback
            traceback.print_exc()

    def run(self, num_cycles: int = 5, delay_seconds: int = 10):
        """
        Run paper trading for multiple cycles.

        Args:
            num_cycles: Number of check cycles to run
            delay_seconds: Seconds between cycles
        """
        print(f"\n{'='*70}")
        print(f"STARTING PAPER TRADING SESSION")
        print(f"{'='*70}")
        print(f"Cycles: {num_cycles}")
        print(f"Delay: {delay_seconds}s between cycles")
        print(f"Starting Balance: ${self.engine.session.starting_balance:,.2f}")
        print(f"{'='*70}\n")

        try:
            for i in range(num_cycles):
                self.run_check_cycle()

                # Show current status
                self.engine.print_performance()

                if i < num_cycles - 1:
                    print(f"Waiting {delay_seconds}s before next check...\n")
                    time.sleep(delay_seconds)

            # Auto-resolve any open positions at end
            if self.engine.session.open_positions:
                print(f"\nSession ending, resolving {len(self.engine.session.open_positions)} open positions...")
                self.engine.simulate_auto_resolve()

            # Final summary
            print(f"\n{'='*70}")
            print(f"PAPER TRADING SESSION COMPLETE")
            print(f"{'='*70}\n")
            self.engine.print_performance()

            print(f"Trade log saved to: {self.engine.log_file}\n")

        except KeyboardInterrupt:
            print(f"\n\nSession interrupted by user")
            self.engine.print_performance()


def main():
    """Run paper trading session."""
    print("\n" + "="*70)
    print("  POLYMARKET PAPER TRADING SYSTEM")
    print("="*70)
    print("\nThis simulates trades without real money to test the system.")
    print("Starting balance: $10,000 (simulated)")
    print("\nThe system will:")
    print("  1. Monitor real Polymarket markets")
    print("  2. Detect arbitrage opportunities")
    print("  3. Validate with AI agents")
    print("  4. Execute simulated trades")
    print("  5. Track P&L and performance")
    print("\nPress Ctrl+C to stop early")
    print("="*70 + "\n")

    # Create monitor
    monitor = PaperTradingMonitor(starting_balance=10000.0)

    # Run for 5 cycles (about 1 minute)
    monitor.run(num_cycles=5, delay_seconds=10)


if __name__ == '__main__':
    main()
