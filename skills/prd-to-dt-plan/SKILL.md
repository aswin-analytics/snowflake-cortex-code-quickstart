---
name: prd-to-dt-plan
description: "Analyze PRD-style requirements files and produce a structured implementation plan for updating a target Dynamic Table. Use when: receiving new business requirements (XLSX, CSV) that affect a Snowflake Dynamic Table pipeline. Triggers: PRD analysis, requirements to DT plan, onboard new source, business rules to pipeline plan."
---

# PRD to Dynamic Table Plan

Reads PRD-style input files (XLSX or CSV) containing business requirements, source onboarding requests, or business rules, and produces a structured implementation plan for updating a target Snowflake Dynamic Table.

## When to Use

- A new PRD, business requirements doc, or source onboarding request arrives
- You need to assess impact on an existing Dynamic Table pipeline
- You want a consistent, repeatable analysis instead of ad-hoc exploration

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| `prd_path` | Yes | Path to the PRD file (XLSX or CSV). May be multiple files separated by commas. |
| `target_dynamic_table` | Yes | Fully-qualified DT name (e.g., `DB.SCHEMA.TABLE`) |

**Collect these before proceeding.** If not provided, ask the user.

## Workflow

### Step 1: Parse PRD Files

**Goal:** Extract structured requirements from the input file(s).

**Actions:**
1. Read each file at `prd_path` using the Read tool (supports XLSX and CSV)
2. Identify the document type:
   - Source onboarding request (new ERP/system to integrate)
   - Business rules (transformation logic, validation rules)
   - Mixed (both in one file)
3. Extract every requirement row into a working set

**If file cannot be read:** Ask user for correct path or format clarification.

### Step 2: Inspect Target Dynamic Table

**Goal:** Understand the current state of the target DT.

**Actions:**
1. Run `SELECT GET_DDL('DYNAMIC_TABLE', '<target_dynamic_table>')` to get current definition
2. Run `DESCRIBE TABLE <target_dynamic_table>` to get column schema
3. Run proof query: `SELECT SOURCE_SYSTEM, COUNT(*) FROM <target_dynamic_table> GROUP BY SOURCE_SYSTEM`
4. Note current: column names, UNION ALL branches, CASE logic, TARGET_LAG, REFRESH_MODE

**If DT does not exist:** Note this — the plan will be for initial creation rather than modification.

### Step 3: Gap Analysis

**Goal:** Compare PRD requirements against current DT state.

**Actions:**
1. **New sources:** Identify source systems in the PRD that are NOT in the current DT's UNION ALL branches
2. **New/changed fields:** Identify columns, mappings, or transformations required by the PRD that don't exist in current DDL
3. **Modified rules:** Identify CASE statements, filters, or dedup logic that needs updating
4. **Confirmed no-ops:** Explicitly note requirements that the current DT already satisfies

### Step 4: Surface Assumptions and Open Questions

**Goal:** Never guess — always surface ambiguity for human decision.

**Rules:**
- If a requirement says "OPEN QUESTION" or "NEEDS DECISION" — flag it
- If two rules conflict (e.g., one says normalize, another says pass-through) — flag it
- If a requirement references an external dependency not yet available (legal approval, mapping table, FX rates) — flag it
- If a value mapping is incomplete (e.g., only some statuses listed) — flag it
- If the requirement is ambiguous about scope (Silver vs Gold, this DT vs another) — flag it
- If implementation timing is unclear (add now with empty source, or wait?) — flag it

**Format each as:**
> **[Question ID]**: [Clear statement of the ambiguity] — [Who owns the decision, if stated in PRD]

**⚠️ MANDATORY STOPPING POINT**: Present the gap analysis and open questions to the user. Do NOT proceed to DDL recommendations until the user has reviewed findings and resolved critical questions.

### Step 5: Produce Implementation Plan

**Goal:** Deliver the structured output contract.

**Actions:**
1. Draft proposed DDL changes (new UNION ALL branches, modified CASE statements)
2. Draft verification queries to validate correctness post-implementation
3. Compile final output in the contract format below

## Output Contract

Every invocation MUST return these 5 sections:

### 1. New Source Systems

| Source System | Platform | Status | Bronze Table | Notes |
|---------------|----------|--------|--------------|-------|

### 2. Field & Rule Changes

| Rule/Change | Category | Impact on Silver DT | Action Required |
|-------------|----------|---------------------|-----------------|

### 3. Open Questions

| ID | Question | Owner | Blocking? |
|----|----------|-------|-----------|

### 4. Proposed DDL Changes

```sql
-- Annotated SQL showing the new/modified CREATE DYNAMIC TABLE statement
-- with comments explaining each change
```

### 5. Verification Queries

```sql
-- Queries to run after implementation to confirm correctness
```

## Stopping Points

- ✋ After Step 1 if file format is unclear or unreadable
- ✋ After Step 4 — present findings before recommending DDL changes
- ✋ After Step 5 — final review before any execution

## Best Practices: Surfacing Assumptions

1. **Never infer mappings** — if the PRD doesn't explicitly state how value X maps to value Y, ask
2. **Never assume layer** — if a rule doesn't specify Silver vs Gold, flag it
3. **Never silently drop** — if a requirement seems contradictory, present both interpretations
4. **Prefer pass-through** — when in doubt, recommend storing raw values and transforming downstream
5. **Cite sources** — reference the specific Rule ID or Request ID from the PRD in every finding
6. **Separate blocking from non-blocking** — clearly mark which open questions block implementation vs which can be deferred

## Example Usage

```
User: $prd-to-dt-plan

Cortex: To analyze your PRD, I need:
1. **prd_path**: Path to the requirements file(s) (XLSX or CSV)
2. **target_dynamic_table**: Fully-qualified DT name

User: Files are sample_business_requirements_source_onboarding.csv and
      sample_business_requirements_business_rules.csv.
      Target is COCO_WORKSHOP.PIPELINE_LAB.SILVER_AP_INVOICES.

Cortex: [Executes workflow Steps 1-4, presents gap analysis and open questions]
        [After user resolves questions, produces Step 5 output]
```

## Supported File Formats

| Format | How Parsed |
|--------|-----------|
| `.xlsx` | Read tool (renders sheet contents as structured table) |
| `.csv` | Read tool (renders as text with comma-delimited columns) |

## Troubleshooting

**Error: File not found**
- Verify path is absolute or relative to working directory
- Check file extension matches expected format

**Error: DT does not exist**
- Switch to "initial creation" mode — skip Step 2 current-state inspection
- Plan will produce a full CREATE DYNAMIC TABLE rather than modifications

**Error: Cannot determine column mappings**
- Ask user which Bronze table columns map to which Silver columns
- Do not guess based on column name similarity alone
