/*
 * Hardware/transport abstraction for the demo skeleton.
 *
 * The skeleton does not depend on any vendor SDK. Implement these functions
 * on top of the connectivity stack of the selected module. hal_port_host.c is
 * a host-side stub that prints to stdout so the skeleton can be built and run
 * on a development machine.
 */
#ifndef HAL_PORT_H
#define HAL_PORT_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    uint16_t id;
    enum { DP_VAL_BOOL, DP_VAL_NUM, DP_VAL_STR } kind;
    bool b;
    double num;
    const char *str;
} dp_value_t;

/* Send one property report to the cloud. Returns 0 on success. */
int hal_dp_report(const dp_value_t *value);

/* Poll for one pending command. Returns 1 and fills *out if a command is waiting, 0 otherwise. */
int hal_dp_poll_command(dp_value_t *out);

/* Monotonic milliseconds. */
uint32_t hal_millis(void);

#endif /* HAL_PORT_H */
