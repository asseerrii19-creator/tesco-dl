# IT Deployment Notes — v1.2

## Evaluation deployment

Use Docker Compose with PostgreSQL, HTTPS through an approved reverse proxy and a non-public test DNS name.

## Recommended test sequence

1. Start with a fresh PostgreSQL database.
2. Create the bootstrap administrator.
3. Add one test company, client user, TSCO sampler, client sampler, Operations Manager and Sampling Supervisor.
4. Add a quotation, PO and transformer asset.
5. Create a sampling order and assignment.
6. Complete the field submission and label.
7. Accept/register through Data Entry and confirm the mock LMS number.
8. Wait or simulate delay, then scan the physical sample through Receiving.
9. Confirm the sample and package appear in Full Laboratory Operations.
10. Enter test results, submit Technical Review and open Technical Assessment.
11. Approve the internal comment and release a test report.
12. Confirm the client sees only its own external milestone timeline.
13. Review Audit Log, Chain of Custody and Sample Man metrics.

## Production gate

Do not use production client information until security, data retention, backups, file storage, SSO, LMS integration, database migration and Quality validation are approved.
