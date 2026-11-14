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
      "title": "Garden Collage",          # the jigsaw details the AI is asked for; omit to skip
      "series_name": null,
      "series_number": null,
      "manufacturer": "Corner Piece",
      "artist": null,
      "piece_count": 1000,
      "dimensions_cm": "68 x 48",         # compared by its numbers, to within 1 cm
      "tags": ["flowers", "garden"],      # scored by how many of these the AI also gives
      "description": "A collage of ...",  # scored only on whether one is given
      "metadata_complete": true           # blank details above are expected to come back empty
    }

The script sends every photo to every model, at every requested image size, using the same
request the app makes, then scores the answers and writes a report.

Run from the repo (reads AI_API_KEY, AI_ENDPOINT_URL and DATABASE_URL from .env). Each run is
recorded as one ``ai_benchmark`` row in the app's AI calls table with the run's total cost, so the
spend shows in AI Spend and counts toward the daily budget; ``--no-record`` skips that.
``--thinking off`` asks the provider to switch model thinking off:
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
import re
import sys
import time
import threading
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
TAGS_GOOD_RECALL = 0.5
DIMENSION_TOLERANCE_CM = 1.0
# Every jigsaw detail the AI is asked for, in the order the prompt lists them.
METADATA_FIELDS = (
    "title", "series_name", "series_number", "manufacturer", "artist",
    "piece_count", "tags", "dimensions_cm", "description",
)
FREE_TEXT_FIELDS = ("title", "series_name", "manufacturer", "artist")
CORNER_GOOD_IOU = 0.9
INSTRUCTION_TEXT = "Extract jigsaw metadata from this image."
# The AI is asked for these four tags; the app's finer box tags map onto them.
AI_TAGS = {"Box", "Box back", "Box side", "In progress", "Completed", "Reference"}
AI_TAG_FOR_APP_TAG = {"Box front": "Box"}
AI_BENCHMARK_OPERATION = "ai_benchmark"
MODEL_COLUMN_MAX_LENGTH = 128
THINKING_CHOICES = ("default", "off", "low", "medium", "high")


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
    """Overlap (intersection over union) of two 4-point shapes given in 0..1 coordinates.

    Both are put in geometric order first, as the app's crop editor does, so corners listed in a
    crossed order are scored as the shape the user would see.
    """
    expected_mask = _polygon_mask(order_corners(expected), size)
    predicted_mask = _polygon_mask(order_corners(predicted), size)
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


def _is_blank(value):
    return value is None or value == [] or (isinstance(value, str) and not value.strip())


def _expected_metadata(expected):
    """(field, right answer) pairs to score: the details given, plus the blank ones as None
    (expected empty) when the photo is marked ``metadata_complete``."""
    complete = bool(expected.get("metadata_complete"))
    for field in METADATA_FIELDS:
        value = expected.get(field)
        if not _is_blank(value):
            yield field, value
        elif complete:
            yield field, None


def _numbers(text):
    return sorted(float(n) for n in re.findall(r"\d+(?:\.\d+)?", str(text)))


def _dimensions_match(expected, actual):
    want, got = _numbers(expected), _numbers(actual)
    return bool(want) and len(want) == len(got) and all(
        abs(w - g) <= DIMENSION_TOLERANCE_CM for w, g in zip(want, got)
    )


def _tag_list(value):
    if _is_blank(value):
        return []
    items = value if isinstance(value, list) else str(value).split(",")
    return [str(item).strip() for item in items if str(item).strip()]


def tag_recall(expected, actual):
    """Share of the right tags that the answer also gives (fuzzy match)."""
    want, got = _tag_list(expected), _tag_list(actual)
    if not want:
        return 1.0
    return sum(1 for tag in want if any(_text_matches(tag, other) for other in got)) / len(want)


def _simplify_code(value):
    return re.sub(r"[^0-9a-z]", "", str(value).lower())


def _score_metadata_field(field, want, got, scores):
    if want is None:
        scores[f"{field}_ok"] = _is_blank(got)
    elif field == "piece_count":
        try:
            scores["piece_count_ok"] = int(got) == int(want)
        except (TypeError, ValueError):
            scores["piece_count_ok"] = False
    elif field == "series_number":
        scores["series_number_ok"] = not _is_blank(got) and _simplify_code(got) == _simplify_code(want)
    elif field == "dimensions_cm":
        scores["dimensions_cm_ok"] = not _is_blank(got) and _dimensions_match(want, got)
    elif field == "tags":
        recall = tag_recall(want, got)
        scores["tags_recall"] = round(recall, 3)
        scores["tags_ok"] = recall >= TAGS_GOOD_RECALL
    elif field == "description":
        scores["description_ok"] = not _is_blank(got)
    else:
        scores[f"{field}_ok"] = _text_matches(want, got)


def _all_right(scores):
    for key, value in scores.items():
        if key == "corners_spurious":
            if value:
                return False
        elif key == "corner_iou":
            if value < CORNER_GOOD_IOU:
                return False
        elif key.endswith("_ok") and not value:
            return False
    return True


def score_case(expected, metadata, suggestion):
    """Compare one answer against the right answers. Fields not given in ``expected`` are skipped.

    ``all_ok`` is True when every scored field is right (corners need an overlap of at least
    CORNER_GOOD_IOU); skew is reported but not part of it.
    """
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

    for field, want in _expected_metadata(expected):
        _score_metadata_field(field, want, (metadata or {}).get(field), scores)

    if scores:
        scores["all_ok"] = _all_right(scores)
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
        detail_results = [
            s[f"{field}_ok"] for s in scored for field in METADATA_FIELDS if f"{field}_ok" in s
        ]
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
                "series_name": rate("series_name_ok"),
                "series_number": rate("series_number_ok"),
                "manufacturer": rate("manufacturer_ok"),
                "artist": rate("artist_ok"),
                "piece_count": rate("piece_count_ok"),
                "dimensions_cm": rate("dimensions_cm_ok"),
                "tags": rate("tags_ok"),
                "tags_recall_mean": _mean([s.get("tags_recall") for s in scored]),
                "description": rate("description_ok"),
                "details_right": (sum(detail_results), len(detail_results)) if detail_results else None,
                # Failed calls count as wrong: the user gets nothing from them.
                "all_right": (
                    sum(1 for s in scored if s.get("all_ok")),
                    len(scored) + sum(1 for item in items if item.get("error")),
                ) if any("all_ok" in s for s in scored) else None,
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
        "Spurious corners | Skew error | Title | Series | Series no. | Manufacturer | Artist | Pieces | "
        "Dimensions | Tags | Description | Details right | All right | Cost/photo $ | Seconds |\n"
        "|" + "---|" * 23 + "\n"
    )
    lines = []
    for row in rows:
        lines.append(
            "| {model} | {edge} | {photos} | {errors} | {tag} | {orientation} | {iou} | {good} | {spurious} | "
            "{skew} | {title} | {series} | {series_number} | {manufacturer} | {artist} | {pieces} | "
            "{dimensions} | {tags} | {description} | {details} | {all_right} | {cost} | {seconds} |".format(
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
                series=_fmt_rate(row["series_name"]),
                series_number=_fmt_rate(row["series_number"]),
                manufacturer=_fmt_rate(row["manufacturer"]),
                artist=_fmt_rate(row["artist"]),
                pieces=_fmt_rate(row["piece_count"]),
                dimensions=_fmt_rate(row["dimensions_cm"]),
                tags=_fmt_rate(row["tags"]),
                description=_fmt_rate(row["description"]),
                details=_fmt_rate(row["details_right"]),
                all_right=_fmt_rate(row["all_right"]),
                cost=_fmt_number(row["cost_usd_mean"], 5),
                seconds=_fmt_number(row["seconds_mean"], 1),
            )
        )
    notes = (
        f"\nCorner IoU is the overlap between the right shape and the model's (1 = perfect); "
        f"'Corners good' counts IoU of at least {CORNER_GOOD_IOU}. Photos with no corners returned score 0. "
        f"'Tags' counts photos where the AI gave at least {TAGS_GOOD_RECALL:.0%} of the right tags; "
        "'Description' only checks that one was given. 'Details right' adds up every jigsaw detail scored. "
        "'All right' counts photos where every scored answer was right (skew aside); failed calls count as wrong.\n"
    )
    return header + "\n".join(lines) + "\n" + notes


# ---------------------------------------------------------------- running


def reasoning_for_thinking(thinking):
    """OpenRouter ``reasoning`` request field for a --thinking choice (None = provider default)."""
    if not thinking or thinking == "default":
        return None
    if thinking == "off":
        return {"enabled": False}
    return {"effort": thinking}


def build_ai_app(timeout_seconds=None, thinking=None):
    app = Flask("ai_benchmark")
    app.config.update(
        AI_ENABLED=True,
        AI_API_KEY=os.environ.get("AI_API_KEY", ""),
        AI_ENDPOINT_URL=os.environ.get("AI_ENDPOINT_URL", ""),
        AI_MODEL="",
        AI_TIMEOUT_SECONDS=int(timeout_seconds or os.environ.get("AI_TIMEOUT_SECONDS") or 120),
        AI_REASONING=reasoning_for_thinking(thinking),
    )
    return app


def _sum_or_none(values):
    present = [value for value in values if isinstance(value, (int, float))]
    return sum(present) if present else None


def record_run_spend(results, *, run_name, database_url, thinking=None):
    """Write one ai_benchmark row with the run's total cost to the app's AI calls table."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.db import ensure_sqlite_datetime_adapters
    from app.models import AiUsageEvent

    models = list(dict.fromkeys(result["model"] for result in results))
    cost_by_model = {}
    for result in results:
        cost_by_model[result["model"]] = cost_by_model.get(result["model"], 0.0) + (result.get("cost_usd") or 0.0)
    total_cost = round(sum(cost_by_model.values()), 6)
    succeeded = sum(1 for result in results if not result.get("error"))
    model_label = models[0] if len(models) == 1 else f"{len(models)} models: " + ", ".join(models)
    if len(model_label) > MODEL_COLUMN_MAX_LENGTH:
        model_label = model_label[: MODEL_COLUMN_MAX_LENGTH - 3] + "..."

    if database_url.startswith("sqlite"):
        ensure_sqlite_datetime_adapters()
    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            event = AiUsageEvent(
                actor_user_id=None,
                image_id=None,
                operation=AI_BENCHMARK_OPERATION,
                status="success" if succeeded else "error",
                model=model_label,
                endpoint_url=os.environ.get("AI_ENDPOINT_URL") or None,
                prompt_tokens=_sum_or_none(r.get("prompt_tokens") for r in results),
                completion_tokens=_sum_or_none(r.get("completion_tokens") for r in results),
                total_tokens=_sum_or_none(r.get("total_tokens") for r in results),
                provider_cost_usd=Decimal(str(total_cost)),
                final_cost_usd=Decimal(str(total_cost)),
                error_code=None if succeeded else "all_calls_failed",
                payload_json=json.dumps(
                    {
                        "run": run_name,
                        "calls": len(results),
                        "failed_calls": len(results) - succeeded,
                        "photos": len({result["photo"] for result in results}),
                        "thinking": thinking or "default",
                        "cost_usd_by_model": {model: round(cost, 6) for model, cost in cost_by_model.items()},
                    },
                    sort_keys=True,
                ),
            )
            session.add(event)
            session.commit()
            return event.id, total_cost
    finally:
        engine.dispose()


_last_response = threading.local()


def _remember_provider_response(post):
    """Wrap the provider call so a failed answer can still be reported, and its cost counted."""

    def wrapper(**kwargs):
        _last_response.text = None
        _last_response.text = post(**kwargs)
        return _last_response.text

    return wrapper


def _failed_call_details(raw_text):
    """Raw answer text and cost from a provider response the app could not use."""
    if not raw_text:
        return {}
    details = {"raw_response": raw_text[:4000]}
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        return details
    costs = api_routes._build_ai_usage_costs(payload)
    cost = costs.get("final_cost_usd")
    details["cost_usd"] = float(cost) if cost else None
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        details[key] = costs.get(key)
    return details


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
    _last_response.text = None
    try:
        with app.app_context():
            inference = api_routes._infer_jigsaw_metadata_from_images(
                [image], INSTRUCTION_TEXT, max_image_edge=max_edge or None
            )
    except Exception as error:  # noqa: BLE001 - a failed call is a result to report, not a crash
        result.update(error=str(error)[:500], seconds=round(time.monotonic() - started, 2), scores={})
        result.update(_failed_call_details(getattr(_last_response, "text", None)))
        return result

    metadata = inference["metadata"]
    suggestion = api_routes._normalize_ai_image_suggestions(metadata)
    cost = inference.get("final_cost_usd")
    result.update(
        error=None,
        seconds=round(time.monotonic() - started, 2),
        cost_usd=float(cost) if isinstance(cost, (Decimal, int, float)) else None,
        prompt_tokens=inference.get("prompt_tokens"),
        completion_tokens=inference.get("completion_tokens"),
        total_tokens=inference.get("total_tokens"),
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

    database_url = None if args.no_record else os.environ.get("DATABASE_URL")
    if not args.no_record and not database_url:
        print("DATABASE_URL is not set, so the spend cannot be recorded. Set it or pass --no-record.", file=sys.stderr)
        return 1

    app = build_ai_app(args.timeout, args.thinking)
    original_post = api_routes._post_ai_chat_completion
    api_routes._post_ai_chat_completion = _remember_provider_response(original_post)
    try:
        return _run_all(args, cases, app, database_url)
    finally:
        api_routes._post_ai_chat_completion = original_post


def _run_all(args, cases, app, database_url):
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
    if args.thinking and args.thinking != "default":
        print(f"Thinking: {args.thinking}")
    print(summary)
    print(f"Report written to {run_dir}")
    if database_url:
        try:
            event_id, total_cost = record_run_spend(
                results, run_name=run_dir.name, database_url=database_url, thinking=args.thinking
            )
        except Exception as error:  # noqa: BLE001 - the report is saved; say what failed
            print(f"WARNING: could not record the spend in AI Spend: {error}", file=sys.stderr)
            return 2
        print(f"Recorded ${total_cost:.4f} in AI Spend as an {AI_BENCHMARK_OPERATION} call (row {event_id}).")
    return 0


BOX_TAGS = {"Box", "Box back", "Box side"}


def jigsaw_details(jigsaw):
    """The jigsaw's stored details as answer fields, as a starting point to check against the photo."""
    details = {}
    for field in METADATA_FIELDS:
        value = getattr(jigsaw, field, None)
        if field == "tags":
            value = _tag_list(value)
        if not _is_blank(value):
            details[field] = value
    return details


def command_export(args):
    from sqlalchemy import select

    from app import create_app
    from app.db import get_session
    from app.models import Jigsaw, JigsawImage

    folder = Path(args.folder)
    folder.mkdir(parents=True, exist_ok=True)
    app = create_app()
    with app.app_context():
        jigsaw = get_session().get(Jigsaw, args.jigsaw)
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
                if jigsaw is not None and answers["tag"] in BOX_TAGS:
                    answers.update(jigsaw_details(jigsaw))
                answers_path.write_text(json.dumps(answers, indent=2) + "\n", encoding="utf-8")
            print(f"wrote {photo_path.name}")
    print(
        f"{len(images)} photos exported. Box photos start with the jigsaw's stored details: check each "
        "against what the photo actually shows before running."
    )
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
    run.add_argument(
        "--thinking",
        choices=THINKING_CHOICES,
        default="default",
        help="ask the provider to switch model thinking off or set its effort (default: the model's own)",
    )
    run.add_argument("--no-record", action="store_true", help="do not record the spend in AI Spend")
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
