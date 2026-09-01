# Offline Field Operation

## Implemented

- previously loaded Field page can be reopened from the PWA cache
- form draft saved locally
- photos and fields queued in IndexedDB
- locally generated Code 39-compatible barcode usable on the bottle
- automatic synchronization when the connection returns and the application is open
- manual `Sync Offline Queue` action
- idempotent server endpoint; replaying the same barcode does not create a duplicate
- queued record is retained if authentication expires or synchronization fails

## Operational control

The Sample Man must not consider the record complete until the app confirms server synchronization and shows the official portal request number.

## IT controls required

- managed iPads or phones
- device encryption and PIN
- remote wipe
- approved PWA/browser configuration
- defined maximum offline retention period
- user training on synchronization status
