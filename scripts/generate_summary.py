#!/usr/bin/env python3
"""
Generate and post daily summaries to Slack.

Fetches unread messages and DMs from Slack, then posts a formatted
summary to your channel via webhook.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

SLACK_API_BASE = "https://slack.com/api"


def load_template():
    """Load the summary template configuration."""
    template_path = Path(__file__).parent.parent / "summary_template.json"
    with open(template_path) as f:
        return json.load(f)


def get_current_date():
    """Get formatted current date."""
    return datetime.now().strftime("%A, %B %d, %Y")


def slack_api_call(endpoint, token, params=None):
    """Make a Slack API call."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{SLACK_API_BASE}/{endpoint}", headers=headers, params=params or {})
    data = response.json()
    if not data.get("ok"):
        print(f"Slack API error ({endpoint}): {data.get('error', 'Unknown error')}")
        return None
    return data


def get_user_info(token):
    """Get the authenticated user's info."""
    data = slack_api_call("auth.test", token)
    return data.get("user_id") if data else None


def get_user_name(token, user_id):
    """Get a user's display name."""
    data = slack_api_call("users.info", token, {"user": user_id})
    if data and data.get("user"):
        user = data["user"]
        return user.get("real_name") or user.get("name", "Unknown")
    return "Unknown"


def get_dm_channels(token):
    """Get all DM channels."""
    data = slack_api_call("conversations.list", token, {"types": "im", "limit": 100})
    return data.get("channels", []) if data else []


def get_unread_dms(token, my_user_id, hours_back=24):
    """Get unread DMs from the last N hours."""
    dm_channels = get_dm_channels(token)
    oldest = (datetime.now() - timedelta(hours=hours_back)).timestamp()
    
    unread_messages = []
    user_cache = {}
    
    for channel in dm_channels:
        channel_id = channel["id"]
        other_user_id = channel.get("user")
        
        data = slack_api_call("conversations.history", token, {
            "channel": channel_id,
            "oldest": str(oldest),
            "limit": 50
        })
        
        if not data:
            continue
            
        messages = data.get("messages", [])
        
        for msg in messages:
            if msg.get("user") != my_user_id and not msg.get("bot_id"):
                sender_id = msg.get("user", other_user_id)
                if sender_id not in user_cache:
                    user_cache[sender_id] = get_user_name(token, sender_id)
                
                unread_messages.append({
                    "from": user_cache[sender_id],
                    "preview": msg.get("text", "")[:80] + ("..." if len(msg.get("text", "")) > 80 else ""),
                    "channel_id": channel_id,
                    "ts": msg.get("ts")
                })
    
    return unread_messages[:10]


def get_channel_mentions(token, my_user_id, hours_back=24):
    """Get recent mentions in channels."""
    data = slack_api_call("conversations.list", token, {
        "types": "public_channel,private_channel",
        "limit": 50
    })
    
    if not data:
        return []
    
    channels = data.get("channels", [])
    oldest = (datetime.now() - timedelta(hours=hours_back)).timestamp()
    mentions = []
    user_cache = {}
    channel_cache = {}
    
    for channel in channels:
        if not channel.get("is_member"):
            continue
            
        channel_id = channel["id"]
        channel_name = channel.get("name", "unknown")
        channel_cache[channel_id] = channel_name
        
        history = slack_api_call("conversations.history", token, {
            "channel": channel_id,
            "oldest": str(oldest),
            "limit": 100
        })
        
        if not history:
            continue
        
        for msg in history.get("messages", []):
            text = msg.get("text", "")
            if f"<@{my_user_id}>" in text:
                sender_id = msg.get("user")
                if sender_id and sender_id not in user_cache:
                    user_cache[sender_id] = get_user_name(token, sender_id)
                
                mentions.append({
                    "from": user_cache.get(sender_id, "Unknown"),
                    "channel": f"#{channel_name}",
                    "preview": text.replace(f"<@{my_user_id}>", "@you")[:80] + ("..." if len(text) > 80 else ""),
                    "ts": msg.get("ts")
                })
    
    return mentions[:10]


def fetch_slack_data(token):
    """Fetch all relevant Slack data."""
    my_user_id = get_user_info(token)
    if not my_user_id:
        return {"dms": [], "mentions": [], "error": "Could not authenticate"}
    
    return {
        "dms": get_unread_dms(token, my_user_id),
        "mentions": get_channel_mentions(token, my_user_id),
        "error": None
    }


def format_slack_section(slack_data):
    """Format Slack data into message blocks."""
    blocks = []
    
    dms = slack_data.get("dms", [])
    mentions = slack_data.get("mentions", [])
    
    if dms:
        dm_text = "*💬 Recent DMs to Reply*\n"
        for dm in dms[:5]:
            dm_text += f"• *{dm['from']}*: {dm['preview']}\n"
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": dm_text.strip()}
        })
    
    if mentions:
        mention_text = "*📢 Channel Mentions*\n"
        for mention in mentions[:5]:
            mention_text += f"• *{mention['from']}* in {mention['channel']}: {mention['preview']}\n"
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": mention_text.strip()}
        })
    
    if not dms and not mentions:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "✨ *Inbox Zero!* No pending messages to reply to."}
        })
    
    return blocks


def build_morning_summary(template, slack_data=None):
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

    if slack_data:
        blocks.extend(format_slack_section(slack_data))
        blocks.append({"type": "divider"})

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
    
    total_pending = len(slack_data.get("dms", [])) + len(slack_data.get("mentions", [])) if slack_data else 0
    footer = f"💡 _You have {total_pending} message(s) to review. Have a productive day!_" if total_pending > 0 else "💡 _Have a productive day!_"
    
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": footer}]
    })

    return {"blocks": blocks}


def build_evening_summary(template, slack_data=None):
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

    if slack_data:
        dms = slack_data.get("dms", [])
        mentions = slack_data.get("mentions", [])
        total = len(dms) + len(mentions)
        
        if total > 0:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*⚠️ Pending Messages*\nYou have *{total}* message(s) still waiting for a reply. Don't forget to respond before EOD!"
                }
            })
            blocks.extend(format_slack_section(slack_data))
            blocks.append({"type": "divider"})
        else:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "✅ *All caught up!* No pending messages."}
            })
            blocks.append({"type": "divider"})

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
        "elements": [{"type": "mrkdwn", "text": "🌟 _Great work today! Rest well._"}]
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

    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    slack_data = None
    
    if bot_token:
        print("Fetching Slack data...")
        slack_data = fetch_slack_data(bot_token)
        if slack_data.get("error"):
            print(f"Warning: {slack_data['error']}")
    else:
        print("Warning: SLACK_BOT_TOKEN not set, skipping message fetch")

    summary_type = os.environ.get("SUMMARY_TYPE", "morning")
    template = load_template()

    if summary_type == "morning":
        message = build_morning_summary(template, slack_data)
    else:
        message = build_evening_summary(template, slack_data)

    post_to_slack(webhook_url, message)


if __name__ == "__main__":
    main()
