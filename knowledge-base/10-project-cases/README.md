# 10 Project cases

Cases show how the rules are applied. They never override 00 to 09.

## Case 1: Demo Smart Plug (synthetic)

- Intake (PM form): `sample-data/smart-plug.pm.intake.json`
- Intake (frontline form, incomplete on purpose): `sample-data/smart-plug.frontline.intake.json`
- Intake with missing fields: `sample-data/smart-plug.missing-fields.intake.json`
- Iteration 2 (adds child lock, widens report interval): `sample-data/smart-plug.pm.v2.intake.json`
- Full generated output: `examples/smart-plug/`

Thing model used throughout:

| Control | Identifier | ID | Access | Interaction |
|---|---|---|---|---|
| Power switch | power_switch | 1 | RW | Tap to toggle; command/report loop |
| Active power | active_power | 2 | R | Read-only number with a small trend chart |
| Overload alarm | overload_alarm | 3 | R | Read-only; shown in red while the alarm is active |
| Overload protection | overload_protect | 4 | RW | Slide switch; command/report loop |
| Timer tasks | timer_task | 5 | RW | List with add/edit/delete; wait for device report after each command |
| Report interval | report_interval | 6 | RW | Slider in minutes; command/report loop |

Lessons encoded as rules:
- IDs drifted between documents when each was written separately: R2 and the validator.
- Vague intake led to guessed values: R1 and the pending-item rules in 01.
- Long generations stopped after the outline: R3, R4 and the progress protocol in 08.
- The panel looked fine but was not usable: the state table and interaction flow in 06.

### Case 1, step 2: insufficient input

`prd-agent check-intake sample-data/smart-plug.missing-fields.intake.json` lists four pending items and exits 2.
What the agent does in CLARIFY_ONLY mode is turn each into a question, for example:

| Pending item | Question for the requester |
|---|---|
| `[missing] hardware.connectivity` | Which connectivity does the plug use (for example Wi-Fi or Bluetooth LE)? |
| `[missing] thing_model.properties[1].unit` | What is the unit of active power? |
| `[conflict] thing_model.properties[5].id` | ID 5 is used twice. Which ID should the report interval get? |
| `[missing] app.provisioning` | Which provisioning methods must the app support? |

No default is proposed and no file is written.

### Case 1, step 3: iteration

`prd-agent diff-model` between the v1 and v2 thing models (the v2 intake adds a child lock and widens the report
interval):

```
2 change(s), 0 breaking.
- ID 6 changed [compatible]: max 60 -> 120
- ID 7 added [compatible]: child_lock (RW, bool)
```

The new property gets a new ID (7). No existing ID is reused, so firmware and apps built for v1 keep working.
The change log goes into the PRD of v2, and the bundle is published under a new name (`-v2`).

## Coverage of this folder

This folder holds one synthetic product. It shows the rules on a single small device class (one Wi-Fi plug,
six properties). It does not yet contain cases for gateways and sub-devices, multi-channel devices, struct-like
properties or a real project retrospective. Add sanitised real cases here before relying on the knowledge base
for other product classes (see docs/handover.md).
