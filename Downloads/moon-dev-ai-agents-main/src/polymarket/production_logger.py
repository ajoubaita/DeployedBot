"""
Production Logging System for Volume Spike Bot

Designed for 24/7 DigitalOcean deployment during Phase 1 (baseline collection).
Tracks key metrics, detects anomalies, and provides actionable insights.

Usage:
    logger = ProductionLogger()
    logger.log_cycle_start(cycle_num)
    logger.log_market_scan(markets_count, volume_data)
    logger.log_baseline_progress(market_id, snapshots_collected)
    logger.log_cycle_complete(cycle_num, duration_seconds)
"""
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import statistics


@dataclass
class CycleMetrics:
    """Metrics for a single monitoring cycle."""
    cycle_num: int
    timestamp: str
    duration_seconds: float

    # Market coverage
    total_markets_scanned: int
    high_volume_markets: int  # >$100K
    target_range_markets: int  # $10K-$100K
    low_volume_markets: int  # <$10K

    # Volume analysis
    total_volume_24h: float
    avg_volume_per_market: float
    median_volume: float
    max_volume: float
    max_volume_market: str

    # Baseline collection progress
    markets_with_5plus_snapshots: int  # Min for spike detection
    markets_with_10plus_snapshots: int  # Good baseline
    markets_with_20_snapshots: int  # Full baseline
    baseline_completion_pct: float

    # API health
    api_response_time_ms: float
    api_errors: int

    # Detection readiness
    markets_ready_for_detection: int  # ≥5 snapshots
    estimated_days_to_full_baseline: float


@dataclass
class DailyReport:
    """Daily summary report."""
    date: str
    total_cycles: int
    total_runtime_hours: float

    # Coverage metrics
    unique_markets_tracked: int
    new_markets_added: int

    # Baseline progress
    baseline_completion_pct: float
    markets_ready_for_detection: int
    markets_needing_more_data: int

    # Volume insights
    avg_total_volume_24h: float
    volume_trend: str  # "increasing", "stable", "decreasing"
    top_volume_markets: List[Dict]  # Top 10 by volume

    # Anomalies detected
    unusual_volume_changes: List[Dict]  # Markets with sudden changes
    potential_early_spikes: List[Dict]  # Markets approaching spike threshold

    # Health metrics
    uptime_pct: float
    avg_cycle_duration: float
    api_error_rate: float


class ProductionLogger:
    """
    Production-grade logging for Phase 1 baseline collection.

    Features:
    - Structured JSON logs for easy parsing
    - Real-time metrics tracking
    - Daily summary reports
    - Anomaly detection
    - Progress monitoring
    """

    def __init__(self, log_dir: str = None):
        """
        Initialize production logger.

        Args:
            log_dir: Directory for log files (default: ./logs)
        """
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(__file__), 'logs')

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Setup structured logging
        self._setup_loggers()

        # Metrics tracking
        self.cycle_metrics: List[CycleMetrics] = []
        self.daily_markets_tracked = set()
        self.baseline_snapshots = {}  # market_id -> snapshot_count
        self.volume_history = {}  # market_id -> [volumes...]

        # Session tracking
        self.session_start = datetime.now()
        self.cycles_run = 0
        self.api_errors = 0

        self.info("Production logger initialized", {
            "log_dir": str(self.log_dir),
            "session_start": self.session_start.isoformat()
        })

    def _setup_loggers(self):
        """Setup different log files for different purposes."""

        # 1. Main activity log (human-readable)
        self.activity_logger = self._create_logger(
            'activity',
            self.log_dir / f'activity_{datetime.now().strftime("%Y%m%d")}.log',
            '%(asctime)s [%(levelname)s] %(message)s'
        )

        # 2. Metrics log (JSON structured)
        self.metrics_logger = self._create_logger(
            'metrics',
            self.log_dir / f'metrics_{datetime.now().strftime("%Y%m%d")}.jsonl',
            '%(message)s'
        )

        # 3. Alerts log (important events)
        self.alerts_logger = self._create_logger(
            'alerts',
            self.log_dir / 'alerts.log',
            '%(asctime)s [ALERT] %(message)s'
        )

        # 4. Daily reports
        self.reports_dir = self.log_dir / 'daily_reports'
        self.reports_dir.mkdir(exist_ok=True)

    def _create_logger(self, name: str, log_file: Path, format_str: str) -> logging.Logger:
        """Create a logger with file and console handlers."""
        logger = logging.getLogger(f'polymarket.{name}')
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(format_str))
        logger.addHandler(file_handler)

        # Console handler (optional, for activity only)
        if name == 'activity':
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(format_str))
            logger.addHandler(console_handler)

        return logger

    def info(self, message: str, data: Dict = None):
        """Log informational message."""
        self.activity_logger.info(message)
        if data:
            self.metrics_logger.info(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "message": message,
                "data": data
            }))

    def alert(self, message: str, data: Dict = None):
        """Log alert (important event)."""
        self.activity_logger.warning(f"⚠️  {message}")
        self.alerts_logger.warning(message)
        if data:
            self.metrics_logger.info(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "level": "ALERT",
                "message": message,
                "data": data
            }))

    def error(self, message: str, error: Exception = None):
        """Log error."""
        self.activity_logger.error(message)
        self.alerts_logger.error(message)
        self.api_errors += 1

        error_data = {
            "timestamp": datetime.now().isoformat(),
            "level": "ERROR",
            "message": message,
            "error": str(error) if error else None
        }
        self.metrics_logger.info(json.dumps(error_data))

    def log_cycle_start(self, cycle_num: int):
        """Log start of monitoring cycle."""
        self.cycles_run = cycle_num
        self.cycle_start_time = datetime.now()

        self.info(f"Starting cycle #{cycle_num}", {
            "cycle": cycle_num,
            "session_runtime_hours": self._get_session_runtime_hours()
        })

    def log_market_scan(self, markets: List[Dict]):
        """Log market scan results with detailed volume breakdown."""

        # Calculate volume metrics
        volumes = [m.get('volume', 0) for m in markets if m.get('volume')]

        high_volume = [m for m in markets if m.get('volume', 0) > 100000]
        target_range = [m for m in markets if 10000 <= m.get('volume', 0) <= 100000]
        low_volume = [m for m in markets if 0 < m.get('volume', 0) < 10000]

        total_volume = sum(volumes)
        avg_volume = statistics.mean(volumes) if volumes else 0
        median_volume = statistics.median(volumes) if volumes else 0
        max_volume = max(volumes) if volumes else 0
        max_volume_market = ""

        if max_volume > 0:
            max_market = max(markets, key=lambda m: m.get('volume', 0))
            max_volume_market = max_market.get('slug', max_market.get('question', 'unknown'))[:50]

        # Track markets
        for market in markets:
            market_id = market.get('id', market.get('condition_id'))
            if market_id:
                self.daily_markets_tracked.add(market_id)

        data = {
            "total_markets": len(markets),
            "high_volume_count": len(high_volume),
            "target_range_count": len(target_range),
            "low_volume_count": len(low_volume),
            "total_volume_24h": f"${total_volume:,.0f}",
            "avg_volume": f"${avg_volume:,.0f}",
            "median_volume": f"${median_volume:,.0f}",
            "max_volume": f"${max_volume:,.0f}",
            "max_volume_market": max_volume_market
        }

        self.info("Market scan complete", data)

        return {
            "total_markets": len(markets),
            "high_volume": len(high_volume),
            "target_range": len(target_range),
            "low_volume": len(low_volume),
            "total_volume": total_volume,
            "avg_volume": avg_volume,
            "median_volume": median_volume,
            "max_volume": max_volume,
            "max_volume_market": max_volume_market
        }

    def log_baseline_progress(self, volume_history_dict: Dict):
        """Log baseline collection progress."""

        # Analyze snapshot counts
        snapshot_counts = {}
        for market_id, history in volume_history_dict.items():
            count = len(history.snapshots) if hasattr(history, 'snapshots') else 0
            snapshot_counts[market_id] = count
            self.baseline_snapshots[market_id] = count

        total_markets = len(snapshot_counts)
        if total_markets == 0:
            return

        # Calculate progress metrics
        markets_5plus = sum(1 for c in snapshot_counts.values() if c >= 5)
        markets_10plus = sum(1 for c in snapshot_counts.values() if c >= 10)
        markets_20 = sum(1 for c in snapshot_counts.values() if c >= 20)

        avg_snapshots = statistics.mean(snapshot_counts.values())
        baseline_completion = (avg_snapshots / 20) * 100

        # Estimate days to completion
        session_hours = self._get_session_runtime_hours()
        if session_hours > 0 and avg_snapshots > 0:
            snapshots_per_hour = avg_snapshots / session_hours
            remaining_snapshots = 20 - avg_snapshots
            hours_to_complete = remaining_snapshots / snapshots_per_hour if snapshots_per_hour > 0 else 999
            days_to_complete = hours_to_complete / 24
        else:
            days_to_complete = 14  # Default estimate

        progress_data = {
            "total_markets_tracked": total_markets,
            "avg_snapshots_per_market": f"{avg_snapshots:.1f}",
            "baseline_completion_pct": f"{baseline_completion:.1f}%",
            "markets_ready_for_detection": markets_5plus,
            "markets_with_good_baseline": markets_10plus,
            "markets_with_full_baseline": markets_20,
            "estimated_days_to_completion": f"{days_to_complete:.1f} days"
        }

        self.info("Baseline collection progress", progress_data)

        # Alert milestones
        if baseline_completion >= 25 and baseline_completion < 26:
            self.alert("🎯 Baseline 25% complete!", progress_data)
        elif baseline_completion >= 50 and baseline_completion < 51:
            self.alert("🎯 Baseline 50% complete - Halfway there!", progress_data)
        elif baseline_completion >= 75 and baseline_completion < 76:
            self.alert("🎯 Baseline 75% complete - Almost ready!", progress_data)
        elif baseline_completion >= 100:
            self.alert("🎉 Baseline 100% complete - Ready for live trading!", progress_data)

        return {
            "markets_5plus": markets_5plus,
            "markets_10plus": markets_10plus,
            "markets_20": markets_20,
            "baseline_completion": baseline_completion,
            "days_to_complete": days_to_complete
        }

    def log_volume_anomaly(self, market_id: str, market_slug: str,
                          current_volume: float, avg_volume: float, spike_ratio: float):
        """Log detected volume anomaly (even if below spike threshold)."""

        # Track for daily report
        if market_id not in self.volume_history:
            self.volume_history[market_id] = []
        self.volume_history[market_id].append(current_volume)

        # Alert on significant changes (even if not tradeable yet)
        if spike_ratio >= 2.0:  # 2x is notable
            self.alert(f"Volume increase detected: {market_slug}", {
                "market_id": market_id,
                "current_volume": f"${current_volume:,.0f}",
                "avg_volume": f"${avg_volume:,.0f}",
                "spike_ratio": f"{spike_ratio:.1f}x",
                "status": "MONITORING" if spike_ratio < 3.0 else "APPROACHING THRESHOLD"
            })

    def log_cycle_complete(self, cycle_num: int, scan_results: Dict,
                          baseline_progress: Dict, api_time_ms: float):
        """Log cycle completion with comprehensive metrics."""

        duration = (datetime.now() - self.cycle_start_time).total_seconds()

        metrics = CycleMetrics(
            cycle_num=cycle_num,
            timestamp=datetime.now().isoformat(),
            duration_seconds=duration,
            total_markets_scanned=scan_results['total_markets'],
            high_volume_markets=scan_results['high_volume'],
            target_range_markets=scan_results['target_range'],
            low_volume_markets=scan_results['low_volume'],
            total_volume_24h=scan_results['total_volume'],
            avg_volume_per_market=scan_results['avg_volume'],
            median_volume=scan_results['median_volume'],
            max_volume=scan_results['max_volume'],
            max_volume_market=scan_results['max_volume_market'],
            markets_with_5plus_snapshots=baseline_progress.get('markets_5plus', 0),
            markets_with_10plus_snapshots=baseline_progress.get('markets_10plus', 0),
            markets_with_20_snapshots=baseline_progress.get('markets_20', 0),
            baseline_completion_pct=baseline_progress.get('baseline_completion', 0),
            api_response_time_ms=api_time_ms,
            api_errors=0,  # Track separately if needed
            markets_ready_for_detection=baseline_progress.get('markets_5plus', 0),
            estimated_days_to_full_baseline=baseline_progress.get('days_to_complete', 14)
        )

        self.cycle_metrics.append(metrics)

        # Log structured metrics
        self.metrics_logger.info(json.dumps(asdict(metrics)))

        self.info(f"Cycle #{cycle_num} complete", {
            "duration": f"{duration:.1f}s",
            "baseline_progress": f"{metrics.baseline_completion_pct:.1f}%",
            "markets_ready": metrics.markets_ready_for_detection
        })

    def generate_daily_report(self) -> DailyReport:
        """Generate comprehensive daily summary report."""

        today = datetime.now().date()

        # Filter today's metrics
        today_metrics = [
            m for m in self.cycle_metrics
            if datetime.fromisoformat(m.timestamp).date() == today
        ]

        if not today_metrics:
            return None

        # Calculate aggregates
        total_cycles = len(today_metrics)
        avg_cycle_duration = statistics.mean([m.duration_seconds for m in today_metrics])

        # Baseline progress
        latest_metrics = today_metrics[-1]
        baseline_completion = latest_metrics.baseline_completion_pct
        markets_ready = latest_metrics.markets_ready_for_detection
        markets_needing_data = latest_metrics.total_markets_scanned - markets_ready

        # Volume trends
        volumes = [m.total_volume_24h for m in today_metrics]
        avg_volume = statistics.mean(volumes)

        # Determine trend
        if len(volumes) >= 3:
            first_half = statistics.mean(volumes[:len(volumes)//2])
            second_half = statistics.mean(volumes[len(volumes)//2:])
            if second_half > first_half * 1.1:
                trend = "increasing"
            elif second_half < first_half * 0.9:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        # Top markets (from latest cycle)
        top_markets = []  # Would need to track individual market volumes

        # Anomalies
        unusual_changes = []
        potential_spikes = []

        for market_id, volumes in self.volume_history.items():
            if len(volumes) >= 2:
                recent = volumes[-1]
                avg = statistics.mean(volumes[:-1])
                ratio = recent / avg if avg > 0 else 1.0

                if ratio >= 2.5:  # Approaching threshold
                    potential_spikes.append({
                        "market_id": market_id,
                        "ratio": f"{ratio:.1f}x",
                        "current_volume": f"${recent:,.0f}"
                    })
                elif ratio >= 1.5:  # Notable increase
                    unusual_changes.append({
                        "market_id": market_id,
                        "ratio": f"{ratio:.1f}x",
                        "current_volume": f"${recent:,.0f}"
                    })

        # Health metrics
        session_runtime = self._get_session_runtime_hours()
        expected_cycles = int(session_runtime * 2)  # 2 cycles per hour (30s interval)
        uptime_pct = (total_cycles / expected_cycles * 100) if expected_cycles > 0 else 100

        report = DailyReport(
            date=today.isoformat(),
            total_cycles=total_cycles,
            total_runtime_hours=session_runtime,
            unique_markets_tracked=len(self.daily_markets_tracked),
            new_markets_added=0,  # Would need historical tracking
            baseline_completion_pct=baseline_completion,
            markets_ready_for_detection=markets_ready,
            markets_needing_more_data=markets_needing_data,
            avg_total_volume_24h=avg_volume,
            volume_trend=trend,
            top_volume_markets=top_markets,
            unusual_volume_changes=unusual_changes[:10],
            potential_early_spikes=potential_spikes[:10],
            uptime_pct=uptime_pct,
            avg_cycle_duration=avg_cycle_duration,
            api_error_rate=(self.api_errors / total_cycles * 100) if total_cycles > 0 else 0
        )

        # Save report
        report_file = self.reports_dir / f'report_{today.isoformat()}.json'
        with open(report_file, 'w') as f:
            json.dump(asdict(report), f, indent=2)

        self.alert(f"📊 Daily report generated: {report_file}")

        return report

    def _get_session_runtime_hours(self) -> float:
        """Get total session runtime in hours."""
        return (datetime.now() - self.session_start).total_seconds() / 3600

    def print_daily_summary(self, report: DailyReport):
        """Print human-readable daily summary to console."""

        print("\n" + "="*70)
        print(f"📊 DAILY REPORT - {report.date}")
        print("="*70)

        print(f"\n⏱️  RUNTIME")
        print(f"  Total Cycles: {report.total_cycles}")
        print(f"  Runtime: {report.total_runtime_hours:.1f} hours")
        print(f"  Uptime: {report.uptime_pct:.1f}%")
        print(f"  Avg Cycle Duration: {report.avg_cycle_duration:.1f}s")

        print(f"\n📈 BASELINE PROGRESS")
        print(f"  Completion: {report.baseline_completion_pct:.1f}%")
        print(f"  Markets Ready: {report.markets_ready_for_detection}")
        print(f"  Markets Needing Data: {report.markets_needing_more_data}")

        print(f"\n💰 VOLUME ANALYSIS")
        print(f"  Avg 24h Volume: ${report.avg_total_volume_24h:,.0f}")
        print(f"  Trend: {report.volume_trend}")

        if report.potential_early_spikes:
            print(f"\n⚡ POTENTIAL SPIKES ({len(report.potential_early_spikes)})")
            for spike in report.potential_early_spikes[:5]:
                print(f"  • {spike['market_id']}: {spike['ratio']} spike")

        if report.unusual_volume_changes:
            print(f"\n🔍 UNUSUAL CHANGES ({len(report.unusual_volume_changes)})")
            for change in report.unusual_volume_changes[:5]:
                print(f"  • {change['market_id']}: {change['ratio']} increase")

        print(f"\n🏥 HEALTH")
        print(f"  API Error Rate: {report.api_error_rate:.2f}%")

        print("\n" + "="*70 + "\n")
