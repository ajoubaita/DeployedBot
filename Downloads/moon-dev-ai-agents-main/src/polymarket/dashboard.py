#!/usr/bin/env python3
"""
Simple Monitoring Dashboard for Polymarket Bot

Generates a static HTML dashboard showing key metrics.
Run this script periodically (cron) to update the dashboard.

Usage:
    python3 dashboard.py
    # Then serve with: python3 -m http.server 8080
    # Access at: http://your-droplet-ip:8080/dashboard.html
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
import statistics


class DashboardGenerator:
    """Generate HTML monitoring dashboard."""

    def __init__(self, log_dir: str = None):
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        self.log_dir = Path(log_dir)
        self.reports_dir = self.log_dir / 'daily_reports'

    def load_recent_reports(self, days: int = 7) -> List[Dict]:
        """Load last N days of reports."""
        reports = []

        if not self.reports_dir.exists():
            return reports

        for report_file in sorted(self.reports_dir.glob('report_*.json'), reverse=True)[:days]:
            try:
                with open(report_file) as f:
                    reports.append(json.load(f))
            except Exception as e:
                print(f"Error loading {report_file}: {e}")

        return reports

    def load_metrics(self, days: int = 1) -> List[Dict]:
        """Load recent metrics from JSONL files."""
        metrics = []
        cutoff = datetime.now() - timedelta(days=days)

        for metrics_file in self.log_dir.glob('metrics_*.jsonl'):
            try:
                with open(metrics_file) as f:
                    for line in f:
                        try:
                            metric = json.loads(line)
                            ts = datetime.fromisoformat(metric.get('timestamp', ''))
                            if ts >= cutoff:
                                metrics.append(metric)
                        except:
                            continue
            except Exception as e:
                print(f"Error loading {metrics_file}: {e}")

        return sorted(metrics, key=lambda m: m.get('timestamp', ''))

    def generate_html(self) -> str:
        """Generate HTML dashboard."""

        reports = self.load_recent_reports(days=7)
        latest_report = reports[0] if reports else None

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Polymarket Bot Dashboard</title>
    <meta http-equiv="refresh" content="300">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        .updated {{
            opacity: 0.8;
            font-size: 14px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: #1e293b;
            border-radius: 10px;
            padding: 20px;
            border: 1px solid #334155;
        }}
        .card h2 {{
            font-size: 18px;
            margin-bottom: 15px;
            color: #60a5fa;
        }}
        .metric {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #334155;
        }}
        .metric:last-child {{
            border-bottom: none;
        }}
        .metric-label {{
            color: #94a3b8;
        }}
        .metric-value {{
            font-weight: bold;
            font-size: 18px;
        }}
        .metric-value.good {{
            color: #34d399;
        }}
        .metric-value.warning {{
            color: #fbbf24;
        }}
        .metric-value.bad {{
            color: #f87171;
        }}
        .progress-bar {{
            width: 100%;
            height: 30px;
            background: #334155;
            border-radius: 5px;
            overflow: hidden;
            margin-top: 10px;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #34d399 0%, #3b82f6 100%);
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
        }}
        .alert {{
            background: #7c2d12;
            border: 2px solid #f87171;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 10px;
        }}
        .alert-title {{
            font-weight: bold;
            margin-bottom: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            text-align: left;
            padding: 10px;
            border-bottom: 1px solid #334155;
        }}
        th {{
            background: #334155;
            color: #60a5fa;
        }}
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }}
        .status-active {{
            background: #065f46;
            color: #34d399;
        }}
        .status-warning {{
            background: #78350f;
            color: #fbbf24;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Polymarket Volume Spike Bot</h1>
            <div class="updated">Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
            <div class="updated">Phase 1: Baseline Collection Mode</div>
        </header>

        {self._render_status_cards(latest_report)}
        {self._render_baseline_progress(latest_report)}
        {self._render_alerts(latest_report)}
        {self._render_volume_trends(reports)}
        {self._render_market_coverage(latest_report)}
    </div>
</body>
</html>
"""
        return html

    def _render_status_cards(self, report: Dict) -> str:
        if not report:
            return '<div class="card"><p>No data available yet</p></div>'

        uptime_class = "good" if report.get('uptime_pct', 0) >= 99 else "warning"
        error_class = "good" if report.get('api_error_rate', 0) < 1 else "bad"

        return f"""
        <div class="grid">
            <div class="card">
                <h2>⏱️ System Health</h2>
                <div class="metric">
                    <span class="metric-label">Uptime</span>
                    <span class="metric-value {uptime_class}">{report.get('uptime_pct', 0):.1f}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Runtime</span>
                    <span class="metric-value">{report.get('total_runtime_hours', 0):.1f}h</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Cycles</span>
                    <span class="metric-value">{report.get('total_cycles', 0)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Error Rate</span>
                    <span class="metric-value {error_class}">{report.get('api_error_rate', 0):.2f}%</span>
                </div>
            </div>

            <div class="card">
                <h2>📈 Baseline Progress</h2>
                <div class="metric">
                    <span class="metric-label">Completion</span>
                    <span class="metric-value good">{report.get('baseline_completion_pct', 0):.1f}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Markets Ready</span>
                    <span class="metric-value">{report.get('markets_ready_for_detection', 0)}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Need More Data</span>
                    <span class="metric-value">{report.get('markets_needing_more_data', 0)}</span>
                </div>
            </div>

            <div class="card">
                <h2>💰 Volume Analysis</h2>
                <div class="metric">
                    <span class="metric-label">Avg 24h Volume</span>
                    <span class="metric-value">${report.get('avg_total_volume_24h', 0):,.0f}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Trend</span>
                    <span class="metric-value">{report.get('volume_trend', 'N/A').upper()}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Markets Tracked</span>
                    <span class="metric-value">{report.get('unique_markets_tracked', 0)}</span>
                </div>
            </div>
        </div>
        """

    def _render_baseline_progress(self, report: Dict) -> str:
        if not report:
            return ""

        completion = report.get('baseline_completion_pct', 0)

        return f"""
        <div class="card">
            <h2>🎯 Baseline Collection Progress</h2>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {completion}%">
                    {completion:.1f}%
                </div>
            </div>
            <p style="margin-top: 15px; color: #94a3b8;">
                Target: 20 snapshots per market |
                Ready: {report.get('markets_ready_for_detection', 0)}/{report.get('unique_markets_tracked', 0)} markets
            </p>
        </div>
        """

    def _render_alerts(self, report: Dict) -> str:
        if not report:
            return ""

        alerts_html = ""

        # Potential spikes
        spikes = report.get('potential_early_spikes', [])
        if spikes:
            alerts_html += '<div class="card"><h2>⚡ Potential Volume Spikes Detected</h2>'
            for spike in spikes[:5]:
                alerts_html += f"""
                <div class="alert">
                    <div class="alert-title">{spike.get('market_id', 'Unknown')}</div>
                    <div>Spike Ratio: {spike.get('ratio', 'N/A')} | Volume: {spike.get('current_volume', 'N/A')}</div>
                </div>
                """
            alerts_html += '</div>'

        # Unusual changes
        changes = report.get('unusual_volume_changes', [])
        if changes:
            alerts_html += '<div class="card"><h2>🔍 Unusual Volume Changes</h2>'
            for change in changes[:5]:
                alerts_html += f"""
                <div style="padding: 10px; border-bottom: 1px solid #334155;">
                    <strong>{change.get('market_id', 'Unknown')}</strong><br>
                    Ratio: {change.get('ratio', 'N/A')} | Volume: {change.get('current_volume', 'N/A')}
                </div>
                """
            alerts_html += '</div>'

        return alerts_html

    def _render_volume_trends(self, reports: List[Dict]) -> str:
        if not reports or len(reports) < 2:
            return ""

        # Simple trend visualization
        dates = [r.get('date', '') for r in reversed(reports)]
        volumes = [r.get('avg_total_volume_24h', 0) for r in reversed(reports)]

        rows = ""
        for date, volume in zip(dates, volumes):
            rows += f"<tr><td>{date}</td><td>${volume:,.0f}</td></tr>"

        return f"""
        <div class="card">
            <h2>📊 7-Day Volume Trend</h2>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Avg 24h Volume</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        """

    def _render_market_coverage(self, report: Dict) -> str:
        if not report:
            return ""

        return f"""
        <div class="card">
            <h2>🎯 Market Coverage</h2>
            <table>
                <thead>
                    <tr>
                        <th>Category</th>
                        <th>Count</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Total Markets Tracked</td>
                        <td>{report.get('unique_markets_tracked', 0)}</td>
                        <td><span class="status-badge status-active">ACTIVE</span></td>
                    </tr>
                    <tr>
                        <td>Markets Ready (≥5 snapshots)</td>
                        <td>{report.get('markets_ready_for_detection', 0)}</td>
                        <td><span class="status-badge status-active">READY</span></td>
                    </tr>
                    <tr>
                        <td>Markets Need More Data</td>
                        <td>{report.get('markets_needing_more_data', 0)}</td>
                        <td><span class="status-badge status-warning">COLLECTING</span></td>
                    </tr>
                </tbody>
            </table>
        </div>
        """

    def save_dashboard(self, output_file: str = 'dashboard.html'):
        """Generate and save dashboard HTML."""
        html = self.generate_html()

        output_path = Path(output_file)
        with open(output_path, 'w') as f:
            f.write(html)

        print(f"✅ Dashboard saved to: {output_path.absolute()}")
        print(f"\nTo view:")
        print(f"  1. python3 -m http.server 8080")
        print(f"  2. Open http://localhost:8080/dashboard.html")


if __name__ == '__main__':
    generator = DashboardGenerator()
    generator.save_dashboard()
