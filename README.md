<p align="center">
  <img src="https://raw.githubusercontent.com/AlirezaT/Gardena_Mower_BLE/main/brand/logo.png" alt="Gardena Mower BLE" width="360">
</p>

# Gardena Mower BLE

Local Bluetooth Low Energy control for Gardena robotic mowers in Home Assistant.

This custom integration talks directly to the mower over BLE. It does not use the
cloud, and it exposes the mower as a Home Assistant lawn mower entity together
with controls, schedule editing, starting point settings, SpotCut, SensorControl,
and diagnostic telemetry.

The integration is based on the Home Assistant Automower BLE work, Gardena app
behavior, decompiled APK analysis, and HCI snoop logs from real mower/app
communication.

## Highlights

- Local BLE connection, no cloud dependency.
- Home Assistant lawn mower entity with start, pause, and dock.
- Manual mowing duration control.
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
- A Bluetooth adapter supported by Home Assistant.
- A compatible Gardena BLE robotic mower.
- The mower PIN.
- The mower must be close enough for a reliable BLE connection.

## Installation

### HACS

1. Open HACS.
2. Add this repository as a custom repository.
3. Select category `Integration`.
4. Install `Gardena Mower BLE`.
5. Restart Home Assistant.
6. Add the integration from `Settings -> Devices & services`.

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
esp32_ble_tracker:
  scan_parameters:
    active: false
    continuous: false
    duration: 50sec

bluetooth_proxy:
  active: true
  cache_services: true

time:
  - platform: homeassistant
    on_time:
      - seconds: 0
        minutes: "*"
        then:
          - esp32_ble_tracker.start_scan:
```

Notes:

- Do not publish your mower MAC address or PIN/passkey in public logs or config
  examples.
- `bluetooth_proxy.active: true` is needed for Home Assistant to make active BLE
  connections through the proxy.
- `cache_services: true` helps avoid repeated full service discovery.
- Non-continuous scanning is gentler on the BLE environment. The example starts
  a scan once per minute for 50 seconds.
- Avoid configuring the mower as an ESPHome `ble_client` at the same time as
  Home Assistant is using it. Only one client can maintain the mower connection
  reliably.

## Supported Controls

| Entity | Type | What it does |
| --- | --- | --- |
| Lawn mower | Lawn mower | Start mowing, pause, and dock. |
| Manual Mowing Duration | Number | Duration used when starting manual mowing. |
| Spot Cut | Switch | Start or stop SpotCut mode. |
| SensorControl | Switch | Enable or disable automatic mowing time adjustment. |
| SensorControl Sensitivity | Select | Set SensorControl sensitivity: Low, Medium, or High. |
| Drive Past Wire | Number | Configure how far the mower drives past the boundary wire. |
| Charging Station Starting Point Distance | Number | Set the first start point distance from the charging station. |
| Starting Point 1-3 | Switch | Enable or disable each manual starting point. |
| Starting Point 1-3 Distance | Number | Set each starting point distance. |
| Starting Point 1-3 Mowing Share | Number | Set mowing share for each starting point. |
| Starting Point 1-3 Wire | Select | Select boundary wire or guide wire for each starting point. |
| Starting Point 1-3 CorridorCut | Switch | Enable or disable CorridorCut per starting point. |
| Schedule | Calendar | View, create, update, and delete weekly mowing schedule tasks. |

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
| Cutting Blade Usage Time | Blade usage time. |
| Number Of Collisions | Lifetime collision count. |
| Number Of Charging Cycles | Lifetime charging cycle count. |

### Binary Sensors

| Binary sensor | Description |
| --- | --- |
| Collision | Realtime collision state. |
| Lift | Realtime lift state. |
| Upside Down | Realtime upside-down state. |
| In Charging Station | Whether the mower reports being in the charging station. |
| Frost Sensor Enabled | Frost sensor enabled state. Read-only for now. |

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
- Frost sensor enable is currently exposed as read-only because the HCI logs
  confirmed the read command, but not a safe write command.
- Some diagnostic values are model and firmware dependent.
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
```

## Credits

Thanks to the Home Assistant Bluetooth mower work, the Gardena BLE community,
and everyone collecting HCI snoop logs and testing commands on real mowers.
