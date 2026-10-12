# 2 Project Overview

### Problem definition

The project brief identifies a resource-allocation problem: a department may purchase an item while a suitable asset remains unused in another department. An inventory entry showing ownership and location does not necessarily show whether the item can be requested, who must authorize its release or whether it is serviceable. Separate approval, transfer and maintenance records can also obscure who currently holds the asset and whether it is available for reuse. [R1, pp. 1–3]

The proposed system addresses these gaps by linking an asset listing to departmental requests, approval decisions, release and receipt confirmations, and its subsequent maintenance history. The project does not assume a measured rate of unnecessary purchasing or a verified description of current university procedures.

### Project objectives

The project has four operational objectives. First, requesters should be able to identify available assets using category, specifications, condition, quantity and location. Second, each completed exchange should have a recorded approval, releasing custodian and receiving user. Third, an asset's custody and condition history should remain accessible after transfer, repair or retirement. Fourth, reuse reports should derive their counts and estimated financial benefits from identifiable events and documented calculation inputs.

AI will support these objectives by identifying relevant assets even when requests and listings use different wording, explaining the matching factors and suggesting appropriate life-cycle actions. Its recommendations will not replace availability checks or approval rules. Prototype success will be assessed against the tests in Section 5; no financial or environmental improvement is claimed as an achieved result.

### Operational process under investigation

The initial process model begins when a custodian identifies a surplus asset and checks its condition. A department expresses a need, an authorized person decides whether release is permitted, and the releasing and receiving staff confirm the exchange. A defect leads to inspection or repair; an item unsuitable for further use requires a documented decision on donation, component recovery, recycling or disposal. This model is a hypothesis for stakeholder validation. [R1, p. 7]

Requirements gathering will establish the records used at each step, the person authorized to decide, the evidence required to confirm completion and the handling of exceptions. The specific exceptions are competing requests, insufficient quantity, rejected approvals, failed receipt confirmation and assets becoming unserviceable while reserved.

### Product scope

The prototype will serve authorized campus users and cover furniture, computers, laboratory equipment, books and other resource categories identified in the brief. Its baseline functions are account and department management, asset registration and publication, structured search, resource requests, reservations, approvals, transfers, inspections, maintenance records, notifications and operational reports. Asset history will include custody changes, repair, refurbishment, donation, recycling, retirement and disposal. [R1, pp. 3–4, 8–9]

The AI scope consists of classification and metadata suggestions, semantic resource matching, ranked recommendations with explanations, sustainable-action recommendations, natural-language assistance and summaries of recorded activity. Structured search and request processing will remain usable when AI services are unavailable. [R1, pp. 4–6]

The proposed boundary excludes public trading, payment processing and automatic procurement. The prototype will initially use labelled sample data. Live university databases, institutional sign-in and other external integrations are not assumed; their access requirements and feasibility will be assessed in Phase 2. The programming language, framework, database, hosting service and AI provider have not been selected. Development is constrained by three team members and the semester schedule.

### Monitor transfer scenario

Consider an illustrative request for one working monitor with a screen size of at least 24 inches and an HDMI connection. Department A has one available monitor that meets those specifications, and Department B needs it for a workstation. Department labels and specifications in this example are sample inputs, not campus observations.

| Step | Required system action | Responsible role |
| --- | --- | --- |
| Register and publish | Save the monitor's specifications, condition, quantity of one, department and location; mark it available | Asset custodian in Department A |
| Submit request | Record the minimum screen size, HDMI connection, quantity and required date | Requester in Department B |
| Match and reserve | Exclude unavailable or incompatible listings; display why the candidate qualifies; reserve the selected quantity without overbooking | System, following requester selection |
| Decide | Record approval or rejection, decision maker, time and reason | Designated approver |
| Release and receive | Record release, then receipt confirmation; update custody and location only when the approved transfer is completed | Releasing custodian and receiving user |
| Maintain history | Retain the transfer event and attach later inspection, repair or retirement records to the same asset | Authorized custodian or maintenance staff |

A 22-inch monitor or a monitor without HDMI must not qualify simply because its description is similar. Rejection must release the reserved quantity and leave custody unchanged. Approval alone must not mark the exchange completed; the releasing custodian and receiving user must confirm their respective steps. A second request cannot reserve the same single monitor while the first reservation remains active. Reservation duration is a policy decision to be established through stakeholder consultation.
