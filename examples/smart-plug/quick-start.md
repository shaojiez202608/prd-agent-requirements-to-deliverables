# Demo Smart Plug: Quick-start Integration Guide

This guide is for developers who integrate the device with their own application. It describes the
data points the device exposes and the generic command/report pattern. Map the message shapes below onto
the protocol of your IoT platform; the shapes here are illustrative and not tied to any vendor.

## 1. Before you start

- A provisioned device of category Smart plug using Wi-Fi.
- Credentials for your IoT platform. Keep them in your platform's secret store, never in source code.
- The thing model file thing-model.json shipped with this guide.

## 2. Provisioning

Supported provisioning methods:
  - Hotspot (SoftAP)
  - BLE-assisted

## 3. Data points

ID is the primary key. Use the ID when you send commands and when you parse reports.

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

Data types and ranges:

- ID 1 `power_switch` (Power switch): bool (true/false)
- ID 2 `active_power` (Active power): float, range 0 to 99999, step 0.1, unit W
- ID 3 `overload_alarm` (Overload alarm): bool (true/false)
- ID 4 `overload_protect` (Overload protection): bool (true/false)
- ID 5 `timer_task` (Timer tasks): string, max length 1024
- ID 6 `report_interval` (Report interval): int, range 1 to 60, step 1, unit min

## 4. Reading values (report)

The device reports properties with access R or RW. Illustrative report body:

```
{
  "1": true,
  "2": 0,
  "3": true
}
```

## 5. Changing values (command)

Only properties with access RW or W accept commands. Illustrative command body:

```
{
  "1": true
}
```

After a command, wait for the next report of the same ID before you treat the change as applied.

## 6. Offline behaviour

Panel greys out writable controls and shows the last reported values with their timestamp.

## 7. Troubleshooting

- A command has no effect: check that the property access is RW or W and that the value is inside the range.
- Values look stale: check the report interval property, if the product has one, and the device connection.
- IDs do not match: regenerate this guide from thing-model.json and run the consistency check.
