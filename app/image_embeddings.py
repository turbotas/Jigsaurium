import hashlib
import math
import threading
from io import BytesIO


_MODEL_LOCK = threading.Lock()
_MODEL_CACHE = {
    "model_key": None,
    "processor": None,
    "model": None,
}
_RUNTIME_CHECK = {
    "checked": False,
    "error": None,
}


def _normalize_vector(values):
    total = 0.0
    for value in values:
        total += float(value) * float(value)
    norm = math.sqrt(total)
    if norm <= 0:
        return [0.0 for _ in values]
    return [float(value) / norm for value in values]


def _compute_test_fallback_embedding(image_bytes):
    from PIL import Image, ImageOps

    with Image.open(BytesIO(image_bytes)) as source_image:
        normalized = ImageOps.exif_transpose(source_image)
        grayscale = normalized.convert("L")
        thumbnail = grayscale.resize((32, 16))
        pixels = list(thumbnail.getdata())

    values = [float(pixel) / 255.0 for pixel in pixels]
    return _normalize_vector(values)


def _load_clip_model(model_name, model_revision):
    from transformers import AutoModel

    try:
        from transformers import AutoProcessor
    except ImportError:
        from transformers import CLIPProcessor as AutoProcessor

    model_key = f"{model_name}@{model_revision}"
    with _MODEL_LOCK:
        if _MODEL_CACHE["model_key"] == model_key and _MODEL_CACHE["processor"] is not None and _MODEL_CACHE["model"] is not None:
            return _MODEL_CACHE["processor"], _MODEL_CACHE["model"]

        processor = AutoProcessor.from_pretrained(model_name, revision=model_revision, use_fast=False)
        model = AutoModel.from_pretrained(model_name, revision=model_revision)
        model.eval()

        _MODEL_CACHE["model_key"] = model_key
        _MODEL_CACHE["processor"] = processor
        _MODEL_CACHE["model"] = model
        return processor, model


def embedding_runtime_error():
    with _MODEL_LOCK:
        if _RUNTIME_CHECK["checked"]:
            return _RUNTIME_CHECK["error"]

        try:
            import torch  # noqa: F401
            from PIL import Image  # noqa: F401
            from transformers import AutoModel  # noqa: F401

            try:
                from transformers import AutoProcessor  # noqa: F401
            except ImportError:
                from transformers import CLIPProcessor  # noqa: F401
        except Exception as error:
            _RUNTIME_CHECK["checked"] = True
            _RUNTIME_CHECK["error"] = str(error)
            return _RUNTIME_CHECK["error"]

        _RUNTIME_CHECK["checked"] = True
        _RUNTIME_CHECK["error"] = None
        return None


def build_model_key(model_name, model_revision):
    return f"{str(model_name or '').strip()}@{str(model_revision or '').strip()}"


def compute_image_embedding(image_bytes, *, model_name, model_revision, allow_test_fallback=False):
    try:
        import torch
        from PIL import Image, ImageOps
    except ImportError as error:
        if allow_test_fallback:
            return _compute_test_fallback_embedding(image_bytes)
        raise RuntimeError("Image embedding dependencies are not installed.") from error

    try:
        processor, model = _load_clip_model(model_name, model_revision)
    except Exception as error:
        if allow_test_fallback:
            return _compute_test_fallback_embedding(image_bytes)
        raise RuntimeError("Image embedding model could not be loaded.") from error

    try:
        with Image.open(BytesIO(image_bytes)) as source_image:
            normalized = ImageOps.exif_transpose(source_image)
            rgb_image = normalized.convert("RGB")
    except Exception as error:
        if allow_test_fallback:
            return _compute_test_fallback_embedding(image_bytes)
        raise RuntimeError("Image bytes could not be decoded for embedding.") from error

    with torch.no_grad():
        inputs = processor(images=rgb_image, return_tensors="pt")
        if hasattr(model, "get_image_features"):
            features = model.get_image_features(**inputs)
        else:
            outputs = model(**inputs)
            features = getattr(outputs, "pooler_output", None)
            if features is None:
                last_hidden_state = getattr(outputs, "last_hidden_state", None)
                if last_hidden_state is None:
                    raise RuntimeError("Image embedding model output is missing feature tensors.")
                features = last_hidden_state.mean(dim=1)

    vector = features[0].detach().cpu().tolist()
    return _normalize_vector(vector)


def compute_content_sha256(image_bytes):
    return hashlib.sha256(image_bytes or b"").hexdigest()


def cosine_similarity(left, right):
    if not left or not right:
        return 0.0
    length = min(len(left), len(right))
    total = 0.0
    for index in range(length):
        total += float(left[index]) * float(right[index])
    return float(total)
