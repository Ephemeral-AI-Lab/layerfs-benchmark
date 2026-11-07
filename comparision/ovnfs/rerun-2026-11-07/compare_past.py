#!/usr/bin/env python3
"""Tabulate this rerun (LayerFS 751b6b83, ovnfs 5d54cb0) next to the 2026-11-06 results.

    python3 compare_past.py > results/summary-vs-past.json
"""
import json, statistics as st, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
NEW = HERE / "results"
OLD = HERE.parent / "results"
def load(p): return json.loads((p/"state.json").read_text())
def med(xs): return round(st.median(xs)) if xs else None
def p90(xs): xs=sorted(xs); return round(xs[min(len(xs)-1,int(0.9*len(xs)))])
out={}
for c in ("S1","S2","S3","S4"):
    for tag,s in (("layerfs_past",load(OLD/f"layerfs-{c}")),("layerfs_new",load(NEW/f"layerfs-{c}")),("ovnfs_past",load(OLD/f"ovnfs-{c}")),("ovnfs_new",load(NEW/f"ovnfs-{c}"))):
        pr={p["label"]:p for p in s["probes"]}; br=list(s["branches"].values()); st_=[x for b in br for x in b["steps"]]
        r=dict(status=s["status"],verified=f'{sum(b["verification"]=="PASS" for b in br)}/{len(br)}',commits=len(st_),
          floor=pr["floor"]["total_bytes"],imp=pr["import"]["total_bytes"],final=pr["final"]["total_bytes"],
          import_ms=round(s["import_ns"]/1e6),control_ms=round(s["control_ns"]/1e6),
          open_med=med([(b["fork_ns"]+b["mount_ns"])/1e6 for b in br]),
          apply_med=med([x["apply_ns"]/1e6 for x in st_]),apply_p90=p90([x["apply_ns"]/1e6 for x in st_]),
          commit_med=med([x["commit_ns"]/1e6 for x in st_]),commit_p90=p90([x["commit_ns"]/1e6 for x in st_]),
          read_ms=[round(b["verify_read_ns"]/1e6) for b in br],load=[x["load"] for x in s.get("load_1m",[])])
        if tag.startswith("ovnfs"):
            r.update(imp_app=pr["import"]["apparent_bytes"],final_app=pr["final"]["apparent_bytes"],parts_final=pr["final"]["parts"],parts_import=pr["import"]["parts"])
            r["app_growth"]=r["final_app"]-r["imp_app"]
        else:
            r["new_stored"]=sum(x["new_stored"] or 0 for x in st_); r["new_meta"]=sum(x["new_metadata"] or 0 for x in st_)
            r["final_file"]=pr["final"]["file_bytes"]; r["final_wal"]=pr["final"]["wal_bytes"]; r["imp_file"]=pr["import"]["file_bytes"]
        r["growth"]=r["final"]-r["imp"]
        out[f"{c}/{tag}"]=r
json.dump(out,sys.stdout,indent=1)
