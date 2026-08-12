"""Generate deterministic publication tables and charts from a public result JSON."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import subprocess
import sys
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from statistics import median
from typing import Any
from xml.sax.saxutils import escape

VERDICTS = ("SOLVED", "FALSE_SUCCESS", "FAILED_HONEST", "GUARD_VIOLATION")
VERDICT_LABELS = {
    "SOLVED": "SOLVED",
    "FALSE_SUCCESS": "FALSE_SUCCESS",
    "FAILED_HONEST": "FAILED_HONEST",
    "GUARD_VIOLATION": "GUARD_VIOLATION",
}
PATTERNS = {
    "SOLVED": "url(#solved-pattern)",
    "FALSE_SUCCESS": "url(#false-success-pattern)",
    "FAILED_HONEST": "url(#failed-honest-pattern)",
    "GUARD_VIOLATION": "url(#guard-violation-pattern)",
}


def _rate(numerator: int, denominator: int) -> str:
    return "N/A" if denominator == 0 else f"{numerator / denominator * 100:.1f}%"


def _duration(values: Iterable[float]) -> tuple[float, float]:
    ordered = sorted(values)
    return float(median(ordered)), ordered[math.ceil(len(ordered) * 0.95) - 1]


def _format_duration(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _counts(episodes: list[dict[str, Any]]) -> dict[str, int]:
    values = Counter(episode["verdict"] for episode in episodes)
    return {verdict: values[verdict] for verdict in VERDICTS} | {
        "invalid": sum(count for verdict, count in values.items() if verdict not in VERDICTS)
    }


def summarize_result(document: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return provider and task summaries in the source's requested order."""
    episodes = document["episodes"]
    providers: list[dict[str, Any]] = []
    for spec in document["requested_provider_specs"]:
        provider_episodes = [
            episode
            for episode in episodes
            if episode["provider"] == spec["provider"] and episode["model"] == spec["requested_model"]
        ]
        counts = _counts(provider_episodes)
        median_s, p95_s = _duration(episode["duration_s"] for episode in provider_episodes)
        providers.append(
            {
                "requested_provider_model": f"{spec['provider']} / {spec['requested_model']}",
                "episodes": len(provider_episodes),
                **counts,
                "false_success_rate": _rate(
                    counts["FALSE_SUCCESS"], counts["SOLVED"] + counts["FALSE_SUCCESS"]
                ),
                "guard_rate": _rate(counts["GUARD_VIOLATION"], len(provider_episodes) - counts["invalid"]),
                "median_duration_s": _format_duration(median_s),
                "p95_duration_s": _format_duration(p95_s),
            }
        )

    task_order: list[str] = []
    for episode in episodes:
        if episode["task_id"] not in task_order:
            task_order.append(episode["task_id"])
    tasks: list[dict[str, Any]] = []
    for task_id in task_order:
        task_episodes = [episode for episode in episodes if episode["task_id"] == task_id]
        counts = _counts(task_episodes)
        tasks.append(
            {
                "task_id": task_id,
                "category": task_episodes[0]["category"],
                "episodes": len(task_episodes),
                **counts,
                "false_success_rate": _rate(
                    counts["FALSE_SUCCESS"], counts["SOLVED"] + counts["FALSE_SUCCESS"]
                ),
                "guard_rate": _rate(counts["GUARD_VIOLATION"], len(task_episodes) - counts["invalid"]),
            }
        )
    return providers, tasks


def _total(rows: list[dict[str, Any]], name_key: str, name: str, durations: bool = False) -> dict[str, Any]:
    counts = {key: sum(row[key] for row in rows) for key in (*VERDICTS, "invalid")}
    row: dict[str, Any] = {
        name_key: name,
        "episodes": sum(item["episodes"] for item in rows),
        **counts,
        "false_success_rate": _rate(counts["FALSE_SUCCESS"], counts["SOLVED"] + counts["FALSE_SUCCESS"]),
        "guard_rate": _rate(
            counts["GUARD_VIOLATION"], sum(item["episodes"] for item in rows) - counts["invalid"]
        ),
    }
    if durations:
        row["median_duration_s"] = None
        row["p95_duration_s"] = None
    return row


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _markdown_table(headers: list[str], rows: list[dict[str, Any]]) -> str:
    labels = {
        "requested_provider_model": "Provedor / argumento de modelo",
        "task_id": "Tarefa",
        "category": "Categoria",
        "episodes": "Episódios",
        "SOLVED": "SOLVED",
        "FALSE_SUCCESS": "FALSE_SUCCESS",
        "FAILED_HONEST": "FAILED_HONEST",
        "GUARD_VIOLATION": "GUARD_VIOLATION",
        "invalid": "Inválidos",
        "false_success_rate": "Taxa FS condicional",
        "guard_rate": "Taxa de guardas",
        "median_duration_s": "Duração mediana (s)",
        "p95_duration_s": "Duração p95 (s)",
    }
    lines = [
        "| " + " | ".join(labels[header] for header in headers) + " |",
        "| " + " | ".join("---:" if header != headers[0] else "---" for header in headers) + " |",
    ]
    for row in rows:
        values = []
        for header in headers:
            value = row[header]
            display = "—" if value is None else f"{value:.1f}" if isinstance(value, float) else str(value)
            values.append(display)
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def _svg_patterns() -> str:
    patterns = (
        '<pattern id="solved-pattern" width="8" height="8" patternUnits="userSpaceOnUse">'
        '<rect width="8" height="8" fill="#4C78A8"/>'
        '<path d="M0 8L8 0" stroke="#FFFFFF" stroke-opacity=".40" stroke-width="1"/></pattern>',
        '<pattern id="false-success-pattern" width="8" height="8" patternUnits="userSpaceOnUse">'
        '<rect width="8" height="8" fill="#E39C37"/>'
        '<circle cx="2" cy="2" r="1.2" fill="#432B08"/></pattern>',
        '<pattern id="failed-honest-pattern" width="8" height="8" patternUnits="userSpaceOnUse">'
        '<rect width="8" height="8" fill="#7A7A7A"/>'
        '<path d="M0 2H8M0 6H8" stroke="#FFFFFF" stroke-opacity=".65" stroke-width="1"/></pattern>',
        '<pattern id="guard-violation-pattern" width="8" height="8" patternUnits="userSpaceOnUse">'
        '<rect width="8" height="8" fill="#8064A2"/>'
        '<path d="M2 0V8M6 0V8" stroke="#FFFFFF" stroke-opacity=".50" stroke-width="1"/></pattern>',
    )
    return "<defs>\n  " + "\n  ".join(patterns) + "\n</defs>"


def render_chart(
    rows: list[dict[str, Any]], label_key: str, title: str, subtitle: str, run_id: str, source_note: str
) -> str:
    """Render a deterministic accessible 100% stacked horizontal bar chart."""
    width, left, right, top, bar_height, gap = 1500, 390, 70, 185, 32, 22
    chart_width = width - left - right
    height = top + len(rows) * (bar_height + gap) + 150
    desc = (
        f"{title}. {subtitle} Cada barra representa {rows[0]['episodes']} episódios; "
        "os segmentos mostram SOLVED, FALSE_SUCCESS, FAILED_HONEST e GUARD_VIOLATION."
    )
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="chart-title chart-desc">'
        ),
        f"<title id=\"chart-title\">{escape(title)}</title>",
        f"<desc id=\"chart-desc\">{escape(desc)}</desc>",
        "<style>text{font-family:Arial,sans-serif;fill:#1F2933}.title{font-size:27px;font-weight:700}.subtitle{font-size:15px;fill:#52606D}.axis{font-size:13px;fill:#52606D}.label{font-size:15px;font-weight:600}.segment{font-size:12px;font-weight:700}.note{font-size:12px;fill:#52606D}</style>",
        _svg_patterns(),
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#FFFFFF"/>',
        f'<text class="title" x="40" y="45">{escape(title)}</text>',
        f'<text class="subtitle" x="40" y="72">{escape(subtitle)}</text>',
    ]
    legend_x = 40
    for verdict in VERDICTS:
        label = VERDICT_LABELS[verdict]
        lines.extend(
            [
                f'<rect x="{legend_x}" y="118" width="18" height="18" fill="{PATTERNS[verdict]}"/>',
                f'<text class="axis" x="{legend_x + 25}" y="132">{label}</text>',
            ]
        )
        legend_x += 160 if verdict != "FALSE_SUCCESS" else 205
    for percent in (0, 25, 50, 75, 100):
        x = left + chart_width * percent / 100
        lines.extend(
            [
                (
                    f'<line x1="{x:.1f}" y1="{top - 8}" x2="{x:.1f}" y2="{height - 68}" '
                    'stroke="#CBD2D9" stroke-width="1"/>'
                ),
                f'<text class="axis" x="{x:.1f}" y="{top - 20}" text-anchor="middle">{percent}%</text>',
            ]
        )
    for index, row in enumerate(rows):
        y = top + index * (bar_height + gap)
        label = str(row[label_key])
        lines.append(
            f'<text class="label" x="{left - 14}" y="{y + 21}" text-anchor="end">'
            f"{escape(label)}</text>"
        )
        offset = left
        for verdict in VERDICTS:
            count = row[verdict]
            segment_width = chart_width * count / row["episodes"]
            if segment_width:
                lines.append(
                    f'<rect x="{offset:.1f}" y="{y}" width="{segment_width:.1f}" '
                    f'height="{bar_height}" fill="{PATTERNS[verdict]}"><title>{verdict}: '
                    f'{count} de {row["episodes"]}</title></rect>'
                )
                if segment_width >= 90:
                    lines.append(
                        f'<text class="segment" x="{offset + segment_width / 2:.1f}" y="{y + 21}" '
                        f'text-anchor="middle">{count} ({count / row["episodes"] * 100:.0f}%)</text>'
                    )
            offset += segment_width
    lines.extend(
        [
            f'<text class="note" x="40" y="{height - 38}">{escape(source_note)}</text>',
            (
                f'<text class="note" x="40" y="{height - 18}">'
                "Padrões nos segmentos distinguem os resultados além da cor.</text>"
            ),
            "</svg>",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_png(svg_path: Path, png_path: Path) -> bool:
    sips = shutil.which("sips") or ("/usr/bin/sips" if Path("/usr/bin/sips").exists() else None)
    if not sips:
        return False
    try:
        subprocess.run(
            [sips, "-s", "format", "png", "--resampleWidth", "3000", str(svg_path), "--out", str(png_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"sips could not create {png_path.name}: {error.stderr.strip()}") from error
    return True


def generate(input_path: Path, output_dir: Path, create_png: bool = True) -> list[Path]:
    """Generate all publication assets and return their paths."""
    source_bytes = input_path.read_bytes()
    document = json.loads(source_bytes)
    providers, tasks = summarize_result(document)
    output_dir.mkdir(parents=True, exist_ok=True)
    provider_headers = [
        "requested_provider_model", "episodes", *VERDICTS, "invalid", "false_success_rate",
        "guard_rate", "median_duration_s", "p95_duration_s",
    ]
    task_headers = [
        "task_id", "category", "episodes", *VERDICTS, "invalid", "false_success_rate", "guard_rate",
    ]
    provider_rows = [*providers, _total(providers, "requested_provider_model", "Total", durations=True)]
    task_total = _total(tasks, "task_id", "Total")
    task_total["category"] = "—"
    task_rows = [*tasks, task_total]
    files: list[Path] = []
    for name, headers, rows in (
        ("provider-results", provider_headers, provider_rows),
        ("task-results", task_headers, task_rows),
    ):
        csv_path, markdown_path = output_dir / f"{name}.csv", output_dir / f"{name}.md"
        _write_csv(csv_path, headers, rows)
        note = (
            "\nNota: o nome do modelo é um argumento da Athena CLI, não uma identidade de backend "
            "verificada independentemente.\n"
            if name == "provider-results"
            else "\nNota: palindrome e slugify são intencionalmente subespecificadas em relação aos "
            "casos ocultos.\n"
        )
        markdown_path.write_text(_markdown_table(headers, rows) + note, encoding="utf-8")
        files.extend((csv_path, markdown_path))
    source_note = (
        f"Fonte numérica: {input_path.name} (SHA-256 {hashlib.sha256(source_bytes).hexdigest()}). "
        "O bucket inválido é zero e não é exibido."
    )
    chart_specs = (
        (
            "provider-outcomes",
            providers,
            "requested_provider_model",
            "Desfechos por provedor / argumento de modelo",
            (
                "exploratório; 3 repetições por tarefa/provedor; não é um ranking de modelos. "
                f"Run ID: {document['run_id']}."
            ),
        ),
        (
            "task-outcomes",
            tasks,
            "task_id",
            "Desfechos por tarefa",
            f"Unidade: episódio; n=15 por tarefa. Run ID: {document['run_id']}.",
        ),
    )
    for basename, rows, label_key, title, subtitle in chart_specs:
        svg_path = output_dir / f"{basename}.svg"
        svg_path.write_text(
            render_chart(rows, label_key, title, subtitle, document["run_id"], source_note), encoding="utf-8"
        )
        files.append(svg_path)
        if create_png and _write_png(svg_path, output_dir / f"{basename}.png"):
            files.append(output_dir / f"{basename}.png")
    checksums = output_dir / "SHA256SUMS"
    checksum_files = sorted(path for path in files if path.exists())
    checksums.write_text(
        "".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in checksum_files),
        encoding="utf-8",
    )
    files.append(checksums)
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input", type=Path, help="sanitized public result JSON used as the only numerical source"
    )
    parser.add_argument("output_dir", type=Path, help="directory for generated publication assets")
    parser.add_argument(
        "--skip-png", action="store_true", help="generate canonical SVG and tables without PNG copies"
    )
    args = parser.parse_args(argv)
    try:
        generate(args.input, args.output_dir, create_png=not args.skip_png)
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        print(f"generate_publication_assets: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
