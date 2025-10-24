"""
Volume Spike Trading Bot for Polymarket

Strategy: Detect and trade on volume spikes that signal imminent resolution
- Monitor 199+ open markets continuously
- Track volume history and detect 3x-5x spikes
- Execute within seconds of spike detection
- Target markets near deadline for higher certainty

This is latency arbitrage - beating the crowd to the trade.
"""
import time
import os
from datetime import datetime, timedelta
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

try:
    from polymarket.gamma_client import GammaClient
    from polymarket.clob_client import ClobClient
    from polymarket.volume_spike_detector import VolumeSpikeDetector, VolumeSpike
    from polymarket.paper_trading import PaperTradingEngine
    from polymarket.authenticated_trader import AuthenticatedTrader
except ImportError:
    from gamma_client import GammaClient
    from clob_client import ClobClient
    from volume_spike_detector import VolumeSpikeDetector, VolumeSpike
    from paper_trading import PaperTradingEngine
    from authenticated_trader import AuthenticatedTrader


class VolumeSpikeBot:
    """
    Complete volume spike trading bot.

    Continuously monitors markets for volume spikes and executes trades
    when strong signals are detected.
    """

    def __init__(self,
                 paper_trading: bool = True,
                 min_spike_ratio: float = 3.0,
                 min_volume_usd: float = 50000,
                 max_hours_to_deadline: float = 72,
                 check_interval: int = 30):
        """
        Initialize volume spike bot.

        Args:
            paper_trading: If True, simulate trades
            min_spike_ratio: Minimum volume spike to trade (e.g., 3.0 = 3x)
            min_volume_usd: Minimum absolute volume
            max_hours_to_deadline: Only trade markets within N hours of deadline
            check_interval: Seconds between market scans
        """
        self.paper_trading = paper_trading
        self.check_interval = check_interval

        print(f"\n{'='*70}")
        print(f"VOLUME SPIKE BOT INITIALIZING")
        print(f"{'='*70}\n")

        # Initialize components
        self.gamma = GammaClient()
        self.clob = ClobClient()

        self.detector = VolumeSpikeDetector(
            min_spike_ratio=min_spike_ratio,
            min_volume_usd=min_volume_usd,
            max_hours_to_deadline=max_hours_to_deadline,
            history_window=20
        )

        # Trading engine
        if paper_trading:
            self.trader = PaperTradingEngine(starting_balance=10000.0)
            print(f"✓ Paper trading engine initialized\n")
        else:
            self.trader = AuthenticatedTrader(paper_trading=False)
            print(f"✓ Authenticated trader initialized\n")

        # Stats
        self.check_count = 0
        self.spikes_detected = 0
        self.trades_executed = 0

        print(f"{'='*70}")
        print(f"BOT CONFIGURATION")
        print(f"{'='*70}")
        print(f"Mode: {'PAPER TRADING' if paper_trading else '⚠️  LIVE TRADING'}")
        print(f"Min Spike Ratio: {min_spike_ratio}x")
        print(f"Min Volume: ${min_volume_usd:,.0f}")
        print(f"Max Hours to Deadline: {max_hours_to_deadline}h")
        print(f"Check Interval: {check_interval}s")
        print(f"{'='*70}\n")

    def fetch_markets(self) -> List[Dict]:
        """
        Fetch active markets with volume data.

        Returns:
            List of markets ready for scanning
        """
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching markets...")

        # Get ALL open markets from Gamma (for high-frequency trading)
        markets = self.gamma.filter_markets(
            active_only=True,
            open_only=True,
            limit=10000  # Get all markets for HFT
        )

        # Filter for markets with volume data
        markets_with_volume = [
            m for m in markets
            if m.get('volume') is not None and m.get('volume') > 0
        ]

        # Categorize by volume tier for HFT optimization
        high_volume = [m for m in markets_with_volume if m.get('volume', 0) > 100000]
        target_range = [m for m in markets_with_volume if 10000 <= m.get('volume', 0) <= 100000]

        print(f"  ✓ {len(markets_with_volume)} markets with volume data found")
        print(f"    • High volume (>$100K): {len(high_volume)} markets")
        print(f"    • Target range ($10K-$100K): {len(target_range)} markets")
        print(f"    • Total HFT targets: {len(high_volume) + len(target_range)} markets")

        return markets_with_volume

    def scan_for_spikes(self, markets: List[Dict]) -> List[VolumeSpike]:
        """
        Scan markets for volume spikes.

        Args:
            markets: List of markets to scan

        Returns:
            List of detected volume spikes
        """
        print(f"  Scanning {len(markets)} markets for volume spikes...")

        spikes = self.detector.detect_spikes(markets)

        print(f"  ✓ {len(spikes)} volume spikes detected\n")

        return spikes

    def execute_trades(self, spikes: List[VolumeSpike]) -> int:
        """
        Execute trades for detected spikes.

        Args:
            spikes: List of volume spike opportunities

        Returns:
            Number of trades executed
        """
        if not spikes:
            return 0

        executed = 0

        # Take top 3 strongest signals
        top_spikes = spikes[:3]

        for spike in top_spikes:
            print(f"\n{'='*70}")
            print(f"EXECUTING TRADE - VOLUME SPIKE DETECTED")
            print(f"{'='*70}")
            print(f"Market: {spike.market_slug[:65]}")
            print(f"Outcome: {spike.outcome}")
            print(f"\nVolume Spike:")
            print(f"  Current: ${spike.current_volume_24h:,.0f}")
            print(f"  Average: ${spike.avg_volume_24h:,.0f}")
            print(f"  Spike Ratio: {spike.volume_spike_ratio:.1f}x")
            print(f"\nPrice Action:")
            print(f"  Current Price: ${spike.current_price:.3f}")
            print(f"  1h Change: {spike.price_change_1h:+.1f}%")
            print(f"\nTiming:")
            print(f"  Hours to Deadline: {spike.hours_to_deadline:.1f}h")
            print(f"  Deadline Proximity: {spike.deadline_proximity_score:.0f}/100")
            print(f"\nSignal:")
            print(f"  Strength: {spike.signal_strength:.0f}/100")
            print(f"  Confidence: {spike.confidence:.0f}/100")
            print(f"\nTrade Sizing:")
            print(f"  Recommended Position: ${spike.recommended_position_usd:,.0f}")
            print(f"  Max Loss: ${spike.max_loss_usd:,.0f}")
            print(f"  Expected ROI: {spike.expected_roi_percent:.1f}%")
            print(f"\nReasoning: {spike.reasoning}")
            print(f"{'='*70}\n")

            try:
                if self.paper_trading:
                    # Execute paper trade directly (no ArbitrageOpportunity needed)
                    trade = self.trader.execute_trade(
                        market_id=spike.market_id,
                        market_slug=spike.market_slug,
                        outcome=spike.outcome,
                        entry_price=spike.current_price,
                        position_size=spike.recommended_position_usd,
                        expected_roi=spike.expected_roi_percent,
                        confidence=spike.confidence,
                        reasoning=spike.reasoning
                    )
                    if trade:
                        executed += 1
                else:
                    # Live trading
                    # TODO: Implement authenticated trade execution
                    print("⚠️  Live trading not yet implemented for volume spikes")
                    print("Would execute trade here...")

            except Exception as e:
                print(f"✗ Trade execution failed: {e}")
                import traceback
                traceback.print_exc()

        return executed

    def run_cycle(self):
        """Run a single monitoring and trading cycle."""
        self.check_count += 1

        print(f"\n{'='*70}")
        print(f"CYCLE #{self.check_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")

        try:
            # 1. Fetch markets with volume data
            markets = self.fetch_markets()

            if not markets:
                print("No markets available\n")
                return

            # 2. Scan for volume spikes
            spikes = self.scan_for_spikes(markets)
            self.spikes_detected += len(spikes)

            if not spikes:
                print("No volume spikes detected this cycle\n")
                return

            # 3. Execute trades for top signals
            executed = self.execute_trades(spikes)
            self.trades_executed += executed

            print(f"\n✓ Executed {executed} trades this cycle\n")

        except Exception as e:
            print(f"\n✗ Error in cycle: {e}")
            import traceback
            traceback.print_exc()

    def print_session_stats(self):
        """Print session statistics."""
        print(f"\n{'='*70}")
        print(f"SESSION STATISTICS")
        print(f"{'='*70}")
        print(f"Cycles Run: {self.check_count}")
        print(f"Volume Spikes Detected: {self.spikes_detected}")
        print(f"Trades Executed: {self.trades_executed}")

        if self.paper_trading and hasattr(self.trader, 'get_performance_summary'):
            stats = self.trader.get_performance_summary()
            print(f"\nPaper Trading Performance:")
            print(f"  Starting Balance: ${stats['starting_balance']:,.2f}")
            print(f"  Current Balance:  ${stats['current_balance']:,.2f}")
            print(f"  P&L:              ${stats['total_profit']:,.2f}")
            print(f"  ROI:              {stats['session_roi']:.1f}%")
            print(f"  Win Rate:         {stats['win_rate']:.1f}%")

        print(f"{'='*70}\n")

    def run(self, num_cycles: int = None, continuous: bool = False):
        """
        Run the trading bot.

        Args:
            num_cycles: Number of cycles to run (None = infinite)
            continuous: If True, run continuously
        """
        print(f"\n{'='*70}")
        print(f"STARTING VOLUME SPIKE BOT")
        print(f"{'='*70}")
        print(f"Mode: {'Continuous' if continuous else f'{num_cycles} cycles'}")
        print(f"Press Ctrl+C to stop")
        print(f"{'='*70}\n")

        try:
            cycle = 0
            while True:
                if num_cycles and cycle >= num_cycles:
                    break

                self.run_cycle()

                # Print stats
                self.print_session_stats()

                # Save volume history
                self.detector.save_history()

                cycle += 1

                if continuous or (num_cycles and cycle < num_cycles):
                    print(f"Waiting {self.check_interval}s before next cycle...\n")
                    time.sleep(self.check_interval)
                else:
                    break

        except KeyboardInterrupt:
            print(f"\n\n{'='*70}")
            print("BOT STOPPED BY USER")
            print(f"{'='*70}\n")
            self.print_session_stats()

        # Final cleanup
        self.detector.save_history()

        if self.paper_trading and self.trader.session.open_positions:
            print(f"\nClosing {len(self.trader.session.open_positions)} open positions...")
            self.trader.simulate_auto_resolve()
            self.print_session_stats()


def main():
    """Run the volume spike bot."""
    print("\n" + "="*70)
    print("  POLYMARKET VOLUME SPIKE TRADING BOT")
    print("="*70)
    print("\nStrategy: Latency Arbitrage via Volume Spike Detection")
    print("\nThis bot will:")
    print("  1. Monitor 199+ open Polymarket markets")
    print("  2. Track volume history and detect spikes (3x-5x+)")
    print("  3. Correlate with price movement and deadline proximity")
    print("  4. Execute trades within seconds of spike detection")
    print("  5. Track P&L and performance")
    print("\nCurrently in PAPER TRADING mode (no real money)")
    print("="*70 + "\n")

    # Check if user wants live trading
    paper_trading = os.getenv('PAPER_TRADING', 'true').lower() == 'true'

    if not paper_trading:
        print("⚠️  WARNING: PAPER_TRADING=false in .env")
        print("This will execute REAL trades with REAL money!")
        response = input("\nType 'CONFIRM' to proceed with live trading: ")
        if response != 'CONFIRM':
            print("Switching to paper trading mode...")
            paper_trading = True

    # Initialize bot
    bot = VolumeSpikeBot(
        paper_trading=paper_trading,
        min_spike_ratio=3.0,  # 3x volume spike minimum
        min_volume_usd=50000,  # $50k minimum volume
        max_hours_to_deadline=72,  # Within 72 hours of deadline
        check_interval=30  # Check every 30 seconds
    )

    # Run for 3 cycles to build history
    bot.run(num_cycles=3, continuous=False)

    print(f"\n{'='*70}")
    print("BOT SESSION COMPLETE")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
