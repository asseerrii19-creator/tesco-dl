# Client Visibility Model

## Client-visible milestones

- Sample submitted / collected
- Returned for correction or rejected, when applicable
- Registered in LMS — awaiting physical receipt
- Received at laboratory
- Testing in progress
- Technical review
- Report approved
- Report released

Internal laboratory substeps are summarized into these external milestones.

## Restricted information

The client portal must not expose:

- Internal QC failures
- Employee performance records
- Draft technical interpretation
- Internal review notes
- Retest rationale before approval
- Other clients' data
- Unassigned commercial data
- Laboratory employee names unless approved by policy

## Current pilot

- Client access is authenticated and restricted by `client_id`.
- Public tracking is disabled by default.
- Report release status is synchronized from Full Laboratory Operations.
- Direct report-file download still requires the approved production report storage/integration design.

## Notifications

Future notifications may be triggered for registration, receipt, delay, correction request and report release. Email/SMS/messaging integrations are not included in v1.2.
