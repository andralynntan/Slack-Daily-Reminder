# Slack Daily Reminder

Automated daily summary posts to Slack at **8am CET** and **5pm CET**.

## Setup

### 1. Create a Slack Incoming Webhook

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Create a new app (or use existing) → "Incoming Webhooks"
3. Activate webhooks and create one for your target channel
4. Copy the webhook URL

### 2. Add GitHub Secret

1. Go to your repository Settings → Secrets and variables → Actions
2. Add a new secret:
   - Name: `SLACK_WEBHOOK_URL`
   - Value: Your Slack webhook URL

### 3. Customize Your Summary

Edit `summary_template.json` to customize what appears in your daily summaries.

## Schedule

| Time | Timezone | Purpose |
|------|----------|---------|
| 8:00 AM | CET (UTC+1/+2) | Morning briefing |
| 5:00 PM | CET (UTC+1/+2) | End-of-day recap |

## Manual Trigger

You can also trigger the summary manually:
1. Go to Actions → "Daily Slack Summary"
2. Click "Run workflow"
3. Select the summary type (morning/evening)

## Customization

- **summary_template.json**: Define the sections and content of your summaries
- **scripts/generate_summary.py**: Modify the summary generation logic
- **.github/workflows/daily-summary.yml**: Adjust schedule times
