# UC-32 Match resources semantically

- **Priority:** Essential
- **Parent group:** AI-02
- **Owner:** Humaid Al Ali
- **Primary actor:** Requester
- **Supporting actors:** None

## Goal

Rank meaningful resource matches without bypassing mandatory eligibility.

## Preconditions

- The requester is signed in with access to the selected synthetic request or search criteria.
- An authorized matching configuration is available.

## Trigger

The requester asks for semantic matches.

## Main flow

1. The requester selects a request and confirms its purpose, mandatory specifications, quantity and required date.
2. The system validates the request inputs and the requester's department scope.
3. The system constructs candidates from permitted, listed, Available and Serviceable physical asset IDs meeting every mandatory specification.
4. The matching service compares the meaning of the request with eligible candidate descriptions.
5. The system ranks suitable results using proposed weights for purpose, technical fit, condition, quantity, location, urgency, required date, costs, waste diversion and carbon estimates where supported inputs exist.
6. The system displays explanatory scores, missing inputs and configuration versions; scores are not proven probabilities.
7. The requester selects candidate IDs for Custodian review through UC-13; this selection does not reserve them.

## Alternative flows

- **Alternative at main step 3:** Fewer eligible physical IDs exist than the requested quantity.
    1. The system explains that full fulfilment is unavailable and does not reserve a partial set.
    2. A permitted request revision may reduce quantity before a new matching attempt.
    - Outcome: End without a reservation.

## Exception flows

- **Exception at main step 4:** The semantic service is unavailable.
    1. The system labels semantic results unavailable and offers structured search over the same eligible scope.
    2. The fallback does not present keyword results as AI rankings.
    - Outcome: End semantic matching without altering the request or assets.

## Postconditions

**Success**

- The requester receives explained, eligible suggestions; no reservation or approval is created by ranking.

**Failure**

- Ineligible or insufficient units do not become an approved allocation.

## Business rules

BR-01, BR-03, BR-04, BR-05, BR-11

## Functional requirements

- **P3-FR-32.1** The system shall exclude candidates that fail any mandatory eligibility condition before recommendation.
- **P3-FR-32.2** The system shall provide a human-readable explanation of each recommended match's score.
- **P3-FR-32.3** The system shall revalidate selected physical IDs during the separate reservation operation.

## Acceptance check

A highly similar but Unserviceable asset never appears as eligible. A request for two units cannot be fulfilled using one ID twice, and selecting a result alone does not reserve it.
