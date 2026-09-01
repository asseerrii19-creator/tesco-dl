# Project 00012 — Final Developer Baseline v2.6

## Purpose
Developer review baseline before formal IT/LMS integration.

## Added in v2.6 — Client hierarchical access
- Client → Division/Region/Area/Project → Facility/Plant/Station/Substation/Site → Asset → Sample.
- Client corporate account: no unit assignment = full-company visibility.
- Regional/area/facility account: assign one or more organization units; visibility automatically includes all descendants.
- Client portal and protected tracking enforce the same scope.
- Assets are attached to a client organization unit.
- Client-unit access can be changed from Admin without code changes.
- Demo hierarchy includes Saudi Aramco (Abqaiq, Haradh, Dhahran) and SEC regional structure.

## Preserved baseline
Multi-site corporate hierarchy, configurable master data, SOP/method revision control, workflows, approval policy, audit trail, LMS integration queue, seamless Laboratory Operations shell, and database-backed operation remain intact.
