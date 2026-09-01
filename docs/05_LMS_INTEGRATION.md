# LMS Integration Contract

## Current pilot behavior

Data Entry acceptance calls the connector immediately. A successful response stores the LMS number and moves the sample to **Awaiting Physical Receipt**. Physical receiving is blocked until the LMS number exists. The accepted sample is also imported to Full Laboratory Operations.

The supplied connector is `mock` and must not be represented as a live LMS integration.

## Required discovery from the current LMS owner/vendor

1. Product name and exact version.
2. Supported interface: REST, SOAP, database view, CSV/XML import or another official connector.
3. Test/sandbox environment.
4. Authentication and network requirements.
5. Sample registration endpoint/import schema.
6. Mandatory/optional fields.
7. Client, quotation, PO, project and test-package identifiers.
8. Test code dictionary and package mapping.
9. Sample-number generation ownership.
10. Status/results/report retrieval.
11. Idempotency and duplicate prevention.
12. Error response and retry rules.
13. Webhooks or polling.
14. Reconciliation process and support owner.

## Integration rules

- Maintain the adapter layer so the platform is not coupled to one LMS vendor.
- Use the portal request number as the outbound idempotency reference.
- Log all connector transactions with sensitive data minimized.
- Never create a second LMS record during receiving.
- Failed registration remains visible to Data Entry for controlled retry.
- Direct production database writes are prohibited unless formally supported and approved.
