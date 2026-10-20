# 07 Device-side demo skeleton

Templates: `dp_table.h.tpl`, `app_main.c.tpl`, `README.md.tpl`; static files `hal_port.h`, `hal_port_host.c`.

- Plain C99, no vendor SDK. `hal_port.h` is the seam to the real module stack.
- `dp_table.h` carries `#define DP_ID_<IDENTIFIER> <id>` and `DP_DEFINE(<id>, "<identifier>", DP_<access>, <type>)`.
  The validator reads both.
- `app_main.c` dispatches commands by ID, rejects commands to non-writable IDs, and reports the applied value
  (command/report loop).
- The skeleton builds and runs on a PC with the host stub:
  `cc -std=c99 -Wall -Wextra -o demo app_main.c hal_port_host.c`.
