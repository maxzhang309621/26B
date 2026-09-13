import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
rows = json.loads(p.read_text(encoding="utf-8"))
print("file", p.name, "n", len(rows))
vts = []
ratios = []
sps = []
for s in rows:
    st = s.get("stats") or {}
    off = s.get("official") or {}
    n = off.get("jammer_count")
    c = st.get("cleared")
    vt = st.get("virtual_time_s")
    om = off.get("omnidirectional_jammer_count")
    dn = off.get("directional_jammer_count")
    ratio = s.get("ratio")
    if isinstance(vt, (int, float)):
        vts.append(float(vt))
    if isinstance(ratio, (int, float)):
        ratios.append(float(ratio))
    if isinstance(vt, (int, float)) and isinstance(n, int) and n > 0:
        sps.append(float(vt) / n)
    print(
        f"i={s.get('index')} n={n} omni={om} dir={dn} cleared={c} "
        f"ratio={ratio} vt={vt} completed={st.get('completed')} "
        f"profile={st.get('q4_path_profile')} dir_corr={st.get('dir_corrector')} "
        f"used={st.get('corrector_used')} fb={st.get('corrector_fallback')} "
        f"travel={((st.get('move_decomposition') or {}).get('total_s'))} "
        f"reason={st.get('termination_reason')} err={s.get('error')}"
    )
if vts:
    print("mean_vt", sum(vts) / len(vts), "min", min(vts), "max", max(vts))
if sps:
    print("mean_s_per_src", sum(sps) / len(sps))
if ratios:
    print("mean_ratio", sum(ratios) / len(ratios), "full", sum(1 for r in ratios if r >= 1.0 - 1e-12), "/", len(ratios))
