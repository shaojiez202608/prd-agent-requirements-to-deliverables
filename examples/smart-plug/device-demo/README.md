# Demo Smart Plug: device-side demo skeleton

Generated from thing-model.json. This is a structure skeleton, not firmware.

| File | Purpose |
|---|---|
| dp_table.h | Property IDs, identifiers and access copied from thing-model.json |
| app_main.c | Command dispatch by property ID and the command/report loop |
| hal_port.h | Transport abstraction; implement it on the selected module's stack |
| hal_port_host.c | Host stub so the skeleton builds and runs on a PC |

Build and run on a PC (any C99 compiler):

```
cc -std=c99 -Wall -Wextra -o demo app_main.c hal_port_host.c
./demo
```

Device architecture from intake: Single-chip (application runs on the connectivity module). Module selection: To be decided.
Replace hal_port_host.c with a port for the real module once it is selected.
