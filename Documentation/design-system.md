# Design System Specification

## Primary Design Standard

Use GOV.UK Design System components and interaction patterns by default.

## Branding Policy

- Follow GOV.UK baseline visuals.
- Allow light branding only (for example: logo and limited color accents).
- Keep custom branding in a separate override layer.
- Do not modify GOV.UK vendor source files directly.

## Frontend Rules for SPA

- Use GOV.UK form patterns and validation guidance.
- Preserve keyboard accessibility and visible focus states.
- Use consistent GOV.UK spacing and typography scales.
- Use accessible error summaries and field-level error messaging.

## Upstream Update Workflow

- Pin a `govuk-frontend` version.
- Keep vendor and custom code separated.
- Vendor files are copied from `node_modules/govuk-frontend/dist/govuk` into `app/static/vendor/govuk`.
- Keep local branding/customizations in `app/static/css/styles.css` only.
- Upgrade process:
  - run `scripts/update_govuk_assets.bat` (Windows) or `./scripts/update_govuk_assets.sh` (Linux/macOS)
  - commit updated vendored files and lock file
  - run UI regression and accessibility checks
  - record outcome in `decisions.md`

## Accessibility Baseline

- Target WCAG 2.2 AA.
- Support keyboard-only navigation.
- Maintain adequate contrast and semantic markup.
