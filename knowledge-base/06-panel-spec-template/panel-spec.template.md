# {{product_name}}: Panel Interaction Specification

Scope: structure, states and thing model mapping of the device panel. Visual design is out of scope.
Panel style requested: {{panel_style}}. Data presentation: {{data_presentation_inline}}.

## 1. Control to thing model mapping

Every control is bound to exactly one property ID. The preview file panel-preview.html shows the same IDs.

<!-- dp-table:begin -->
{{dp_table}}
<!-- dp-table:end -->

## 2. Layout (top to bottom)

{{layout}}

## 3. Control states

| State | Meaning | Panel behaviour |
|---|---|---|
| reported | Last value reported by the device | Show the value |
| pending | Command sent, no matching report yet | Show a pending marker on the control; do not show the new value yet |
| failed | No report within the timeout configured by the app | Revert to the last reported value and show a short error |
| offline | Device is offline | {{offline_behavior}} |

## 4. App interaction flow

{{panel_interaction_flow}}

## 5. Per-control behaviour

{{control_behaviour}}
