# Demo Smart Plug: Panel Interaction Specification

Scope: structure, states and thing model mapping of the device panel. Visual design is out of scope.
Panel style requested: Minimal. Data presentation: Generic property list, Statistics charts.

## 1. Control to thing model mapping

Every control is bound to exactly one property ID. The preview file panel-preview.html shows the same IDs.

<!-- dp-table:begin -->
| Control | Identifier | ID | Access | Interaction |
|---|---|---|---|---|
| Power switch | `power_switch` | 1 | RW | Tap to toggle; command/report loop |
| Active power | `active_power` | 2 | R | Read-only number with a small trend chart |
| Overload alarm | `overload_alarm` | 3 | R | Read-only; shown in red while the alarm is active |
| Overload protection | `overload_protect` | 4 | RW | Slide switch; command/report loop |
| Timer tasks | `timer_task` | 5 | RW | List with add/edit/delete; wait for device report after each command |
| Report interval | `report_interval` | 6 | RW | Slider in minutes; command/report loop |
<!-- dp-table:end -->

## 2. Layout (top to bottom)

1. Card `power_switch` (ID 1): Toggle
2. Card `active_power` (ID 2): Value display
3. Card `overload_alarm` (ID 3): Alarm indicator
4. Card `overload_protect` (ID 4): Toggle
5. Card `timer_task` (ID 5): List editor
6. Card `report_interval` (ID 6): Slider

## 3. Control states

| State | Meaning | Panel behaviour |
|---|---|---|
| reported | Last value reported by the device | Show the value |
| pending | Command sent, no matching report yet | Show a pending marker on the control; do not show the new value yet |
| failed | No report within the timeout configured by the app | Revert to the last reported value and show a short error |
| offline | Device is offline | Panel greys out writable controls and shows the last reported values with their timestamp. |

## 4. App interaction flow

1. Sign in (Phone number + one-time code or Email).
2. Add device: provisioning by Hotspot (SoftAP) or BLE-assisted. On failure show the reason and a retry action.
3. Device appears in the device list with its online state.
4. Open the panel: controls load the last reported values; writable controls are disabled until the first report.
5. Change a writable control: send the command, show the pending state, update only when the device reports.
6. Device goes offline: apply the offline behaviour (offline state in section 3); re-enable controls on the next report.

## 5. Per-control behaviour

- ID 1 `power_switch` (RW), Toggle: Tap to toggle; command/report loop. Uses the command/report loop.
- ID 2 `active_power` (R), Value display: Read-only number with a small trend chart.
- ID 3 `overload_alarm` (R), Alarm indicator: Read-only; shown in red while the alarm is active.
- ID 4 `overload_protect` (RW), Toggle: Slide switch; command/report loop. Uses the command/report loop.
- ID 5 `timer_task` (RW), List editor: List with add/edit/delete; wait for device report after each command. Uses the command/report loop.
- ID 6 `report_interval` (RW), Slider: Slider in minutes; command/report loop. Uses the command/report loop.
