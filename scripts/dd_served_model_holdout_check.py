"""Evaluate the served laminate response models on the fixed v2 3-size holdout.

Calls the same in-process function the /predict/response endpoints use, and tags each
holdout row by whether that model saw it (or its angle pair) in training.
"""
import csv
import json
import sys
from collections import defaultdict

import numpy as np

from src.backend.api.v1 import dd_laminate as api

ROOT = "/home/user/projects/KyulAI"
HOLDOUT = f"{ROOT}/reports/dd_response_geometry_split_v2_3size/fixed_holdout_manifest.csv"
OLD_SPLIT = f"{ROOT}/data/datasets/DD_cases_2_3_4_geometry_grouped_v1/split_manifest.csv"

rows = [r for r in csv.DictReader(open(HOLDOUT)) if r["split"] == "holdout"]
assert len(rows) == 549, len(rows)


def panel(r):
    return f"{float(r['panel_a_in']):g}x{float(r['panel_b_in']):g}"


def pair(r):
    return (float(r["theta1"]), float(r["theta2"]))


# canonical_v2 models: n_samples=1800 = every 6x4 and 6x8 row, no holdout.
canon_rows = set()
canon_pairs = set()
# 3size_grouped models: development side of the old case|theta split (sha af7b4b02...).
old_dev_rows = set()
old_dev_pairs = set()
for r in csv.DictReader(open(OLD_SPLIT)):
    key = (r["case"], r["Test_ID"])
    p = pair(r)
    pn = f"{float(r['panel_a_in']):g}x{float(r['panel_b_in']):g}"
    if pn in ("6x4", "6x8"):
        canon_rows.add(key)
        canon_pairs.add(p)
    if r["split"] == "development":
        old_dev_rows.add(key)
        old_dev_pairs.add(p)

MODELS = {
    # key: (seen rows, seen pairs, three-size preview?)
    "response_geometry_tree_canonical_v2": (canon_rows, canon_pairs, False),
    "response_geometry_goint_canonical_v2": (canon_rows, canon_pairs, False),
    "response_hybrid_student_canonical_v2": (canon_rows, canon_pairs, False),
    "response_pt_consistent_tree_3size_grouped_v1": (old_dev_rows, old_dev_pairs, True),
    "response_pt_consistent_goint_3size_grouped_v1": (old_dev_rows, old_dev_pairs, True),
    "response_pt_consistent_hybrid_3size_grouped_v1": (old_dev_rows, old_dev_pairs, True),
}

out = {}
detail = []
for key, (seen_rows, seen_pairs, preview) in MODELS.items():
    recs = []
    for r in rows:
        req = api.ResponsePredictionRequest(
            theta1=float(r["theta1"]), theta2=float(r["theta2"]), case=r["case"],
            panel_a_in=float(r["panel_a_in"]), panel_b_in=float(r["panel_b_in"]), model=key,
        )
        if preview:
            res = api._predict_estimated_response(
                req, postprocess_curve=False, curve_fit_style="p1_transition_guided"
            )
        else:
            res = api._predict_estimated_response(req)
        if (r["case"], r["test_id"]) in seen_rows:
            status = "row_in_train"
        elif pair(r) in seen_pairs:
            status = "pair_in_train"
        else:
            status = "clean"
        rec = dict(panel=panel(r), status=status, type=int(r["type"]), pt=float(r["pt"]),
                   pred_type=res.predicted_type, pred_pt=res.predicted_pt)
        recs.append(rec)
        detail.append(dict(model=key, case=r["case"], test_id=r["test_id"], **rec))

    def summ(sub):
        if not sub:
            return None
        pt = np.array([x["pt"] for x in sub])
        err = np.abs(np.array([x["pred_pt"] for x in sub]) - pt)
        acc = np.mean([x["type"] == x["pred_type"] for x in sub])
        t1 = [x for x in sub if x["type"] == 1]
        return dict(n=len(sub), acc=float(acc), pt_mae=float(err.mean()),
                    pt_rel=float(err.mean() / pt.mean()),
                    pt_mape_median=float(np.median(err / pt)),
                    t1_recall=(float(np.mean([x["pred_type"] == 1 for x in t1])) if t1 else None))

    groups = defaultdict(list)
    for x in recs:
        groups[("all", "all")].append(x)
        groups[(x["panel"], "all")].append(x)
        groups[("all", x["status"])].append(x)
        groups[(x["panel"], x["status"])].append(x)
    out[key] = {f"{p}|{s}": summ(v) for (p, s), v in sorted(groups.items())}
    print(key, json.dumps(out[key]["all|all"]), file=sys.stderr)

json.dump(out, open(sys.argv[1], "w"), indent=1)
with open(sys.argv[2], "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(detail[0]))
    w.writeheader()
    w.writerows(detail)
