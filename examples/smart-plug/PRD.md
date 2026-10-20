# Demo Smart Plug: Requirements Specification (PRD)

> Generated from a structured intake (schema 1.0, form pm).
> The thing model file `thing-model.json` is the single source of truth for property ID, identifier and access.
> This document must not change those three values.

## 1. Background and scenario

- Scene category: Smart home
- Scenario: Households want to switch plugged-in appliances remotely, see the current power draw and be warned about overload.
- Pain points:
  - Remote monitoring is hard
  - Faults are not alerted in time
  - Coarse energy management
- End users:
  - Consumers
  - After-sales staff

## 2. Scope

In scope for this iteration:
- Thing model (JSON)
- Product architecture diagram (mermaid)
- Quick-start integration guide (Markdown -> PDF)
- Requirements specification / PRD (Markdown)
- Panel interaction spec (Markdown + HTML)
- Device-side demo skeleton (C)

Out of scope:
- Visual polish of the panel. The panel specification guarantees structure and ID mapping only.
- Production hardening of the device firmware.
- Any value that the intake did not provide. Such items are listed in section 9.

## 3. Hardware and device side

| Item | Value |
|---|---|
| Product category | Smart plug |
| Connectivity | Wi-Fi |
| Power supply | Mains |
| Device architecture | Single-chip (application runs on the connectivity module) |
| Module selection | To be decided |
| Firmware | Custom firmware |
| Channels | 1 |

## 4. Functional requirements (thing model)

Control to thing model mapping. ID is the primary key.

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

### 4.1 Property details

- ID 1 `power_switch` (Power switch): bool (true/false)
- ID 2 `active_power` (Active power): float, range 0 to 99999, step 0.1, unit W
- ID 3 `overload_alarm` (Overload alarm): bool (true/false)
- ID 4 `overload_protect` (Overload protection): bool (true/false)
- ID 5 `timer_task` (Timer tasks): string, max length 1024
- ID 6 `report_interval` (Report interval): int, range 1 to 60, step 1, unit min

## 5. Cloud panel and application side

- Client application types:
  - Mobile app
- Network provisioning:
  - Hotspot (SoftAP)
  - BLE-assisted
- Login methods:
  - Phone number + one-time code
  - Email
- Panel style: Minimal
- Data presentation:
  - Generic property list
  - Statistics charts

## 6. App interaction flow

1. Sign in (Phone number + one-time code or Email).
2. Add device: provisioning by Hotspot (SoftAP) or BLE-assisted. On failure show the reason and a retry action.
3. Device appears in the device list with its online state.
4. Open the panel: controls load the last reported values; writable controls are disabled until the first report.
5. Change a writable control: send the command, show the pending state, update only when the device reports.
6. Device goes offline: apply the offline behaviour (section 7); re-enable controls on the next report.

## 7. Constraints and non-functional requirements

- Offline behaviour: Panel greys out writable controls and shows the last reported values with their timestamp.
- Security and privacy: No personal data is stored on the device. Credentials are never written to logs.
- Command handling: every writable property follows a command/report loop. The panel shows the new value
  only after the device reports it; until then the control shows a pending state.

## 8. Acceptance criteria

1. A switch command changes the panel state only after the device reports the new state.
2. The overload alarm is shown in red within one report cycle after the device raises it.
3. Timer tasks created in the panel are listed again after an app restart.
4. Changing the report interval changes how often active_power is reported.

## 9. Open items to confirm

- Module selection is to be decided. The device skeleton uses a host stub until then.
- Note from intake: Rated power is a placeholder in this synthetic example; take it from the hardware datasheet.
- Encoding of string property ID 5 `timer_task` (for example a list format) is not in the intake; confirm before device and app work start.
- Command timeout and retry policy of the app are not part of the intake; confirm with the app team.

## 10. Deliverable index

- Thing model (JSON): `thing-model.json`
- Product architecture diagram (mermaid): `architecture.mmd`
- Quick-start integration guide (Markdown -> PDF): `quick-start.md`, `quick-start.pdf`
- Requirements specification / PRD (Markdown): `PRD.md`
- Panel interaction spec (Markdown + HTML): `panel-spec.md`, `panel-preview.html`
- Device-side demo skeleton (C): `device-demo/dp_table.h`, `device-demo/app_main.c`, `device-demo/hal_port.h`, `device-demo/hal_port_host.c`, `device-demo/README.md`
