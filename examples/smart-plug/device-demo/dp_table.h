/*
 * Demo Smart Plug: data point table (generated from thing-model.json).
 *
 * Do not edit IDs, identifiers or access here by hand. Change thing-model.json,
 * regenerate, then run `prd-agent validate` on the output folder.
 */
#ifndef DP_TABLE_H
#define DP_TABLE_H

#include <stdint.h>

typedef enum { DP_R = 1, DP_W = 2, DP_RW = 3 } dp_access_t;
typedef enum { DP_TYPE_BOOL, DP_TYPE_INT, DP_TYPE_FLOAT, DP_TYPE_ENUM, DP_TYPE_STRING } dp_type_t;

typedef struct {
    uint16_t id;
    const char *identifier;
    dp_access_t access;
    dp_type_t type;
} dp_def_t;

#define DP_DEFINE(id_, ident_, access_, type_) { (id_), (ident_), (access_), (type_) }

/* Property IDs */
#define DP_ID_POWER_SWITCH 1
#define DP_ID_ACTIVE_POWER 2
#define DP_ID_OVERLOAD_ALARM 3
#define DP_ID_OVERLOAD_PROTECT 4
#define DP_ID_TIMER_TASK 5
#define DP_ID_REPORT_INTERVAL 6

#define DP_COUNT 6

static const dp_def_t DP_TABLE[DP_COUNT] = {
    DP_DEFINE(1, "power_switch", DP_RW, DP_TYPE_BOOL),
    DP_DEFINE(2, "active_power", DP_R, DP_TYPE_FLOAT),
    DP_DEFINE(3, "overload_alarm", DP_R, DP_TYPE_BOOL),
    DP_DEFINE(4, "overload_protect", DP_RW, DP_TYPE_BOOL),
    DP_DEFINE(5, "timer_task", DP_RW, DP_TYPE_STRING),
    DP_DEFINE(6, "report_interval", DP_RW, DP_TYPE_INT),
};

#endif /* DP_TABLE_H */
