# Enterprise Architecture Baseline — v2.4

This baseline freezes the structural decisions that must survive future feature growth.

## Hierarchy
Corporate -> Site -> Department -> User. Site-less management accounts operate at corporate scope; site-linked accounts are operationally scoped.

## Client isolation and hierarchy
Client accounts remain isolated by client_id. Clients may contain Projects, Regions, Plants, Stations or Sites through ClientUnit. Assets can be attached to a client unit while retaining client ownership.

## Controlled configuration
Sites, departments, clients, client units, users, assets, controlled documents, test packages, workflows and approval policies are administered from the application rather than source-code edits.

## Workflow versioning
WorkflowDefinition + ordered WorkflowStep records provide corporate defaults or site-specific versions. Publishing a new version does not erase previous versions.

## Approval policies
ApprovalPolicy stores ordered role-based approval stages by corporate or site scope. Runtime enforcement is a controlled UAT implementation item to validate with Technical/Quality owners before production.

## Integration boundary
The existing LMS adapter remains the official connector boundary. IntegrationQueue provides status/attempt/error visibility for queued LMS or future enterprise messages. The real LMS API/database contract must be supplied and approved by IT.

## Stable integration keys
Use existing unique system keys as canonical references: Site.code, Client.code, ClientUnit(client_id+code), Asset(client_id+asset_code), SamplingOrder.order_number, SampleRequest.request_number, barcode_value and TestPackageConfig.code. Do not integrate by display names.

## Data continuity
DATABASE_URL keeps application code and operational data separated. Production changes must use database migrations, backups and controlled deployment; application upgrades must not recreate or replace the production database.
