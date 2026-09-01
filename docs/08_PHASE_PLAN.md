# Delivery and Hardening Plan

## Integrated pilot delivered in v1.2

- Administration/master data
- Operations Manager orders
- Sampling Supervisor allocation
- TSCO/client-side field capture
- Barcode/GPS/photos
- Data Entry control gate
- Mock LMS registration before physical receipt
- Receiving/chain of custody
- Client tracking
- Full laboratory operations, QC, calculations and reports
- Initial technical assessment
- Management indicators

## Next hardening work

### Integration
- Replace mock LMS connector with approved sandbox connector.
- Map production client, quotation, PO and test codes.
- Add reconciliation/error dashboard.

### Security and infrastructure
- SSO/MFA, device policy and fine-grained permissions.
- Controlled database migrations.
- File/object storage and upload scanning.
- Monitoring, backup and disaster recovery.

### Field offline capability
- Encrypted IndexedDB queue for form data and photos.
- Deterministic offline IDs and conflict handling.
- Retry/resume upload with server acknowledgements.
- Device revocation and local retention policy.

### Quality validation
- QDF report print comparison.
- Calculation and QC validation.
- Complete client/manufacturer assessment profiles.
- Electronic approval/signature policy.

### Enterprise expansion
- Activate Jubail and Bahrain after site-specific workflows and data separation are validated.
- Notifications, SLA/TAT, asset history and corporate BI.
