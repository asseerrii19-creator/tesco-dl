# Client Hierarchical Access — v2.6

## Data hierarchy
Client → organization units (recursive parent/child) → Asset → Sample.

Recommended unit types include CORPORATE, DIVISION, REGION, AREA, PROJECT, FACILITY, PLANT, STATION, SUBSTATION and SITE.

## Visibility rule
- A client account with no unit assignments has company-wide access.
- A client account assigned to one or more units sees those units and every descendant below them.
- An account never sees another client company.
- Asset ownership defines sample scope; protected sample tracking uses the same rule.

## Examples
Saudi Aramco Corporate → all Aramco areas.
Aramco Abqaiq account → Abqaiq and child facilities/assets/samples only.
SEC Eastern Region account → Eastern Region and its substations/assets/samples only.

## Administration
System Admin can create client units, attach assets to units, and change account unit scope without code changes.
