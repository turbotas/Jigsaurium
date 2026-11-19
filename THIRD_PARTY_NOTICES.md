# Third-Party Notices

This file is the index of every licence that applies to Jigsaurium: the project's own licence, and each third-party component it ships, with a link to where that component's licence text lives. It ships in the container image beside [`LICENSE`](LICENSE).

## Jigsaurium

- **AGPL-3.0-only**: [`LICENSE`](LICENSE)

## Third-party files in this repository

These files are committed here and served by the app, so their licence texts are committed beside them.

| Component | What is shipped | Licence | Licence text |
| --- | --- | --- | --- |
| Lexend typeface | Font files in `app/static/fonts/lexend/` | SIL Open Font License 1.1. Copyright 2018 The Lexend Project Authors (https://github.com/googlefonts/lexend), with Reserved Font Name "RevReading Lexend" | [`app/static/fonts/lexend/OFL.txt`](app/static/fonts/lexend/OFL.txt) |
| GOV.UK Frontend 6.6.0 | JavaScript, and CSS compiled from its Sass, in `app/static/vendor/govuk/` | MIT. Copyright (C) 2017 Crown Copyright (Government Digital Service) | [`app/static/vendor/govuk/LICENSE.txt`](app/static/vendor/govuk/LICENSE.txt) |

GOV.UK Frontend's own font (GDS Transport) and images (the crown crest and GOV.UK icons) are GOV.UK branding and are deliberately not shipped.

## Third-party software added to the container image

These are installed when the image is built. Their licence texts come with them and stay inside the image.

| Component | Where it is in the image | Licence | Licence text |
| --- | --- | --- | --- |
| Python runtime packages (listed below) | Python `site-packages` | As listed below | Each package's `*.dist-info/` folder (`LICENSE`, `licenses/` or the `License` metadata field) |
| CLIP image-embedding model `openai/clip-vit-base-patch32`, revision `3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268` | `/opt/models/clip-vit-base-patch32` | The Hugging Face model page declares no licence. OpenAI's CLIP code repository is MIT | https://github.com/openai/CLIP/blob/main/LICENSE and https://huggingface.co/openai/clip-vit-base-patch32 |
| Debian base image (`python:3.12-slim`) | Operating-system packages | Various, per package | `/usr/share/doc/<package>/copyright` |

### Python runtime packages (direct dependencies)

Licences as declared in each package's metadata.

| Package | Licence |
| --- | --- |
| Flask | BSD-3-Clause |
| SQLAlchemy | MIT |
| Alembic | MIT |
| PyMySQL | MIT |
| PyJWT | MIT |
| Pillow | MIT-CMU |
| pillow-heif | BSD-3-Clause |
| gunicorn | MIT |
| torch (CPU wheel) | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND ISC AND MIT AND Zlib |
| transformers | Apache-2.0 |
| huggingface_hub (via transformers; also fetches the model during the image build) | Apache-2.0 |

## Build and test tools (not shipped)

Used to build or test Jigsaurium; none of these end up in the app or the image.

| Tool | Used for | Licence |
| --- | --- | --- |
| govuk-frontend (npm) | Source of the GOV.UK Frontend files above | MIT |
| sass (npm) | Compiles the GOV.UK Frontend CSS | MIT |
| @fontsource/lexend (npm) | Source of the Lexend font files above | OFL-1.1 |
| pytest | Tests | MIT |
| python-dotenv | Local configuration | BSD-3-Clause |
| playwright | Browser tests | Apache-2.0 |
| Syft (run by `anchore/sbom-action` in CI) | Scans the prod image for its SBOM | Apache-2.0 |

## Services called but not shipped

- The AI service configured with `AI_ENDPOINT_URL` / `AI_MODEL` is called over its API; no model or code from it is shipped. Its provider's terms apply to its use.

## Compatibility review summary

As of 2026-11-17, every shipped component above is under a permissive licence (MIT, BSD, Apache-2.0, ISC, Zlib, BSL-1.0) or the SIL Open Font License, all compatible with distributing Jigsaurium under AGPL-3.0. The OFL covers only the font files, not the software or pages that use them. The CLIP weights have no declared licence on their model page; that is recorded above rather than assumed.

## Keeping this index current

Adding or replacing a dependency, font, image, model or other third-party file means updating this file in the same change, and committing any licence text the component requires next to the shipped files. See [`CONTRIBUTING.md`](CONTRIBUTING.md).
