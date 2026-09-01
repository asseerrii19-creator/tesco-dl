# Administration and Portal Design

## Public landing

The public landing page exposes only three entry points: Client Portal, Employee Sign In and Field Sampling. It does not list internal roles, employee emails or departments.

## Company administration

System administrators can add, update, activate and disable clients. Historical records remain attached to disabled clients, but new field submissions cannot use them.

## User administration

- Client users must be linked to one client.
- Employee users can be linked to a site.
- Field samplers can be assigned to selected clients.
- Temporary passwords require a password change.
- User activation changes are audited.

## Commercial and asset master data

Quotation and PO records are client-specific. Assets are identified by client + asset code and carry serial number, equipment type, ratings, station, exact location and GPS coordinates.

## Audit

Administration changes create audit records with actor, action, entity, summary, timestamp and source IP where available. Sample operational changes remain additionally represented in chain-of-custody events.
