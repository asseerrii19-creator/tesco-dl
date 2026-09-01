# Data Model Principles

## Identity separation

- **Sampling Order Number:** management request covering one or more field tasks.
- **Assignment Code:** one sampler/asset collection task.
- **Asset ID / serial number:** permanent equipment identity.
- **Portal Request Number:** field collection transaction.
- **Barcode value:** physical container/request tracking identifier.
- **Client Sample Reference:** optional customer identifier.
- **LMS Sample Number:** official laboratory accession identifier.
- **Quotation / PO:** commercial authorization.

These identifiers are linked but must never be collapsed into one number.

## Key relational entities

- Site
- Client
- User / Role / UserClientAssignment
- Quotation
- PurchaseOrder
- Asset
- SamplingOrder
- SamplingAssignment
- SampleRequest
- SamplePhoto
- CustodyEvent
- DataQualityIssue
- LmsSyncLog
- TechnicalAssessmentRecord
- AuditLog

## Integrated laboratory state

The detailed v7 laboratory operational dataset is stored per site in `OperationsState` and includes batches, tests, results, QC, reports, retained samples, retests, document revisions and operations records. Synchronization links it to `SampleRequest` by portal request/LMS number.

For production scaling, IT may normalize this operational JSON into relational tables after pilot acceptance without changing the business identifiers.

## Multi-site readiness

Operational records carry a site identifier. Dammam is active in this pilot. Jubail and Bahrain placeholders must not be activated until site-specific workflows, test catalogs, roles and data-isolation tests are approved.
