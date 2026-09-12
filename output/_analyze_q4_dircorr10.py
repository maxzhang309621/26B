import json
from pathlib import Path

ROOT = Path(r"D:\maxzhang\python files\Math-modeling\26B")
CUR = ROOT / "output" / "drill" / "q4-batch-summary.json"
PREV = ROOT / "output" / "drill" / "q4-batch-summary-hexbatch-20260912-1701.json"
OUT = ROOT / "output" / "drill" / "q4-dircorr-10-analysis.json"


def rows(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for s in data:
        st = s.get("stats") or {}
        off = s.get("official") or {}
        md = st.get("move_decomposition") or {}
        audit = st.get("clear_audit") or {}
        n = off.get("jammer_count") or st.get("cleared")
        vt = float(st.get("virtual_time_s") or 0)
        travel = float(st.get("travel_s") or md.get("total_s") or 0)
        rec = {
            "index": s.get("index"),
            "n": n,
            "omni": off.get("omnidirectional_jammer_count"),
            "dir": off.get("directional_jammer_count"),
            "cleared": st.get("cleared"),
            "ratio": s.get("ratio"),
            "vt": vt,
            "s_per_src": (vt / n) if n else None,
            "avg_clear_s": st.get("avg_clear_s"),
            "travel_s": travel,
            "detect_s": st.get("detect_s"),
            "switch_s": st.get("switch_s"),
            "clear_ok": st.get("clear_ok"),
            "clear_miss": st.get("clear_miss"),
            "n_measure": st.get("n_measure"),
            "n_clear": st.get("n_clear"),
            "backbone_s": md.get("backbone_scan_s"),
            "detour_s": md.get("clear_detour_s"),
            "optical_hits": st.get("optical_grid_hits"),
            "optical_calls": st.get("optical_grid_calls"),
            "route_rechecks": st.get("route_rechecks"),
            "route_recheck_hits": st.get("route_recheck_hits"),
            "dir_corrector": st.get("dir_corrector"),
            "corrector_used": st.get("corrector_used"),
            "corrector_fallback": st.get("corrector_fallback"),
            "profile": st.get("q4_path_profile"),
            "completed": st.get("completed"),
            "reason": st.get("termination_reason"),
            "audit": {
                k: {
                    "attempts": v.get("attempts"),
                    "success": v.get("success"),
                    "miss": v.get("miss"),
                    "travel_s": v.get("travel_s"),
                }
                for k, v in audit.items()
                if isinstance(v, dict)
            },
            "log_path": s.get("log_path"),
        }
        out.append(rec)
    return out


def agg(items: list[dict]) -> dict:
    vts = [x["vt"] for x in items]
    sps = [x["s_per_src"] for x in items if x["s_per_src"] is not None]
    travels = [x["travel_s"] for x in items]
    dets = [x["detour_s"] for x in items if x["detour_s"] is not None]
    misses = [x["clear_miss"] or 0 for x in items]
    ns = [x["n"] or 0 for x in items]
    dirs = [x["dir"] or 0 for x in items]
    used = [x["corrector_used"] or 0 for x in items]
    fb = [x["corrector_fallback"] or 0 for x in items]
    return {
        "games": len(items),
        "full_clear": sum(1 for x in items if x.get("ratio") == 1.0),
        "mean_vt": sum(vts) / len(vts),
        "min_vt": min(vts),
        "max_vt": max(vts),
        "mean_s_per_src": sum(sps) / len(sps),
        "mean_travel": sum(travels) / len(travels),
        "mean_detour": sum(dets) / len(dets) if dets else None,
        "mean_clear_miss": sum(misses) / len(misses),
        "mean_n": sum(ns) / len(ns),
        "mean_dir": sum(dirs) / len(dirs),
        "mean_corrector_used": sum(used) / len(used),
        "mean_fallback": sum(fb) / len(fb),
        "total_sources": sum(ns),
        "total_cleared": sum(x["cleared"] or 0 for x in items),
    }


cur = rows(CUR)
prev = rows(PREV) if PREV.exists() else []
payload = {
    "current_label": "hexbatch + dir_corrector (2026-09-12 20:14)",
    "previous_label": "hexbatch without dir_corrector (2026-09-12 17:01)",
    "current": cur,
    "previous": prev,
    "current_agg": agg(cur),
    "previous_agg": agg(prev) if prev else None,
}
if prev:
    a, b = payload["current_agg"], payload["previous_agg"]
    payload["delta"] = {
        "mean_vt": a["mean_vt"] - b["mean_vt"],
        "mean_s_per_src": a["mean_s_per_src"] - b["mean_s_per_src"],
        "mean_travel": a["mean_travel"] - b["mean_travel"],
        "mean_detour": (a["mean_detour"] or 0) - (b["mean_detour"] or 0),
        "mean_dir": a["mean_dir"] - b["mean_dir"],
        "mean_n": a["mean_n"] - b["mean_n"],
    }
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
backup = ROOT / "output" / "drill" / "q4-batch-summary-dircorr-20260912-2014.json"
backup.write_text(CUR.read_text(encoding="utf-8"), encoding="utf-8")
print(json.dumps({"current": payload["current_agg"], "previous": payload["previous_agg"], "delta": payload.get("delta")}, ensure_ascii=False, indent=2))
print("--- current rounds ---")
for x in cur:
    print(
        f"i={x['index']:2d} n={x['n']:2d} omni={x['omni']} dir={x['dir']} "
        f"vt={x['vt']:.1f} s/src={x['s_per_src']:.1f} travel={x['travel_s']:.1f} "
        f"detour={x['detour_s']:.1f} miss={x['clear_miss']} used={x['corrector_used']} fb={x['corrector_fallback']}"
    )
