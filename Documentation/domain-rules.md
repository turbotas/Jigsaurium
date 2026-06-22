# Domain Rules (v1)

## Role Rules

- `administrator` can manage users, roles, jigsaws, and lending records.
- `borrower` can view catalog availability and own loan records.
- Borrowers cannot mutate user/role data.

## Jigsaw Rules

- Jigsaw create accepts empty values for all user-entered fields in v1 (to support future image-driven creation workflows).
- Optional metadata fields: manufacturer, artist, dimensions (cm), description, and last-completed timestamp.
- When provided, `piece_count` must be a positive integer.
- Duplicate jigsaw titles are allowed.
- Status values in v1:
  - `available`
  - `on_loan`
  - `maintenance`
  - `retired`
- Retired jigsaws are hidden from borrower browse views by default.

## Jigsaw Image Rules

- Jigsaw images are stored in the database in v1.
- Each image record includes a tag (for example `completed puzzle`, `box front`, `box side`) and binary image content.
- Image create/list endpoints are administrator-only in the initial rollout.

## Jigsaw State Transitions

- `available` -> `on_loan` when checked out.
- `on_loan` -> `available` when returned in good condition.
- `on_loan` -> `maintenance` when returned damaged/incomplete.
- `available` or `maintenance` -> `retired` by admin action.
- `retired` -> `available` by admin restore action.

## Loan Rules

- A jigsaw can have only one active loan at a time.
- A borrower can hold multiple active loans in v1 (no policy cap enforced yet).
- For administrative checkout workflows, users with `administrator` role are also eligible loan recipients.
- Loan states in v1:
  - `active`
  - `returned`
  - `overdue`
- Overdue is derived from due date and return status.
- New loans set `due_at` to four weeks (28 days) after `checked_out_at`.

## Audit Rules

- Record audit events for create/update/delete and state transition actions.
- Each event includes actor, action, entity type/id, timestamp, and request context.
- Request context includes resolved client address details from trusted forwarded headers.

## Policy Values (deferred for now)

- No max-active-loan limit is enforced in v1.
- No renewal rules are enforced in v1.
- No overdue grace period is enforced in v1.
- Policy caps and renewal behavior can be introduced in a later milestone.
