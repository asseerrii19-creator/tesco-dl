# Integrated Architecture — v1.2

```text
Client / Commercial Master Data
            │
Operations Manager ──> Sampling Order
            │
Sampling Supervisor ─> Assignment (TSCO or CLIENT)
            │
Field Portal ─────────> GPS / photos / barcode / tag
            │
Data Entry ───────────> Accept + LMS registration / Return / Reject
            │
Awaiting Physical Receipt
            │
Barcode Receiving
            │
Full Laboratory Operations
  ├─ Batches and workstations
  ├─ QC and calculations
  ├─ Retests and retained samples
  ├─ Methods/SOP/EOP
  └─ Reports
            │
Technical Assessment + Senior Chemist decision
            │
Client external status / report release milestone
```

## Data ownership

- FastAPI/SQL database owns users, companies, assets, orders, assignments, field records, intake decisions, custody events and LMS references.
- The integrated OperationsState owns the detailed laboratory operational dataset for each site in this pilot.
- Synchronization functions link the two datasets by portal request and LMS number.
- Production architecture may normalize the laboratory state into relational tables after pilot acceptance.
