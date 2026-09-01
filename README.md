# TSCO Digital Laboratory Platform v2.6

Integrated laboratory operations web application for the complete sample lifecycle.

Start with `START_HERE.md`.

Core application: FastAPI + SQLAlchemy. Local developer review uses SQLite. Shared deployment supports PostgreSQL/Docker. The LMS integration boundary is isolated under `app/integrations/lms/`; the current connector is a mock adapter until TSCO IT provides the official LMS interface/API specification.

## v2.6 developer baseline

The developer-review package now includes:

- Multi-client master data and isolated client portal accounts.
- Multi-site structure for Dammam, Jubail, Bahrain and future sites.
- Site-scoped operational users plus corporate management visibility across sites.
- Platform-admin configuration for sites, clients, users/access, controlled SOP/Method/EOP revisions and test packages without source-code edits.
- Database-backed configuration changes that become available while the application remains running.
- Existing sample lifecycle, laboratory operations, audit, barcode, technical assessment and client tracking.

Code-level feature changes still require a normal application deployment. Production-grade zero-downtime deployment, backups, SSO/security and the official LMS connector are finalized with IT.


## Architecture Baseline
Adds Corporate/Site/Department hierarchy, client organization units, runtime workflow versioning, approval-policy configuration, master-data center, and an integration control queue. See `docs/15_ENTERPRISE_ARCHITECTURE_BASELINE_v2.4.md`.

## v2.6 Laboratory workspace integration
The established Laboratory Operations module is now presented inside one continuous platform shell: one sidebar, one top bar, no duplicate laboratory navigation, synchronized section routing and automatic content-height sizing.


## v2.6 Client Hierarchy
Client access supports company-wide or scoped organization visibility (region/area/project/facility/station) with descendant inheritance. See `docs/16_CLIENT_HIERARCHICAL_ACCESS_v2.6.md`.
