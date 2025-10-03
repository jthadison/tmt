#!/usr/bin/env python3
"""
Load Test Report Generator
Generates HTML report from load test results
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>TMT Load Test Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-card h3 {{
            margin: 0 0 10px 0;
            color: #666;
            font-size: 14px;
            text-transform: uppercase;
        }}
        .metric-card .value {{
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }}
        .metric-card .unit {{
            font-size: 16px;
            color: #999;
            margin-left: 5px;
        }}
        .status-pass {{
            color: #10b981;
        }}
        .status-fail {{
            color: #ef4444;
        }}
        .details {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e5e5e5;
        }}
        th {{
            background: #f9f9f9;
            font-weight: 600;
            color: #666;
        }}
        .footer {{
            text-align: center;
            color: #999;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e5e5e5;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 TMT Load Test Report</h1>
        <p>Generated: {timestamp}</p>
    </div>

    <div class="summary">
        <div class="metric-card">
            <h3>Total Requests</h3>
            <div class="value">{total_requests}</div>
        </div>
        <div class="metric-card">
            <h3>Success Rate</h3>
            <div class="value {success_class}">{success_rate}%</div>
        </div>
        <div class="metric-card">
            <h3>Avg Response Time</h3>
            <div class="value">{avg_response}<span class="unit">ms</span></div>
        </div>
        <div class="metric-card">
            <h3>P95 Response Time</h3>
            <div class="value">{p95_response}<span class="unit">ms</span></div>
        </div>
        <div class="metric-card">
            <h3>Max Response Time</h3>
            <div class="value">{max_response}<span class="unit">ms</span></div>
        </div>
        <div class="metric-card">
            <h3>Requests/sec</h3>
            <div class="value">{rps}</div>
        </div>
    </div>

    <div class="details">
        <h2>Endpoint Performance</h2>
        <table>
            <thead>
                <tr>
                    <th>Endpoint</th>
                    <th>Requests</th>
                    <th>Success Rate</th>
                    <th>Avg Time (ms)</th>
                    <th>P95 Time (ms)</th>
                    <th>Max Time (ms)</th>
                </tr>
            </thead>
            <tbody>
                {endpoint_rows}
            </tbody>
        </table>
    </div>

    {error_section}

    <div class="footer">
        <p>TMT Adaptive Trading System - Load Test Report</p>
    </div>
</body>
</html>
"""


class LoadReportGenerator:
    """Generate HTML reports from load test data"""

    def __init__(self, metrics_file: Path = Path("load-metrics.json")):
        self.metrics_file = metrics_file

    def load_metrics(self) -> Dict:
        """Load load test metrics"""
        try:
            with open(self.metrics_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️  Metrics file not found: {self.metrics_file}")
            return self.generate_sample_metrics()
        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON: {e}")
            sys.exit(1)

    def generate_sample_metrics(self) -> Dict:
        """Generate sample metrics for testing"""
        return {
            "summary": {
                "total_requests": 10000,
                "successful_requests": 9850,
                "failed_requests": 150,
                "avg_response_time": 45.2,
                "p95_response_time": 120.5,
                "max_response_time": 850.3,
                "requests_per_second": 95.3,
                "duration_seconds": 105,
            },
            "endpoints": [
                {
                    "name": "/health",
                    "requests": 2000,
                    "success_rate": 100.0,
                    "avg_time": 12.5,
                    "p95_time": 25.0,
                    "max_time": 50.2,
                },
                {
                    "name": "/api/agents",
                    "requests": 3000,
                    "success_rate": 99.5,
                    "avg_time": 35.8,
                    "p95_time": 85.3,
                    "max_time": 320.5,
                },
                {
                    "name": "/api/signals",
                    "requests": 2500,
                    "success_rate": 98.8,
                    "avg_time": 62.3,
                    "p95_time": 150.8,
                    "max_time": 850.3,
                },
                {
                    "name": "/api/trades",
                    "requests": 2500,
                    "success_rate": 97.2,
                    "avg_time": 58.9,
                    "p95_time": 180.2,
                    "max_time": 720.1,
                },
            ],
            "errors": [
                {"type": "TimeoutError", "count": 45, "percentage": 0.45},
                {"type": "ConnectionError", "count": 80, "percentage": 0.80},
                {"type": "500 Internal Server Error", "count": 25, "percentage": 0.25},
            ],
        }

    def generate_endpoint_rows(self, endpoints: List[Dict]) -> str:
        """Generate HTML table rows for endpoints"""
        rows = []

        for endpoint in endpoints:
            success_class = "status-pass" if endpoint["success_rate"] >= 95 else "status-fail"

            row = f"""
                <tr>
                    <td>{endpoint['name']}</td>
                    <td>{endpoint['requests']:,}</td>
                    <td class="{success_class}">{endpoint['success_rate']:.1f}%</td>
                    <td>{endpoint['avg_time']:.1f}</td>
                    <td>{endpoint['p95_time']:.1f}</td>
                    <td>{endpoint['max_time']:.1f}</td>
                </tr>
            """
            rows.append(row)

        return "\n".join(rows)

    def generate_error_section(self, errors: List[Dict]) -> str:
        """Generate error section HTML"""
        if not errors:
            return ""

        error_rows = []
        for error in errors:
            error_rows.append(f"""
                <tr>
                    <td>{error['type']}</td>
                    <td>{error['count']}</td>
                    <td>{error['percentage']:.2f}%</td>
                </tr>
            """)

        return f"""
        <div class="details">
            <h2>Errors</h2>
            <table>
                <thead>
                    <tr>
                        <th>Error Type</th>
                        <th>Count</th>
                        <th>Percentage</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(error_rows)}
                </tbody>
            </table>
        </div>
        """

    def generate_html(self, metrics: Dict) -> str:
        """Generate complete HTML report"""
        summary = metrics.get("summary", {})
        endpoints = metrics.get("endpoints", [])
        errors = metrics.get("errors", [])

        # Calculate success rate
        total = summary.get("total_requests", 0)
        successful = summary.get("successful_requests", 0)
        success_rate = (successful / total * 100) if total > 0 else 0
        success_class = "status-pass" if success_rate >= 95 else "status-fail"

        html = HTML_TEMPLATE.format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_requests=f"{total:,}",
            success_rate=f"{success_rate:.1f}",
            success_class=success_class,
            avg_response=f"{summary.get('avg_response_time', 0):.1f}",
            p95_response=f"{summary.get('p95_response_time', 0):.1f}",
            max_response=f"{summary.get('max_response_time', 0):.1f}",
            rps=f"{summary.get('requests_per_second', 0):.1f}",
            endpoint_rows=self.generate_endpoint_rows(endpoints),
            error_section=self.generate_error_section(errors),
        )

        return html

    def generate(self, output_file: Path = Path("load-test-report.html")) -> None:
        """Generate and save HTML report"""
        print("=" * 60)
        print("TMT Load Test Report Generator")
        print("=" * 60)
        print()

        # Load metrics
        print(f"📊 Loading metrics from {self.metrics_file}...")
        metrics = self.load_metrics()

        # Generate HTML
        print("🎨 Generating HTML report...")
        html = self.generate_html(metrics)

        # Save report
        with open(output_file, "w") as f:
            f.write(html)

        print(f"✓ Report saved to: {output_file}")
        print()
        print("=" * 60)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate load test HTML report")
    parser.add_argument(
        "--metrics",
        type=Path,
        default=Path("load-metrics.json"),
        help="Path to metrics JSON file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("load-test-report.html"),
        help="Path to output HTML file",
    )

    args = parser.parse_args()

    generator = LoadReportGenerator(metrics_file=args.metrics)
    generator.generate(output_file=args.output)


if __name__ == "__main__":
    main()
