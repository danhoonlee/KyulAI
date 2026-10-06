"""Evaluate served laminate response models on the fixed angle-pair holdout.

Calls the same in-process function the /predict/response endpoints use, and tags each
holdout row by whether that model saw it (or its angle pair) in training.

    python scripts/dd_served_model_holdout_check.py OUT.json OUT.csv [--kink]

Default scores the P1-era served models against the P1 holdout (2026-10-06 first run).
--kink scores the kink-Pt family against the kink dataset, plus two lookups that learn
nothing: the original angle-only one, and a stronger one restricted to the same Case and panel.
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.backend.api.v1 import dd_laminate as api  # noqa: E402

HOLDOUT = ROOT / "reports/dd_response_geometry_split_v2_3size/fixed_holdout_manifest.csv"
OLD_SPLIT = ROOT / "data/datasets/DD_cases_2_3_4_geometry_grouped_v1/split_manifest.csv"
KINK_MANIFEST = ROOT / "data/datasets/DD_cases_2_3_4_geometry_3size_kink_v1/manifest.csv"
KINK_SPLIT = ROOT / "data/datasets/DD_cases_2_3_4_geometry_3size_kink_v1/split_manifest.csv"


def panel(r):
    return f"{float(r['panel_a_in']):g}x{float(r['panel_b_in']):g}"


def pair(r):
    return (float(r["theta1"]), float(r["theta2"]))


def p1_models():
    # canonical_v2 models: n_samples=1800 = every 6x4 and 6x8 row, no holdout.
    canon_rows, canon_pairs, old_dev_rows, old_dev_pairs = set(), set(), set(), set()
    # 3size_grouped models: development side of the old case|theta split (sha af7b4b02...).
    for r in csv.DictReader(open(OLD_SPLIT)):
        key, p = (r["case"], r["Test_ID"]), pair(r)
        if panel(r) in ("6x4", "6x8"):
            canon_rows.add(key)
            canon_pairs.add(p)
        if r["split"] == "development":
            old_dev_rows.add(key)
            old_dev_pairs.add(p)
    return {
        "response_geometry_tree_canonical_v2": (canon_rows, canon_pairs, False),
        "response_geometry_goint_canonical_v2": (canon_rows, canon_pairs, False),
        "response_hybrid_student_canonical_v2": (canon_rows, canon_pairs, False),
        "response_pt_consistent_tree_3size_grouped_v1": (old_dev_rows, old_dev_pairs, True),
        "response_pt_consistent_goint_3size_grouped_v1": (old_dev_rows, old_dev_pairs, True),
        "response_pt_consistent_hybrid_3size_grouped_v1": (old_dev_rows, old_dev_pairs, True),
    }


def summarize(sub):
    if not sub:
        return None
    pt = np.array([x["pt"] for x in sub])
    err = np.abs(np.array([x["pred_pt"] for x in sub]) - pt)
    t1 = [x for x in sub if x["type"] == 1]
    called1 = [x for x in sub if x["pred_type"] == 1]
    return dict(
        n=len(sub),
        acc=float(np.mean([x["type"] == x["pred_type"] for x in sub])),
        pt_mae=float(err.mean()),
        pt_rel=float(err.mean() / pt.mean()),
        pt_mape_median=float(np.median(err / pt)),
        t1_n=len(t1),
        t1_recall=(float(np.mean([x["pred_type"] == 1 for x in t1])) if t1 else None),
        t1_precision=(float(np.mean([x["type"] == 1 for x in called1])) if called1 else None),
    )


def grouped(recs):
    groups = defaultdict(list)
    for x in recs:
        for key in (("all", "all"), (x["panel"], "all"), ("all", x["status"]),
                    (x["panel"], x["status"])):
            groups[key].append(x)
    return {f"{p}|{s}": summarize(v) for (p, s), v in sorted(groups.items())}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("out_json")
    parser.add_argument("out_csv")
    parser.add_argument("--kink", action="store_true")
    args = parser.parse_args()

    if args.kink:
        truth = list(csv.DictReader(open(KINK_MANIFEST)))
        split = {(r["case"], r["Test_ID"]): r["split"] for r in csv.DictReader(open(KINK_SPLIT))}
        train = [r for r in truth if split[(r["case"], r["Test_ID"])] == "train"]
        rows = [r for r in truth if split[(r["case"], r["Test_ID"])] == "holdout"]
        seen_rows = {(r["case"], r["Test_ID"]) for r in train}
        seen_pairs = {pair(r) for r in train}
        models = {key: (seen_rows, seen_pairs, True) for key in api.KINK_RESPONSE_MODEL_KEYS}
        id_key, pt_key = "Test_ID", "Pt"
    else:
        rows = [r for r in csv.DictReader(open(HOLDOUT)) if r["split"] == "holdout"]
        train, models, id_key, pt_key = [], p1_models(), "test_id", "pt"
    assert len(rows) == 549, len(rows)

    out, detail = {}, []

    def status_of(r, seen_rows, seen_pairs):
        if (r["case"], r[id_key]) in seen_rows:
            return "row_in_train"
        return "pair_in_train" if pair(r) in seen_pairs else "clean"

    def record(model, r, pred_type, pred_pt, status):
        rec = dict(panel=panel(r), status=status, type=int(r["type"]), pt=float(r[pt_key]),
                   pred_type=int(pred_type), pred_pt=float(pred_pt))
        detail.append(dict(model=model, case=r["case"], test_id=r[id_key], **rec))
        return rec

    for key, (seen_rows, seen_pairs, preview) in models.items():
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
            recs.append(record(key, r, res.predicted_type, res.predicted_pt,
                               status_of(r, seen_rows, seen_pairs)))
        out[key] = grouped(recs)
        print(key, json.dumps(out[key]["all|all"]), file=sys.stderr)

    if train:
        points = np.array([pair(r) for r in train])
        for name, same_slice in (("lookup_angle_only", False), ("lookup_same_case_panel", True)):
            recs = []
            for r in rows:
                mask = np.array([
                    (t["case"] == r["case"] and panel(t) == panel(r)) if same_slice else True
                    for t in train
                ])
                idx = np.flatnonzero(mask)
                d = np.hypot(*(points[idx] - np.array(pair(r))).T)
                near = train[int(idx[int(np.argmin(d))])]
                recs.append(record(name, r, near["type"], near[pt_key], "clean"))
            out[name] = grouped(recs)
            print(name, json.dumps(out[name]["all|all"]), file=sys.stderr)

    json.dump(out, open(args.out_json, "w"), indent=1)
    with open(args.out_csv, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(detail[0]))
        writer.writeheader()
        writer.writerows(detail)


if __name__ == "__main__":
    main()
