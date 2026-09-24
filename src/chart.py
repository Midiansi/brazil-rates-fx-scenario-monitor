"""A single lightweight inline-SVG chart: PTAX closes against the decision levels.

No charting library: the page only needs one line, a few reference lines and
native hover titles.  Two variants are emitted (wide and compact) because SVG
text scales with the viewBox and would be unreadable on a phone otherwise.
"""
from __future__ import annotations

from html import escape
from typing import Any, Callable


def _ticks(low: float, high: float, step: float = 0.05) -> list[float]:
    start = round(low / step + 0.4999) * step
    values = []
    value = start
    while value <= high + 1e-9:
        values.append(round(value, 4))
        value += step
    return values


def ptax_svg(
    history: list[list[Any]],
    levels: list[dict[str, Any]],
    events: list[dict[str, Any]],
    fmt_value: Callable[[float], str],
    fmt_date: Callable[[str], str],
    title: str,
    desc: str,
    compact: bool = False,
) -> str:
    """Return one-line SVG markup (safe for Markdown: no blank lines)."""

    points = [(str(d), float(v)) for d, v in history]
    if len(points) < 2:
        return ""
    width, height = (380, 270) if compact else (760, 320)
    left, right, top, bottom = (40, 12, 16, 30) if compact else (48, 150, 18, 34)
    font = 12 if compact else 12
    values = [v for _, v in points] + [float(level["value"]) for level in levels]
    low, high = min(values), max(values)
    pad = (high - low) * 0.08 or 0.05
    low, high = low - pad, high + pad
    plot_w, plot_h = width - left - right, height - top - bottom

    def x(i: int) -> float:
        return left + plot_w * i / (len(points) - 1)

    def y(v: float) -> float:
        return top + plot_h * (high - v) / (high - low)

    parts = [
        f'<svg class="chart {"chart-compact" if compact else "chart-wide"}" viewBox="0 0 {width} {height}" role="img" '
        f'aria-labelledby="ct{int(compact)} cd{int(compact)}" xmlns="http://www.w3.org/2000/svg" font-family="inherit">',
        f'<title id="ct{int(compact)}">{escape(title)}</title><desc id="cd{int(compact)}">{escape(desc)}</desc>',
    ]
    # Recessive horizontal grid with value ticks.
    for tick in _ticks(low, high, 0.05 if not compact else 0.10):
        ty = y(tick)
        parts.append(f'<line x1="{left}" x2="{width - right}" y1="{ty:.1f}" y2="{ty:.1f}" class="c-grid"/>')
        parts.append(f'<text x="{left - 8}" y="{ty + 4:.1f}" text-anchor="end" class="c-tick" font-size="{font - 1}">{escape(fmt_value(tick))}</text>')
    # Month ticks on the x axis.
    seen: set[str] = set()
    for i, (d, _) in enumerate(points):
        month = d[:7]
        if month not in seen and (i > 3 or i == 0):
            seen.add(month)
            if compact and len(seen) % 2 == 0:
                continue
            parts.append(f'<text x="{x(i):.1f}" y="{height - 10}" text-anchor="start" class="c-tick" font-size="{font - 1}">{escape(fmt_date(d))}</text>')
    # Event markers (vertical, dotted hairline).
    for event in events:
        index = next((i for i, (d, _) in enumerate(points) if d >= event["date"]), None)
        if index is None or index == 0:
            continue
        ex = x(index)
        parts.append(f'<line x1="{ex:.1f}" x2="{ex:.1f}" y1="{top}" y2="{height - bottom}" class="c-event"/>')
        if not compact:
            parts.append(f'<text x="{ex - 6:.1f}" y="{height - bottom - 8}" text-anchor="end" class="c-note" font-size="{font - 1}">{escape(event["label"])}</text>')
    # Decision levels.
    for level in levels:
        ly = y(float(level["value"]))
        parts.append(f'<line x1="{left}" x2="{width - right}" y1="{ly:.1f}" y2="{ly:.1f}" class="c-level c-{level["kind"]}"/>')
        if not compact:
            anchor_x = width - right + 8
            parts.append(f'<text x="{anchor_x}" y="{ly + 4 + level.get("nudge", 0):.1f}" class="c-label" font-size="{font}">{escape(level["label"])}</text>')
    # The series.
    path = " ".join(f"{'M' if i == 0 else 'L'}{x(i):.1f},{y(v):.1f}" for i, (_, v) in enumerate(points))
    parts.append(f'<path d="{path}" class="c-line"/>')
    # Hover targets (wide variant only; the compact one is for touch screens):
    # one invisible column per session with a native tooltip.
    step = plot_w / (len(points) - 1)
    for i, (d, v) in enumerate([] if compact else points):
        parts.append(
            f'<rect x="{x(i) - step / 2:.1f}" y="{top}" width="{step:.1f}" height="{plot_h}" class="c-hit">'
            f'<title>{escape(fmt_date(d))} · {escape(fmt_value(v))}</title></rect>'
        )
    last_x, last_y = x(len(points) - 1), y(points[-1][1])
    # The latest value is stated in the figure heading, so the dot stays unlabelled
    # and cannot collide with the level labels.
    parts.append(f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="4.5" class="c-dot"/>')
    parts.append("</svg>")
    return "".join(parts)
