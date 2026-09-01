# TSCO Digital Laboratory Platform — Developer Review Build v2.6

This is the application package for functional/developer review before company IT connects the official LMS interface and deploys it in the company environment.

## Fastest local start — Windows

Double-click:

`START_LOCAL_REVIEW.bat`

Then open:

`http://127.0.0.1:8000`

Primary review administrator:

- Email: `admin@tsco.local`
- Password: `Demo123!`

The administrator can review the complete platform and configure sites, clients, users, controlled documents and test packages from the web interface.

## Useful review accounts

All seeded review accounts use password `Demo123!`.

- Corporate management: `corporate@tsco.local`
- Dammam management: `manager@tsco.local`
- Operations: `operations@tsco.local`
- Sampling supervisor: `supervisor@tsco.local`
- Field sampler: `fieldman@tsco.local`
- Data entry: `intake@tsco.local`
- Receiving: `receiving@tsco.local`
- Laboratory: `chemist@tsco.local`
- Senior chemist: `senior@tsco.local`
- Quality: `quality@tsco.local`
- SEC client: `client@sec.local`
- Saudi Aramco client: `client@aramco.local`

Client portal accounts are company-isolated: a client user is scoped to its own `client_id`.

## Multi-site review

Dammam is active by default. Jubail and Bahrain are seeded as future sites and can be activated from:

`Administration → Sites & Laboratories`

Assign local users to a site from:

`Administration → Users & Access`

A management account with no single site assignment receives the consolidated corporate view.

## Live operational configuration

The following are managed from the running platform without editing source code:

- Sites / laboratories
- Clients
- Users, roles, site assignment and client scope
- Assets, quotations and purchase orders
- Controlled SOP / Method / EOP / Quick Guide revisions
- Test packages and their test lists

Publishing a new controlled-document revision supersedes the previous active revision with the same code/scope while keeping revision history.

## Main review path

Sampling Orders → Sampling Supervision → Field Capture → Data Entry → LMS registration boundary → Receiving → Laboratory Operations → Technical Assessment → Report / Client tracking.

## Mac / Linux

Run:

`./START_LOCAL_REVIEW.sh`

Then open `http://127.0.0.1:8000`.

## Shared server / company environment

Use `docker-compose.yml` with PostgreSQL. IT then supplies/approves the official LMS connector, company authentication/SSO, server/domain/HTTPS, backup/monitoring and production deployment controls.


For developer review, validate `/admin/master-data`, `/admin/hierarchy`, `/admin/workflows`, and `/admin/integrations` before LMS connector work.

## Laboratory review in v2.6
Open any Laboratory item from the main sidebar. The full Laboratory Operations functions now stay visually inside the same TSCO Digital Laboratory shell rather than appearing as a second site inside the platform.


## v2.6 client hierarchy demo accounts
- Saudi Aramco corporate: `client@aramco.local` / `Demo123!` — company-wide.
- Saudi Aramco Abqaiq: `abqaiq@aramco.local` / `Demo123!` — Abqaiq subtree only.
- SEC Eastern Region: `eastern@sec.local` / `Demo123!` — Eastern Region subtree only.

Client hierarchy and account scope are managed under Admin → Organization Hierarchy and Admin → Users & Access.
