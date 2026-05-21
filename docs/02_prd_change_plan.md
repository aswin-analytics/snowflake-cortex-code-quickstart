# PRD Change Plan: SILVER_AP_INVOICES

**PRD Source:** `sample_business_requirements_column_mapping.csv`  
**Target:** `COCO_WORKSHOP.PIPELINE_LAB.SILVER_AP_INVOICES`  
**Generated:** 2026-05-16

---

## 1. Summary of Requested Changes

The PRD introduces **2 new source systems** (Baan IV and Workday) to be added to `SILVER_AP_INVOICES`. Both have confirmed column mappings to the existing 16-column Silver schema. Key changes:

- Add 2 new `UNION ALL` branches (Baan, Workday)
- Extend the status normalization CASE to handle `POSTED`, `Approved`, `In Review`
- Apply Baan-specific dedup logic (BR-003 from earlier requirements)
- Drop system-specific columns (`BAN_COMPANY`, `WD_TENANT_ID`)
- **No new columns** added to Silver — both sources fit the existing schema exactly

---

## 2. Source-to-Silver Mapping Summary

### Baan IV → Silver

| Source Column | Silver Column | Transform |
|---|---|---|
| `BAN_INVOICE_ID` | `INVOICE_ID` | Direct |
| `BAN_INVOICE_REF` | `INVOICE_NUMBER` | Direct (also used for dedup) |
| `BAN_VENDOR_CODE` | `VENDOR_ID` | Direct |
| `BAN_VENDOR_DESC` | `VENDOR_NAME` | Direct |
| `BAN_INV_DATE` | `INVOICE_DATE` | Direct |
| `BAN_PAY_DATE` | `DUE_DATE` | Direct |
| `BAN_AMOUNT` | `INVOICE_AMOUNT` | Direct |
| `BAN_CURR` | `CURRENCY_CODE` | Direct |
| `BAN_PAY_TERMS` | `PAYMENT_TERMS` | Pass-through (keep raw `N30`/`N60`) |
| `BAN_PO_REF` | `PO_NUMBER` | Direct |
| `BAN_LINE_DESC` | `LINE_DESCRIPTION` | Direct |
| `BAN_GL_CODE` | `GL_ACCOUNT` | Direct |
| `BAN_COST_CTR` | `COST_CENTER` | Direct |
| `BAN_STATUS` | `APPROVAL_STATUS` | `POSTED`→`APPROVED`, `APPROVED`→`APPROVED`, `PENDING`→`PENDING` |
| `BAN_CREATED` | `CREATED_AT` | Direct (already UTC) |
| `BAN_COMPANY` | — | DROP |

### Workday → Silver

| Source Column | Silver Column | Transform |
|---|---|---|
| `WD_INVOICE_ID` | `INVOICE_ID` | Direct |
| `WD_INVOICE_NUM` | `INVOICE_NUMBER` | Direct |
| `WD_SUPPLIER_ID` | `VENDOR_ID` | Direct |
| `WD_SUPPLIER_NAME` | `VENDOR_NAME` | Direct |
| `WD_INVOICE_DATE` | `INVOICE_DATE` | Direct |
| `WD_DUE_DATE` | `DUE_DATE` | Direct |
| `WD_AMOUNT` | `INVOICE_AMOUNT` | Direct |
| `WD_CURRENCY` | `CURRENCY_CODE` | Direct |
| `WD_PAY_TERMS` | `PAYMENT_TERMS` | Pass-through (keep raw `Net 30`/`Net 60`) |
| `WD_PO_NUMBER` | `PO_NUMBER` | Direct |
| `WD_MEMO` | `LINE_DESCRIPTION` | Direct |
| `WD_LEDGER_ACCOUNT` | `GL_ACCOUNT` | Direct |
| `WD_COST_CENTER` | `COST_CENTER` | Direct |
| `WD_APPROVAL_STATUS` | `APPROVAL_STATUS` | `Approved`→`APPROVED`, `In Review`→`PENDING` |
| `WD_CREATED_DATE` | `CREATED_AT` | Direct (already UTC) |
| `WD_TENANT_ID` | — | DROP |

---

## 3. Open Questions and Assumptions

| ID | Question | Owner | Blocking? |
|----|----------|-------|-----------|
| OQ-1 | **Payment terms normalization**: The PRD says "keep as-is for now, normalize in Gold." But the *current* DT already normalizes Oracle `N30`→`NET30`. Should we (a) revert Oracle normalization to match the new policy, or (b) also normalize Baan/Workday for consistency? | Sarah Chen / David Kim | **Yes** — inconsistent behavior if unresolved |
| OQ-2 | **Baan dedup scope**: BR-003 requires `QUALIFY ROW_NUMBER() OVER (PARTITION BY INVOICE_NUMBER ORDER BY CREATED_AT DESC) = 1` on Baan. Should this apply *only* inside the Baan branch (before UNION ALL), or as a global dedup across all sources? | Engineering | No — safe to apply Baan-only per PRD |
| OQ-3 | **Workday case sensitivity**: Workday statuses are `Approved` and `In Review` (mixed case). Is this guaranteed, or could future data arrive as `APPROVED` / `IN REVIEW`? Affects whether CASE should use `UPPER()` defensively. | Karen van der Berg / IT | No — can add `UPPER()` defensively without risk |
| OQ-4 | **TARGET_LAG change**: BR-009 recommends `DOWNSTREAM`. Current DT uses `'1 minute'`. Changing to DOWNSTREAM requires a Gold DT to exist as a consumer. Should we change now or defer? | Engineering | No — defer until Gold exists |

**Assumption made (non-blocking):** OQ-2 resolved as "Baan-only dedup" per PRD wording. OQ-3 resolved defensively with `UPPER()`.

---

## 4. DDL Delta Plan for SILVER_AP_INVOICES

Changes from current DDL:
- Add Baan UNION ALL branch with dedup (`QUALIFY`)
- Add Workday UNION ALL branch
- Extend outer CASE to handle `POSTED`, `Approved`, `In Review` (using `UPPER()` for safety)
- **Payment terms**: left as pass-through for Baan/Workday (pending OQ-1 resolution on Oracle)

```sql
CREATE OR REPLACE DYNAMIC TABLE COCO_WORKSHOP.PIPELINE_LAB.SILVER_AP_INVOICES
  TARGET_LAG = '1 minute'
  WAREHOUSE = COMPUTE_WH
  REFRESH_MODE = INCREMENTAL
  COMMENT = 'Silver AP Invoices: unified SAP + Oracle + Baan + Workday with normalized status'
AS
SELECT
    INVOICE_ID,
    INVOICE_NUMBER,
    VENDOR_ID,
    VENDOR_NAME,
    INVOICE_DATE,
    DUE_DATE,
    INVOICE_AMOUNT,
    CURRENCY_CODE,
    PAYMENT_TERMS,
    PO_NUMBER,
    LINE_DESCRIPTION,
    GL_ACCOUNT,
    COST_CENTER,
    CASE 
        WHEN UPPER(APPROVAL_STATUS) IN ('APPROVED', 'VALIDATED', 'POSTED') THEN 'APPROVED'
        WHEN UPPER(APPROVAL_STATUS) IN ('PENDING', 'IN REVIEW') THEN 'PENDING'
        ELSE 'OTHER'
    END AS APPROVAL_STATUS,
    CREATED_AT,
    SOURCE_SYSTEM
FROM (
    -- SAP branch (unchanged)
    SELECT
        INVOICE_ID,
        INVOICE_NUMBER,
        VENDOR_ID,
        VENDOR_NAME,
        INVOICE_DATE,
        DUE_DATE,
        INVOICE_AMOUNT,
        CURRENCY_CODE,
        PAYMENT_TERMS,
        PO_NUMBER,
        LINE_DESCRIPTION,
        GL_ACCOUNT,
        COST_CENTER,
        APPROVAL_STATUS,
        CREATED_AT,
        'SAP' AS SOURCE_SYSTEM
    FROM COCO_WORKSHOP.SOURCE_DATA.BRONZE_SAP_AP_INVOICES

    UNION ALL

    -- Oracle branch (payment terms normalization kept for now — see OQ-1)
    SELECT
        INV_ID AS INVOICE_ID,
        INV_NUM AS INVOICE_NUMBER,
        SUPPLIER_ID AS VENDOR_ID,
        SUPPLIER_NAME AS VENDOR_NAME,
        INV_DATE AS INVOICE_DATE,
        PAYMENT_DUE_DATE AS DUE_DATE,
        TOTAL_AMOUNT AS INVOICE_AMOUNT,
        CURRENCY AS CURRENCY_CODE,
        CASE 
            WHEN TERMS_CODE = 'N30' THEN 'NET30'
            WHEN TERMS_CODE = 'N60' THEN 'NET60'
            ELSE TERMS_CODE
        END AS PAYMENT_TERMS,
        PURCHASE_ORDER AS PO_NUMBER,
        DESCRIPTION AS LINE_DESCRIPTION,
        ACCOUNT_CODE AS GL_ACCOUNT,
        DEPT_CODE AS COST_CENTER,
        STATUS AS APPROVAL_STATUS,
        CREATION_DATE AS CREATED_AT,
        'ORACLE' AS SOURCE_SYSTEM
    FROM COCO_WORKSHOP.SOURCE_DATA.BRONZE_ORACLE_AP_INVOICES

    UNION ALL

    -- Baan branch (NEW) with dedup per BR-003
    SELECT
        BAN_INVOICE_ID AS INVOICE_ID,
        BAN_INVOICE_REF AS INVOICE_NUMBER,
        BAN_VENDOR_CODE AS VENDOR_ID,
        BAN_VENDOR_DESC AS VENDOR_NAME,
        BAN_INV_DATE AS INVOICE_DATE,
        BAN_PAY_DATE AS DUE_DATE,
        BAN_AMOUNT AS INVOICE_AMOUNT,
        BAN_CURR AS CURRENCY_CODE,
        BAN_PAY_TERMS AS PAYMENT_TERMS,
        BAN_PO_REF AS PO_NUMBER,
        BAN_LINE_DESC AS LINE_DESCRIPTION,
        BAN_GL_CODE AS GL_ACCOUNT,
        BAN_COST_CTR AS COST_CENTER,
        BAN_STATUS AS APPROVAL_STATUS,
        BAN_CREATED AS CREATED_AT,
        'BAAN' AS SOURCE_SYSTEM
    FROM COCO_WORKSHOP.SOURCE_DATA.BRONZE_BAAN_AP_INVOICES
    QUALIFY ROW_NUMBER() OVER (PARTITION BY BAN_INVOICE_REF ORDER BY BAN_CREATED DESC) = 1

    UNION ALL

    -- Workday branch (NEW)
    SELECT
        WD_INVOICE_ID AS INVOICE_ID,
        WD_INVOICE_NUM AS INVOICE_NUMBER,
        WD_SUPPLIER_ID AS VENDOR_ID,
        WD_SUPPLIER_NAME AS VENDOR_NAME,
        WD_INVOICE_DATE AS INVOICE_DATE,
        WD_DUE_DATE AS DUE_DATE,
        WD_AMOUNT AS INVOICE_AMOUNT,
        WD_CURRENCY AS CURRENCY_CODE,
        WD_PAY_TERMS AS PAYMENT_TERMS,
        WD_PO_NUMBER AS PO_NUMBER,
        WD_MEMO AS LINE_DESCRIPTION,
        WD_LEDGER_ACCOUNT AS GL_ACCOUNT,
        WD_COST_CENTER AS COST_CENTER,
        WD_APPROVAL_STATUS AS APPROVAL_STATUS,
        WD_CREATED_DATE AS CREATED_AT,
        'WORKDAY' AS SOURCE_SYSTEM
    FROM COCO_WORKSHOP.SOURCE_DATA.BRONZE_WORKDAY_AP_INVOICES
);
```

---

## 5. Verification Queries

```sql
-- 1. Record counts by source (expect SAP:15, ORACLE:15, BAAN:≤10, WORKDAY:10)
SELECT SOURCE_SYSTEM, COUNT(*) AS RECORD_COUNT
FROM COCO_WORKSHOP.PIPELINE_LAB.SILVER_AP_INVOICES
GROUP BY SOURCE_SYSTEM
ORDER BY SOURCE_SYSTEM;

-- 2. Confirm status normalization (should only see APPROVED, PENDING, OTHER)
SELECT APPROVAL_STATUS, SOURCE_SYSTEM, COUNT(*) AS CNT
FROM COCO_WORKSHOP.PIPELINE_LAB.SILVER_AP_INVOICES
GROUP BY APPROVAL_STATUS, SOURCE_SYSTEM
ORDER BY APPROVAL_STATUS, SOURCE_SYSTEM;

-- 3. Confirm Baan dedup worked (count should be ≤ source row count)
SELECT 
    (SELECT COUNT(*) FROM COCO_WORKSHOP.SOURCE_DATA.BRONZE_BAAN_AP_INVOICES) AS BAAN_BRONZE_COUNT,
    (SELECT COUNT(*) FROM COCO_WORKSHOP.PIPELINE_LAB.SILVER_AP_INVOICES WHERE SOURCE_SYSTEM = 'BAAN') AS BAAN_SILVER_COUNT;

-- 4. Confirm no NULLs in required fields
SELECT SOURCE_SYSTEM, 
    COUNT_IF(INVOICE_ID IS NULL) AS NULL_INVOICE_ID,
    COUNT_IF(VENDOR_NAME IS NULL) AS NULL_VENDOR_NAME,
    COUNT_IF(INVOICE_AMOUNT IS NULL) AS NULL_AMOUNT,
    COUNT_IF(CURRENCY_CODE IS NULL) AS NULL_CURRENCY
FROM COCO_WORKSHOP.PIPELINE_LAB.SILVER_AP_INVOICES
GROUP BY SOURCE_SYSTEM;

-- 5. Payment terms distribution (visual check for consistency decision)
SELECT SOURCE_SYSTEM, PAYMENT_TERMS, COUNT(*) AS CNT
FROM COCO_WORKSHOP.PIPELINE_LAB.SILVER_AP_INVOICES
GROUP BY SOURCE_SYSTEM, PAYMENT_TERMS
ORDER BY SOURCE_SYSTEM, PAYMENT_TERMS;
```

---

## Next Steps

1. Resolve **OQ-1** (payment terms normalization policy)
2. Execute the DDL above
3. Run verification queries
4. Update `TARGET_LAG` to `DOWNSTREAM` once Gold layer DT exists
