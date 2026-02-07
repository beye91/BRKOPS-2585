# WebEx Integration Setup Guide

## Overview

BRKOPS-2585 supports WebEx notifications via two methods:
1. **Incoming Webhook** (Simpler, recommended)
2. **Bot Token** (Full API access)

## Method 1: Incoming Webhook (Recommended)

### Step 1: Create Webhook in WebEx Space

1. Open WebEx Teams (desktop or web)
2. Navigate to the space where you want notifications
3. Click the space name → **Integrations & Bots**
4. Click **Add Integrations**
5. Search for **Incoming Webhooks**
6. Click **Add**
7. Name: "BRKOPS-2585 Notifications"
8. Copy the webhook URL (starts with `https://webexapis.com/v1/webhooks/incoming/...`)

### Step 2: Configure Environment Variable

Add to `.env` file or environment:
```bash
WEBEX_WEBHOOK_URL=https://webexapis.com/v1/webhooks/incoming/YOUR_WEBHOOK_ID
```

### Step 3: Test Connection

```bash
curl -X POST http://198.18.134.22:8003/api/v1/notifications/test/webex

# Expected response:
{"success": true, "method": "webhook", "message": "Connection test sent"}
```

## Method 2: Bot Token (Advanced)

### Step 1: Create WebEx Bot

1. Go to https://developer.webex.com/
2. Log in with your WebEx account
3. Click your profile picture (top right) → **My WebEx Apps**
4. Click **Create a New App**
5. Select **Create a Bot**
6. Fill in details:
   - Bot Name: "BRKOPS-2585 Network Ops Bot"
   - Bot Username: `brkops-netops` (must be unique)
   - Icon: Upload Cisco logo
   - Description: "Automated network operations notifications"
7. Click **Add Bot**
8. **IMPORTANT**: Copy the Bot Access Token immediately (shown only once)

### Step 2: Add Bot to WebEx Space

1. Create or open a WebEx space
2. Add the bot by email: `brkops-netops@webex.bot`
3. The bot will join the space

### Step 3: Get Room ID

```bash
# Using bot token, list all rooms
curl -X GET https://webexapis.com/v1/rooms \
  -H "Authorization: Bearer YOUR_BOT_TOKEN"

# Find your target room in JSON response and copy the "id" field
```

### Step 4: Configure Environment Variables

Add to `.env` file or environment:
```bash
WEBEX_BOT_TOKEN=Bearer YOUR_LONG_TOKEN_STRING
NOTIFICATIONS_WEBEX_ROOM_ID=YOUR_ROOM_ID
```

### Step 5: Test Connection

```bash
curl -X POST http://198.18.134.22:8003/api/v1/notifications/test/webex

# Expected response:
{"success": true, "method": "bot", "message": "Connection test sent"}
```

## Notification Features

### Rich Markdown Formatting

WebEx messages support markdown:
- **Bold text** with `**text**`
- *Italic text* with `*text*`
- `Code blocks` with backticks
- Lists, tables, and links

### Automated Notifications

Notifications are sent automatically at these stages:

1. **Pre-Deployment (AI Advice)**
   - Risk assessment
   - Recommended actions
   - Configuration summary

2. **Post-Deployment (Validation)**
   - Network state changes
   - Validation results
   - Rollback recommendations (if needed)

### Notification Severity Levels

- **SUCCESS** (✅): Clean deployment, no issues
- **WARNING** (⚠️): Deployment completed but with warnings
- **CRITICAL** (🔴): Deployment failed or rollback required

## Troubleshooting

### Webhook Issues

- Verify webhook URL is complete and starts with `https://webexapis.com/`
- Check that the WebEx space still exists
- Regenerate webhook if expired

### Bot Issues

- Verify bot token starts with `Bearer`
- Ensure bot is member of the target room
- Check room ID is correct (Base64-encoded string)
- Bot tokens don't expire but can be revoked

### No Messages Received

- Check backend logs: `docker logs brkops-backend`
- Verify use case has `notification_template.webex` configured
- Test with manual API call: `POST /api/v1/notifications/webex`
- Ensure WebEx space has not been archived or deleted

### Testing Notifications

To send a test notification:

```bash
curl -X POST http://198.18.134.22:8003/api/v1/notifications/test/webex \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Test notification from BRKOPS-2585"
  }'
```

## Configuration Management

### Via Environment Variables

Set in `.env` file:
```env
# Webhook method (simpler)
WEBEX_WEBHOOK_URL=https://webexapis.com/v1/webhooks/incoming/YOUR_ID

# OR Bot method (advanced)
WEBEX_BOT_TOKEN=Bearer YOUR_TOKEN
NOTIFICATIONS_WEBEX_ROOM_ID=YOUR_ROOM_ID
```

### Via Docker Compose

Update `docker-compose.yml`:
```yaml
services:
  backend:
    environment:
      - WEBEX_WEBHOOK_URL=${WEBEX_WEBHOOK_URL}
      # OR
      - WEBEX_BOT_TOKEN=${WEBEX_BOT_TOKEN}
      - NOTIFICATIONS_WEBEX_ROOM_ID=${NOTIFICATIONS_WEBEX_ROOM_ID}
```

### Via Admin UI

1. Navigate to http://198.18.134.22:3003/admin
2. Go to **Configuration** → **Notifications**
3. Add WebEx settings:
   - Webhook URL or Bot Token
   - Room ID (if using bot)
4. Click **Save**

## Security Best Practices

1. **Never commit tokens to git** - use `.env` or secrets management
2. **Rotate bot tokens periodically** - regenerate every 90 days
3. **Use webhooks when possible** - simpler and more secure
4. **Restrict room access** - only add necessary users
5. **Monitor notification logs** - check for unauthorized access

## Advanced Features

### Custom Templates

Customize notification templates per use case:

```json
{
  "webex": {
    "success": "✅ {{use_case}} completed on {{device}}",
    "warning": "⚠️ {{use_case}} completed with warnings: {{warnings}}",
    "critical": "🔴 CRITICAL: {{use_case}} failed - {{error}}"
  }
}
```

### Detailed Notifications

Enable detailed format in use case configuration:

```json
{
  "webex": {
    "use_detailed_format": true,
    "include_diff": true,
    "include_splunk_data": true
  }
}
```

Detailed messages include:
- Complete network state diffs (before/after)
- Splunk analysis event counts
- AI validation scores and findings
- Rollback commands (if applicable)
- Link to full details in UI

## Support

For issues or questions:
1. Check backend logs: `docker logs brkops-backend`
2. Review WebEx API status: https://status.webex.com/
3. Consult WebEx developer docs: https://developer.webex.com/docs/api/basics
4. Open issue in GitHub repository
