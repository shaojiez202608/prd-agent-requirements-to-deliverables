# {{product_name}}: Requirements Specification (PRD)

> Generated from a structured intake (schema {{schema_version}}, form {{variant}}).
> The thing model file `thing-model.json` is the single source of truth for property ID, identifier and access.
> This document must not change those three values.

## 1. Background and scenario

- Scene category: {{scene_category}}
- Scenario: {{scene_description}}
- Pain points:
{{pain_points}}
- End users:
{{end_users}}

## 2. Scope

In scope for this iteration:
{{deliverables}}

Out of scope:
- Visual polish of the panel. The panel specification guarantees structure and ID mapping only.
- Production hardening of the device firmware.
- Any value that the intake did not provide. Such items are listed in section 9.

## 3. Hardware and device side

| Item | Value |
|---|---|
| Product category | {{product_category}} |
| Connectivity | {{connectivity}} |
| Power supply | {{power_supply}} |
| Device architecture | {{architecture_mode}} |
| Module selection | {{module_selection}} |
| Firmware | {{firmware_custom}} |
| Channels | {{channels}} |

## 4. Functional requirements (thing model)

Control to thing model mapping. ID is the primary key.

<!-- dp-table:begin -->
{{dp_table}}
<!-- dp-table:end -->

### 4.1 Property details

{{property_details}}

## 5. Cloud panel and application side

- Client application types:
{{app_types}}
- Network provisioning:
{{provisioning}}
- Login methods:
{{login}}
- Panel style: {{panel_style}}
- Data presentation:
{{data_presentation}}

## 6. App interaction flow

{{interaction_flow}}

## 7. Constraints and non-functional requirements

- Offline behaviour: {{offline_behavior}}
- Security and privacy: {{security_privacy_notes}}
- Command handling: every writable property follows a command/report loop. The panel shows the new value
  only after the device reports it; until then the control shows a pending state.

## 8. Acceptance criteria

{{acceptance_criteria}}

## 9. Open items to confirm

{{open_items}}

## 10. Deliverable index

{{deliverable_index}}
