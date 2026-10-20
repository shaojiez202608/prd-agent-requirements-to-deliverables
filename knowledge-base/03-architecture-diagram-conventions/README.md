# 03 Architecture diagram conventions

File: `architecture.mmd` (mermaid flowchart). Template: `architecture.template.mmd` in this folder.

Rules:
1. Four subgraphs, left to right: Device, Thing model, IoT cloud platform (generic), Client applications.
2. The Thing model subgraph has one node per property. Node label format, exactly:
   `"DP <id> <identifier> <access>"`, for example `dp1["DP 1 power_switch RW"]`. The validator reads these labels.
3. Edge labels say what flows: `report / command`, `state`, `command`. Dotted edges mean "defines" or "binds",
   not data flow.
4. Name the cloud side generically (connection and messaging, state store, rules). Do not name a vendor service
   unless the intake names it.
5. Put the connectivity from the intake on the device-to-cloud edge.
6. One diagram per product. If a diagram gets too wide, split the thing model into a second diagram with the same
   node label format rather than dropping properties.
