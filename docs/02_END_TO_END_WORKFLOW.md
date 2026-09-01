# End-to-End Integrated Workflow

## Planned TSCO sampling

1. Operations Manager creates a sampling order against Client → Quotation → PO and assigns a Sampling Supervisor.
2. The order contains one or more asset/sample assignments.
3. Sampling Supervisor assigns each item to a TSCO Field Sampler or an approved client-side sampler according to the source party.
4. The sampler opens the assignment or enters its assignment code on the field portal.
5. Assigned commercial/client/package fields are server-controlled; the sampler captures remaining field data, exact GPS and photos.
6. The system generates the portal request, barcode/QR and printable sample label.
7. Data Entry reviews the electronic submission before the bottle arrives.
8. Data Entry selects:
   - Accept and Register in LMS;
   - Return for Correction; or
   - Reject.
9. On acceptance the LMS connector supplies the LMS/sample number and the record becomes **Awaiting Physical Receipt**.
10. The record is automatically created in Full Laboratory Operations with its requested package/tests.
11. When the bottle arrives, Receiving scans the barcode and confirms containers/seal/condition against the existing record.
12. Laboratory Chemists process the sample through batches, workstations, QC and calculations.
13. Test progress synchronizes to the platform/client milestone.
14. Senior Chemist reviews results and the internal Technical Assessment; retest, resampling, escalation or approval is recorded.
15. Report release synchronizes to the client portal.

## Client-side sampling

1. Operations may create a CLIENT-source assignment for a client sampler/client operations account, or the authorized client account may submit an allowed direct field sample.
2. The client-side user sees only their company, commercial references and assets.
3. The same barcode, GPS, photo and field-information workflow is used.
4. Data Entry remains the control gate and may accept/register, return or reject.
5. After acceptance, the sample waits for physical receipt under the same LMS-linked record.

## Traceability identifiers

- Sampling Order Number
- Assignment Code
- Portal Request Number
- Barcode / QR value
- Client Sample Reference
- Asset ID and Serial Number
- Quotation and PO
- LMS Number
- Report record

No single identifier replaces the others; they are linked to the same SampleRequest record.
