# End-to-End Workflow v2

1. Operations Manager creates a sampling order linked to Client, Quotation and PO.
2. Sampling Supervisor assigns assets to TSCO Sample Men or authorized client-side sampling personnel.
3. Sampler captures transformer identity, exact location, GPS, photos, sample conditions and requested package.
4. The device issues a barcode. Offline records remain queued until synchronized.
5. Data Entry reviews the electronic submission before the bottle arrives.
6. Data Entry accepts and registers it through the LMS connector, returns it for correction, or rejects it with a recorded reason.
7. On acceptance, the platform records the official LMS number and status `Awaiting Physical Receipt`.
8. Receiving scans the physical bottle later and confirms seal/condition/container count.
9. The sample appears in the integrated laboratory queue and the full laboratory operations module.
10. Chemists complete workstations, calculations and QC.
11. Senior Chemist reviews results, retests, technical assessment and recommendations.
12. Quality/authorized reviewer controls report release.
13. Client sees simplified milestones and the released report only; internal QC and technical notes remain hidden.
14. Management sees workload, status, recurring field errors and sampler performance records.
