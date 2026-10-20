/*
 * {{product_name}}: data point table (generated from thing-model.json).
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
{{id_defines}}

#define DP_COUNT {{dp_count}}

static const dp_def_t DP_TABLE[DP_COUNT] = {
{{dp_defines}}
};

#endif /* DP_TABLE_H */
