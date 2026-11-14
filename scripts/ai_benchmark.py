"""Compare AI models on the image-suggestion job using photos with known right answers.

Each test photo sits in a folder next to a JSON file with the same name holding the right
answers (``box-front-1.jpg`` + ``box-front-1.json``). Fill these in with
``scripts/ai_benchmark_labeller.html`` or by hand:

    {
      "tag": "Box",                       # or a list of acceptable tags; omit or null to skip
      "orientation": 270,                 # clockwise quarter turn to upright, or a list
      "skew": 4,                          # optional, degrees clockwise after the quarter turn
      "corners": [[60, 190], [880, 190], [930, 885], [110, 885]],
                                          # 0-1000 grid over the photo as the browser shows it,
                                          # null when no corners are expected, omit to skip
      "title": "Garden Collage",          # optional text fields, omit to skip
      "manufacturer": "Corner Piece",
      "piece_count": 1000
    }

The script sends every photo to every model, at every requested image size, using the same
request the app makes, then scores the answers and writes a report.

Run from the repo (reads AI_API_KEY and AI_ENDPOINT_URL from .env; nothing is written to the
database):
    .venv\\Scripts\\python.exe scripts\\ai_benchmark.py run instance\\ai-benchmark ^
        --model openai/gpt-4o-mini --model google/gemini-3.1-flash-lite --max-edge 0 --max-edge 1024

Copy a jigsaw's photos out of the app database as a starting point (writes answer templates
pre-filled with the stored tag):
    .venv\\Scripts\\python.exe scripts\\ai_benchmark.py export instance\\ai-benchmark --jigsaw 215

Each run writes ``runs/<timestamp>/`` inside the folder: ``summary.md`` (one row per model and
size), ``results.json`` (every answer and score) and, with ``--overlays``, pictures with the
right corners in green and the model's in yellow.
"""

import argparse
import difflib
import json
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - containers pass settings as real env vars
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(REPO_ROOT / ".env")

os.environ["IMAGE_EMBEDDINGS_WARM_ON_STARTUP"] = "0"

from flask import Flask  # noqa: E402
from PIL import Image, ImageChops, ImageDraw, ImageOps  # noqa: E402

from app.api.v1 import routes as api_routes  # noqa: E402

IMAGE_SUFFIXES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
GRID = api_routes.AI_CORNER_GRID_SIZE
TEXT_MATCH_RATIO = 0.8
CORNER_GOOD_IOU = 0.9
INSTRUCTION_TEXT = "Extract jigsaw metadata from this image."
# The AI is asked for these four tags; the app's finer box tags map onto them.
AI_TAGS = {"Box", "Box side", "Completed", "Reference"}
AI_TAG_FOR_APP_TAG = {"Box front": "Box", "Box back": "Box side"}


# ---------------------------------------------------------------- loading


def load_cases(folder):
    """Return test cases: every image in ``folder`` that has a matching answers JSON."""
    cases = []
    for path in sorted(Path(folder).iterdir()):
        mime_type = IMAGE_SUFFIXES.get(path.suffix.lower())
        if mime_type is None:
            continue
        answers_path = path.with_suffix(".json")
        if not answers_path.exists():
            continue
        cases.append(
            {
                "name": path.name,
                "path": path,
                "mime_type": mime_type,
                "expected": json.loads(answers_path.read_text(encoding="utf-8")),
            }
        )
    return cases


# ---------------------------------------------------------------- scoring


def _as_list(value):
    if value is None:
        return None
    return value if isinstance(value, list) else [value]


def order_corners(points):
    """Sort 4 (x, y) points into top-left, top-right, bottom-right, bottom-left order."""
    cx = sum(p[0] for p in points) / 4.0
    cy = sum(p[1] for p in points) / 4.0
    by_angle = sorted(points, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
    start = min(range(4), key=lambda i: by_angle[i][0] + by_angle[i][1])
    return by_angle[start:] + by_angle[:start]


def _polygon_mask(points, size):
    mask = Image.new("1", (size, size), 0)
    ImageDraw.Draw(mask).polygon([(x * size, y * size) for x, y in points], fill=1)
    return mask


def _count_set(mask):
    return mask.histogram()[255]


def corner_iou(expected, predicted, size=400):
    """Overlap (intersection over union) of two 4-point shapes given in 0..1 coordinates."""
    expected_mask = _polygon_mask(expected, size)
    predicted_mask = _polygon_mask(predicted, size)
    union = _count_set(ImageChops.logical_or(expected_mask, predicted_mask))
    if union == 0:
        return 0.0
    return _count_set(ImageChops.logical_and(expected_mask, predicted_mask)) / union


def max_corner_distance(expected, predicted):
    """Largest distance between matching corners, as a fraction of the photo's size."""
    pairs = zip(order_corners(expected), order_corners(predicted))
    return max(((ex - px) ** 2 + (ey - py) ** 2) ** 0.5 for (ex, ey), (px, py) in pairs)


def _text_matches(expected, actual):
    if actual is None:
        return False
    a = " ".join(str(expected).lower().split())
    b = " ".join(str(actual).lower().split())
    return a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() >= TEXT_MATCH_RATIO


def score_case(expected, metadata, suggestion):
    """Compare one answer against the right answers. Fields not given in ``expected`` are skipped."""
    scores = {}

    if expected.get("tag") is not None:
        scores["tag_ok"] = suggestion["suggested_tag"] in _as_list(expected["tag"])

    if expected.get("orientation") is not None:
        accepted = [int(value) % 360 for value in _as_list(expected["orientation"])]
        scores["orientation_ok"] = suggestion["suggested_rotation_degrees"] in accepted

    if expected.get("skew") is not None and suggestion["suggested_skew_degrees"] is not None:
        scores["skew_error"] = abs(float(expected["skew"]) - suggestion["suggested_skew_degrees"])

    if "corners" in expected:
        predicted = suggestion["suggested_corners"]
        if expected["corners"] is None:
            scores["corners_spurious"] = bool(predicted)
        else:
            truth = [(float(x) / GRID, float(y) / GRID) for x, y in expected["corners"]]
            if predicted:
                points = [(p["x"], p["y"]) for p in predicted]
                scores["corner_iou"] = round(corner_iou(truth, points), 4)
                scores["corner_max_distance"] = round(max_corner_distance(truth, points), 4)
            else:
                scores["corner_iou"] = 0.0
                scores["corner_max_distance"] = None

    for field in ("title", "manufacturer"):
        if expected.get(field):
            scores[f"{field}_ok"] = _text_matches(expected[field], metadata.get(field))
    if expected.get("piece_count") is not None:
        try:
            scores["piece_count_ok"] = int(metadata.get("piece_count")) == int(expected["piece_count"])
        except (TypeError, ValueError):
            scores["piece_count_ok"] = False
    return scores


def _mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def summarize(results):
    """One row per (model, max_edge) with accuracy, corner quality, cost and time."""
    groups = {}
    for result in results:
        groups.setdefault((result["model"], result["max_edge"]), []).append(result)

    rows = []
    for (model, max_edge), items in groups.items():
        scored = [item["scores"] for item in items if item.get("error") is None]

        def rate(key, wanted=True, scored=scored):
            values = [s[key] == wanted for s in scored if key in s]
            return (sum(values), len(values)) if values else None

        ious = [s["corner_iou"] for s in scored if "corner_iou" in s]
        rows.append(
            {
                "model": model,
                "max_edge": max_edge,
                "photos": len(items),
                "errors": sum(1 for item in items if item.get("error")),
                "tag": rate("tag_ok"),
                "orientation": rate("orientation_ok"),
                "corner_iou_mean": _mean(ious),
                "corners_good": (sum(1 for v in ious if v >= CORNER_GOOD_IOU), len(ious)) if ious else None,
                "corners_spurious": rate("corners_spurious"),
                "skew_error_mean": _mean([s.get("skew_error") for s in scored]),
                "title": rate("title_ok"),
                "manufacturer": rate("manufacturer_ok"),
                "piece_count": rate("piece_count_ok"),
                "cost_usd_mean": _mean([item.get("cost_usd") for item in items]),
                "seconds_mean": _mean([item.get("seconds") for item in items]),
            }
        )
    rows.sort(key=lambda row: (row["model"], row["max_edge"] or 0))
    return rows


def _fmt_rate(value):
    return "-" if value is None else f"{value[0]}/{value[1]}"


def _fmt_number(value, digits):
    return "-" if value is None else f"{value:.{digits}f}"


def render_summary_markdown(rows):
    header = (
        "| Model | Max edge | Photos | Errors | Tag | Orientation | Corner IoU | Corners good | "
        "Spurious corners | Skew error | Title | Manufacturer | Pieces | Cost/photo $ | Seconds |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    )
    lines = []
    for row in rows:
        lines.append(
            "| {model} | {edge} | {photos} | {errors} | {tag} | {orientation} | {iou} | {good} | {spurious} | "
            "{skew} | {title} | {manufacturer} | {pieces} | {cost} | {seconds} |".format(
                model=row["model"],
                edge=row["max_edge"] or "full",
                photos=row["photos"],
                errors=row["errors"],
                tag=_fmt_rate(row["tag"]),
                orientation=_fmt_rate(row["orientation"]),
                iou=_fmt_number(row["corner_iou_mean"], 2),
                good=_fmt_rate(row["corners_good"]),
                spurious=_fmt_rate(row["corners_spurious"]),
                skew=_fmt_number(row["skew_error_mean"], 1),
                title=_fmt_rate(row["title"]),
                manufacturer=_fmt_rate(row["manufacturer"]),
                pieces=_fmt_rate(row["piece_count"]),
                cost=_fmt_number(row["cost_usd_mean"], 5),
                seconds=_fmt_number(row["seconds_mean"], 1),
            )
        )
    notes = (
        f"\nCorner IoU is the overlap between the right shape and the model's (1 = perfect); "
        f"'Corners good' counts IoU of at least {CORNER_GOOD_IOU}. Photos with no corners returned score 0.\n"
    )
    return header + "\n".join(lines) + "\n" + notes


# ---------------------------------------------------------------- running


def build_ai_app(timeout_seconds=None):
    app = Flask("ai_benchmark")
    app.config.update(
        AI_ENABLED=True,
        AI_API_KEY=os.environ.get("AI_API_KEY", ""),
        AI_ENDPOINT_URL=os.environ.get("AI_ENDPOINT_URL", ""),
        AI_MODEL="",
        AI_TIMEOUT_SECONDS=int(timeout_seconds or os.environ.get("AI_TIMEOUT_SECONDS") or 120),
    )
    return app


def run_case(app, case, model, max_edge):
    image = SimpleNamespace(
        id=1,
        image_data=case["path"].read_bytes(),
        mime_type=case["mime_type"],
        filename=case["name"],
        tag=None,
        jigsaw_id=None,
        is_cropped=False,
    )
    result = {"photo": case["name"], "model": model, "max_edge": max_edge or None}
    started = time.monotonic()
    try:
        with app.app_context():
            inference = api_routes._infer_jigsaw_metadata_from_images(
                [image], INSTRUCTION_TEXT, max_image_edge=max_edge or None
            )
    except Exception as error:  # noqa: BLE001 - a failed call is a result to report, not a crash
        result.update(error=str(error)[:500], seconds=round(time.monotonic() - started, 2), scores={})
        return result

    metadata = inference["metadata"]
    suggestion = api_routes._normalize_ai_image_suggestions(metadata)
    cost = inference.get("final_cost_usd")
    result.update(
        error=None,
        seconds=round(time.monotonic() - started, 2),
        cost_usd=float(cost) if isinstance(cost, (Decimal, int, float)) else None,
        metadata=metadata,
        suggestion=suggestion,
        scores=score_case(case["expected"], metadata, suggestion),
    )
    return result


def _upright_image(path):
    with Image.open(path) as source:
        return ImageOps.exif_transpose(source).convert("RGB")


def draw_overlay(case, result, out_path):
    image = _upright_image(case["path"])
    width, height = image.size
    draw = ImageDraw.Draw(image)
    line_width = max(4, width // 250)

    def polygon(points, colour):
        pixels = [(x * width, y * height) for x, y in points]
        draw.line(pixels + [pixels[0]], fill=colour, width=line_width)

    expected = case["expected"].get("corners")
    if expected:
        polygon([(x / GRID, y / GRID) for x, y in expected], (0, 200, 0))
    predicted = (result.get("suggestion") or {}).get("suggested_corners")
    if predicted:
        polygon([(p["x"], p["y"]) for p in predicted], (255, 210, 0))
    image.thumbnail((1200, 1200))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path, quality=85)


def _json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"not JSON serializable: {type(value)!r}")


def command_run(args):
    cases = load_cases(args.folder)
    if not cases:
        print(f"No photos with answer files found in {args.folder}.", file=sys.stderr)
        return 1
    if not os.environ.get("AI_API_KEY") or not os.environ.get("AI_ENDPOINT_URL"):
        print("AI_API_KEY and AI_ENDPOINT_URL must be set (in .env or the environment).", file=sys.stderr)
        return 1

    app = build_ai_app(args.timeout)
    edges = args.max_edge or [0]
    run_dir = Path(args.folder) / "runs" / datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for model in args.model:
        # Models run one after another: the app reads the model from shared config.
        app.config["AI_MODEL"] = model
        for edge in edges:
            print(f"{model} @ {edge or 'full'}: {len(cases)} photos", flush=True)
            with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
                batch = list(pool.map(lambda case, m=model, e=edge: run_case(app, case, m, e), cases))
            for case, result in zip(cases, batch):
                status = "error: " + result["error"] if result.get("error") else json.dumps(result["scores"])
                print(f"  {case['name']}: {status}", flush=True)
                if args.overlays and not result.get("error"):
                    label = f"{model.replace('/', '_')}__{edge or 'full'}"
                    draw_overlay(case, result, run_dir / "overlays" / label / f"{case['path'].stem}.jpg")
            results.extend(batch)

    rows = summarize(results)
    summary = render_summary_markdown(rows)
    (run_dir / "summary.md").write_text(summary, encoding="utf-8")
    (run_dir / "results.json").write_text(
        json.dumps({"results": results, "summary": rows}, indent=1, default=_json_default), encoding="utf-8"
    )
    print()
    print(summary)
    print(f"Report written to {run_dir}")
    return 0


def command_export(args):
    from sqlalchemy import select

    from app import create_app
    from app.db import get_session
    from app.models import JigsawImage

    folder = Path(args.folder)
    folder.mkdir(parents=True, exist_ok=True)
    app = create_app()
    with app.app_context():
        images = get_session().execute(
            select(JigsawImage).where(JigsawImage.jigsaw_id == args.jigsaw).order_by(JigsawImage.id)
        ).scalars().all()
        for image in images:
            suffix = {"image/png": ".png", "image/webp": ".webp"}.get(image.mime_type, ".jpg")
            photo_path = folder / f"jigsaw{args.jigsaw}-image{image.id}{suffix}"
            photo_path.write_bytes(image.image_data)
            answers_path = photo_path.with_suffix(".json")
            if not answers_path.exists():
                answers = {"tag": AI_TAG_FOR_APP_TAG.get(image.tag, image.tag), "orientation": None}
                if answers["tag"] not in AI_TAGS:
                    answers["tag"] = None
                answers_path.write_text(json.dumps(answers, indent=2) + "\n", encoding="utf-8")
            print(f"wrote {photo_path.name}")
    print(f"{len(images)} photos exported. Fill in the .json answer files before running.")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="send every photo to every model and score the answers")
    run.add_argument("folder", help="folder of photos with matching .json answer files")
    run.add_argument("--model", action="append", required=True, help="OpenRouter model id; repeat for several")
    run.add_argument(
        "--max-edge",
        action="append",
        type=int,
        help="longest image edge in pixels to send (0 = full size); repeat to compare sizes",
    )
    run.add_argument("--workers", type=int, default=4, help="photos sent at the same time (default 4)")
    run.add_argument("--timeout", type=int, help="seconds to wait for each answer")
    run.add_argument("--overlays", action="store_true", help="save pictures of the right and returned corners")
    run.set_defaults(handler=command_run)

    export = commands.add_parser("export", help="copy a jigsaw's photos from the app database into the folder")
    export.add_argument("folder")
    export.add_argument("--jigsaw", type=int, required=True)
    export.set_defaults(handler=command_export)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
