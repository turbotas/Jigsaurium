"""Tests for scripts/ai_benchmark.py (comparing AI models on photos with known answers)."""

import importlib.util
import json
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from app.api.v1 import routes

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ai_benchmark.py"


@pytest.fixture(scope="module")
def bench():
    spec = importlib.util.spec_from_file_location("ai_benchmark", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _suggestion(tag=None, orientation=None, skew=None, corners=None):
    return {
        "suggested_tag": tag,
        "suggested_rotation_degrees": orientation,
        "suggested_skew_degrees": skew,
        "suggested_corners": corners,
        "has_suggestion": True,
    }


SQUARE = [(0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9)]


@pytest.mark.functional
def test_order_corners_returns_top_left_first_clockwise(bench):
    shuffled = [(0.9, 0.9), (0.1, 0.1), (0.1, 0.9), (0.9, 0.1)]
    assert bench.order_corners(shuffled) == SQUARE


@pytest.mark.functional
def test_corner_iou(bench):
    assert bench.corner_iou(SQUARE, SQUARE) == pytest.approx(1.0, abs=0.01)
    assert bench.corner_iou(SQUARE, [(0.0, 0.0), (0.05, 0.0), (0.05, 0.05), (0.0, 0.05)]) == 0.0
    left_half = [(0.1, 0.1), (0.5, 0.1), (0.5, 0.9), (0.1, 0.9)]
    assert bench.corner_iou(SQUARE, left_half) == pytest.approx(0.5, abs=0.02)


@pytest.mark.functional
def test_score_case_checks_each_given_answer(bench):
    expected = {
        "tag": ["Box", "Box side"],
        "orientation": [90, 270],
        "skew": 4,
        "corners": [[100, 100], [900, 100], [900, 900], [100, 900]],
        "title": "Garden Collage",
        "manufacturer": "Corner Piece",
        "piece_count": 1000,
    }
    metadata = {"title": "Garden Collage Jigsaw Puzzle", "manufacturer": "Corner Piece Puzzles", "piece_count": 1000}
    corners = [{"x": x, "y": y} for x, y in SQUARE]

    scores = bench.score_case(expected, metadata, _suggestion("Box side", 270, 2.5, corners))

    assert scores["tag_ok"] is True
    assert scores["orientation_ok"] is True
    assert scores["skew_error"] == pytest.approx(1.5)
    assert scores["corner_iou"] == pytest.approx(1.0, abs=0.01)
    assert scores["corner_max_distance"] == pytest.approx(0.0, abs=0.001)
    assert scores["title_ok"] is True
    assert scores["manufacturer_ok"] is True
    assert scores["piece_count_ok"] is True


@pytest.mark.functional
def test_score_case_penalises_missing_and_unwanted_corners(bench):
    wants_corners = {"corners": [[100, 100], [900, 100], [900, 900], [100, 900]]}
    assert bench.score_case(wants_corners, {}, _suggestion())["corner_iou"] == 0.0

    no_corners = {"corners": None}
    corners = [{"x": x, "y": y} for x, y in SQUARE]
    assert bench.score_case(no_corners, {}, _suggestion(corners=corners))["corners_spurious"] is True
    assert bench.score_case(no_corners, {}, _suggestion())["corners_spurious"] is False


@pytest.mark.functional
def test_score_case_skips_answers_not_given(bench):
    scores = bench.score_case({"tag": "Box"}, {"title": "x"}, _suggestion("Reference", 0))
    assert scores == {"tag_ok": False}


@pytest.mark.functional
def test_summarize_and_render(bench):
    results = [
        {"model": "m1", "max_edge": None, "error": None, "cost_usd": 0.001, "seconds": 2.0,
         "scores": {"tag_ok": True, "orientation_ok": False, "corner_iou": 0.95}},
        {"model": "m1", "max_edge": None, "error": None, "cost_usd": 0.003, "seconds": 4.0,
         "scores": {"tag_ok": False, "orientation_ok": True, "corner_iou": 0.5}},
        {"model": "m1", "max_edge": 1024, "error": "timeout", "seconds": 60.0, "scores": {}},
    ]
    rows = bench.summarize(results)

    full = next(row for row in rows if row["max_edge"] is None)
    assert full["tag"] == (1, 2)
    assert full["orientation"] == (1, 2)
    assert full["corners_good"] == (1, 2)
    assert full["corner_iou_mean"] == pytest.approx(0.725)
    assert full["cost_usd_mean"] == pytest.approx(0.002)
    small = next(row for row in rows if row["max_edge"] == 1024)
    assert small["errors"] == 1

    markdown = bench.render_summary_markdown(rows)
    assert "| m1 | full | 2 | 0 | 1/2 | 1/2 | 0.72 | 1/2 |" in markdown
    assert "| m1 | 1024 | 1 | 1 |" in markdown


@pytest.mark.functional
def test_run_scores_photos_and_writes_report(bench, tmp_path, monkeypatch):
    photo = Image.new("RGB", (2000, 1000), (120, 40, 200))
    photo.save(tmp_path / "box.jpg", format="JPEG")
    (tmp_path / "box.json").write_text(
        json.dumps({"tag": "Box", "orientation": 0, "corners": [[100, 100], [900, 100], [900, 900], [100, 900]]}),
        encoding="utf-8",
    )
    (tmp_path / "unlabelled.jpg").write_bytes((tmp_path / "box.jpg").read_bytes())

    monkeypatch.setenv("AI_API_KEY", "test-key")
    monkeypatch.setenv("AI_ENDPOINT_URL", "https://example.invalid/v1/chat/completions")
    sent_sizes = []

    def fake_post(*, endpoint_url, api_key, request_payload, timeout_seconds):
        import base64

        data_url = request_payload["messages"][1]["content"][1]["image_url"]["url"]
        with Image.open(BytesIO(base64.b64decode(data_url.split(",", 1)[1]))) as sent:
            sent_sizes.append(sent.size)
        content = json.dumps({
            "title": "Test",
            "image_suggestion": {
                "tag": "Box", "orientation": 0, "skew": 0,
                "corners": [[100, 100], [900, 100], [900, 900], [100, 900]],
            },
        })
        return json.dumps({"choices": [{"message": {"content": content}}], "usage": {"cost": 0.002}})

    monkeypatch.setattr(routes, "_post_ai_chat_completion", fake_post)

    exit_code = bench.main(["run", str(tmp_path), "--model", "fake/model", "--max-edge", "0", "--max-edge", "500", "--overlays"])

    assert exit_code == 0
    assert sorted(sent_sizes) == [(500, 250), (2000, 1000)]
    run_dir = next((tmp_path / "runs").iterdir())
    report = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    assert len(report["results"]) == 2
    assert all(result["photo"] == "box.jpg" for result in report["results"])
    assert all(result["scores"]["corner_iou"] > 0.98 for result in report["results"])
    summary = (run_dir / "summary.md").read_text(encoding="utf-8")
    assert "| fake/model | full | 1 | 0 | 1/1 | 1/1 |" in summary
    assert "| fake/model | 500 | 1 | 0 | 1/1 | 1/1 |" in summary
    assert (run_dir / "overlays" / "fake_model__500" / "box.jpg").exists()


@pytest.mark.functional
def test_prepare_ai_image_payload_scales_to_max_edge_only_when_larger():
    buffer = BytesIO()
    Image.new("RGB", (3000, 1500), (10, 20, 30)).save(buffer, format="JPEG")
    image = SimpleNamespace(image_data=buffer.getvalue(), mime_type="image/jpeg")

    _, scaled = routes._prepare_ai_image_payload(image, max_edge=1200)
    with Image.open(BytesIO(scaled)) as sent:
        assert sent.size == (1200, 600)

    _, untouched = routes._prepare_ai_image_payload(image, max_edge=4000)
    assert untouched == image.image_data
