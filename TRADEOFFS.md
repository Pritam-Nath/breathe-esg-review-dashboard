# Tradeoffs

1. I did not build live third-party integrations. Mocking SAP, utilities, and Concur auth flows would add surface area without improving the core judgment being evaluated: source shape, normalization, review, and auditability.

2. I did not build a full emissions factor service. The prototype uses a tiny fixed factor map so the review workflow is demonstrable. Production should use versioned emission factor datasets and store factor provenance per row.

3. I did not build role-based authentication. The model records actors on review actions, but real deployment should add tenant-scoped users, analyst/auditor permissions, and immutable edit history before handling client data.
