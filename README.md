# Snowflake Cortex Code Quickstart

Workshop and reusable template for building end-to-end data pipelines and AI-powered analytics on Snowflake using Cortex Code, Cortex Analyst, Semantic Views, and Streamlit.

## What You'll Build

An **Accounts Payable (AP) Invoice Analytics** pipeline that:

1. Ingests invoice data from 4 ERP systems (SAP, Oracle, Baan, Workday)
2. Unifies and normalizes data using a **Dynamic Table** (Silver layer)
3. Defines business semantics with a **Semantic View**
4. Deploys a **Cortex Agent** for natural-language Q&A
5. Visualizes data with an interactive **Streamlit** app

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                      SNOWFLAKE ACCOUNT                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │   SAP   │  │ Oracle  │  │  Baan   │  │Workday  │  BRONZE   │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘           │
│       │             │            │             │                  │
│       └─────────────┴────────────┴─────────────┘                 │
│                          │                                        │
│                    ┌─────▼─────┐                                 │
│                    │  Dynamic  │                                  │
│                    │   Table   │  SILVER                          │
│                    └─────┬─────┘                                  │
│                          │                                        │
│              ┌───────────┼───────────┐                           │
│              │           │           │                            │
│       ┌──────▼──┐  ┌─────▼────┐  ┌──▼───────┐                  │
│       │Semantic │  │  Cortex  │  │Streamlit │                   │
│       │  View   │  │  Agent   │  │   App    │                   │
│       └─────────┘  └──────────┘  └──────────┘                   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Snowflake account (Enterprise edition or higher recommended)
- [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code) installed
- Python 3.10+ (for the Streamlit app)
- ACCOUNTADMIN role (for initial setup) or a role with CREATE DATABASE/WAREHOUSE/ROLE privileges

## Quick Start (Single User / Demo)

1. **Set up the environment:**
   ```sql
   -- Run setup/00_snowday_setup.sql to create database, schema, warehouse, and role
   ```

2. **Load sample data:**
   ```sql
   -- Run setup/00_sample_data.sql to populate bronze tables
   ```

3. **Build the pipeline with Cortex Code:**
   ```
   cortex -c COCO
   ```
   Ask Cortex Code to create the Silver Dynamic Table, Semantic View, and Agent.

4. **Run the Streamlit app:**
   ```bash
   cd streamlit
   pip install -r requirements.txt
   streamlit run ap_analytics_app.py
   ```

## Multi-Participant Lab Setup (Workshop/Event)

1. **Admin setup** (run once before the event):
   ```sql
   -- Run setup/00_admin_lab_setup.sql
   -- This creates per-user schemas (USER_01 ... USER_N), roles, and grants
   ```

2. **Distribute connection template:**
   Share `setup/connection_template.toml` with participants. Each participant appends it to their `~/.snowflake/connections.toml` and fills in their credentials.

3. **Reset between sessions:**
   ```sql
   -- Run setup/01_admin_lab_reset.sql to clear participant-created objects
   ```

4. **Full teardown** (after event):
   ```sql
   -- Run setup/02_admin_lab_teardown.sql to remove all resources
   ```

## Folder Structure

| Folder | Contents |
|--------|----------|
| `setup/` | Admin setup, data loading, reset, and teardown scripts |
| `sql/` | Pipeline DDL, validation queries, agent spec, usage monitoring |
| `semantic/` | Semantic View YAML definition |
| `streamlit/` | Interactive analytics app (Cortex Analyst + Streamlit) |
| `skills/` | Reusable Cortex Code skills (copy to `.cortex/skills/` to activate) |
| `docs/` | Workshop presentation, pipeline lineage, PRD change plans, and workflow docs |
| `assets/` | Sample business requirements CSVs |

## Key Files

| File | Description |
|------|-------------|
| `sql/03_silver_ap_invoices_prd_update.sql` | Silver Dynamic Table DDL (4-source UNION ALL) |
| `semantic/sv_ap_analytics.yaml` | Semantic View definition for Cortex Analyst |
| `sql/ap_analytics_assistant_spec.json` | Cortex Agent specification |
| `streamlit/ap_analytics_app.py` | Streamlit app with KPIs, charts, and AI chat |
| `sql/cortex_code_usage_queries.sql` | Cortex Code credit monitoring queries |

## Workshop Presentation

The `docs/` folder contains a ready-to-use workshop presentation and supporting materials:

| File | Description |
|------|-------------|
| `docs/Cortex_Code_Demo_Presentation.pptx` | 11-slide workshop deck covering Cortex Code intro, 3-demo walkthrough, pipeline lineage, cost model, and next steps |
| `docs/ap_pipeline_lineage.html` | Interactive pipeline lineage diagram (Mermaid.js) — open in any browser to see the full Bronze → Silver → Semantic View → Agent flow |
| `docs/create_presentation.py` | Python script to regenerate the PPTX (requires `pip install python-pptx`). Modify and rerun to customize slides for your audience. |

The presentation is designed for a 30-60 minute workshop and walks through:
1. What is Cortex Code and its core capabilities
2. Workshop storyline — AP Invoices across 4 ERP systems
3. Pipeline lineage — end-to-end data flow
4. Demo 1: Pipeline Builder (Dynamic Table creation)
5. Demo 2: Pipeline Maintenance (PRD-driven source onboarding)
6. Demo 3: Cortex Agent (Semantic View + NL analytics)
7. Key features and business value
8. Cost model and governance controls

## Cortex Code Usage Monitoring

The `sql/cortex_code_usage_queries.sql` file contains queries to track Cortex Code credit consumption, per-user usage, weekly trends, and cost comparisons with other AI services. Requires ACCOUNTADMIN role.

## Reusable Skills

This repo includes a Cortex Code **skill** that can be activated in any project:

### `prd-to-dt-plan`

Analyzes PRD-style requirements files (CSV/XLSX) and produces a structured implementation plan for updating a Snowflake Dynamic Table. It handles gap analysis, surfaces open questions, and generates DDL + verification queries.

**To install:**

```bash
# From the root of your project, copy the skill into your local .cortex directory
mkdir -p .cortex/skills/prd-to-dt-plan
cp skills/prd-to-dt-plan/SKILL.md .cortex/skills/prd-to-dt-plan/SKILL.md
```

**To use (inside Cortex Code CLI):**

```
$prd-to-dt-plan
```

Then provide:
- `prd_path` — path to your requirements CSV/XLSX file(s)
- `target_dynamic_table` — fully-qualified DT name (e.g., `DB.SCHEMA.MY_TABLE`)

The skill will parse the PRD, inspect the current DT, produce a gap analysis, surface open questions, and generate a DDL change plan with verification queries.

## Acknowledgements

Inspired by the Snowflake Northstar workshop. This repo contains original implementations, extensions, and a reusable template built using Cortex Code.

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
