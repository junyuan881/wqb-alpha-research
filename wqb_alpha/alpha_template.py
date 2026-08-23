"""Default alpha template and search space.

This file is deliberately separate from the genetic-search implementation so you can
change research hypotheses without touching API, login, storage, or simulation code.

The original notebook used USA/TOP3000 field IDs that are not present in the uploaded
GLB / Delay-1 / TOPDIV3000 catalog. The default below keeps the same structural idea,
but uses field IDs that exist in the uploaded GLB catalog.
"""

ALPHA_TEMPLATE = """
data1 = ts_backfill(<funds_data>, <backfill_days>);
data2 = ts_backfill(<debt_data>, <backfill_days>);
diff = <diff_op>(data1, data2);
alpha = <ts_neut_op>(diff, <ts_neut_days>);
alpha_gp = <group_neut_op>(<group_neut_op>(alpha, <gp1>), <gp2>);
<ts_decay_op>(alpha_gp, <ts_decay_days>)
""".strip()

ALPHA_SPACE = {
    "<funds_data>": [
        "free_cash_flow_firm",
        "free_cash_flow_annual",
        "other_operating_cash_flows",
    ],
    "<debt_data>": [
        "fnd23_net_debt",
        "net_debt_annual",
        "long_term_loans_total_debt",
        "finance_lease_debt_total",
    ],
    "<backfill_days>": ["5", "10", "21", "63", "126"],
    "<group_neut_op>": ["group_zscore", "group_rank", "group_neutralize"],
    "<ts_decay_op>": ["ts_mean", "ts_decay_linear"],
    "<ts_neut_op>": ["ts_rank", "ts_zscore", "ts_av_diff", "ts_delta"],
    "<ts_neut_days>": ["5", "10", "21", "63", "126", "252", "512"],
    "<ts_decay_days>": ["1", "5", "10", "21", "42", "63"],
    "<diff_op>": ["subtract", "divide"],
    "<gp1>": ["market", "sector", "industry", "subindustry"],
    "<gp2>": ["market", "sector", "industry", "subindustry"],
}

ALPHA_SETTINGS = {
    "type": "REGULAR",
    "settings": {
        "instrumentType": "EQUITY",
        "region": "GLB",
        "universe": "TOPDIV3000",
        "delay": 1,
        "decay": 0,
        "neutralization": "MARKET",
        "truncation": 0.08,
        "pasteurization": "ON",
        "unitHandling": "VERIFY",
        "nanHandling": "OFF",
        "language": "FASTEXPR",
        "visualization": False,
    },
}

DEFAULT_GA_CONFIG = {
    "generation": 2,
    "population": 10,
    "select_rate": 0.5,
    "mutation_prob": 0.05,
}
