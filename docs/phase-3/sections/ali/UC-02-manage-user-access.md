# UC-02 Manage user access

- **Priority:** Essential
- **Parent group:** FR-01
- **Owner:** Ali Alawadhi
- **Primary actor:** Administrator
- **Supporting actors:** None

## Goal

Maintain prototype account access so assigned roles and departments determine subsequent protected actions without altering historical ownership of work.

## Preconditions

- The Administrator is authenticated.
- The reference roles and departments exist in the prototype.

## Trigger

The Administrator opens access management to change an account's assignments or enabled status.

## Main flow

1. The system verifies the Administrator's permission to manage accounts.
2. The Administrator selects the target account, and the system displays its current enabled status, roles and department assignments.
3. The Administrator selects the intended assignments or deactivation and submits the change.
4. The system validates the referenced roles and departments and rechecks the Administrator's authority.
5. The system saves the access change and appends an audit event identifying the administrator, target account, time and changed assignments.
6. The system confirms the result. Subsequent protected operations use the revised permissions, while earlier requests, approvals and audit events retain their original actor references.

## Alternative flows

- **Alternative at main step 2:** A new synthetic account is required.
    1. The Administrator selects account creation and supplies a unique identifier, initial access details and proposed assignments.
    2. The system presents the new account configuration for confirmation.
    - Outcome: Return to main step 3; successful completion creates the account.

## Exception flows

- **Exception at main step 4:** An assignment references an unavailable department, or the acting account no longer has administration permission.
    1. The system rejects the submitted change and identifies the permitted correction without exposing restricted account data.
    2. Existing access assignments remain unchanged.
    - Outcome: End unsuccessfully without an access change.

## Postconditions

**Success**

- The recorded access configuration governs the target account's next protected operation.

**Failure**

- No partial assignment or account deactivation is committed.

## Business rules

BR-01, BR-02, BR-14, BR-16

## Functional requirements

- **P3-FR-02.1** The system shall restrict account creation and access changes to authorized Administrators.
- **P3-FR-02.2** The system shall apply revised account permissions to subsequent protected operations.
- **P3-FR-02.3** The system shall retain historical actor references when an account is changed or disabled.

## Acceptance check

Remove a Custodian assignment and verify that the account's next asset update is denied. An Administrator-only account must still be denied a transfer approval, and a non-Administrator access change must leave assignments intact.
