import sys
from pathlib import Path

sys.path.insert(0, r"D:\maxzhang\python files\Math-modeling\26B\src")
from coverage import (
    q4_double_ring_cover_ok,
    q4_double_ring_search_time,
    q4_opt_inner_r,
    regular_ring_rho_interval,
)

rho7 = q4_opt_inner_r()
lines = [f"rho7={rho7}"]
for n in range(5, 13):
    lines.append(f"omni n={n} interval={regular_ring_rho_interval(n)}")

catalog = [
    (7, rho7, 12, 1865.0, "radial", None),
    (8, 1000.0, 12, 1865.0, "radial", None),
    (8, 995.0, 12, 1865.0, "radial", None),
    (9, 1000.0, 12, 1865.0, "radial", None),
    (7, rho7, 12, 1865.0, "stagger", None),
    (6, 1150.0, 12, 1865.0, "radial", 900.0),
    (6, 1150.0, 12, 1865.0, "radial", None),
    (8, 1200.0, 12, 2100.0, "radial", 900.0),
    (7, rho7, 11, 1900.0, "radial", None),
    (7, rho7, 14, 1865.0, "radial", None),
    (10, 1000.0, 12, 1865.0, "radial", None),
]
lines.append("--- times (no cover check) ---")
for n_in, rin, n_out, rout, align, enr in catalog:
    row = q4_double_ring_search_time(
        n_in, rin, n_out, rout, align=align, enroute_r=enr, check_cover=False
    )
    lines.append(
        f"{n_in}+{n_out} r={rin:.1f}/{rout:.0f} {align} enr={enr} "
        f"stops={row['n_stops']} travel={row['travel_s']:.1f} "
        f"dwell={row['dwell_s']:.0f} total={row['total_s']:.1f}"
    )

# a few cover checks that are cheap-ish
lines.append("--- cover checks ---")
for item in (
    (7, rho7, 12, 1865.0, "radial", None),
    (6, 1150.0, 12, 1865.0, "radial", None),
    (7, rho7, 11, 1900.0, "radial", None),
    (8, 995.0, 12, 1865.0, "radial", None),
):
    n_in, rin, n_out, rout, align, enr = item
    cover = q4_double_ring_cover_ok(
        n_in, rin, n_out, rout, align=align, enroute_r=enr,
        n_radial=6, n_ang=48, n_headings=24,
    )
    lines.append(f"{n_in}+{n_out} r={rin:.1f}/{rout:.0f} {align} enr={enr} {cover}")

Path = __import__("pathlib").Path
Path(r"D:\maxzhang\python files\Math-modeling\26B\output\_q4_ring_times.txt").write_text(
    "\n".join(lines), encoding="utf-8"
)
print("\n".join(lines))
