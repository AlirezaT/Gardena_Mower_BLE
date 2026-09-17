# Robot error history

The GARDENA Bluetooth app reads this history from the mower, not from Home
Assistant's recorder. App 9.2.0's `ErrorHistoryViewModel` calls
`Mower.getNumberOfMessages`, caps the display at 50, and calls
`Mower.getSpecificMessage` for indexes 0–9, then subsequent chunks of ten.
The shared Messages protocol uses 4730/0 for the count and 4730/1 for an
indexed message (time uint32, code uint32, severity uint8). No model-specific
branch was found in this history UI; availability still depends on the robot.
Evidence: retained app DEX, the existing entity/model protocol audit, and
`ProtocolTypes.IMessagesSeverity`. No proprietary source is distributed here.

## Read it in Home Assistant

After installing a version containing this feature, open Developer Tools →
Actions and run:

```yaml
action: gardena_mower_ble.get_error_history
data:
  max_entries: 10
  offset: 0
```

The action returns an `entries` list with device index, raw error code,
model-aware description, severity number/name, raw `time`, and available
app-style date/time display fields. It also returns `total_messages`,
`available_messages` (capped at 50), `returned`, and `next_offset`.
Use `next_offset` for another page; null means the app-sized view is exhausted.
With multiple mowers, supply `config_entry_id` to select one explicitly.

For scripts/automations use Home Assistant's
[action response data](https://developers.home-assistant.io/docs/dev_101_services/#response-data):

```yaml
- action: gardena_mower_ble.get_error_history
  data:
    max_entries: 10
  response_variable: mower_history
- action: persistent_notification.create
  data:
    title: Mower error history
    message: >-
      {% for item in mower_history.entries %}
      {{ item.get('app_date', 'Unknown date') }}
      {{ item.get('app_time_24h', '') }} — {{ item.description }}
      ({{ item.code }}, {{ item.severity_name }})

      {% else %}No stored messages.{% endfor %}
```

The response action remains available separately from the cached sensor history
below. The existing `log_error_history` action remains available
unchanged for log-based diagnostics. Fetches do not change settings, acknowledge
or delete errors, or command mowing. No release or installed HA files are changed
merely by preparing this feature in the development repository.

## Limits and safety

- Default page: ten; maximum: 50; zero-based offset: 0–49.
- Messages remain in device index order. Do not infer guaranteed chronological
  ordering or deduplicate repeated errors.
- Raw timestamps are preserved. App date uses the local timezone while its time
  display uses UTC formatting; the absolute event-time interpretation remains
  unverified. Invalid timestamps do not remove otherwise valid entries.
- Severity 0–6 maps to unknown/fatal/error/warning/info/debug/software; other
  values and unknown error codes remain visible. History can contain more than
  just errors; entries are not filtered by severity.
- Unsupported commands, malformed entries, transport failures and partial reads
  raise an action error rather than returning a misleading empty/successful log.
- Reads are serialized and time-limited to 60 seconds. Count and first-entry
  rechecks detect common concurrent log changes, but the mower offers no atomic
  snapshot: separate pages can overlap if new messages arrive. Retry from zero.
- No persistent historical archive is added. The robot's own retention policy
  and app's 50-message display limit are not the same thing.

## Existing error entity and dashboard list

The existing Error Description and Error Code entities keep their current states
and gain these attributes:

- `reason`: description of the currently reported error.
- `error_history`: up to 50 stored messages with `code`, `description`, severity,
  raw `time`, and available `app_date` / `app_time_24h` display fields.
- `latest_stored_message`: index-zero record, separately from the current error.
  It is not proof of when the current error began, even if the codes match.
- `error_history_status`: `not_loaded`, `ready`, `stale`, or `unavailable`.
- `error_history_updated_at`: last successful full fetch time (not an error time).
- `error_history_total`, `error_history_limit`, `error_history_source`, and
  `error_history_order`.

The five-minute diagnostic poll compares the count and newest message with the
cache. A changed count/head or failed previous fetch triggers a full refresh.
The last complete history survives read failures but is marked stale. A genuine
empty robot log clears it. History is fetched again after integration reload;
no new sensor is created. Identical count/head cannot reveal changes deeper in
the robot log. Reading the standalone action does not update the sensor cache.

Add this standard Markdown card below the mower card (or in a vertical stack).
Replace the example entity ID with your existing Error Description entity. It
lists the fetched messages in device order, with date and reason; no custom card
dependency or change to the live dashboard is required.

```yaml
type: markdown
title: Mower error history
content: |-
  {% set entity = 'sensor.gardena_error_description' %}
  {% set status = state_attr(entity, 'error_history_status') %}
  {% set entries = state_attr(entity, 'error_history') or [] %}
  {% if status != 'ready' %}
  History status: {{ status or 'not loaded' }}. Entries may be outdated.
  {% endif %}
  {% for item in entries %}
  - **{{ item.get('app_date', 'Unknown date') }} {{ item.get('app_time_24h', '') }}** — {{ item.description }} (code {{ item.code }}, {{ item.severity_name }})
  {% else %}
  {{ 'No stored messages.' if status == 'ready' else 'History is not available yet.' }}
  {% endfor %}

  Dates/times follow the app display; absolute event times are unverified.
```

Validation uses simulated responses and existing regressions, not a fresh
physical comparison of all stored entries. Compare codes/severity and displayed
times with the app on the same robot before relying on event chronology.
