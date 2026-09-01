# IT / Developer Handover — v2.6

## Purpose
Review the working application and preserve its functional architecture while connecting it to TSCO infrastructure and the existing LMS.

## Application boundary
The application already contains the functional sample lifecycle, roles, client isolation, multi-site structure, laboratory operations, technical review, audit, barcode, client tracking and database-backed operational configuration.

## LMS connector boundary
`app/integrations/lms/` contains the connector contract and current mock adapter. Replace/extend the mock implementation only after the official LMS interface is confirmed. The application workflow calls the connector through the existing abstraction; business workflow pages should not need to be redesigned for the connection itself.

## Multi-tenant / multi-site intent
- Client users are isolated by company (`client_id`).
- Local operational users are scoped by `site_id`.
- Corporate management may have no single site and receives consolidated visibility.
- Sites, clients and users are administered from the platform.

## Database-backed configuration
Controlled documents and custom test packages are stored in the application database. Document files are stored under the configured application data path for developer review; production storage location/backup policy must be approved by IT.

## Production items for IT
- Official LMS API/database/interface connector and credentials.
- PostgreSQL production database and migration process.
- Corporate identity / SSO and password policy.
- HTTPS, domain, reverse proxy and network segmentation.
- Backup/restore, document storage durability, monitoring and logs.
- Secret management and production environment variables.
- Deployment method supporting safe releases; rolling/blue-green deployment if zero-downtime is required.
- UAT/business/Quality acceptance before production go-live.

## v2.6 UI integration note
The legacy Laboratory Operations header/navigation is suppressed only when the module is embedded in the main platform. The outer platform shell remains the navigation authority; the laboratory module retains its existing functional logic and server data API.
