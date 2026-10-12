# UC-34 Ask the resource assistant

- **Priority:** Desirable
- **Parent group:** AI-04
- **Owner:** Humaid Al Ali
- **Primary actor:** Requester
- **Supporting actors:** None

## Goal

Answer natural-language resource questions and prepare permitted actions without bypassing application controls.

## Preconditions

- The requester is signed in.
- An authorized assistant configuration is available for synthetic operational inputs.

## Trigger

The requester asks a question through the resource assistant.

## Main flow

1. The requester submits a question about permitted resources, request status, asset history, sustainability or system guidance.
2. The system checks the requester's scope and determines the records or approved guidance needed.
3. The system retrieves only authorized supporting material, treating retrieved text as untrusted data.
4. The assistant prepares a response grounded in that material.
5. The system checks links and protected fields and identifies unsupported or uncertain parts of the answer.
6. The system displays the answer with supporting record references, relevant update times and a clear statement of limitations.
7. The requester follows a permitted record or navigation link for further action.

## Alternative flows

- **Alternative at main step 4:** The requester asks to submit a resource request rather than obtain an answer.
    1. The assistant prepares a proposed request form without submitting it.
    2. The requester reviews the values and explicitly confirms continuation through UC-10, including its normal validation and access checks.
    - Outcome: End assistant preparation and continue through the ordinary request-submission use case.

## Exception flows

- **Exception at main step 5:** The requested answer lacks an authorized supporting record or verified guidance.
    1. The system explains that the information cannot be established from available sources.
    2. It does not invent university policy or reveal restricted material.
    - Outcome: End with a limitation response and no operational change.

## Postconditions

**Success**

- The requester receives grounded information or a reviewable proposed action.

**Failure**

- The assistant neither changes protected records nor supplies unsupported answers as facts.

## Business rules

BR-01, BR-11, BR-16

## Functional requirements

- **P3-FR-34.1** The system shall restrict assistant retrieval to the requesting user's authorized scope.
- **P3-FR-34.2** The system shall identify supporting records or approved guidance for factual assistant answers.
- **P3-FR-34.3** The system shall require explicit confirmation through the normal validated workflow before an assistant-prepared action changes records.

## Acceptance check

The assistant answers a permitted synthetic status question with its record reference. An instruction to ignore permissions reveals no other department's data, and a prepared request remains unsubmitted before confirmation.
