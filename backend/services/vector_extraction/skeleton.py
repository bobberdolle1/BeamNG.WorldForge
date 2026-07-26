"""
Trace a skeletonised mask into polylines.

**The bug this replaces.** Road centrelines were extracted by skeletonising the
mask and then running ``cv2.findContours`` over the result. ``findContours``
traces the *outline* of a shape, not a path through it - so a one-pixel-wide
skeleton comes back as a loop that runs to the far end and then all the way
back. An L-shaped road of 85 skeleton pixels produced a contour 137 pixels
long::

    (58,10) -> (58,39) -> (57,40) -> (5,40) -> (59,40) -> (58,39)
                                       ^^^^^^^^^^^^^^^ retraces the run

Exported as a BeamNG decal road, every such road doubled back over itself.

**What this does instead.** Treats the skeleton as a graph of 8-connected
pixels and walks it: branches run from one endpoint or junction to the next,
each pixel consumed once. A straight road yields one polyline; a fork yields
one polyline per branch.
"""

from __future__ import annotations

import numpy as np

#: Relative offsets of the eight neighbours of a pixel.
_NEIGHBOURS = (
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
)


def _neighbours(pixels: set[tuple[int, int]], point: tuple[int, int]) -> list[tuple[int, int]]:
    """Skeleton pixels adjacent to ``point``."""
    row, column = point
    return [
        (row + dr, column + dc)
        for dr, dc in _NEIGHBOURS
        if (row + dr, column + dc) in pixels
    ]


def trace_skeleton(skeleton: np.ndarray, min_length: int = 2) -> list[list[tuple[int, int]]]:
    """
    Walk a skeleton image into polylines.

    Args:
        skeleton: 2D array; any non-zero value is a skeleton pixel.
        min_length: Discard polylines with fewer points than this.

    Returns:
        Polylines as lists of ``(x, y)`` pixel coordinates, matching OpenCV's
        column-major convention so the result is interchangeable with contours.
    """
    mask = np.asarray(skeleton) > 0
    if mask.ndim != 2:
        raise ValueError(f"skeleton must be 2D, got shape {mask.shape}")

    pixels = {(int(row), int(column)) for row, column in zip(*np.nonzero(mask), strict=True)}
    if not pixels:
        return []

    degree = {point: len(_neighbours(pixels, point)) for point in pixels}

    # Endpoints first, then junctions: starting a walk in the middle of a
    # through-path would split one road into two halves.
    endpoints = sorted(point for point, count in degree.items() if count == 1)
    junctions = sorted(point for point, count in degree.items() if count >= 3)

    visited_edges: set[frozenset[tuple[int, int]]] = set()
    polylines: list[list[tuple[int, int]]] = []

    for start in endpoints + junctions:
        for neighbour in _neighbours(pixels, start):
            edge = frozenset((start, neighbour))
            if edge in visited_edges:
                continue
            path = _walk(pixels, degree, visited_edges, start, neighbour)
            if len(path) >= min_length:
                polylines.append([(column, row) for row, column in path])

    # Closed loops have no endpoint and no junction, so nothing above starts
    # them. Pick any unvisited pixel and walk the ring.
    for start in sorted(pixels):
        for neighbour in _neighbours(pixels, start):
            if frozenset((start, neighbour)) in visited_edges:
                continue
            path = _walk(pixels, degree, visited_edges, start, neighbour)
            if len(path) >= min_length:
                polylines.append([(column, row) for row, column in path])

    return polylines


def _walk(
    pixels: set[tuple[int, int]],
    degree: dict[tuple[int, int], int],
    visited_edges: set[frozenset[tuple[int, int]]],
    start: tuple[int, int],
    first_step: tuple[int, int],
) -> list[tuple[int, int]]:
    """Follow a branch from ``start`` until it reaches an endpoint or junction."""
    path = [start, first_step]
    visited_edges.add(frozenset((start, first_step)))

    previous, current = start, first_step

    while degree.get(current, 0) == 2:
        options = [
            candidate
            for candidate in _neighbours(pixels, current)
            if candidate != previous and frozenset((current, candidate)) not in visited_edges
        ]
        if not options:
            break

        following = options[0]
        visited_edges.add(frozenset((current, following)))
        path.append(following)
        previous, current = current, following

        if current == start:  # closed the loop
            break

    return path


def simplify_polyline(
    points: list[tuple[int, int]], tolerance: float = 2.0
) -> list[tuple[int, int]]:
    """
    Reduce a polyline with the Douglas-Peucker algorithm.

    Applied per branch rather than to a closed contour, which is what
    ``cv2.approxPolyDP(..., closed=False)`` did over the retraced outline - it
    simplified a shape that should never have been a shape.
    """
    if len(points) <= 2 or tolerance <= 0:
        return list(points)

    start, end = points[0], points[-1]
    max_distance = 0.0
    index = 0

    for position in range(1, len(points) - 1):
        distance = _perpendicular_distance(points[position], start, end)
        if distance > max_distance:
            max_distance = distance
            index = position

    if max_distance <= tolerance:
        return [start, end]

    left = simplify_polyline(points[: index + 1], tolerance)
    right = simplify_polyline(points[index:], tolerance)
    return left[:-1] + right


def _perpendicular_distance(
    point: tuple[int, int], start: tuple[int, int], end: tuple[int, int]
) -> float:
    """Distance from ``point`` to the segment ``start``-``end``."""
    x, y = point
    x0, y0 = start
    x1, y1 = end

    dx, dy = x1 - x0, y1 - y0
    if dx == 0 and dy == 0:
        return float(np.hypot(x - x0, y - y0))

    return abs(dy * x - dx * y + x1 * y0 - y1 * x0) / float(np.hypot(dx, dy))
