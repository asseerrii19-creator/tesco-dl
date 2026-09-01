# UAT Acceptance Checklist — TSCO Digital Laboratory Platform v2.0

## Environment

- [ ] UAT domain and HTTPS configured
- [ ] PostgreSQL database available
- [ ] Application secrets replaced
- [ ] Demo data enabled only in UAT
- [ ] Public tracking disabled unless approved
- [ ] Database, uploads and barcode storage included in backup scope

## Portal and access separation

- [ ] Public landing shows Client, Employee and Field portals only
- [ ] Client user sees only the linked company
- [ ] TSCO field sampler sees only assigned companies/work
- [ ] Client sampler submits only for the linked client
- [ ] Chemist cannot access Technical Supervision or Management
- [ ] Senior Chemist can access review, assessment and Retained Samples
- [ ] System Administrator can manage master data and accounts

## End-to-end sample workflow

- [ ] Operations Manager creates sampling order linked to quotation/PO
- [ ] Sampling Supervisor assigns order to sampler
- [ ] Sampler captures asset, serial number, GPS and required photos
- [ ] Barcode/tag is generated
- [ ] Offline submission survives connection loss and syncs once online
- [ ] Data Entry can Accept, Return or Reject
- [ ] Accepted submission receives a mock/official LMS number
- [ ] Status becomes Awaiting Physical Receipt
- [ ] Receiving scans the same barcode without duplicating registration
- [ ] Sample appears in Laboratory Operations with full metadata
- [ ] Chemist records results and completes required QC
- [ ] Senior Chemist reviews results/assessment and handles retest/resample
- [ ] Released report status becomes visible to the correct client

## Laboratory module

- [ ] Laboratory Progress opens inside the unified platform shell
- [ ] Technical Supervision opens only for authorized roles
- [ ] Retained Samples is directly accessible to authorized roles
- [ ] Test Workstations and calculations are available
- [ ] Methods & Procedures open correctly
- [ ] Operations Records preserve user/time/action trace
- [ ] Report print output is compared with the approved QDF form

## Integration and production readiness

- [ ] Official LMS product/version documented
- [ ] API/CSV/XML interface and sandbox supplied
- [ ] Client/test/quotation/PO code mapping approved
- [ ] Duplicate and retry behavior validated
- [ ] SSO/MFA decision completed
- [ ] Security review and penetration testing completed
- [ ] File retention, malware validation and encryption policy approved
- [ ] Backup restore test completed
- [ ] Monitoring, alerting and log-retention configured
- [ ] Quality, Laboratory, Operations and IT sign-off completed
