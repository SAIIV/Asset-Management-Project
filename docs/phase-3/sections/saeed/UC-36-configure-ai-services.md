# UC-36 Configure AI services

- **Priority:** Essential
- **Parent group:** AI-01 to AI-05
- **Owner:** Saeed Alkaabi
- **Primary actor:** Administrator
- **Supporting actors:** None

## Goal

Control AI configurations without granting business authority or exposing credentials.

## Preconditions

- The administrator is signed in with configuration-management permission.

## Trigger

The administrator requests a new or revised AI service configuration.

## Main flow

1. The administrator selects the AI function and opens a draft configuration.
2. The administrator specifies the model or service, version, prompt or ranking rules, supported inputs and fallback behavior.
3. The system validates the configuration and checks recorded authorization for any proposed external transmission of synthetic inputs.
4. The administrator supplies any required credential through protected credential storage and links its reference to the configuration.
5. The system tests a bounded synthetic request and presents response validation without exposing credentials.
6. The administrator reviews the result and confirms activation of the configuration version.
7. The system activates the version, retains the previous configuration record and records the administrative change.

## Alternative flows

- **Alternative at main step 6:** The administrator chooses to disable the service instead of activate the draft.
    1. The system records the disabled state and exposes the configured manual or deterministic fallback.
    2. Existing recommendation history retains its original configuration references.
    - Outcome: End with the service disabled and operational approval rules unchanged.

## Exception flows

- **Exception at main step 3:** External transmission lacks authorization or includes non-synthetic operational data.
    1. The system blocks validation and activation; administrator status cannot supply missing authorization.
    - Outcome: End without external transmission or activation.
- **Exception at main step 5:** The service fails or returns an invalid response.
    1. The system rejects activation and preserves the previous configuration.
    - Outcome: End with the draft inactive.

## Postconditions

**Success**

- A validated, identified configuration is active and traceable for subsequent AI outputs.

**Failure**

- The previous active configuration remains unchanged; unauthorized transmission does not occur.

## Business rules

BR-01, BR-02, BR-11, BR-14, BR-16

## Functional requirements

- **P3-FR-36.1** The system shall restrict AI configuration changes to authorized administrators.
- **P3-FR-36.2** The system shall keep service credentials out of reports, repository content and ordinary audit text.
- **P3-FR-36.3** The system shall associate each AI response with its active configuration version.
- **P3-FR-36.4** The system shall block external AI requests without recorded input-transmission authorization.

## Acceptance check

Activating a valid synthetic configuration records its version. An unauthorized external configuration sends no request, and changing service settings does not allow the administrator to approve a business transfer.
