# 5 Initial Requirements Specification

### Data requirements

The records below define proposed information needs, not a final database schema. All records will have a unique identifier. Asset, request and event references will allow the system to connect a recommendation or report value to the underlying operational record. Photographs and supporting documents are included in the source brief. [R1, pp. 3–5]

| Record | Proposed fields | Validation or use |
| --- | --- | --- |
| Asset | Name, description, category, specifications, quantity, owner, department, custodian, location, purchase date, estimated value, condition, availability, photographs and documents | Require name, category, department, custodian, location, condition and positive whole-number quantity before publication; record unavailable optional values explicitly |
| Request | Requester, department, purpose, required category and specifications, quantity, acceptable condition, urgency, location and required date | Require purpose, positive whole-number quantity and essential specifications; distinguish mandatory constraints from preferences |
| Approval and transfer | Asset and request IDs, decision, reason, approver, decision time, released quantity, releasing user, receiving user, confirmations and destination | Reject unauthorized decisions or quantities exceeding the reservation; retain release and receipt separately |
| Maintenance and life cycle | Asset ID, event type, defect, action, event date, responsible user, cost, resulting condition and supporting evidence | Preserve earlier events; record the approval reference for an action requiring authorization |
| Recommendation | Request or asset ID, candidate, matching factors, explanation, missing inputs, model or service version and user response | Retain enough context to review suitability and compare outputs |
| Impact and audit | Source event, actor, time, input values, units, calculation assumptions and result | Trace reported totals and estimates to eligible events; prevent duplicate counting |

### Functional requirements

The following requirements define proposed prototype behavior. The associated conditions specify actions and exceptions for validation before implementation. [R1, pp. 3–4, 8–9]

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-01 | The system shall authenticate users and check role, department and assigned-record permissions before each protected operation. | High |
| FR-02 | The system shall allow assigned custodians to create, update and publish assets that meet the publication validation rules. | High |
| FR-03 | The system shall search available resources, record requests, reserve eligible quantities and display request status without overbooking. | High |
| FR-04 | The system shall record approval, release and receipt before completing a transfer and updating custody and location. | High |
| FR-05 | The system shall retain asset custody, inspection, repair, refurbishment, donation, recycling, retirement and disposal events. | High |
| FR-06 | The system shall notify relevant users of request and transfer status changes and report recorded operational totals. | Medium |

FR-01 shall reject an unauthenticated operation and any action outside the user's assigned permissions. Rejection shall not modify the target record. Account and department administration shall support the role assignments used by these checks.

FR-02 shall identify missing mandatory fields and reject zero, negative or fractional quantities. A condition or availability change shall affect subsequent searches and reservations. A retired or unserviceable asset shall not appear as an available working item.

FR-03 shall support filters for category, condition, department, location, quantity and availability, and for age, value and life-cycle status where those data are available and permitted. A request shall distinguish essential specifications from preferences. Reserving a quantity shall reduce the quantity available to competing requests. An unsuccessful reservation shall explain that the requested quantity is unavailable without creating a partial reservation. Proposed request states are submitted, reserved, approved, rejected, cancelled and completed; rejection or cancellation shall release its reservation.

FR-04 shall allow only the assigned approver to record a decision and only authorized releasing and receiving users to confirm their respective steps. Receipt cannot complete a transfer that lacks approval or release confirmation. On completion, custody, location and the transfer event shall update together. An interrupted operation shall leave either the previous state or the complete new state, never a partially updated exchange. Delivery arrangements and supporting documents shall remain linked to the transfer.

FR-05 shall append each event to the asset's history with its responsible user and date. A maintenance event shall include the reported problem, action taken, cost when applicable and resulting condition. A donation, recycling or disposal event shall retain the applicable approval and final disposition. Removing an asset from availability shall not delete its history.

FR-06 shall generate status notifications for the requester and responsible custodian when a request is approved, rejected or cancelled, and when a transfer is completed. Reports shall show available assets, open requests, completed transfers, approvals, maintenance events and custody changes for a selected reporting period. Totals shall reconcile with source records and respect the viewer's access restrictions.

### AI requirements

| ID | Proposed requirement | Priority |
| --- | --- | --- |
| AI-01 | Suggest a category, tags and missing metadata from the supplied asset information; require custodian acceptance before saving suggestions. | High |
| AI-02 | Exclude incompatible or unavailable assets, rank eligible candidates and explain the factors used for each recommendation. | High |
| AI-03 | Suggest an appropriate life-cycle action using recorded condition, repair history and available cost or impact inputs. | Medium |
| AI-04 | Answer permitted search and status questions and prepare resource requests for explicit user confirmation. | Medium |
| AI-05 | Summarize recorded exchanges, maintenance activity and traceable financial or environmental estimates. | Medium |

For AI-01, the custodian shall be able to accept, edit or reject each suggestion. The brief includes descriptions, specifications, images and documents as potential inputs. Phase 2 will assess which input-processing methods can be supported; the system shall identify missing information rather than silently infer an unsupported specification. [R1, pp. 4–5]

For AI-02, eligibility shall be checked before ranking. Available quantity, required specifications and acceptable condition are mandatory constraints when stated in the request. Location, urgency, timing and recorded transfer or repair costs may influence ordering after eligibility has been established. Each explanation shall identify the matching fields and any unresolved information. A similarity score shall not be described as a probability that the asset is suitable.

For AI-03, candidate actions include continued use, transfer, repair, refurbishment, donation, component recovery, recycling and disposal. A recommendation shall state its supporting condition or cost evidence and flag missing inputs. It shall not create an approval or change the asset's disposition.

For AI-04, the assistant shall use the same permissions as the signed-in user. Before submitting a request, it shall display the requested specifications, quantity, department and required date for confirmation. The assistant shall not confirm physical receipt or authorize a transfer on the user's behalf.

For AI-05, each numerical summary shall be derived from stored records or a documented calculation. Estimated savings shall remain labelled as estimates, and missing cost or environmental inputs shall be disclosed. The system shall not generate an unsupported count of avoided purchases. If an AI operation fails, the interface shall report the failure and retain access to structured search and standard request forms. [R1, pp. 4–6, 8–9]
