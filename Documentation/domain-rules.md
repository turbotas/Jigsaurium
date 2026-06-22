# Domain Rules (v1)

## Role Rules

- `administrator` can manage users, roles, jigsaws, and lending records.
- `borrower` can view catalog availability and own loan records.
- Borrowers cannot mutate user/role data.

## Jigsaw Rules

- Required fields: title, piece count, status.
- `piece_count` must be a positive integer.
- Status values in v1:
  - `available`
  - `on_loan`
  - `maintenance`
  - `retired`
- Retired jigsaws are hidden from borrower browse views by default.

## Jigsaw State Transitions

- `available` -> `on_loan` when checked out.
- `on_loan` -> `available` when returned in good condition.
- `on_loan` -> `maintenance` when returned damaged/incomplete.
- `available` or `maintenance` -> `retired` by admin action.
- `retired` -> `available` by admin restore action.

## Loan Rules

- A jigsaw can have only one active loan at a time.
- A borrower can hold multiple active loans up to configured policy limits.
- Loan states in v1:
  - `active`
  - `returned`
  - `overdue`
- Overdue is derived from due date and return status.

## Audit Rules

- Record audit events for create/update/delete and state transition actions.
- Each event includes actor, action, entity type/id, timestamp, and request context.
- Request context includes resolved client address details from trusted forwarded headers.

## Policy Values (to finalize)

- Default loan duration (days).
- Maximum active loans per borrower.
- Renewal allowance and limits.
- Overdue grace period rules.
