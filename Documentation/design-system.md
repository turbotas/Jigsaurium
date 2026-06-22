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
- Upgrade process:
  - bump pinned version
  - rebuild frontend assets
  - run UI regression and accessibility checks
  - record outcome in `decisions.md`

## Accessibility Baseline

- Target WCAG 2.2 AA.
- Support keyboard-only navigation.
- Maintain adequate contrast and semantic markup.
