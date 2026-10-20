/*
 * {{product_name}}: device-side demo skeleton.
 *
 * Structure only: command dispatch by property ID and the command/report loop.
 * Fill in the TODO blocks with real hardware access. Build on a PC with:
 *   cc -std=c99 -Wall -Wextra -o demo app_main.c hal_port_host.c
 */
#include <stdio.h>
#include <string.h>
#include "dp_table.h"
#include "hal_port.h"

static const dp_def_t *dp_find(uint16_t id) {
    for (int i = 0; i < DP_COUNT; i++) {
        if (DP_TABLE[i].id == id) return &DP_TABLE[i];
    }
    return NULL;
}

/* Apply a command to the hardware, then report the resulting state (command/report loop). */
static void handle_command(const dp_value_t *cmd) {
    const dp_def_t *def = dp_find(cmd->id);
    if (def == NULL || (def->access & DP_W) == 0) {
        printf("reject command id=%u (unknown or not writable)\n", (unsigned)cmd->id);
        return;
    }
    switch (cmd->id) {
{{command_cases}}
    default:
        break;
    }
    hal_dp_report(cmd); /* report the applied value so the panel can leave the pending state */
}

static void report_all(void) {
{{report_calls}}
}

int main(void) {
    printf("demo start: %d data points\n", DP_COUNT);
    report_all();
    dp_value_t cmd;
    while (hal_dp_poll_command(&cmd)) {
        if (cmd.id == 0) cmd.id = {{demo_command_id}};
        handle_command(&cmd);
    }
    printf("demo end\n");
    return 0;
}
