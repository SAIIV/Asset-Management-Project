# UC-31 Suggest asset classifications

- **Priority:** Essential
- **Parent group:** AI-01
- **Owner:** Humaid Al Ali
- **Primary actor:** Custodian
- **Supporting actors:** None

## Goal

Suggest classifications for human review without changing authoritative asset data.

## Preconditions

- The custodian is signed in and may inspect the selected synthetic asset.
- An authorized classification configuration is available.

## Trigger

The custodian requests classification suggestions for an asset draft or permitted record.

## Main flow

1. The custodian selects the asset title, description, specifications and approved JPEG/PNG photographs or text-based PDF documents.
2. The system validates access and files, analyzes photographs and extracts readable PDF text; scanned-document OCR is outside the proposed boundary.
3. The system prepares synthetic inputs, treating documents as data rather than instructions.
4. The classification service produces suggested category, subcategory, tags, description, possible material and missing-metadata observations.
5. The system validates suggested values against reference data and identifies uncertainty or unsupported suggestions.
6. The system displays the candidate classification with its explanation and model, prompt or rule version.
7. The custodian opens human review through UC-35; the asset fields remain unchanged until separately confirmed.

## Alternative flows

- **Alternative at main step 5:** Image interpretation, text extraction or classification is uncertain.
    1. The system withholds unsupported labels and requests human review of the uncertain evidence.
    2. The custodian may supply clearer supported inputs or missing metadata.
    - Outcome: End with an advisory clarification request and unchanged asset fields.

## Exception flows

- **Exception at main step 4:** The classification service fails or returns an invalid response.
    1. The system reports that suggestions are unavailable.
    2. Manual classification through the ordinary asset workflow remains available.
    - Outcome: End without applying a classification.

## Postconditions

**Success**

- A traceable advisory classification is available for human review.

**Failure**

- Service errors or uncertainty do not corrupt the asset record.

## Business rules

BR-01, BR-11, BR-16

## Functional requirements

- **P3-FR-31.1** The system shall use permitted text, JPEG/PNG image content and readable PDF text to suggest asset classifications and metadata.
- **P3-FR-31.2** The system shall validate suggested reference values before presenting them for acceptance.
- **P3-FR-31.3** The system shall retain asset fields unchanged until an authorized user confirms an update.
- **P3-FR-31.4** The system shall record the model, prompt or rule version associated with each classification suggestion.

## Acceptance check

Supported synthetic text, photograph and PDF inputs produce reviewable suggestions. Uncertain extraction requests review; unsupported categories are withheld. Service failure permits manual entry, and no suggestion silently changes the asset.
