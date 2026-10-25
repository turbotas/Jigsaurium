from io import BytesIO
import sys
from types import ModuleType, SimpleNamespace

import torch
from PIL import Image

from app import image_embeddings


def _make_png_bytes(color=(10, 20, 30), size=(12, 12)):
    output = BytesIO()
    image = Image.new("RGB", size, color=color)
    image.save(output, format="PNG")
    output.seek(0)
    return output.getvalue()


def test_load_clip_model_accepts_transformers_without_clip_exports(monkeypatch):
    image_embeddings._MODEL_CACHE["model_key"] = None
    image_embeddings._MODEL_CACHE["processor"] = None
    image_embeddings._MODEL_CACHE["model"] = None

    class FakeProcessor:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            return cls()

    class FakeModel:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            return cls()

        def eval(self):
            return self

    fake_transformers = ModuleType("transformers")
    fake_transformers.AutoProcessor = FakeProcessor
    fake_transformers.AutoModel = FakeModel
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)

    processor, model = image_embeddings._load_clip_model("demo/model", "main")

    assert isinstance(processor, FakeProcessor)
    assert isinstance(model, FakeModel)


def test_load_clip_model_falls_back_to_use_fast_when_backend_is_unsupported(monkeypatch):
    image_embeddings._MODEL_CACHE["model_key"] = None
    image_embeddings._MODEL_CACHE["processor"] = None
    image_embeddings._MODEL_CACHE["model"] = None

    call_kwargs = []

    class FakeProcessor:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            call_kwargs.append(kwargs)
            if "backend" in kwargs:
                raise TypeError("unexpected keyword argument 'backend'")
            return cls()

    class FakeModel:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            return cls()

        def eval(self):
            return self

    fake_transformers = ModuleType("transformers")
    fake_transformers.AutoProcessor = FakeProcessor
    fake_transformers.AutoModel = FakeModel
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)

    processor, model = image_embeddings._load_clip_model("demo/model", "main")

    assert isinstance(processor, FakeProcessor)
    assert isinstance(model, FakeModel)
    assert call_kwargs[0]["backend"] == "pil"
    assert call_kwargs[1]["use_fast"] is False


def test_load_clip_model_enforces_local_files_only_when_requested(monkeypatch):
    image_embeddings._MODEL_CACHE["model_key"] = None
    image_embeddings._MODEL_CACHE["processor"] = None
    image_embeddings._MODEL_CACHE["model"] = None

    processor_kwargs = []
    model_kwargs = []

    class FakeProcessor:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            processor_kwargs.append(kwargs)
            return cls()

    class FakeModel:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            model_kwargs.append(kwargs)
            return cls()

        def eval(self):
            return self

    fake_transformers = ModuleType("transformers")
    fake_transformers.AutoProcessor = FakeProcessor
    fake_transformers.AutoModel = FakeModel
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)

    processor, model = image_embeddings._load_clip_model("demo/model", "main", local_files_only=True)

    assert isinstance(processor, FakeProcessor)
    assert isinstance(model, FakeModel)
    assert processor_kwargs[0]["local_files_only"] is True
    assert model_kwargs[0]["local_files_only"] is True


def test_compute_image_embedding_falls_back_to_model_outputs_without_get_image_features(monkeypatch):
    class FakeProcessor:
        def __call__(self, *, images, return_tensors):
            assert return_tensors == "pt"
            return {"pixel_values": torch.zeros((1, 3, 12, 12))}

    class FakeModel:
        def __call__(self, **kwargs):
            return SimpleNamespace(pooler_output=torch.tensor([[3.0, 4.0]]))

    monkeypatch.setattr(
        image_embeddings,
        "_load_clip_model",
        lambda model_name, model_revision, **kwargs: (FakeProcessor(), FakeModel()),
    )

    vector = image_embeddings.compute_image_embedding(
        _make_png_bytes(),
        model_name="demo/model",
        model_revision="main",
    )

    assert vector == [0.6, 0.8]


def test_compute_image_embedding_flattens_nested_pooler_output(monkeypatch):
    class FakeProcessor:
        def __call__(self, *, images, return_tensors):
            assert return_tensors == "pt"
            return {"pixel_values": torch.zeros((1, 3, 12, 12))}

    class FakeModel:
        def __call__(self, **kwargs):
            return SimpleNamespace(pooler_output=torch.tensor([[[3.0, 4.0]]]))

    monkeypatch.setattr(
        image_embeddings,
        "_load_clip_model",
        lambda model_name, model_revision, **kwargs: (FakeProcessor(), FakeModel()),
    )

    vector = image_embeddings.compute_image_embedding(
        _make_png_bytes(),
        model_name="demo/model",
        model_revision="main",
    )

    assert vector == [0.6, 0.8]


def test_compute_image_embedding_handles_model_output_from_get_image_features(monkeypatch):
    class FakeProcessor:
        def __call__(self, *, images, return_tensors):
            assert return_tensors == "pt"
            return {"pixel_values": torch.zeros((1, 3, 12, 12))}

    class FakeModel:
        def get_image_features(self, **kwargs):
            return SimpleNamespace(pooler_output=torch.tensor([[3.0, 4.0]]))

    monkeypatch.setattr(
        image_embeddings,
        "_load_clip_model",
        lambda model_name, model_revision, **kwargs: (FakeProcessor(), FakeModel()),
    )

    vector = image_embeddings.compute_image_embedding(
        _make_png_bytes(),
        model_name="demo/model",
        model_revision="main",
    )

    assert vector == [0.6, 0.8]


def test_embedding_runtime_error_reports_missing_transformer_exports(monkeypatch):
    image_embeddings._RUNTIME_CHECK["checked"] = False
    image_embeddings._RUNTIME_CHECK["error"] = None

    fake_transformers = ModuleType("transformers")
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)

    error = image_embeddings.embedding_runtime_error()

    assert isinstance(error, str)
    assert "AutoModel" in error or "CLIPProcessor" in error
