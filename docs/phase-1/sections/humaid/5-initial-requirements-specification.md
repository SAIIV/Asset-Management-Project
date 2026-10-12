# 5 Initial Requirements Specification

### Nonfunctional requirements

| ID | Quality requirement | Proposed verification |
| --- | --- | --- |
| NFR-01 | At least 95% of structured searches shall complete within 2 seconds with 500 sample assets and 10 concurrent users. | Record search response times under a repeatable workload and documented environment |
| NFR-02 | Protected operations and reports shall reject every unauthorized case in the role and department test matrix. | Exercise both permitted and prohibited actions through interface and direct requests |
| NFR-03 | Transfer completion shall preserve consistency between custody, location and history. | Interrupt completion and verify that no partial transfer remains |
| NFR-04 | At least 4 of 5 testers shall complete asset discovery, request submission and request-status checking without assistance. | Observe each tester using the same tasks and record completion and errors |
| NFR-05 | Publication, approval, transfer, maintenance and final disposition changes shall retain actor, time, action and affected record. | Compare audit entries with each executed test event |
| NFR-06 | AI service failure shall not prevent structured search or standard request submission. | Simulate an AI failure and complete both baseline functions |

### Acceptance and evaluation plan

The following thresholds are proposed prototype acceptance targets, not instructor-prescribed values or achieved test results. The test record will identify inputs, expected output, observed output and pass or fail status.

| Area | Acceptance target | Evidence |
| --- | --- | --- |
| Core workflow | Pass all 10 scenarios specified below | Scenario records and resulting asset or request states |
| Access control | Reject every unauthorized action in the defined test matrix | Positive and negative role and department tests |
| Search performance | At least 95% of searches within 2 seconds with 500 assets and 10 concurrent users | Timing results with workload and environment details |
| Usability | At least 4 of 5 testers complete the specified tasks without help | Individual observation sheets |
| Match usefulness | Return an acceptable asset in the top 3 for at least 16 of 20 feasible requests | Predetermined suitability labels and ranked results |
| Impact calculations | Reproduce expected values for all 10 reuse and repair test cases | Independent calculations compared with system output |

The 10 workflow scenarios will cover valid publication, invalid publication, successful search, search with no eligible results, request submission, a competing reservation, rejected approval, a completed transfer, interrupted transfer completion, and a maintenance or retirement update that removes an asset from availability. Each case will verify both the displayed outcome and the stored state.

The matching test will use 20 sample requests, each with at least one compatible asset. Acceptable assets will be labelled before running either method. Semantic ranking and conventional keyword or filter search will use the same dataset and requests. The reported measure will be the number of requests with an acceptable asset among the first three results; it will not be presented as general AI accuracy. Classification suggestions will also be reviewed against labelled categories, while explanations will be checked against the actual asset fields.

Usability participants will be identified as staff or student proxies. Results from five testers will describe those observed sessions, not establish campus-wide acceptance. Search performance results will document the test device or server, workload, dataset and measurement interval.

For each eligible completed reuse event, estimated net savings will equal the avoided replacement cost minus transfer and repair costs. Calculations will retain the currency, input source and event reference. Reuse counts will include only completed exchanges. Diverted mass will require a recorded mass and a justified disposal baseline; carbon estimates will additionally require an identified emissions factor and unit. A missing input will produce an unavailable estimate, not a zero value. The 10 calculation cases will include missing inputs and duplicate-event checks as well as known reuse and repair values.
