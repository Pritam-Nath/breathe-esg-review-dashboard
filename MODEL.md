# Data model

The core model is intentionally small: `Tenant`, `SourceBatch`, `ActivityRow`, and `AuditEvent`.

## Tenant

`Tenant` owns all imported rows and source batches. Every activity row references a tenant directly, even though it can also be reached through its batch. That denormalization is deliberate: tenant filtering is a first-class safety boundary in a multi-tenant ESG system, and production would enforce it in queryset managers and row-level authorization.

## SourceBatch

`SourceBatch` records the source-of-truth envelope:

- `source_type`: SAP, utility, or travel.
- `ingestion_method`: for example SAP OData snapshot, Green Button portal CSV, Concur export.
- `source_system`, `original_filename`, `imported_by`, `imported_at`.
- `row_count`, `failed_count`, `suspicious_count`.

This answers “where did this row come from?” without requiring analysts to inspect each row’s raw payload.

## ActivityRow

`ActivityRow` is the normalized review object. It stores:

- Scope category: Scope 1 fuel, Scope 2 electricity, Scope 3 procurement/travel.
- Raw quantity/unit and normalized quantity/unit.
- Period fields for utility bills and an activity date for transactional SAP/travel rows.
- Emission factor and computed `co2e_kg`.
- Raw source payload as JSON for traceability.
- Validation errors, suspicious reasons, status, approval, and lock timestamps.

Rows are unique per `source_batch + external_id` to prevent accidental duplicate ingestion from a single file or API pull.

## Audit trail

`AuditEvent` records review actions such as approval and audit lock with actor, timestamp, and details. In production I would also record edit diffs for any change to normalized quantities, factors, scope, or facility mapping.

## Unit normalization

The prototype normalizes common units: liters/gallons to liters, MWh to kWh, miles to km, and nights to room-nights. Production would move this into a versioned factor/unit library so historical rows are reproducible after factor updates.
