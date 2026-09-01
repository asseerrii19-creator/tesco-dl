# Final Architecture Review — v2.4

Developer review should confirm these structural decisions before LMS integration:

1. One platform, multiple sites: Corporate -> Dammam / Jubail / Bahrain -> Department -> User.
2. Client isolation by company, with optional client hierarchy below each company (Project / Region / Plant / Station / Site).
3. Site-scoped and corporate-scoped configuration rather than separate site copies.
4. Runtime administration for sites, departments, clients, client units, users/access, assets, SOP/Method/EOP revisions, test packages, workflows and approval policies.
5. Existing immutable operational identifiers are integration keys; display names are not integration keys.
6. LMS remains an external system-of-record boundary connected through the adapter/integration layer.
7. Integration transactions require status/error/retry visibility.
8. Operational data lives in the configured database and is not replaced when application code is upgraded.
9. Production changes must be migration-backed and deployed with backup/rollback controls.
10. Phase-2 modules can be added without creating separate platform copies per site or client.
