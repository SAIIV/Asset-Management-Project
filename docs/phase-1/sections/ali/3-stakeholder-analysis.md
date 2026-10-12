# 3 Stakeholder Analysis

### Roles and responsibilities

The proposed permission model separates requesting, record maintenance, business approval and technical administration. A person may hold more than one assigned role, but each action must be checked against the permission required for that action and its department or asset scope. Technical administration does not by itself authorize a transfer or disposal. [R1, pp. 3–4, 7–8]

| Stakeholder | Required information and responsibility | Proposed authority |
| --- | --- | --- |
| Department representative or requester | Asset specifications, condition, available quantity and request status; submit departmental needs and confirm receipt | View available listings; create and manage permitted requests; confirm assigned receipts |
| Asset custodian | Assigned asset details, current location and pending requests; maintain condition and availability | Create and update assigned assets; publish listings; confirm release after approval |
| Designated approver | Request purpose, asset condition, departmental ownership and supporting records | Approve or reject releases and applicable life-cycle actions within assigned authority |
| Maintenance staff | Defect reports, service history and repair costs | Record inspections and service work for assigned assets; update resulting condition |
| Procurement and finance officers | Replacement-cost assumptions, repair and transfer costs, completed exchange records | Review permitted cost inputs and financial reports |
| Sustainability officers | Completed reuse events, asset mass and documented environmental factors | Review impact assumptions and sustainability reports |
| System administrator | User accounts, roles, department membership and audit records | Configure access and review authorized administrative records |
| Project team | Requirements, source evidence, sample data, implementation and test results | Develop, review and test the prototype and documentation |
| Instructor and lab engineer | Phase deliverables, repository history and demonstrations | Review scope, assess progress and evaluate project work |

### Data access boundaries

Requesters need sufficient listing information to judge suitability, but access to a listing will not automatically grant access to purchase values, unrestricted service records or another department's private requests. Custodians will modify only assets assigned to them. Approval screens will expose the records needed for the assigned decision; finance and sustainability reports will be restricted to their permitted users. The detailed organizational assignments require validation with an authorized stakeholder.

Permission checks will apply both to screen access and to the underlying operation. A user who cannot edit an asset through the interface must also be prevented from editing it through a direct request. Audit records will retain the acting user, time, action and affected record so that changes can be traced to an accountable account.
