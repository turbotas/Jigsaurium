# Design System Specification

## Primary Design Standard

Use GOV.UK Design System components and interaction patterns by default.

## Branding Policy

- Follow GOV.UK baseline visuals.
- Allow light branding only (for example: logo and limited color accents).
- Typeface: **Lexend** (SIL Open Font License 1.1), self-hosted in `app/static/fonts/lexend` with its `OFL.txt`. Jigsaurium is not a GOV.UK service, so it does not use the GOV.UK-only GDS Transport font. Custom CSS uses `var(--app-font-family)`, never a font name.
- Keep custom branding in a separate override layer.
- Do not modify GOV.UK vendor source files directly.

## Frontend Rules for SPA

- Use GOV.UK form patterns and validation guidance.
- Preserve keyboard accessibility and visible focus states.
- Use consistent GOV.UK spacing and typography scales.
- Use accessible error summaries and field-level error messaging.

## Upstream Update Workflow

- Pin a `govuk-frontend` version (and the `sass` and `@fontsource/lexend` dev dependencies used to build it).
- Keep vendor and custom code separated.
- `scripts/vendor_govuk_assets.py` builds `app/static/vendor/govuk` from the pinned package:
  - the JavaScript is copied from `node_modules/govuk-frontend/dist/govuk`; GOV.UK's `assets` folder (GDS Transport font, crown crest and GOV.UK icons) is not shipped, because it is GOV.UK branding;
  - GOV.UK Frontend's MIT licence stays beside the copied files as `app/static/vendor/govuk/LICENSE.txt` (the npm package has no licence file, so it comes from the `alphagov/govuk-frontend` repository at the pinned tag; refresh it when changing major version);
  - `govuk-frontend.min.css` is compiled from GOV.UK Frontend's Sass through `app/static/scss/govuk-frontend.scss`, which sets the supported options `$govuk-font-family` (Lexend), `$govuk-include-default-font-face: false` and `$govuk-assets-path`;
  - the Lexend font files are copied from `@fontsource/lexend` into `app/static/fonts/lexend`.
- Never edit the compiled or copied files by hand; change the Sass settings file and re-run the script.
- Keep local branding/customizations in `app/static/css/styles.css` (and the Sass settings file for GOV.UK's own options) only.
- Upgrade process:
  - run `scripts/update_govuk_assets.bat` (Windows) or `./scripts/update_govuk_assets.sh` (Linux/macOS)
  - commit updated vendored files and lock file
  - run UI regression and accessibility checks
  - record outcome in `decisions.md`

## Accessibility Baseline

- Target WCAG 2.2 AA.
- Support keyboard-only navigation.
- Maintain adequate contrast and semantic markup.
