#!/usr/bin/env python3
"""
Generate and post daily summaries to Slack.

This script reads the summary template and posts formatted messages
to Slack via webhook at scheduled times.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests


def load_template():
    """Load the summary template configuration."""
    template_path = Path(__file__).parent.parent / "summary_template.json"
    with open(template_path) as f:
        return json.load(f)


def get_current_date():
    """Get formatted current date."""
    return datetime.now().strftime("%A, %B %d, %Y")


def build_morning_summary(template):
    """Build the morning briefing message."""
    sections = template.get("morning", {})

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"☀️ Good Morning! — {get_current_date()}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": sections.get("greeting", "Here's your morning briefing:")
            }
        },
        {"type": "divider"}
    ]

    if "priority_tasks" in sections:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*🎯 Today's Priorities*\n" + sections["priority_tasks"]
            }
        })

    if "reminders" in sections:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📋 Reminders*\n" + sections["reminders"]
            }
        })

    for section in sections.get("custom_sections", []):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{section['title']}*\n{section['content']}"
            }
        })

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [{
            "type": "mrkdwn",
            "text": "💡 _Have a productive day!_"
        }]
    })

    return {"blocks": blocks}


def build_evening_summary(template):
    """Build the end-of-day recap message."""
    sections = template.get("evening", {})

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🌙 End of Day Recap — {get_current_date()}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": sections.get("greeting", "Here's your end-of-day summary:")
            }
        },
        {"type": "divider"}
    ]

    if "accomplishments" in sections:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*✅ Today's Progress*\n" + sections["accomplishments"]
            }
        })

    if "tomorrow_prep" in sections:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📅 Tomorrow's Focus*\n" + sections["tomorrow_prep"]
            }
        })

    for section in sections.get("custom_sections", []):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{section['title']}*\n{section['content']}"
            }
        })

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [{
            "type": "mrkdwn",
            "text": "🌟 _Great work today! Rest well._"
        }]
    })

    return {"blocks": blocks}


def post_to_slack(webhook_url, message):
    """Post message to Slack via webhook."""
    response = requests.post(
        webhook_url,
        json=message,
        headers={"Content-Type": "application/json"}
    )

    if response.status_code != 200:
        print(f"Error posting to Slack: {response.status_code} - {response.text}")
        sys.exit(1)

    print("Successfully posted summary to Slack!")


def main():
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("Error: SLACK_WEBHOOK_URL environment variable not set")
        sys.exit(1)

    summary_type = os.environ.get("SUMMARY_TYPE", "morning")
    template = load_template()

    if summary_type == "morning":
        message = build_morning_summary(template)
    else:
        message = build_evening_summary(template)

    post_to_slack(webhook_url, message)


if __name__ == "__main__":
    main()
