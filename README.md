<p align="center">
  <img src="https://raw.githubusercontent.com/AlirezaT/Gardena_Mower_BLE/main/brand/logo.png" alt="Gardena Mower BLE" width="360">
</p>

# Gardena Mower BLE

Local Bluetooth Low Energy control for Gardena robotic mowers in Home Assistant.

[Home Assistant Gardena mower, HACS Gardena mower
integration, Gardena robotic mower Bluetooth, Gardena BLE, Automower BLE, and
ESPHome Bluetooth proxy mower control]

This custom integration talks directly to the mower over BLE. It does not use the
cloud, and it exposes the mower as a Home Assistant lawn mower entity together
with controls, schedule editing, starting point settings, SpotCut, SensorControl,
and diagnostic telemetry.

The integration is based on the Home Assistant Automower BLE work, Gardena app
behavior, decompiled APK analysis, and HCI snoop logs from real mower/app
communication.

Mower communication is provided by the original
[`alistair23/AutoMower-BLE`](https://github.com/alistair23/AutoMower-BLE)
library, not a local fork or a PR branch. Version 3.08 pins upstream commit
[`4bf4b009`](https://github.com/alistair23/AutoMower-BLE/commit/4bf4b00959f9ef712b5e1beebd725b0c75c80637),
the latest upstream main revision checked on 2026-09-08. This includes the merged
Gardena commands (PR #148), SILENO sense 600/650 model additions (PR #159), and
clearer pairing diagnostics (PR #158). PyPI's latest `0.2.9` release predates these
changes. We pin a tested immutable revision for reproducible installations;
updates to upstream main are not installed automatically.

## Dashboard card

The companion [Gardena Mower Card](https://github.com/AlirezaT/gardena-mower-card)
brings animated mower status, battery and next-start information, Spot Cut and
parking controls, inline settings, lawn coverage, schedule access and grouped
diagnostics to your Home Assistant dashboard.

Install it separately through **HACS → Custom repositories**: add
`https://github.com/AlirezaT/gardena-mower-card` with type **Dashboard**.
See the [installation guide](https://github.com/AlirezaT/gardena-mower-card#install-with-hacs)
and [screenshot gallery](https://github.com/AlirezaT/gardena-mower-card#screenshots-and-animation).

<a href="https://github.com/AlirezaT/gardena-mower-card"><img src="https://raw.githubusercontent.com/AlirezaT/gardena-mower-card/v1.0.2/docs/mower-card.gif" alt="Full Gardena Mower Card showing animated mower status, battery, metrics and controls" width="440"></a>

The full-card animation uses simulated mower data. Available controls depend on
your mower and integration version.

## Highlights

- Local BLE connection, no cloud dependency.
- Home Assistant lawn mower entity with start, pause, and dock.
- Manual mowing duration control, persisted across restarts and integration
  reloads, including half-hour values.
- Weekly schedule calendar with create, update, and delete support.
- SpotCut switch with live state tracking.
- Starting point configuration, including charging station distance.
- Starting point mowing share validation so the total cannot exceed 100 percent.
- Drive past wire setting.
- SensorControl automatic mowing time adjustment and sensitivity.
- Battery, signal, orientation, sensor, hardware, software, and error diagnostics.
- Runtime fallbacks for commands that are not available on every mower model.

## Requirements

- Home Assistant `2026.5.1` or newer.
- A Bluetooth adapter supported by Home Assistant. (Tested with ESPHome + EPS32 as BLE proxy)
- A compatible Gardena BLE robotic mower. (Tested with Gardena Sileno minimo 250) 
- The mower PIN.
  ```txt
  - On/OFF Power button = 1
  - Go/Schedule button = 2
  - Go button = 3
  - Park button = 4
  ```
- The mower must be close enough for a reliable BLE connection.

## Installation

### HACS

1. Open HACS.
2. Add this repository as a custom repository.
3. Select category `Integration`.
4. Install `Gardena Mower BLE`.
5. Restart Home Assistant.
6. Add the integration from `Settings -> Devices & services`.

For the stable 3.08 release, select `v3.08` in HACS and restart Home Assistant.
Beta users can switch from `v3.08-beta.1` to this stable tag; the integration
code and upstream dependency are unchanged. Existing blueprint users upgrading
from 3.07.1 or earlier must also re-import the
blueprint using the URL below and reload automations. Updating the integration
does not update imported blueprints or flash ESPHome proxy firmware.

### Manual

1. Copy `custom_components/gardena_mower_ble` into your Home Assistant
   `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration from `Settings -> Devices & services`.

## ESPHome Bluetooth Proxy

This integration can work through a Home Assistant Bluetooth adapter or through
an ESPHome Bluetooth proxy. During development and testing, an ESP32 running
ESPHome Bluetooth proxy was used successfully.

Example ESPHome configuration:

```yaml
wifi:
  # Keep your existing Wi-Fi credentials and other options.
  power_save_mode: none

esp32_ble_tracker:
  scan_parameters:
    active: true
    continuous: true

bluetooth_proxy:
  active: true
  cache_services: true

```

Notes:

- Do not publish your mower MAC address or PIN/passkey in public logs or config
  examples.
- `bluetooth_proxy.active: true` is needed for Home Assistant to make active BLE
  connections through the proxy.
- `cache_services: true` helps avoid repeated full service discovery.
- Continuous scanning avoids scheduled gaps in mower discovery. Tracker
  `active` scanning and proxy `active` connections are separate settings.
- Remove any old timed `start_scan` actions when using continuous scanning.
- Keep Home Assistant's ESPHome Bluetooth scanning mode on Auto unless you
  intentionally want it to override the firmware scan setting.
- ESP-IDF is suitable for a dedicated proxy. For a combined light/proxy, check
  the light driver's framework requirements before switching frameworks; do
  not copy a dedicated proxy's framework blindly onto a lighting device.
- Avoid configuring the mower as an ESPHome `ble_client` at the same time as
  Home Assistant is using it. Only one client can maintain the mower connection
  reliably.

## Smart Dry-Weather Mowing Blueprint

This repository includes a generic Home Assistant automation blueprint:

```text
blueprints/automation/gardena_smart_mowing.yaml
```

The blueprint calculates mowing need from lawn surface and mower capacity, then
adjusts that baseline with weather, season, lawn type, grass type, recent rain,
temperature, humidity, and lawn exposure. It starts the mower only when the
weather forecast, dew model, and optional wetness blockers say the grass should
be dry enough. It updates the integration's `Manual Mowing Duration` number
before starting the mower, so the same blueprint can adjust session length
through the season.

It acts as a dynamic Home Assistant schedule instead of writing fixed onboard
mower schedule entries, which lets it react to changing rain forecasts.

The newer algorithm works like a small mowing budget:

- dry/warm/growing weather adds mowing debt
- manual and automatic mowing subtract real cutting time from that debt
- rainy, humid, dewy, or shaded conditions delay mowing until a dry window
- mower recharge pauses are treated as part of the same run until a grace period
  expires

The weekly budget is at least `minimum sessions × minimum session length`.
For example, five sessions of at least 60 minutes establish a 300-minute weekly
floor; a higher area/growth-based need still takes precedence. This prevents a
low growth estimate from defeating the configured minimum and postponing the
next session unnecessarily. It is a budget target, not a guarantee: rain,
excluded days, available dry windows and mower limits can still reduce mowing.

Inputs include:

- weather entity with hourly forecast; rainy-days reporting also uses the
  hourly forecast, so no separate daily forecast support is required
- lawn mower entity
- manual mowing duration number entity
- lawn area in square meters
- mower capacity in square meters per hour
- baseline weekly coverage multiplier
- lawn type, grass climate type, growth adjustment, and lawn exposure
- minimum and maximum sessions per week
- minimum and maximum session length
- excluded mowing weekdays; weekly mowing need is spread over the remaining days
- allowed mowing time window, either fixed or relative to sunrise/sunset
- rain forecast thresholds
- optional measured rainfall and irrigation totals, their shared lookback
  period, and optional soil moisture for water-aware growth estimates
- rainy-days report lookahead
- drying delay after rain and morning dew drying time
- optional binary sensors/helpers that block mowing, such as Smart Irrigation,
  rain, soil moisture, or leaf wetness sensors
- optional total cutting time sensor, used to measure real cutting duration
  across sessions split by battery charging

Create these helpers before using the blueprint:

- `input_datetime` for last rain/wetness detection
- `input_datetime` for last completed mow
- `input_datetime` for the current mowing start
- `input_text` for the compact fallback weekly mowing run log

Optional helpers:

- `input_number` for the cutting-time value at the start of the current smart
  mowing run
- `input_number` for accumulated mowing debt
- `input_datetime` for when mowing debt was last updated
- `input_datetime` for the next expected smart mowing start
- `input_text` for the estimated smart mowing schedule for the coming week
- `input_text` for the last schedule summary that was sent as a notification
- local `calendar` entity for full completed-run history and weekly reports
- `input_datetime` for last mower cleaning
- `input_datetime` for last blade change
- `input_number` for blade/cutting usage at the last blade change when using a
  lifetime counter
- optional `input_button` helpers for "refresh smart mowing schedule", "manual
  watering", "mower cleaned", and "blades changed"

### Measured Rainfall And Irrigation

Rainfall plus irrigation can adjust the estimated growth rate, separately from
the wet-grass safety blockers. Supply water totals for the same lookback period:
for example, rolling seven-day rainfall and irrigation totals require a
seven-day lookback. An irrigation volume needs the configured irrigated area
(or the full lawn area when that input is zero) to
convert it to water depth. AquaPrecise data can be used once suitable sensors
are exposed in Home Assistant; selecting a device alone does not provide totals.

When a configured total is unavailable, the blueprint falls back to soil
moisture, then its weather-based estimate, instead of interpreting missing data
as zero water. A valid zero total still indicates dry conditions. An unavailable
irrigation blocker is reported as unavailable, not falsely as active irrigation.

### Manual Irrigation Button

If you manually irrigate the lawn, create an `input_button` helper and select it
as the blueprint's optional manual watering button. Pressing it updates the same
last rain/wetness helper used by weather detection, so the blueprint treats
manual watering like rain and waits for the configured drying time before mowing
again. If `Dock mower when rain/wetness is detected` is enabled and the mower is
currently mowing, the button also sends a dock command.

For best weekly reports, create a Home Assistant **Local calendar** and select
it as the blueprint's mowing history calendar. `input_text` helpers are limited
to 255 characters in Home Assistant, so the calendar is the reliable place to
store every completed mowing run with start, end, and duration.

For smart mowing duration tracking, use the mower's **Total Cutting Time**
sensor. That counter is lifetime usage and should not be reset. For blade
maintenance, use **Cutting Blade Usage Time** when available. Because that
counter can be reset by the mower, you can leave the blade time-at-change helper
blank and optionally select the integration's **Reset Cutting Blade Usage Time**
button as the blueprint's mower blade usage reset button. If you use a lifetime
counter for blade maintenance instead, also configure the blade time-at-change
helper so the blueprint can calculate the delta since the last blade change.

If you configure the maintenance helpers, update the last cleaning helper after
cleaning the mower and the last blade change helper after changing blades. The
blueprint will then remind you based on days, weeks, and optional cutting/blade
usage time.

For dashboard buttons, create input button helpers and select them in the
blueprint's optional schedule refresh, manual watering, cleaning reset, and
blade-change reset inputs. Add the helpers to a dashboard entities card or
button card:

```yaml
type: entities
entities:
  - entity: input_button.smart_mowing_refresh
    name: Refresh mowing plan
  - entity: input_button.lawn_manually_watered
    name: Lawn watered
  - entity: input_button.mower_cleaned
    name: Mower cleaned
  - entity: input_button.mower_blades_changed
    name: Blades changed
```

The blueprint can also send persistent notifications and, optionally, a mobile
app notification service such as `notify.mobile_app_phone_name`.

Monitoring features:

- alert if the mower becomes unavailable
- alert if a start command does not result in mowing
- alert if a dock command after wet weather does not stop mowing
- alert if wet weather blocks mowing for too many days
- alert if a mowing run ends much earlier than planned
- alert if a run never resumes or completes after the recharge grace period
- count manually started mowing runs toward the smart schedule
- daily status feedback explaining why mowing is ready or blocked
- cleaning reminder after wet/humid mowing
- routine cleaning and blade-change reminders when helpers are configured
- store the next expected mowing start and an estimated weekly plan, respecting the mowing window, in optional
  helpers
- send a daily schedule-changed notification when the estimated smart mowing
  plan changes
- send a weekly persistent report with run day, start time, end time, and
  duration from the mowing history calendar when configured

Import URL:

```text
https://raw.githubusercontent.com/AlirezaT/Gardena_Mower_BLE/main/blueprints/automation/gardena_smart_mowing.yaml
```

## Supported Controls

| Entity | Type | What it does |
| --- | --- | --- |
| Lawn mower | Lawn mower | Start mowing, pause, and dock. |
| Manual Mowing Duration | Number | Duration used when starting manual mowing. |
| Spot Cut | Switch | Start or stop SpotCut mode. |
| SensorControl | Switch | Enable or disable automatic mowing time adjustment. |
| SensorControl Sensitivity | Select | Set SensorControl sensitivity: Low, Medium, or High. |
| Frost Sensor | Switch | Enable or disable frost-based mowing prevention when the writable command is supported. |
| Eco Mode | Switch | Disable the charging station loop signal while parked/charging. |
| Avoid Garage | Switch | Make the mower enter the charging station straight when a garage is installed. |
| Anti-collision Radar | Switch | Enable or disable the detected Anti-collision Radar accessory when available. |
| Drive Past Wire | Number | Configure how far the mower drives past the boundary wire. |
| Charging Station Starting Point Distance | Number | Set the first start point distance from the charging station. |
| Starting Point 1-3 | Switch | Enable or disable each manual starting point. |
| Starting Point 1-3 Distance | Number | Set each starting point distance. |
| Starting Point 1-3 Mowing Share | Number | Set mowing share for each starting point. |
| Starting Point 1-3 Wire | Select | Select boundary wire or guide wire for each starting point. |
| Starting Point 1-3 CorridorCut | Switch | Enable or disable CorridorCut per starting point. |
| Schedule | Calendar | View, create, update, and delete weekly mowing schedule tasks. |

### Buttons

| Button | Description |
| --- | --- |
| Diagnostic Refresh | Force a one-shot mower refresh including diagnostic telemetry. |
| Generate Loop Signal | Regenerate the charging station loop signal. |
| Reset Cutting Blade Usage Time | Reset the mower's cutting blade usage timer. |

## Supported Sensors

### Status

| Sensor | Description |
| --- | --- |
| Battery Level | Battery level in percent. |
| Activity | Current mower activity. |
| State | Current mower state. |
| Next Start Time | Next scheduled start time. |
| Remaining Charging Time | Remaining charging time. |
| Operator State | PIN/operator login state. |
| Spot Cutting | Current SpotCut state. |
| Charging Station Mowing Share | Remaining mowing share assigned to the charging station. |

### Errors And Messages

| Sensor | Description |
| --- | --- |
| Error Code | Current mower error code. |
| Error Description | Human readable description for known error codes. |
| Number Of Messages | Number of stored mower messages. |
| Last Message | Latest mower message entry. |

### Diagnostics

| Sensor | Description |
| --- | --- |
| Battery Voltage | Battery voltage in mV. |
| Battery Current | Battery current in mA. |
| Battery Temperature | Battery temperature. |
| Pitch / Roll | Realtime comboard pitch and roll. |
| Orientation Pitch / Orientation Roll | Orientation diagnostic pitch and roll. |
| Mower Temperature | Realtime mower temperature. |
| Signal Quality | Overall loop/guide signal quality. |
| A0 Signal | Boundary signal. |
| F Signal | F-signal. |
| N Signal | N-signal. |
| Guide 1/2/3 Signal | Guide wire signal values. |
| Message From Charging Station | Charging station message value. |
| Total Running Time | Lifetime running time. |
| Total Cutting Time | Lifetime cutting time. |
| Total Charging Time | Lifetime charging time. |
| Total Searching Time | Lifetime searching time. |
| Cutting Blade Usage Time | Blade usage time in hours. |
| Number Of Collisions | Lifetime collision count. |
| Number Of Charging Cycles | Lifetime charging cycle count. |

### Binary Sensors

| Binary sensor | Description |
| --- | --- |
| Collision | Realtime collision state. |
| Lift | Realtime lift state. |
| Upside Down | Realtime upside-down state. |
| In Charging Station | Whether the mower reports being in the charging station. |
| Frost Sensor Enabled | Frost sensor enabled state. |
| Garage Supported | Avoid-garage command support detected from the mower. |
| ZoneProtect Supported | Legacy ZoneProtect accessory bitmask, when reported by the mower. |
| Anti-collision Radar Available | Whether the mower reports an available Anti-collision Radar accessory. |

### Device Information

| Sensor | Description |
| --- | --- |
| Model | Detected mower model. |
| Mower Name | Name stored on the mower. |
| Serial Number | Mower serial number. |
| Hardware Serial Number | Hardware serial number. |
| Hardware Revision | Hardware revision. |
| Production Time | Production timestamp. |
| Node IPR ID | Node IPR identifier. |
| Husqvarna ID | Husqvarna identifier. |
| Boot Software Version | Boot software version. |
| Application Software Version | Application software version. |
| Sub Software Version | Sub software version. |

## Services

| Service | Description |
| --- | --- |
| `gardena_mower_ble.delete_schedule` | Delete one weekly schedule task. |
| `gardena_mower_ble.clear_schedule` | Delete all weekly schedule tasks. |
| `gardena_mower_ble.log_error_history` | Read mower message history and write it to the Home Assistant log. |
| `gardena_mower_ble.refresh_diagnostics` | Run a one-shot mower refresh including diagnostics. |

## Notes And Limitations

- BLE range and adapter quality matter. If updates are delayed or commands time
  out, move the adapter closer or use a better Bluetooth adapter.
- Not every mower model supports every BLE command. Unsupported features are
  disabled at runtime after the mower reports that a command is unavailable.
- Some diagnostic values are model and firmware dependent.
- The SILENO City restart/start report (#11) has software recovery coverage,
  but still needs confirmation on the affected physical mower. An explicit
  start can reconnect and retry once after an ambiguous/busy BLE response;
  state is checked before retrying to avoid replaying an accepted start.
- Loading the integration does not start mowing, clear schedules, or force an
  operating mode. Physical STOP/PIN/error states and firmware daily operating
  limits are not bypassed by the recovery logic.
- This is an unofficial community integration and is not affiliated with Gardena
  or Husqvarna.

## Troubleshooting

1. Confirm the mower is awake and within Bluetooth range.
2. Confirm the PIN is correct.
3. Restart Home Assistant after installing or updating the integration.
4. Enable debug logging for `custom_components.gardena_mower_ble` if you need to
   capture details for an issue.

Example `configuration.yaml` logging:

```yaml
logger:
  default: warning
  logs:
    custom_components.gardena_mower_ble: debug
    automower_ble: debug
```

## Credits

Thanks to Alistair Francis and the contributors to
[`AutoMower-BLE`](https://github.com/alistair23/AutoMower-BLE), the Home
Assistant Bluetooth mower work, the Gardena BLE community, and everyone
collecting HCI snoop logs and testing commands on real mowers.
