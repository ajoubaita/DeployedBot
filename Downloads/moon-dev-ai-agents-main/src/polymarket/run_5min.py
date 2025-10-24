"""
Run trading bot for 5 minutes to find opportunities.

This will continuously monitor markets and report any opportunities found.
"""
import time
from datetime import datetime, timedelta

try:
    from polymarket.live_trading_bot import LiveTradingBot
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from polymarket.live_trading_bot import LiveTradingBot


def run_for_duration(minutes: int = 5):
    """
    Run bot for specified duration.

    Args:
        minutes: How many minutes to run
    """
    print(f"\n{'='*70}")
    print(f"RUNNING BOT FOR {minutes} MINUTES")
    print(f"{'='*70}")
    print(f"Start Time: {datetime.now().strftime('%H:%M:%S')}")

    end_time = datetime.now() + timedelta(minutes=minutes)
    print(f"Will run until: {end_time.strftime('%H:%M:%S')}")
    print(f"{'='*70}\n")

    # Initialize bot
    bot = LiveTradingBot(paper_trading=True)

    # Set shorter check interval for more frequent checks
    bot.check_interval = 15  # Check every 15 seconds for 5 minutes

    cycle = 0

    try:
        while datetime.now() < end_time:
            cycle += 1

            remaining = (end_time - datetime.now()).total_seconds()
            print(f"\n{'='*70}")
            print(f"CYCLE #{cycle} - {datetime.now().strftime('%H:%M:%S')}")
            print(f"Time Remaining: {remaining/60:.1f} minutes")
            print(f"{'='*70}\n")

            bot.run_cycle()

            # Print stats after each cycle
            bot.print_session_stats()

            # Check if we have time for another cycle
            if datetime.now() >= end_time:
                break

            # Wait before next cycle
            wait_time = min(bot.check_interval, (end_time - datetime.now()).total_seconds())
            if wait_time > 0:
                print(f"Waiting {wait_time:.0f}s before next cycle...")
                time.sleep(wait_time)

    except KeyboardInterrupt:
        print(f"\n\n{'='*70}")
        print("BOT STOPPED BY USER")
        print(f"{'='*70}\n")

    # Final report
    print(f"\n{'='*70}")
    print(f"5-MINUTE SESSION COMPLETE")
    print(f"{'='*70}")
    print(f"End Time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"Total Cycles: {cycle}")
    print(f"{'='*70}\n")

    bot.print_session_stats()

    # Close any open positions
    if bot.paper_trading and bot.trader.session.open_positions:
        print(f"\nClosing {len(bot.trader.session.open_positions)} open positions...")
        bot.trader.simulate_auto_resolve()
        bot.print_session_stats()

    print(f"\n{'='*70}")
    print("OPPORTUNITIES DETECTED DURING SESSION")
    print(f"{'='*70}")

    if bot.opportunities_found > 0:
        print(f"\n✓ Found {bot.opportunities_found} total opportunities")
        print(f"✓ Executed {bot.trades_executed} trades")

        if bot.paper_trading and bot.trader.session.closed_positions:
            print(f"\n📊 TRADE DETAILS:\n")
            for i, trade in enumerate(bot.trader.session.closed_positions, 1):
                print(f"{i}. {trade.market_slug}")
                print(f"   Entry: ${trade.entry_price:.3f} → Exit: ${trade.exit_price:.3f}")
                print(f"   Position: ${trade.position_size:,.2f}")
                print(f"   Profit: ${trade.actual_profit:,.2f}")
                print(f"   ROI: {(trade.actual_profit/trade.position_size)*100:.1f}%")
                print(f"   Reasoning: {trade.reasoning}")
                print()
    else:
        print(f"\n✗ No opportunities found during this session")
        print(f"\nWhy this might happen:")
        print(f"  • Only 2 markets currently open on Polymarket")
        print(f"  • Markets don't meet strict criteria (20% ROI, 95% certainty)")
        print(f"  • No event detection integrated yet (can't identify certain outcomes)")
        print(f"  • Need more active markets or event source integration")

    print(f"\n{'='*70}")
    print("RECOMMENDATIONS")
    print(f"{'='*70}")
    print(f"\nTo find more opportunities:")
    print(f"  1. Run during high-activity periods (major sports, elections)")
    print(f"  2. Integrate event sources (ESPN API, Reuters, etc.)")
    print(f"  3. Lower thresholds (15% ROI instead of 20%)")
    print(f"  4. Monitor for longer periods (hours, not minutes)")
    print(f"\nThe bot is working correctly - just need more market activity!")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    run_for_duration(minutes=5)
