# Artifacts: SILVER_AP_INVOICES PRD Update

Checklist of deliverables from the Baan + Workday onboarding sprint.
Another engineer can use this to review the change, rerun validation, and reuse the workflow.

---

## PRD Source Files

| File | Purpose |
|------|---------|
| `sample_business_requirements_source_onboarding.csv` | New source system requests (Baan IV, Workday) |
| `sample_business_requirements_business_rules.csv` | Business rules (status mapping, dedup, payment terms, refresh timing) |
| `sample_business_requirements_column_mapping.csv` | Column-level source-to-Silver mapping for Baan and Workday |

---

## Output Artifacts

| File | Purpose |
|------|---------|
| `notes/02_prd_change_plan.md` | Full change plan: gap analysis, open questions, proposed DDL, verification queries |
| `sql/02_silver_ap_invoices_proof.sql` | Baseline proof query (record counts by SOURCE_SYSTEM) |
| `sql/03_silver_ap_invoices_prd_update.sql` | Final DDL + validation queries for the 4-source SILVER_AP_INVOICES |

---

## Project Skill

| File | Purpose |
|------|---------|
| `.cortex/skills/prd-to-dt-plan/SKILL.md` | Reusable skill for analyzing PRD files and producing DT update plans |

**To invoke:** `$prd-to-dt-plan` then provide `prd_path` and `target_dynamic_table`.

---

## How to Review

1. Read `notes/02_prd_change_plan.md` for the full rationale and open questions
2. Review the DDL in `sql/03_silver_ap_invoices_prd_update.sql`
3. Run the 5 validation queries at the bottom of that file to confirm correctness
4. Check the "Assumptions Requiring Engineering Review" section for unresolved decisions

---

## How to Rerun Validation

```sql
-- From sql/03_silver_ap_invoices_prd_update.sql, run the validation section:
-- 1. Record counts by source
-- 2. Status normalization check
-- 3. Baan dedup verification
-- 4. NULL check on required fields
-- 5. Payment terms distribution
```

---

## How to Reuse the Skill for Future PRDs

```
$prd-to-dt-plan
```

Provide:
- **prd_path**: path to the new XLSX or CSV requirements file(s)
- **target_dynamic_table**: fully-qualified DT name (e.g., `COCO_WORKSHOP.PIPELINE_LAB.SILVER_AP_INVOICES`)

The skill will parse the PRD, inspect the current DT state, produce a gap analysis, surface open questions, and generate a DDL delta plan.

---

## Open Decisions (Unresolved)

| ID | Question | Owner | Status |
|----|----------|-------|--------|
| OQ-1 | Normalize payment terms at Silver or Gold? | Sarah Chen / David Kim | Pending (due 2025-06-20) |
| OQ-4 | Change TARGET_LAG to DOWNSTREAM? | Engineering | Deferred until Gold DT exists |
