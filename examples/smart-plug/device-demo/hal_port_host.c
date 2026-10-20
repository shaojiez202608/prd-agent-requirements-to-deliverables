/* Host-side stub of hal_port.h for building and running the skeleton on a PC. */
#include <stdio.h>
#include "hal_port.h"

static uint32_t fake_clock_ms = 0;
static int commands_left = 1;

int hal_dp_report(const dp_value_t *v) {
    switch (v->kind) {
    case DP_VAL_BOOL: printf("report id=%u value=%s\n", (unsigned)v->id, v->b ? "true" : "false"); break;
    case DP_VAL_NUM:  printf("report id=%u value=%g\n", (unsigned)v->id, v->num); break;
    case DP_VAL_STR:  printf("report id=%u value=\"%s\"\n", (unsigned)v->id, v->str ? v->str : ""); break;
    }
    return 0;
}

int hal_dp_poll_command(dp_value_t *out) {
    if (commands_left-- <= 0) return 0;
    /* Simulate one command for the first writable bool property in the table. */
    out->id = 0; /* 0 means: let app_main pick the demo target */
    out->kind = DP_VAL_BOOL;
    out->b = true;
    out->num = 0;
    out->str = 0;
    return 1;
}

uint32_t hal_millis(void) { fake_clock_ms += 1000; return fake_clock_ms; }
