# 02 Thing model specification

File: `thing-model.json`, UTF-8, two-space indent, one key per line. Format tag `prd-agent/thing-model@1`.

```json
{
  "format": "prd-agent/thing-model@1",
  "product": {"name": "...", "category": "smart_plug", "connectivity": "wifi"},
  "properties": [
    {
      "id": 1,
      "identifier": "power_switch",
      "name": "Power switch",
      "access": "RW",
      "data_type": {"type": "bool"},
      "panel": {"control": "toggle", "interaction": "Tap to toggle; command/report loop"}
    }
  ]
}
```

| Key | Rule |
|---|---|
| id | Positive integer, unique, never reused for a different meaning (see 09 for change rules) |
| identifier | `^[a-z][a-z0-9_]{0,31}$`, unique |
| name | Human-readable control name |
| access | `R` (device reports), `RW` (reports and accepts commands), `W` (accepts commands only) |
| data_type.type | `bool`, `int`, `float`, `enum`, `string` |
| data_type.min/max/step/unit | Required for int and float |
| data_type.values | Required for enum, at least two |
| data_type.max_length | Required for string |
| panel.control / panel.interaction | Copied from the intake; used by the panel spec |

Properties are sorted by id. Keep `"id"` as the first key of each property; the validator uses the line of
`"id"` when it reports differences.

Structured values such as timer lists are modelled as `string` with a `max_length`. The encoding is not
guessed: the PRD lists it as an open item until the requester confirms it. A richer struct/array type is a possible extension (see OPEN-QUESTIONS.md).
