#!/usr/bin/env python3
"""
Test Notification System

This script sends notifications based on test results for CI/CD pipeline integration.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests


def load_test_analysis(analysis_file: str) -> Dict[str, Any]:
    """Load test analysis results"""

    try:
        with open(analysis_file, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading analysis file {analysis_file}: {e}", file=sys.stderr)
        return {}


def send_slack_notification(
    webhook_url: str, message: str, attachments: List[Dict] = None
):
    """Send notification to Slack"""

    payload = {"text": message, "attachments": attachments or []}

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        print("Slack notification sent successfully")
    except Exception as e:
        print(f"Error sending Slack notification: {e}", file=sys.stderr)


def send_teams_notification(
    webhook_url: str, message: str, title: str = "Test Results"
):
    """Send notification to Microsoft Teams"""

    payload = {"title": title, "text": message, "themeColor": "0076D7"}

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        print("Teams notification sent successfully")
    except Exception as e:
        print(f"Error sending Teams notification: {e}", file=sys.stderr)


def format_test_summary(analysis: Dict[str, Any]) -> str:
    """Format test summary for notifications"""

    summary = []
    summary.append("🧪 **Test Results Summary**")
    summary.append("")

    # Overall status
    overall_status = analysis.get("overall_status", "UNKNOWN")
    status_emoji = "✅" if overall_status == "PASS" else "❌"
    summary.append(f"{status_emoji} **Overall Status**: {overall_status}")
    summary.append("")

    # Test statistics
    total_tests = analysis.get("total_tests", 0)
    passed_tests = analysis.get("passed_tests", 0)
    failed_tests = analysis.get("failed_tests", 0)
    success_rate = analysis.get("success_rate", 0.0)

    summary.append(f"📊 **Test Statistics**:")
    summary.append(f"  • Total Tests: {total_tests}")
    summary.append(f"  • Passed: {passed_tests}")
    summary.append(f"  • Failed: {failed_tests}")
    summary.append(f"  • Success Rate: {success_rate:.1%}")
    summary.append("")

    # Performance regressions
    if "performance_regressions" in analysis:
        regressions = analysis["performance_regressions"]
        if regressions:
            summary.append("⚠️ **Performance Regressions**:")
            for regression in regressions[:5]:  # Limit to first 5
                summary.append(
                    f"  • {regression.get('endpoint', 'Unknown')}: "
                    f"{regression.get('change_percentage', 0):.1%} change"
                )
            if len(regressions) > 5:
                summary.append(f"  • ... and {len(regressions) - 5} more")
            summary.append("")

    # Compatibility scores
    if "compatibility_score" in analysis:
        compat_score = analysis["compatibility_score"]
        summary.append(f"🔗 **API Compatibility**: {compat_score:.1%}")

    if "behavioral_parity_score" in analysis:
        parity_score = analysis["behavioral_parity_score"]
        summary.append(f"🔄 **Behavioral Parity**: {parity_score:.1%}")

    return "\n".join(summary)


def determine_notification_level(analysis: Dict[str, Any]) -> str:
    """Determine notification level based on test results"""

    overall_status = analysis.get("overall_status", "UNKNOWN")
    success_rate = analysis.get("success_rate", 0.0)

    if overall_status == "FAIL" or success_rate < 0.8:
        return "CRITICAL"
    elif overall_status == "PASS" and success_rate >= 0.95:
        return "INFO"
    else:
        return "WARNING"


def send_notifications(analysis_file: str, report_file: str = None):
    """Send notifications based on test analysis"""

    # Load analysis
    analysis = load_test_analysis(analysis_file)
    if not analysis:
        print("Error: Could not load test analysis", file=sys.stderr)
        sys.exit(1)

    # Format message
    message = format_test_summary(analysis)
    notification_level = determine_notification_level(analysis)

    # Add timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message += f"\n\n⏰ Generated at: {timestamp}"

    # Send Slack notification
    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
    if slack_webhook:
        color = "#36a64f" if notification_level == "INFO" else "#ff0000"
        attachments = [
            {"color": color, "text": message, "footer": "GraphMemory CI/CD Pipeline"}
        ]
        send_slack_notification(slack_webhook, "Test Results", attachments)

    # Send Teams notification
    teams_webhook = os.getenv("TEAMS_WEBHOOK_URL")
    if teams_webhook:
        title = f"Test Results - {notification_level}"
        send_teams_notification(teams_webhook, message, title)

    # Send email notification (if configured)
    email_recipients = os.getenv("EMAIL_RECIPIENTS")
    if email_recipients:
        print(f"Email notification would be sent to: {email_recipients}")
        print(f"Message: {message}")

    print("Notifications sent successfully")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python send_notifications.py <analysis_file> [report_file]")
        sys.exit(1)

    analysis_file = sys.argv[1]
    report_file = sys.argv[2] if len(sys.argv) > 2 else None

    if not Path(analysis_file).exists():
        print(f"Error: Analysis file {analysis_file} does not exist", file=sys.stderr)
        sys.exit(1)

    send_notifications(analysis_file, report_file)


if __name__ == "__main__":
    main()
