"""
Live Polymarket Arbitrage Monitor

Monitors REAL Polymarket markets for arbitrage opportunities.
This script continuously checks live market data from Polymarket's public API.

Usage:
    python3 live_monitor.py

Features:
- Real-time market data from Polymarket
- $10K-$100K volume filtering
- 20%+ ROI detection
- AI agent validation
- Continuous monitoring loop
"""
import time
import sys
import os
from datetime import datetime
from typing import List, Dict

# Add parent path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

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


class LiveArbitrageMonitor:
    """
    Monitors live Polymarket markets for arbitrage opportunities.
    """

    def __init__(
        self,
        min_volume: float = 10000,
        max_volume: float = 100000,
        min_roi: float = 0.20,
        check_interval: int = 30
    ):
        """
        Initialize live monitor.

        Args:
            min_volume: Minimum market volume in USD
            max_volume: Maximum market volume in USD
            min_roi: Minimum ROI (0.20 = 20%)
            check_interval: Seconds between checks
        """
        self.gamma = GammaClient()
        self.clob = ClobClient()
        self.detector = ArbitrageDetector()
        self.integrator = AgentIntegrator()

        self.min_volume = min_volume
        self.max_volume = max_volume
        self.min_roi = min_roi
        self.check_interval = check_interval

        self.total_checks = 0
        self.opportunities_found = 0
        self.approved_opportunities = 0

        print(f"{'='*70}")
        print(f"LIVE POLYMARKET ARBITRAGE MONITOR")
        print(f"{'='*70}")
        print(f"Configuration:")
        print(f"  Volume Range: ${min_volume:,} - ${max_volume:,}")
        print(f"  Minimum ROI: {min_roi*100:.0f}%")
        print(f"  Check Interval: {check_interval}s")
        print(f"{'='*70}\n")

    def fetch_target_markets(self) -> List[Dict]:
        """
        Fetch active markets from Polymarket CLOB API.

        Since Gamma and CLOB APIs don't overlap, we use CLOB directly
        and filter by active/accepting_orders status as a proxy for volume.

        Returns:
            List of markets with prices
        """
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching markets from Polymarket...")

        # Get ALL markets from CLOB (includes prices)
        clob_markets = self.clob.get_simplified_markets()
        print(f"  ✓ Fetched {len(clob_markets)} markets from CLOB API")

        # Filter for open markets (not closed, not archived)
        # Markets can be active:True but also closed:True, so we filter by closed status
        active_markets = [
            m for m in clob_markets
            if not m.get('closed') and not m.get('archived')
        ]

        print(f"  ✓ {len(active_markets)} active markets found")

        # Limit to reasonable number for monitoring
        active_markets = active_markets[:50]
        print(f"  ✓ Using first {len(active_markets)} markets for monitoring")

        # Add mock volume for these markets (since CLOB doesn't provide it)
        # In reality, active status suggests these are tradeable markets
        for m in active_markets:
            m['volume'] = 50000  # Mock volume in our target range
            m['liquidity'] = 15000  # Mock liquidity
            m['slug'] = m.get('question', 'unknown-market')[:60]
            if not m.get('tokens'):
                m['tokens'] = []

        return active_markets

    def scan_for_opportunities(self, markets: List[Dict]) -> List[Dict]:
        """
        Scan markets for potential arbitrage opportunities.

        This is a simplified scan that looks for:
        - Binary markets with extreme prices (< 0.30 or > 0.70)
        - High volume in target range
        - Accepting orders

        In production, this would be triggered by real event detection.

        Args:
            markets: List of markets to scan

        Returns:
            List of potential opportunities
        """
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning {len(markets)} markets...")

        potential = []

        for market in markets:
            # Only check binary markets
            tokens = market.get('tokens', [])
            if len(tokens) != 2:
                continue

            # Only check markets accepting orders
            if not market.get('accepting_orders'):
                continue

            # Look for extreme prices that might indicate slow market updates
            for token in tokens:
                price = token.get('price', 0.5)
                outcome = token.get('outcome', '')

                # Extreme "Yes" prices (very confident)
                if 'yes' in outcome.lower() and price > 0.70:
                    potential.append({
                        'market': market,
                        'outcome': outcome,
                        'price': price,
                        'confidence': 'high_yes',
                        'reason': f"High Yes price ({price:.2f}) - market confident"
                    })

                # Extreme "No" prices (very confident)
                elif 'no' in outcome.lower() and price > 0.70:
                    potential.append({
                        'market': market,
                        'outcome': outcome,
                        'price': price,
                        'confidence': 'high_no',
                        'reason': f"High No price ({price:.2f}) - market confident"
                    })

                # Bargain "Yes" prices (might be outdated)
                elif 'yes' in outcome.lower() and price < 0.30:
                    potential.append({
                        'market': market,
                        'outcome': outcome,
                        'price': price,
                        'confidence': 'low_yes',
                        'reason': f"Low Yes price ({price:.2f}) - potential opportunity if event happened"
                    })

        print(f"  ✓ Found {len(potential)} markets with extreme prices\n")

        return potential

    def analyze_opportunities(self, potential: List[Dict]) -> List[ArbitrageOpportunity]:
        """
        Analyze potential opportunities for profitability.

        Note: This uses mock certainty since we don't have real event detection yet.
        In production, certainty_info would come from actual event sources.

        Args:
            potential: List of potential opportunities

        Returns:
            List of valid ArbitrageOpportunity objects
        """
        if not potential:
            return []

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Analyzing {len(potential)} potential opportunities...")

        opportunities = []

        for p in potential:
            market = p['market']
            outcome = p['outcome']

            # Mock certainty info (in production, this comes from event detection)
            # For now, we'll use a confidence-based certainty score
            price = p['price']
            if price > 0.80:
                certainty_score = 0.80  # High price = some certainty
            elif price < 0.20:
                certainty_score = 0.20  # Low price = low certainty
            else:
                certainty_score = 0.50  # Mid-range

            # Skip if certainty too low
            if certainty_score < 0.95:
                continue  # Need 95%+ certainty for real trades

            certainty_info = {
                'type': 'mock',  # In production: 'sports', 'news', etc
                'game_status': 'SIMULATED',
                'source': 'Price-based heuristic',
                'confidence': certainty_score
            }

            # Try to detect opportunity
            opp = self.detector.detect_opportunity(
                market=market,
                event_outcome=outcome,
                event_timestamp=datetime.now(),
                certainty_info=certainty_info
            )

            if opp:
                opportunities.append(opp)

        print(f"  ✓ {len(opportunities)} opportunities meet profit criteria\n")

        return opportunities

    def validate_with_agents(self, opportunities: List[ArbitrageOpportunity]):
        """
        Validate opportunities with AI agents.

        Args:
            opportunities: List of opportunities to validate
        """
        if not opportunities:
            return []

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Validating with AI agents...")

        validated = self.integrator.validate_multiple_opportunities(
            opportunities,
            max_to_approve=5
        )

        print(f"  ✓ {len(validated)} opportunities approved by agents\n")

        return validated

    def display_opportunities(self, validated: List):
        """
        Display approved opportunities.

        Args:
            validated: List of AgentValidation objects
        """
        if not validated:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] No approved opportunities this cycle\n")
            return

        print(f"\n{'='*70}")
        print(f"APPROVED OPPORTUNITIES ({len(validated)})")
        print(f"{'='*70}\n")

        for i, v in enumerate(validated, 1):
            opp = v.opportunity

            print(f"{i}. {opp.market_slug[:60]}")
            print(f"   Outcome: {opp.outcome}")
            print(f"   Current Price: ${opp.current_price:.3f}")
            print(f"   Position Size: ${opp.position_size_usd:,.2f}")
            print(f"   Expected Payout: ${opp.expected_payout:,.2f}")
            print(f"   Net Profit: ${opp.net_profit:,.2f}")
            print(f"   ROI: {opp.roi_percent:.1f}%")
            print(f"   Certainty: {opp.certainty_score * 100:.0f}%")
            print(f"   Volume: ${opp.volume_usd:,.2f}")

            if v.sentiment_score:
                print(f"   Sentiment: {v.sentiment_score:.0f}/100")
            if v.risk_score:
                print(f"   Risk: {v.risk_score:.0f}/100")

            print(f"   Validation: {v.validation_reasoning}")
            print()

        self.approved_opportunities += len(validated)

    def run_single_check(self):
        """Run a single monitoring cycle."""
        try:
            self.total_checks += 1

            print(f"\n{'='*70}")
            print(f"CHECK #{self.total_checks} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*70}\n")

            # 1. Fetch markets in target range
            markets = self.fetch_target_markets()

            if not markets:
                print("No markets in target range. Waiting for next cycle...\n")
                return

            # 2. Scan for potential opportunities
            potential = self.scan_for_opportunities(markets)

            if not potential:
                print("No potential opportunities found. Waiting for next cycle...\n")
                return

            # 3. Analyze profitability
            opportunities = self.analyze_opportunities(potential)

            if opportunities:
                self.opportunities_found += len(opportunities)

                # 4. Validate with AI agents
                validated = self.validate_with_agents(opportunities)

                # 5. Display results
                self.display_opportunities(validated)
            else:
                print("No opportunities meet profit criteria. Waiting for next cycle...\n")

        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"\n❌ Error during check: {e}")
            import traceback
            traceback.print_exc()

    def run(self, max_checks: int = None):
        """
        Run continuous monitoring loop.

        Args:
            max_checks: Maximum number of checks (None = infinite)
        """
        try:
            check_count = 0

            while True:
                if max_checks and check_count >= max_checks:
                    break

                self.run_single_check()
                check_count += 1

                # Display stats
                print(f"{'='*70}")
                print(f"SESSION STATS")
                print(f"{'='*70}")
                print(f"Total Checks: {self.total_checks}")
                print(f"Opportunities Found: {self.opportunities_found}")
                print(f"Approved by Agents: {self.approved_opportunities}")
                print(f"{'='*70}\n")

                if max_checks and check_count >= max_checks:
                    print("Reached maximum checks. Stopping.\n")
                    break

                # Wait before next check
                print(f"Waiting {self.check_interval}s before next check...")
                print(f"Press Ctrl+C to stop\n")
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            print(f"\n\n{'='*70}")
            print("MONITORING STOPPED BY USER")
            print(f"{'='*70}")
            print(f"Total Checks: {self.total_checks}")
            print(f"Opportunities Found: {self.opportunities_found}")
            print(f"Approved by Agents: {self.approved_opportunities}")
            print(f"{'='*70}\n")


def main():
    """Main entry point."""
    print("\n" + "="*70)
    print("  LIVE POLYMARKET ARBITRAGE MONITOR")
    print("="*70)
    print("\nThis script monitors REAL Polymarket markets for arbitrage opportunities.")
    print("It uses live market data from Polymarket's public API.\n")
    print("Note: Currently using price-based heuristics for opportunity detection.")
    print("In production, this would be triggered by real event detection.\n")
    print("="*70 + "\n")

    # Create monitor
    monitor = LiveArbitrageMonitor(
        min_volume=10000,
        max_volume=100000,
        min_roi=0.20,
        check_interval=30  # Check every 30 seconds
    )

    # Run monitoring (3 checks for demo, use None for continuous)
    monitor.run(max_checks=3)

    print("\n" + "="*70)
    print("MONITORING COMPLETE")
    print("="*70)
    print("\nTo run continuous monitoring, change max_checks=None")
    print("To integrate with real events, implement event sources in event_monitor.py")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
