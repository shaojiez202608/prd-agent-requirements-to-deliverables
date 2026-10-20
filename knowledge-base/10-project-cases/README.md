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
