import hashlib
import math
import os
import threading
import time
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
    flattened_values = []
    for value in values:
        if isinstance(value, (list, tuple)):
            for nested_value in value:
                flattened_values.append(float(nested_value))
            continue
        flattened_values.append(float(value))

    total = 0.0
    for value in flattened_values:
        total += value * value
    norm = math.sqrt(total)
    if norm <= 0:
        return [0.0 for _ in flattened_values]
    return [value / norm for value in flattened_values]


def _extract_feature_tensor(features):
    if hasattr(features, "detach"):
        return features

    if isinstance(features, (list, tuple)):
        for value in features:
            if hasattr(value, "detach"):
                return value

    pooler_output = getattr(features, "pooler_output", None)
    if hasattr(pooler_output, "detach"):
        return pooler_output

    last_hidden_state = getattr(features, "last_hidden_state", None)
    if hasattr(last_hidden_state, "mean"):
        return last_hidden_state.mean(dim=1)

    raise RuntimeError("Image embedding model output is missing feature tensors.")


def _compute_test_fallback_embedding(image_bytes):
    from PIL import Image, ImageOps

    with Image.open(BytesIO(image_bytes)) as source_image:
        normalized = ImageOps.exif_transpose(source_image)
        grayscale = normalized.convert("L")
        thumbnail = grayscale.resize((32, 16))
        if hasattr(thumbnail, "get_flattened_data"):
            pixels = list(thumbnail.get_flattened_data())
        else:
            pixels = list(thumbnail.getdata())

    values = [float(pixel) / 255.0 for pixel in pixels]
    return _normalize_vector(values)


def _load_clip_model(model_name, model_revision, *, model_local_path=None, local_files_only=False):
    from transformers import AutoModel

    try:
        from transformers import AutoProcessor
    except ImportError:
        from transformers import CLIPProcessor as AutoProcessor

    resolved_local_path = str(model_local_path or "").strip()
    model_source = resolved_local_path or model_name
    model_key = f"{model_source}@{model_revision}|local_only={bool(local_files_only)}"
    with _MODEL_LOCK:
        if _MODEL_CACHE["model_key"] == model_key and _MODEL_CACHE["processor"] is not None and _MODEL_CACHE["model"] is not None:
            return _MODEL_CACHE["processor"], _MODEL_CACHE["model"]

        if resolved_local_path and not os.path.isdir(resolved_local_path):
            raise RuntimeError(f"Configured embedding model path does not exist: {resolved_local_path}")

        load_kwargs = {}
        if resolved_local_path:
            load_kwargs["local_files_only"] = True
        elif bool(local_files_only):
            load_kwargs["local_files_only"] = True
            if model_revision:
                load_kwargs["revision"] = model_revision
        elif model_revision:
            load_kwargs["revision"] = model_revision

        try:
            processor = AutoProcessor.from_pretrained(
                model_source,
                backend="pil",
                **load_kwargs,
            )
        except TypeError:
            processor = AutoProcessor.from_pretrained(
                model_source,
                use_fast=False,
                **load_kwargs,
            )
        model = AutoModel.from_pretrained(model_source, **load_kwargs)
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


def warm_embedding_runtime(*, model_name, model_revision, model_local_path=None, local_files_only=False):
    runtime_error = embedding_runtime_error()
    if runtime_error is not None:
        raise RuntimeError(runtime_error)

    started = time.perf_counter()
    processor, model = _load_clip_model(
        model_name,
        model_revision,
        model_local_path=model_local_path,
        local_files_only=local_files_only,
    )
    duration_seconds = time.perf_counter() - started
    return {
        "processor_loaded": processor is not None,
        "model_loaded": model is not None,
        "duration_seconds": duration_seconds,
    }


def compute_image_embedding(
    image_bytes,
    *,
    model_name,
    model_revision,
    model_local_path=None,
    local_files_only=False,
    allow_test_fallback=False,
):
    if allow_test_fallback:
        runtime_error = embedding_runtime_error()
        if runtime_error is not None:
            return _compute_test_fallback_embedding(image_bytes)

    try:
        import torch
        from PIL import Image, ImageOps
    except ImportError as error:
        if allow_test_fallback:
            return _compute_test_fallback_embedding(image_bytes)
        raise RuntimeError("Image embedding dependencies are not installed.") from error

    try:
        processor, model = _load_clip_model(
            model_name,
            model_revision,
            model_local_path=model_local_path,
            local_files_only=local_files_only,
        )
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
            features = model(**inputs)

    feature_tensor = _extract_feature_tensor(features)

    vector = feature_tensor.detach().cpu().reshape(-1).tolist()
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
