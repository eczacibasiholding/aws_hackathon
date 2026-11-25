"""Build assets/map/land.svg from the frontend's own world-atlas file (land-50m.json).

Projection: Mercator, x = (lon - LON0) * K, y = (Y(LAT_TOP) - Y(lat)) * K, K in px per radian.
The same constants are repeated in compositions/*.html (function `proj`), keep them in sync.
"""
import json
import math
import sys
from pathlib import Path

LON0, LON1 = 10.0, 140.0
LAT_TOP, LAT_BOTTOM = 64.0, -5.0
W = 3840.0
K = W / math.radians(LON1 - LON0)


def ymerc(lat):
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


H = (ymerc(LAT_TOP) - ymerc(LAT_BOTTOM)) * K


def proj(lon, lat):
    lat = max(min(lat, 85), -85)
    return (math.radians(lon - LON0) * K, (ymerc(LAT_TOP) - ymerc(lat)) * K)


def main(src, dst):
    topo = json.loads(Path(src).read_text())
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def ring(idx):
        out = []
        for i in idx:
            pts = arcs[i] if i >= 0 else list(reversed(arcs[~i]))
            out.extend(pts if not out else pts[1:])
        return out

    polys = []
    for g in topo["objects"]["land"]["geometries"]:
        if g["type"] == "Polygon":
            polys.append(g["arcs"])
        elif g["type"] == "MultiPolygon":
            polys.extend(g["arcs"])

    parts = []
    margin = 200
    for poly in polys:
        for r in poly:
            pts = [proj(lon, lat) for lon, lat in ring(r)]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            if max(xs) < -margin or min(xs) > W + margin or max(ys) < -margin or min(ys) > H + margin:
                continue
            # drop points closer than 1.2 px to the previous kept one
            kept = [pts[0]]
            for p in pts[1:]:
                if abs(p[0] - kept[-1][0]) + abs(p[1] - kept[-1][1]) >= 1.2:
                    kept.append(p)
            if len(kept) < 3:
                continue
            d = "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in kept) + "Z"
            parts.append(d)

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" '
        f'width="{W:.0f}" height="{H:.0f}">'
        f'<path d="{"".join(parts)}" fill="#0f2236" stroke="#1f4466" stroke-width="1.6" '
        f'stroke-linejoin="round"/></svg>'
    )
    Path(dst).write_text(svg)
    print(f"K={K:.4f} H={H:.1f} rings={len(parts)} bytes={len(svg)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
