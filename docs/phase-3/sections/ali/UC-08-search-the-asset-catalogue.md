# UC-08 Search the asset catalogue

- **Priority:** Essential
- **Parent group:** FR-03
- **Owner:** Ali Alawadhi
- **Primary actor:** Requester
- **Supporting actors:** None

## Goal

Find eligible physical units or inspect authorized inventory using explicit structured filters.

## Preconditions

- The Requester has an authenticated prototype account.

## Trigger

The Requester opens catalogue search.

## Main flow

1. The system displays catalogue mode, permitted reference choices and search controls.
2. The Requester submits the selected mode, keywords, mandatory specifications and filters: category, condition, department, location, quantity, availability, asset age, value and lifecycle status.
3. The system validates supplied ranges, references and positive integer quantity, then applies current access scope.
4. The system selects listed, Available, Serviceable units meeting mandatory specifications. Quantity n requires at least n distinct eligible IDs in a matching category/specification group.
5. The system displays individual IDs, current states and permitted details; group counts do not turn one asset record into pooled stock.
6. The Requester reviews results. Searching changes no request, reservation or asset state; detailed inspection follows UC-09.

## Alternative flows

- **Alternative at main step 2:** No filters are supplied.
    1. The system browses the permitted catalogue.
    - Outcome: Return to main step 3.
- **Alternative at main step 4:** Authorized inventory/history mode was selected.
    1. The system applies filters across all permitted states, retaining the eligible-ID quantity calculation.
    2. It labels ineligible units not reservable.
    - Outcome: Return to main step 5; viewing does not grant allocation rights.
- **Alternative at main step 4:** No results satisfy the filters.
    1. The system shows an empty result without relaxing mandatory constraints.
    - Outcome: End with no matches.

## Exception flows

- **Exception at main step 3:** A filter is invalid or the selected mode is unauthorized.
    1. The system rejects the query without broadening access.
    - Outcome: Return to main step 2.

## Postconditions

**Success**

- Results reflect the authorized mode, filters and current eligibility.

**Failure**

- No record is modified and no restricted listing is disclosed.

## Business rules

BR-01, BR-04

## Functional requirements

- **P3-FR-08.1** The system shall support all nine structured filters listed in step 2.
- **P3-FR-08.2** The system shall restrict catalogue results to eligible units meeting mandatory specifications.
- **P3-FR-08.3** The system shall calculate available quantity using distinct eligible physical IDs.
- **P3-FR-08.4** The system shall label ineligible inventory/history results not reservable.

## Acceptance check

Quantity two excludes a matching group with one eligible ID and one Reserved ID. With quantity cleared, authorized history search can show the Reserved unit as not reservable; catalogue search excludes it. A reversed age range fails validation.
