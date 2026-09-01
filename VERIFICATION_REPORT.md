# Verification Report — v2.6 Developer Baseline

Verification date: 31 August 2026

## Automated verification

- Full pytest suite: **19 passed, 0 failed** on a clean seeded database.
- Existing end-to-end sampling, intake, LMS mock registration, receiving, laboratory operations, technical assessment and client release tests retained.
- Existing multi-client isolation, multi-site hierarchy, runtime SOP/test-package configuration, workflow versioning, approval-policy and integration queue tests retained.
- New v2.6 checks verify the seamless laboratory shell, hidden duplicate laboratory header/navigation, section synchronization hooks and Laboratory Settings navigation.
- Python compile check completed successfully.

## v2.6 laboratory presentation

- One TSCO platform sidebar and top bar remain visible.
- The embedded laboratory application's duplicate header and tab navigation are hidden.
- The laboratory frame has no visible border/shadow and automatically follows content height.
- Laboratory section changes synchronize the parent URL, title and active sidebar state.
- Existing laboratory server API contract and operational storage key are preserved.

## Boundaries

- LMS still uses the mock adapter until TSCO IT supplies the approved LMS interface/API/database contract.
- Production security, SSO, TLS, infrastructure, backup/restore, monitoring and deployment remain IT-controlled production gates.

## Result

**Developer-review architecture and seamless laboratory baseline verified. Not a production go-live declaration.**


## v2.6 verification
- Full automated suite: 21 passed, 0 failed.
- Client hierarchy checks verify descendant inheritance, portal filtering, and admin-managed unit scope.
