# v3.94 — stable Start, parking and recovery improvements

Stable release promoted from `v3.94.0-beta.10`, with no runtime code changes.
Release tag: `v3.94`. Manifest version: `3.94`.

## Changes since v3.93

- P0 timed Start uses AUTO → SetOverrideMow → StartTrigger without a preliminary
  ClearOverride. One bounded departure observer replaces duplicated confirmation
  reads, with five seconds before and between status samples. Charging or an OK
  acknowledgement alone is not confirmed departure on this P0 service path.
- Uncertain Start outcomes never automatically replay movement or force an
  action-level recovery reconnect. Ordinary transport cleanup and later polling
  still handle failed sessions. Existing STOP/PIN/error checks remain.
- Dock configures its model-specific parking target before StartTrigger and
  checks fresh state afterward. Return Home defaults to Until further notice;
  saved preferences also offer For a duration and Until next schedule. An existing
  indefinite hold is preserved until an explicit Start or Resume schedule action.
- If an onboard task read succeeds and finds no tasks, next-schedule parking
  falls back to indefinite parking. Failed or malformed reads are not empty schedules.
- The calendar preserves whole-second schedule times and stays registered but
  unavailable after a failed read, recovering on a successful retry. No automatic
  rewriting of onboard schedules or mower clock is introduced.
- Start/Dock confirmation defers background polling and calendar reads while
  keeping explicit controls and KeepAlive eligible. History reads release the
  command lock between entries. Optional static-information failures back off for
  five minutes; connection discovery allows up to ten seconds for rediscovery.
- Debug logs include command/lock timing, local action/session identifiers and
  response provenance. P0 Start captures fresh mode, override, restriction and
  charging context before safety checks and movement writes. Firmware parsing
  accepts the application-version format reported by older City models.

## Validation and field feedback

- 243 automated tests pass against the pinned upstream dependency. Release-tag
  matching, Home Assistant version parsing, compilation and whitespace checks pass.
- On September 29, the [issue #11 reporter confirmed beta.10 automation working
  without reboots or unknown states](https://github.com/AlirezaT/Gardena_Mower_BLE/issues/11#issuecomment-5895222967).
  The attached HA history shows mowing, returning and docking. His suggestion that
  earlier tests were too soon after restarting is not an established root cause;
  no new diagnostic log or HCI capture accompanies that confirmation.
- [Issue #10 also received a successful-test reply](https://github.com/AlirezaT/Gardena_Mower_BLE/issues/10#issuecomment-5783157921)
  after the beta.5 test request and is closed. That is not a separate beta.10 test.
- Existing maintainer Minimo feedback remains positive. This promotion adds no
  new hardware-test claim and does not claim to resolve every pairing, docking
  or firmware-reboot problem on every model.

The original AutoMower-BLE dependency remains pinned to upstream commit `4bf4b009`;
gardena-bluetooth remains at 2.8.1. Minimo Start and SpotCut, blueprint and proxy
firmware are unchanged. No speculative changes from the later HCI comparison
are included. Historical beta notes remain available as testing history.

## Installation

Install `v3.94` through HACS and restart Home Assistant. From beta.10, only release
metadata and documentation change. No forced re-pairing, blueprint re-import or
proxy firmware update is required. Close the official app when using HA control
and wait for updated entities after a mower restart. If a movement outcome is
uncertain, check the physical mower before retrying.
