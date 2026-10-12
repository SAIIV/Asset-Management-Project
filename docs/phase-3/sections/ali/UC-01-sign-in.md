# UC-01 Sign in

- **Priority:** Essential
- **Parent group:** FR-01
- **Owner:** Ali Alawadhi
- **Primary actor:** Requester (representative of every account role)
- **Supporting actors:** None

## Goal

Establish an authenticated session with the permissions assigned to an existing prototype account, without granting additional business authority.

## Preconditions

- An account has been provisioned in the prototype.
- The user can access the sign-in interface without an authenticated session.

## Trigger

The user chooses to sign in to the prototype.

## Main flow

1. The system presents the account-identifier and password fields.
2. The user enters the account identifier and password and submits the form.
3. The system validates the submitted credentials and confirms that the account is enabled.
4. The system loads the account's current roles, department assignments and permitted record scope.
5. The system establishes an authenticated session without including the password in its response or operational audit.
6. The system records the authentication outcome and opens the user's permitted starting view. Subsequent protected actions remain subject to fresh authorization checks.

## Alternative flows

- **Alternative at main step 4:** The account holds more than one assigned role.
    1. The system presents the functions available through those assignments.
    2. The user selects a permitted working view; selecting it does not add permissions or remove the prohibition on approving the user's own proposals.
    - Outcome: Return to main step 5.

## Exception flows

- **Exception at main step 3:** Credentials are incorrect or the account is disabled.
    1. The system displays a generic sign-in failure without revealing whether the identifier exists.
    2. The system retains no authenticated session from this attempt and does not expose credentials in its failure record.
    - Outcome: End unsuccessfully; the user may start another sign-in attempt.

## Postconditions

**Success**

- The session identifies the enabled account and its current permitted scope.

**Failure**

- The attempt grants no access and changes no account assignments.

## Business rules

BR-01, BR-02, BR-14

## Functional requirements

- **P3-FR-01.1** The system shall authenticate an account only when its credentials are valid and the account is enabled.
- **P3-FR-01.2** The system shall associate the authenticated session with the account's current role and department assignments.
- **P3-FR-01.3** The system shall exclude passwords from authentication responses and operational audit records.

## Acceptance check

A valid enabled synthetic Requester reaches the requester view. The same credentials fail after deactivation, and an incorrect password creates no authenticated session or credential-bearing log entry.
