# v2.6.0 — Client Hierarchical Access

- Client → Region/Area/Project → Facility/Plant/Station/Substation → Asset → Sample hierarchy.
- Company-wide or scoped client accounts with descendant inheritance.
- Asset-to-client-unit placement.
- Client portal and protected sample tracking enforce unit scope.
- Admin-managed organization permissions without code changes.
- Preserves v2.5 seamless Laboratory Workspace.

# v2.5.0 — Seamless Laboratory Workspace

- Integrated the full Laboratory Operations application visually into the main TSCO Digital Laboratory shell.
- Removed the duplicate laboratory header/navigation when embedded.
- Removed the bordered “site inside a site” presentation.
- Added automatic embedded-page height synchronization to eliminate nested scrolling.
- Laboratory section changes update the main platform URL, top bar and active sidebar item.
- Added Laboratory Settings to the unified sidebar for Technical Manager / System Admin.
- Updated visible laboratory persistence wording from legacy Netlify terminology to platform-server terminology.
- Preserved the existing Laboratory Operations data key and server API contract.

# v2.4.0 — Enterprise Architecture Baseline

- Corporate -> Site -> Department -> User hierarchy.
- Client organization hierarchy (Project / Region / Plant / Station / Site).
- Asset-to-client-unit association.
- Master Data Center for runtime configuration.
- Versioned workflow definitions and ordered steps.
- Configurable approval policies.
- Integration control queue with status, attempts, errors and retry boundary.
- Existing multi-client isolation, site scoping, controlled documents, test packages and audit retained.
- LMS remains the official pending external connector; no fake live connection is claimed.

# v2.3 — Scalable Developer Review Build

- Preserved the complete v2.2 operational workflow and full Laboratory Operations module.
- Added web-based Site & Laboratory administration for Dammam, Jubail, Bahrain and future sites.
- Added corporate management aggregation across sites while retaining site-scoped local operations.
- Retained company-isolated client accounts and added separate seeded SEC and Saudi Aramco client review logins.
- Added user profile administration for role, site and client-account scope changes without editing code.
- Added database-backed Controlled Document management for SOP, METHOD, EOP, QUICK GUIDE, FORM and OTHER document types.
- Added controlled revision behavior: publishing a new active revision supersedes the prior active revision for the same code/site scope without deleting history.
- Added a site-aware Controlled Document Library for laboratory/quality/technical/management users.
- Added database-backed Test Package configuration; newly configured active packages are immediately available to sampling operations and laboratory synchronization.
- Added an Alembic migration for the new controlled-document and test-package tables.
- Preserved the isolated LMS connector boundary under `app/integrations/lms/` for official IT integration.
- No IT/UAT narration was added to normal user-facing operational pages.


## v2.6.0 — Client hierarchical access
- Recursive client organization hierarchy and descendant-scoped visibility.
- Region/area/facility-level client accounts.
- Asset-to-client-unit placement and portal filtering.
- Admin-managed client unit permissions.
