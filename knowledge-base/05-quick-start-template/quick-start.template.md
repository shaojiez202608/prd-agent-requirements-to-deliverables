# {{product_name}}: Quick-start Integration Guide

This guide is for developers who integrate the device with their own application. It describes the
data points the device exposes and the generic command/report pattern. Map the message shapes below onto
the protocol of your IoT platform; the shapes here are illustrative and not tied to any vendor.

## 1. Before you start

- A provisioned device of category {{product_category}} using {{connectivity}}.
- Credentials for your IoT platform. Keep them in your platform's secret store, never in source code.
- The thing model file thing-model.json shipped with this guide.

## 2. Provisioning

Supported provisioning methods:
{{provisioning}}

## 3. Data points

ID is the primary key. Use the ID when you send commands and when you parse reports.

<!-- dp-table:begin -->
{{dp_table}}
<!-- dp-table:end -->

Data types and ranges:

{{property_details}}

## 4. Reading values (report)

The device reports properties with access R or RW. Illustrative report body:

```
{{report_example}}
```

## 5. Changing values (command)

Only properties with access RW or W accept commands. Illustrative command body:

```
{{command_example}}
```

After a command, wait for the next report of the same ID before you treat the change as applied.

## 6. Offline behaviour

{{offline_behavior}}

## 7. Troubleshooting

- A command has no effect: check that the property access is RW or W and that the value is inside the range.
- Values look stale: check the report interval property, if the product has one, and the device connection.
- IDs do not match: regenerate this guide from thing-model.json and run the consistency check.
