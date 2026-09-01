# LMS Connector Contract

The platform isolates LMS-specific code under `app/integrations/lms/`.

## Required operation

`register_sample(sample)` should return at minimum:

```json
{
  "success": true,
  "lms_number": "official LMS accession number",
  "external_reference": "optional vendor transaction ID",
  "message": "registration response"
}
```

## Required behavior

- Idempotent registration: the same platform sample must not create duplicate LMS records.
- Validate client, quotation, PO, asset and test codes before sending.
- Store request/response metadata in `lms_sync_logs` without storing secrets.
- Retry transient failures safely.
- Return actionable validation errors to Data Entry.
- Use the official LMS number as the laboratory sample key after registration.

## Mapping required from LMS owner

- client code
- quotation and PO fields
- asset/serial number fields
- sample type and sampling point
- package and individual test codes
- priority
- field/ambient conditions
- sampler and collection timestamp
- report/release status
