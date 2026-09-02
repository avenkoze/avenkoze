#!/usr/bin/env python3
"""Generate the low-poly surf sculpture used by the profile README.

The output is deliberately ASCII STL: GitHub can render the same geometry
directly inside a Markdown `stl` fence without JavaScript or a third-party
viewer.
"""

from __future__ import annotations

import math
from pathlib import Path


Vec3 = tuple[float, float, float]
Triangle = tuple[Vec3, Vec3, Vec3]


def add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(v: Vec3, amount: float) -> Vec3:
    return (v[0] * amount, v[1] * amount, v[2] * amount)


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def normalize(v: Vec3) -> Vec3:
    length = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    if length == 0:
        return (0.0, 0.0, 0.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def cubic_bezier(p0: Vec3, p1: Vec3, p2: Vec3, p3: Vec3, t: float) -> Vec3:
    u = 1.0 - t
    return (
        u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
        u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1],
        u**3 * p0[2] + 3 * u * u * t * p1[2] + 3 * u * t * t * p2[2] + t**3 * p3[2],
    )


def wave_path() -> list[Vec3]:
    # A rising body followed by a clockwise tightening curl.
    path: list[Vec3] = []
    p0 = (-3.35, -1.02, 0.0)
    p1 = (-1.75, -1.0, 0.0)
    p2 = (-1.25, 2.05, 0.0)
    p3 = (0.05, 2.92, 0.0)
    for step in range(10):
        path.append(cubic_bezier(p0, p1, p2, p3, step / 9))

    center = (0.68, 1.48)
    start_angle = 1.93
    end_angle = -4.38
    for step in range(1, 23):
        t = step / 22
        angle = start_angle + (end_angle - start_angle) * t
        radius = 1.72 * (1.0 - t) + 0.22 * t
        path.append(
            (
                center[0] + radius * math.cos(angle),
                center[1] + radius * math.sin(angle),
                0.10 * math.sin(t * math.pi),
            )
        )
    return path


def sweep_wave(path: list[Vec3], sides: int = 8) -> list[Triangle]:
    rings: list[list[Vec3]] = []
    last = len(path) - 1

    for index, point in enumerate(path):
        if index == 0:
            tangent = normalize(sub(path[1], point))
        elif index == last:
            tangent = normalize(sub(point, path[index - 1]))
        else:
            tangent = normalize(sub(path[index + 1], path[index - 1]))

        # The path lives mostly in XY, so this gives a stable low-poly frame.
        planar_normal = normalize((-tangent[1], tangent[0], 0.0))
        depth_axis = (0.0, 0.0, 1.0)
        progress = index / last
        if progress < 0.28:
            radius = 0.72 - 0.18 * (progress / 0.28)
        else:
            curl_progress = (progress - 0.28) / 0.72
            radius = 0.54 * (1.0 - curl_progress) + 0.075 * curl_progress

        ring: list[Vec3] = []
        for side in range(sides):
            angle = 2.0 * math.pi * side / sides
            width = scale(planar_normal, math.cos(angle) * radius)
            depth = scale(depth_axis, math.sin(angle) * radius * 0.58)
            ring.append(add(point, add(width, depth)))
        rings.append(ring)

    triangles: list[Triangle] = []
    for ring_index in range(len(rings) - 1):
        current = rings[ring_index]
        following = rings[ring_index + 1]
        for side in range(sides):
            nxt = (side + 1) % sides
            triangles.append((current[side], following[side], following[nxt]))
            triangles.append((current[side], following[nxt], current[nxt]))

    start_center = path[0]
    end_center = path[-1]
    for side in range(sides):
        nxt = (side + 1) % sides
        triangles.append((start_center, rings[0][nxt], rings[0][side]))
        triangles.append((end_center, rings[-1][side], rings[-1][nxt]))
    return triangles


def extrude_polygon(points: list[tuple[float, float]], depth: float) -> list[Triangle]:
    front = [(x, y, depth) for x, y in points]
    back = [(x, y, -depth) for x, y in points]
    triangles: list[Triangle] = []

    # The base polygon is convex enough for a fan triangulation.
    for index in range(1, len(points) - 1):
        triangles.append((front[0], front[index], front[index + 1]))
        triangles.append((back[0], back[index + 1], back[index]))

    for index in range(len(points)):
        nxt = (index + 1) % len(points)
        triangles.append((front[index], back[index], back[nxt]))
        triangles.append((front[index], back[nxt], front[nxt]))
    return triangles


def octahedron(center: Vec3, radius: float) -> list[Triangle]:
    x, y, z = center
    top = (x, y + radius, z)
    bottom = (x, y - radius, z)
    ring = [
        (x + radius, y, z),
        (x, y, z + radius * 0.72),
        (x - radius, y, z),
        (x, y, z - radius * 0.72),
    ]
    triangles: list[Triangle] = []
    for index in range(4):
        nxt = (index + 1) % 4
        triangles.append((top, ring[index], ring[nxt]))
        triangles.append((bottom, ring[nxt], ring[index]))
    return triangles


def normal_for(triangle: Triangle) -> Vec3:
    a, b, c = triangle
    return normalize(cross(sub(b, a), sub(c, a)))


def stl_text(triangles: list[Triangle]) -> str:
    lines = ["solid surf_signal_001"]
    for triangle in triangles:
        normal = normal_for(triangle)
        lines.append(f"  facet normal {normal[0]:.5f} {normal[1]:.5f} {normal[2]:.5f}")
        lines.append("    outer loop")
        for vertex in triangle:
            lines.append(f"      vertex {vertex[0]:.5f} {vertex[1]:.5f} {vertex[2]:.5f}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append("endsolid surf_signal_001")
    return "\n".join(lines) + "\n"


def main() -> None:
    triangles = sweep_wave(wave_path())
    triangles.extend(
        extrude_polygon(
            [
                (-4.10, -1.58),
                (3.55, -1.58),
                (3.05, -1.18),
                (1.65, -1.02),
                (0.15, -1.13),
                (-1.55, -0.99),
                (-3.55, -1.17),
            ],
            depth=0.34,
        )
    )
    for center, radius in [
        ((1.85, 2.83, 0.42), 0.18),
        ((2.30, 2.43, -0.34), 0.13),
        ((2.47, 1.94, 0.44), 0.095),
    ]:
        triangles.extend(octahedron(center, radius))

    output = Path(__file__).resolve().parents[1] / "assets" / "surf-signal-001.stl"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(stl_text(triangles), encoding="utf-8", newline="\n")
    print(f"wrote {output} ({len(triangles)} triangles)")


if __name__ == "__main__":
    main()
