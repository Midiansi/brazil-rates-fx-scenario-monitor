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


# ---------------------------------------------------------------------------
# Study figures.  Same approach as ``ptax_svg``: plain inline SVG, one wide and
# one compact variant (SVG text scales with the viewBox), native hover titles,
# colours from CSS classes so the figures follow the page tokens.


class _Frame:
    """Linear scales for one plot area."""

    def __init__(self, width: int, height: int, margins: tuple[int, int, int, int], x_range: tuple[float, float], y_range: tuple[float, float]):
        self.width, self.height = width, height
        self.left, self.right, self.top, self.bottom = margins
        self.x0, self.x1 = x_range
        self.y0, self.y1 = y_range
        self.plot_w, self.plot_h = width - self.left - self.right, height - self.top - self.bottom

    def x(self, value: float) -> float:
        return self.left + self.plot_w * (value - self.x0) / (self.x1 - self.x0)

    def y(self, value: float) -> float:
        return self.top + self.plot_h * (self.y1 - value) / (self.y1 - self.y0)


def _open(width: int, height: int, title: str, desc: str, compact: bool, uid: str) -> list[str]:
    variant = "chart-compact" if compact else "chart-wide"
    return [
        f'<svg class="chart {variant}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="{uid}t {uid}d" xmlns="http://www.w3.org/2000/svg" font-family="inherit">',
        f'<title id="{uid}t">{escape(title)}</title><desc id="{uid}d">{escape(desc)}</desc>',
    ]


def _hgrid(parts: list[str], frame: _Frame, ticks: list[float], fmt: Callable[[float], str], size: int) -> None:
    for tick in ticks:
        ty = frame.y(tick)
        parts.append(f'<line x1="{frame.left}" x2="{frame.width - frame.right}" y1="{ty:.1f}" y2="{ty:.1f}" class="c-grid"/>')
        parts.append(f'<text x="{frame.left - 8}" y="{ty + 4:.1f}" text-anchor="end" class="c-tick" font-size="{size}">{escape(fmt(tick))}</text>')


def curve_svg(rows: list[dict[str, Any]], survey: list[tuple[float, float, str]], policy: float, labels: dict[str, str],
              fmt: Callable[[float], str], title: str, desc: str, compact: bool = False) -> str:
    """Zero curve before and after the first round, the Selic and the economists' own path.

    ``rows`` carry ``years``, ``before``, ``after`` and ``change_bp``; ``survey`` is a list of
    (years, rate, label) for the Focus-implied average rate at one and two years.
    """

    width, height = (380, 320) if compact else (760, 360)
    frame = _Frame(width, height, (44, 14, 18, 36) if compact else (52, 118, 22, 40),
                   (0.0, 3.3), (12.0, 14.8))
    transform = lambda years: years ** 0.5
    frame.x0, frame.x1 = transform(0.04), transform(10.4)
    font = 11 if compact else 12
    parts = _open(width, height, title, desc, compact, "cv" + str(int(compact)))
    _hgrid(parts, frame, [12.0, 12.5, 13.0, 13.5, 14.0, 14.5], fmt, font - 1)
    tick_years = (0.5, 1, 2, 3, 5, 10) if not compact else (1, 2, 5, 10)
    names = {0.5: "6m", 1: "1y", 2: "2y", 3: "3y", 5: "5y", 10: "10y"}
    for years in tick_years:
        parts.append(f'<text x="{frame.x(transform(years)):.1f}" y="{height - 12}" text-anchor="middle" class="c-tick" font-size="{font - 1}">{names[years]}</text>')
    # Policy rate.
    py = frame.y(policy)
    parts.append(f'<line x1="{frame.left}" x2="{width - frame.right}" y1="{py:.1f}" y2="{py:.1f}" class="c-prev"/>')
    if not compact:
        parts.append(f'<text x="{width - frame.right + 8}" y="{py + 4:.1f}" class="c-label" font-size="{font}">{escape(labels["selic"])}</text>')
    for key, css in (("before", "c-before"), ("after", "c-line")):
        path = " ".join(f"{'M' if i == 0 else 'L'}{frame.x(transform(r['years'])):.1f},{frame.y(r[key]):.1f}" for i, r in enumerate(rows))
        parts.append(f'<path d="{path}" class="{css}"/>')
        for r in rows:
            parts.append(
                f'<circle cx="{frame.x(transform(r["years"])):.1f}" cy="{frame.y(r[key]):.1f}" r="{3 if key == "after" else 2.4}" class="{"c-dot" if key == "after" else "c-pt"}">'
                f'<title>{escape(labels[key])} · {r["vertex"]}d · {escape(fmt(r[key]))}</title></circle>')
    end = rows[-1]
    if not compact:
        parts.append(f'<text x="{frame.x(transform(end["years"])) + 10:.1f}" y="{frame.y(end["after"]) + 4:.1f}" class="c-value" font-size="{font}">{escape(labels["after"])}</text>')
        parts.append(f'<text x="{frame.x(transform(end["years"])) + 10:.1f}" y="{frame.y(end["before"]) + 4:.1f}" class="c-label" font-size="{font}">{escape(labels["before"])}</text>')
    # Economists' path markers (diamonds) and the two-year change callout.
    for years, rate, label in survey:
        cx, cy = frame.x(transform(years)), frame.y(rate)
        parts.append(f'<path d="M{cx:.1f},{cy - 5:.1f} L{cx + 5:.1f},{cy:.1f} L{cx:.1f},{cy + 5:.1f} L{cx - 5:.1f},{cy:.1f} Z" class="c-survey"><title>{escape(label)}</title></path>')
    if survey and not compact:
        cx, cy = frame.x(transform(survey[-1][0])), frame.y(survey[-1][1])
        parts.append(f'<text x="{cx + 10:.1f}" y="{cy + 18:.1f}" class="c-note" font-size="{font - 1}">{escape(labels["survey"])}</text>')
    two = next((r for r in rows if abs(r["years"] - 2) < 1e-6), None)
    if two:
        cx = frame.x(transform(2))
        top, bottom = frame.y(two["before"]), frame.y(two["after"])
        parts.append(f'<line x1="{cx + 14:.1f}" x2="{cx + 14:.1f}" y1="{top:.1f}" y2="{bottom:.1f}" class="c-event"/>')
        parts.append(f'<text x="{cx + 20:.1f}" y="{(top + bottom) / 2 + 4:.1f}" class="c-value" font-size="{font}">{escape(labels["delta"])}</text>')
    parts.append("</svg>")
    return "".join(parts)


def events_svg(paths: list[dict[str, Any]], levels: list[dict[str, Any]], labels: dict[str, str], fmt: Callable[[float], str],
               title: str, desc: str, compact: bool = False) -> str:
    """Event-time paths: PTAX indexed to 100 on the Friday before each first round.

    ``paths``: dicts with ``year``, ``points`` (session, index), and ``kind`` (``past``, ``surprise`` or ``now``).
    """

    width, height = (380, 320) if compact else (760, 360)
    values = [p[1] for item in paths for p in item["points"]] + [lv["value"] for lv in levels]
    low, high = min(values) - 1.2, max(values) + 1.2
    frame = _Frame(width, height, (40, 70, 16, 34) if compact else (48, 108, 18, 38), (0, max(p[0] for item in paths for p in item["points"])), (low, high))
    font = 11 if compact else 12
    parts = _open(width, height, title, desc, compact, "ev" + str(int(compact)))
    step = 2 if high - low < 14 else 5
    ticks, value = [], (int(low) // step + 1) * step
    while value < high:
        ticks.append(float(value))
        value += step
    _hgrid(parts, frame, ticks, lambda v: f"{v:.0f}", font - 1)
    for session in range(0, int(frame.x1) + 1, 5):
        parts.append(f'<text x="{frame.x(session):.1f}" y="{height - 12}" text-anchor="middle" class="c-tick" font-size="{font - 1}">{session}</text>')
    parts.append(f'<text x="{frame.left + frame.plot_w / 2:.1f}" y="{height - 1}" text-anchor="middle" class="c-note" font-size="{font - 2}">{escape(labels["axis"])}</text>')
    for level in levels:  # named in the legend, so the right-hand margin is free for the years
        ly = frame.y(level["value"])
        parts.append(f'<line x1="{frame.left}" x2="{width - frame.right}" y1="{ly:.1f}" y2="{ly:.1f}" class="c-level c-{level["kind"]}"><title>{escape(level["label"])}</title></line>')
    order = {"past": 0, "surprise": 1, "now": 2}
    for item in sorted(paths, key=lambda p: order[p["kind"]]):
        points = item["points"]
        path = " ".join(f"{'M' if i == 0 else 'L'}{frame.x(s):.1f},{frame.y(v):.1f}" for i, (s, v) in enumerate(points))
        parts.append(f'<path d="{path}" class="c-ev-{item["kind"]} c-y{item["year"]}"><title>{item["year"]} · {escape(fmt(points[-1][1]))}</title></path>')
        last_s, last_v = points[-1]
        if item["kind"] != "past" or not compact:
            parts.append(f'<circle cx="{frame.x(last_s):.1f}" cy="{frame.y(last_v):.1f}" r="{4 if item["kind"] == "now" else 2.8}" class="c-ev-dot c-ev-{item["kind"]}"/>')
        if not compact or item["kind"] != "past":
            dx, anchor, dy = 8, "start", 4
            parts.append(f'<text x="{frame.x(last_s) + dx:.1f}" y="{frame.y(last_v) + dy:.1f}" text-anchor="{anchor}" class="c-label{" c-value" if item["kind"] == "now" else ""}" font-size="{font}">{escape(item.get("label") or str(item["year"]))}</text>')
    parts.append("</svg>")
    return "".join(parts)


def scatter_svg(points: list[list[float]], slope: float, intercept: float, labels: dict[str, str], title: str, desc: str, compact: bool = False) -> str:
    """Monthly change of the commodity basket (x) against monthly change of USD/BRL (y), in percent."""

    width, height = (380, 320) if compact else (760, 380)
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    frame = _Frame(width, height, (42, 12, 14, 38), (min(xs) - 1, max(xs) + 1), (min(ys) - 1, max(ys) + 1))
    font = 11 if compact else 12
    parts = _open(width, height, title, desc, compact, "sc" + str(int(compact)))
    _hgrid(parts, frame, [t for t in (-10.0, 0.0, 10.0) if frame.y0 < t < frame.y1], lambda v: f"{v:+.0f}%" if v else "0%", font - 1)
    for tick in (-20, -10, 0, 10, 20):
        if frame.x0 < tick < frame.x1:
            parts.append(f'<line x1="{frame.x(tick):.1f}" x2="{frame.x(tick):.1f}" y1="{frame.top}" y2="{height - frame.bottom}" class="c-grid"/>')
            parts.append(f'<text x="{frame.x(tick):.1f}" y="{height - 20}" text-anchor="middle" class="c-tick" font-size="{font - 1}">{tick:+d}%' + '</text>' if tick else
                         f'<text x="{frame.x(tick):.1f}" y="{height - 20}" text-anchor="middle" class="c-tick" font-size="{font - 1}">0%</text>')
    parts.append(f'<text x="{frame.left + frame.plot_w / 2:.1f}" y="{height - 4}" text-anchor="middle" class="c-note" font-size="{font - 1}">{escape(labels["x"])}</text>')
    parts.append(f'<text x="{frame.left + 4}" y="{frame.top + 10}" class="c-note" font-size="{font - 1}">{escape(labels["y"])}</text>')
    for x, y in points:
        parts.append(f'<circle cx="{frame.x(x):.1f}" cy="{frame.y(y):.1f}" r="{2.2 if compact else 2.6}" class="c-scatter"/>')
    x_a, x_b = frame.x0 + 1, frame.x1 - 1
    parts.append(f'<line x1="{frame.x(x_a):.1f}" y1="{frame.y(intercept * 100 + slope * x_a):.1f}" x2="{frame.x(x_b):.1f}" y2="{frame.y(intercept * 100 + slope * x_b):.1f}" class="c-fit"/>')
    parts.append(f'<text x="{width - frame.right - 6}" y="{frame.top + 14}" text-anchor="end" class="c-value" font-size="{font + 1}">{escape(labels["fit"])}</text>')
    parts.append("</svg>")
    return "".join(parts)


def bars_svg(rows: list[dict[str, Any]], labels: dict[str, str], fmt: Callable[[float], str], title: str, desc: str, compact: bool = False) -> str:
    """Grouped horizontal bars: the same benchmark's twelve-month change in dollars and in reais."""

    width = 380 if compact else 760
    group = 50 if compact else 46
    height = 34 + group * len(rows)
    values = [r["usd"] for r in rows] + [r["brl"] for r in rows]
    low, high = min(0.0, min(values)) - 4, max(0.0, max(values)) + 6
    frame = _Frame(width, height, (96 if compact else 120, 52, 12, 22), (low, high), (0, 1))
    font = 11 if compact else 12
    parts = _open(width, height, title, desc, compact, "br" + str(int(compact)))
    for tick in (-20, -10, 0, 10, 20, 30):
        if low < tick < high:
            parts.append(f'<line x1="{frame.x(tick):.1f}" x2="{frame.x(tick):.1f}" y1="{frame.top}" y2="{height - frame.bottom}" class="c-grid"/>')
            parts.append(f'<text x="{frame.x(tick):.1f}" y="{height - 6}" text-anchor="middle" class="c-tick" font-size="{font - 1}">{tick:+d}%' + '</text>' if tick else
                         f'<text x="{frame.x(tick):.1f}" y="{height - 6}" text-anchor="middle" class="c-tick" font-size="{font - 1}">0%</text>')
    zero = frame.x(0)
    parts.append(f'<line x1="{zero:.1f}" x2="{zero:.1f}" y1="{frame.top}" y2="{height - frame.bottom}" class="c-axis"/>')
    bar = 14 if compact else 13
    for i, row in enumerate(rows):
        top = frame.top + 8 + i * group
        parts.append(f'<text x="{frame.left - 10}" y="{top + bar + 4}" text-anchor="end" class="c-label" font-size="{font}">{escape(row["name"])}</text>')
        for j, (key, css) in enumerate((("usd", "c-bar-usd"), ("brl", "c-bar-brl"))):
            y0 = top + j * (bar + 3)
            value = row[key]
            x_a, x_b = sorted((zero, frame.x(value)))
            parts.append(f'<rect x="{x_a:.1f}" y="{y0}" width="{max(x_b - x_a, 0.5):.1f}" height="{bar}" rx="2" class="{css}"><title>{escape(labels[key])} · {escape(fmt(value))}</title></rect>')
            tx = frame.x(value) + (5 if value >= 0 else -5)
            parts.append(f'<text x="{tx:.1f}" y="{y0 + bar - 3}" text-anchor="{"start" if value >= 0 else "end"}" class="c-label" font-size="{font - 1}">{escape(fmt(value))}</text>')
    parts.append("</svg>")
    return "".join(parts)
