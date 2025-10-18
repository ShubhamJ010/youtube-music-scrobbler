#!/bin/bash

set -e

log_content="${SCROBBLE_LOG}"
# Escape for JSON
log_content="${log_content//\\/\\\\}"
log_content="${log_content//"/\"}"

# Replace newlines with \n
log_content_escaped_newlines=""
while IFS= read -r line; do
  log_content_escaped_newlines+="$line\n"
done <<< "$log_content"
log_content="$log_content_escaped_newlines"


if [ ${#log_content} -gt 1980 ]; then
  log_content="$(echo "$log_content" | cut -c 1-1980)... (log truncated)"
fi

json_payload=$(printf '{"content": "YouTube Music Scrobble Sync succeeded!", "embeds": [{"title": "Scrobble Log", "description": "```\n%s\n```"}]}' "$log_content")

curl -H "Content-Type: application/json" -d "$json_payload" "$DISCORD_WEBHOOK_URL"