import base64
import json
from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image

from app.api.v1 import routes


def _jpeg_with_exif_orientation(size, orientation):
    image = Image.new("RGB", size, (200, 30, 30))
    exif = Image.Exif()
    exif[routes.AI_EXIF_ORIENTATION_TAG] = orientation
    buffer = BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


def _fake_image(image_id, data, mime_type="image/jpeg", is_cropped=False):
    return SimpleNamespace(
        id=image_id,
        image_data=data,
        mime_type=mime_type,
        filename=f"image-{image_id}.jpg",
        tag=None,
        jigsaw_id=None,
        is_cropped=is_cropped,
    )


@pytest.mark.functional
def test_prepare_ai_image_payload_applies_exif_orientation_at_full_resolution():
    # Orientation 6 = the camera saved the photo sideways; upright it is taller than wide.
    data = _jpeg_with_exif_orientation((400, 300), orientation=6)

    mime_type, sent = routes._prepare_ai_image_payload(_fake_image(1, data))

    assert mime_type == "image/jpeg"
    with Image.open(BytesIO(sent)) as sent_image:
        assert sent_image.size == (300, 400)
        assert sent_image.getexif().get(routes.AI_EXIF_ORIENTATION_TAG, 1) == 1


@pytest.mark.functional
def test_prepare_ai_image_payload_sends_original_bytes_when_already_upright():
    data = _jpeg_with_exif_orientation((400, 300), orientation=1)

    mime_type, sent = routes._prepare_ai_image_payload(_fake_image(1, data))

    assert mime_type == "image/jpeg"
    assert sent == data


@pytest.mark.functional
@pytest.mark.parametrize(
    ("raw_item", "expected"),
    [
        ({"orientation": 90, "skew": 4.5}, (90, 4.5)),
        ({"orientation": 268, "skew": 0}, (270, 0.0)),
        ({"orientation": None, "skew": -12}, (None, -12.0)),
        ({"orientation": 0, "skew": 60}, (0, None)),
        ({"orientation": "sideways"}, (None, None)),
        ({"rotation_degrees": 91.25}, (90, 1.25)),
        ({"rotation_degrees": 355}, (0, -5.0)),
        ({}, (None, None)),
    ],
)
def test_split_ai_rotation(raw_item, expected):
    assert routes._split_ai_rotation(raw_item) == expected


@pytest.mark.functional
def test_normalize_ai_suggested_corners_reads_the_0_to_1000_grid():
    corners = routes._normalize_ai_suggested_corners(
        [{"x": 100, "y": 50}, {"x": 900, "y": 50}, [900, 950], {"x": 100, "y": 950}]
    )
    assert corners == [
        {"x": 0.1, "y": 0.05},
        {"x": 0.9, "y": 0.05},
        {"x": 0.9, "y": 0.95},
        {"x": 0.1, "y": 0.95},
    ]


@pytest.mark.functional
def test_normalize_ai_suggested_corners_accepts_values_already_between_0_and_1():
    corners = routes._normalize_ai_suggested_corners(
        [{"x": 0.1, "y": 0.2}, {"x": 0.8, "y": 0.2}, {"x": 0.8, "y": 0.9}, {"x": 0.1, "y": 0.9}]
    )
    assert corners[0] == {"x": 0.1, "y": 0.2}
    assert corners[2] == {"x": 0.8, "y": 0.9}


@pytest.mark.functional
@pytest.mark.parametrize(
    "raw_corners",
    [
        None,
        [{"x": 10, "y": 10}, {"x": 990, "y": 10}, {"x": 990, "y": 990}],
        [{"x": 10, "y": 10}, {"x": 3000, "y": 10}, {"x": 3000, "y": 2000}, {"x": 10, "y": 2000}],
        [{"x": 10, "y": 10}, {"x": 10, "y": 10}, {"x": 990, "y": 990}, {"x": 10, "y": 990}],
        [{"x": "a", "y": 10}, {"x": 990, "y": 10}, {"x": 990, "y": 990}, {"x": 10, "y": 990}],
    ],
)
def test_normalize_ai_suggested_corners_rejects_unusable_answers(raw_corners):
    assert routes._normalize_ai_suggested_corners(raw_corners) is None


@pytest.mark.functional
def test_suggestion_with_only_upright_unskewed_rotation_is_not_pending_review():
    suggestion = routes._normalize_ai_image_suggestions({"image_suggestion": {"orientation": 0, "skew": 0}})
    assert suggestion["has_suggestion"] is False


@pytest.mark.functional
def test_ai_image_prompt_explains_tags_rotation_and_corner_grid():
    prompt = routes._build_ai_image_prompt(include_image_suggestion=True, image_count=1)

    for phrase in ("Box =", "Box side =", "Completed =", "Reference =", "orientation", "skew", "0-1000 grid"):
        assert phrase in prompt
    assert "coordinate_space" not in prompt
    assert "rotation_degrees" not in prompt

    multi_prompt = routes._build_ai_image_prompt(include_image_suggestion=True, image_count=3)
    assert "image_suggestions" in multi_prompt
    assert "image_id" in multi_prompt

    no_suggestion_prompt = routes._build_ai_image_prompt(include_image_suggestion=False)
    assert "orientation" not in no_suggestion_prompt


@pytest.mark.functional
def test_inference_sends_upright_image_to_provider(app, monkeypatch):
    app.config["AI_ENABLED"] = True
    app.config["AI_API_KEY"] = "test-key"
    app.config["AI_MODEL"] = "mock-vision"
    app.config["AI_ENDPOINT_URL"] = "https://example.invalid/v1/chat/completions"

    captured = {}

    def fake_post(*, endpoint_url, api_key, request_payload, timeout_seconds):
        captured["payload"] = request_payload
        content = json.dumps({"title": "Upright", "image_suggestion": {"tag": "Box", "orientation": 0}})
        return json.dumps({"choices": [{"message": {"content": content}}]})

    monkeypatch.setattr(routes, "_post_ai_chat_completion", fake_post)

    data = _jpeg_with_exif_orientation((400, 300), orientation=8)
    with app.app_context():
        result = routes._infer_jigsaw_metadata_from_images([_fake_image(7, data)], "Extract jigsaw metadata from this image.")

    assert result["metadata"]["title"] == "Upright"
    image_part = captured["payload"]["messages"][1]["content"][1]
    data_url = image_part["image_url"]["url"]
    assert data_url.startswith("data:image/jpeg;base64,")
    sent = base64.b64decode(data_url.split(",", 1)[1])
    with Image.open(BytesIO(sent)) as sent_image:
        assert sent_image.size == (300, 400)
