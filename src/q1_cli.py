"""Offline problem-1 CLI: stations and bearings -> polygon diameter and cover test."""

from __future__ import annotations

import argparse
import json
import math

from geometry import diameter_circle_covers, intersect_cones, jung_bound, smallest_enclosing_circle


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--json", help='{"stations":[[x,y],...],"bearings":[deg,...]}')
    args = p.parse_args()
    if args.json:
        data = json.loads(args.json)
        stations = [tuple(s) for s in data["stations"]]
        bearings = list(data["bearings"])
    else:
        stations = [(0.0, 0.0), (400.0, 0.0)]
        g = (200.0, 300.0)
        bearings = [
            math.degrees(math.atan2(g[1] - s[1], g[0] - s[0])) for s in stations
        ]
    res = intersect_cones(stations, bearings)
    out = {
        "empty": res.empty,
        "bounded": res.bounded,
        "vertices": res.vertices,
        "diameter": res.diameter,
    }
    if not res.empty and res.bounded and res.vertices:
        cen, rad = smallest_enclosing_circle(res.vertices)
        out["sec_center"] = cen
        out["sec_radius"] = rad
        out["diameter_circle_covers"] = diameter_circle_covers(res.vertices)
        out["jung_radius"] = jung_bound(res.diameter)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
