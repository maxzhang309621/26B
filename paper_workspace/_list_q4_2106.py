import json
from pathlib import Path

p = Path(r"D:\maxzhang\python files\Math-modeling\26B\output\drill\q4-batch-summary.json")
rows = json.loads(p.read_text(encoding="utf-8"))
for i, r in enumerate(rows, 1):
    s = r["stats"]
    print(
        f"{i:02d} n={r['jammer_count']:2d} "
        f"omni={r['omnidirectional_jammer_count']} "
        f"dir={r['directional_jammer_count']} "
        f"vt={s['virtual_time_s']:.0f} "
        f"avg={s['avg_clear_s']:.0f} "
        f"log={Path(r['log_path']).name}"
    )
