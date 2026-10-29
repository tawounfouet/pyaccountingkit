# PyAccountingKit

Modular Python accounting toolkit (early implementation scaffold).

## Company Configuration

The Company Configuration bounded context governs company accounting parameters and their published versions. It does **not** create journal entries or post to the ledger.

Implementation follows an evidence-based, incremental approach: L00 audit and baseline, L01 domain kernel, L02 technical foundations. Do not treat this bootstrap commit as a completed qualification gate or a stable release.

See `docs/company_configuration/` on the foundation implementation branch for its first audited scope.
