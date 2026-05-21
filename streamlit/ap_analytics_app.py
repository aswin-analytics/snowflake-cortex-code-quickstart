"""
AP Invoice Analytics Assistant
Interactive Streamlit app powered by Cortex Analyst + Semantic View (SV_AP_ANALYTICS).
Connects to the unified AP invoices pipeline (SAP, Oracle, Baan, Workday).
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import requests
import snowflake.connector
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration — reads from ~/.snowflake/config.toml (COCO connection)
# ---------------------------------------------------------------------------
SEMANTIC_VIEW = "COCO_WORKSHOP.PIPELINE_LAB.SV_AP_ANALYTICS"
DATABASE = "COCO_WORKSHOP"
SCHEMA = "PIPELINE_LAB"
WAREHOUSE = "COCO_WORKSHOP_WH"


def _parse_toml_connection(connection_name: str = "COCO") -> dict:
    """Simple TOML parser for Snowflake config (compatible with Python 3.10)."""
    config_path = Path.home() / ".snowflake" / "config.toml"
    text = config_path.read_text()
    section_header = f"[connections.{connection_name}]"
    start = text.find(section_header)
    if start == -1:
        raise ValueError(f"Connection '{connection_name}' not found in config.toml")
    start += len(section_header)
    # Find next section or end of file
    next_section = text.find("\n[", start)
    section_text = text[start:next_section] if next_section != -1 else text[start:]
    result = {}
    for line in section_text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r'(\w+)\s*=\s*"([^"]*)"', line)
        if match:
            result[match.group(1)] = match.group(2)
    return result


_conn_cfg = _parse_toml_connection("COCO")
ACCOUNT = _conn_cfg["account"]
HOST = f"{ACCOUNT}.snowflakecomputing.com"
USER = _conn_cfg["user"]
PASSWORD = _conn_cfg.get("password", os.environ.get("SNOWFLAKE_PASSWORD", ""))
ROLE = _conn_cfg.get("role", "ACCOUNTADMIN")

SUGGESTED_QUESTIONS = [
    "What is the total AP spend by vendor?",
    "Top 10 vendors by unpaid invoice amount",
    "What is the total spend by source system?",
    "Show me overdue invoices",
    "What is the total spend by currency?",
    "How many invoices per month by business unit?",
    "Total AP spend by vendor over the last 12 months",
]


# ---------------------------------------------------------------------------
# Snowflake Connection
# ---------------------------------------------------------------------------
@st.cache_resource
def get_connection():
    """Create a cached Snowflake connection."""
    return snowflake.connector.connect(
        user=USER,
        password=PASSWORD,
        account=ACCOUNT,
        host=HOST,
        port=443,
        warehouse=WAREHOUSE,
        role=ROLE,
        database=DATABASE,
        schema=SCHEMA,
    )


def run_sql(query: str) -> pd.DataFrame:
    """Execute a SQL query and return results as a DataFrame."""
    conn = get_connection()
    try:
        return pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"SQL Error: {e}")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Cortex Analyst API
# ---------------------------------------------------------------------------
def send_message(prompt: str, messages_history: List[Dict]) -> Dict[str, Any]:
    """Call Cortex Analyst REST API with the semantic view."""
    conn = get_connection()

    # Build conversation messages for multi-turn
    api_messages = []
    for msg in messages_history:
        api_messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current user message
    api_messages.append(
        {"role": "user", "content": [{"type": "text", "text": prompt}]}
    )

    request_body = {
        "messages": api_messages,
        "semantic_view": SEMANTIC_VIEW,
    }

    resp = requests.post(
        url=f"https://{HOST}/api/v2/cortex/analyst/message",
        json=request_body,
        headers={
            "Authorization": f'Snowflake Token="{conn.rest.token}"',
            "Content-Type": "application/json",
        },
    )

    request_id = resp.headers.get("X-Snowflake-Request-Id")
    if resp.status_code < 400:
        return {**resp.json(), "request_id": request_id}
    else:
        raise Exception(
            f"Failed request (id: {request_id}) with status {resp.status_code}: {resp.text}"
        )


# ---------------------------------------------------------------------------
# UI Helpers
# ---------------------------------------------------------------------------
def display_content(content: List[Dict[str, Any]], message_index: int) -> None:
    """Display Cortex Analyst response content blocks."""
    for item in content:
        if item["type"] == "text":
            st.markdown(item["text"])
        elif item["type"] == "suggestions":
            st.markdown("**Suggested follow-ups:**")
            for idx, suggestion in enumerate(item["suggestions"]):
                if st.button(
                    suggestion,
                    key=f"suggestion_{message_index}_{idx}",
                    use_container_width=True,
                ):
                    st.session_state.active_suggestion = suggestion
        elif item["type"] == "sql":
            with st.expander("SQL Query", expanded=False):
                st.code(item["statement"], language="sql")
            with st.spinner("Running query..."):
                df = run_sql(item["statement"])
                if not df.empty:
                    st.dataframe(df, use_container_width=True)
                    # Auto-chart for multi-row results
                    if len(df) > 1 and len(df.columns) >= 2:
                        numeric_cols = df.select_dtypes(include="number").columns
                        if len(numeric_cols) > 0:
                            fig = px.bar(
                                df,
                                x=df.columns[0],
                                y=numeric_cols[0],
                                title=f"{numeric_cols[0]} by {df.columns[0]}",
                                color_discrete_sequence=["#29B5E8"],
                            )
                            fig.update_layout(
                                plot_bgcolor="rgba(0,0,0,0)",
                                paper_bgcolor="rgba(0,0,0,0)",
                            )
                            st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Page Config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AP Invoice Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# App Header & Overview
# ---------------------------------------------------------------------------
st.title("AP Invoice Analytics Assistant")
st.markdown(
    """
    This application provides an interactive analytics interface for the **unified Accounts Payable (AP) invoices pipeline**.
    It connects to data from **4 ERP systems** (SAP, Oracle, Baan, Workday) via a Snowflake 
    **Semantic View** and **Cortex Analyst** — allowing you to ask questions in plain English 
    and get instant answers with SQL and charts.
    """
)

st.divider()

# ---------------------------------------------------------------------------
# KPI Metrics & Charts
# ---------------------------------------------------------------------------
st.subheader("Pipeline Overview")

# Fetch KPI data
kpi_data = run_sql("""
    SELECT 
        COUNT(*) AS TOTAL_INVOICES,
        SUM(INVOICE_AMOUNT) AS TOTAL_AMOUNT,
        COUNT(DISTINCT VENDOR_NAME) AS VENDOR_COUNT,
        COUNT(DISTINCT SOURCE_SYSTEM) AS SOURCE_COUNT
    FROM COCO_WORKSHOP.PIPELINE_LAB.SILVER_AP_INVOICES
""")

status_data = run_sql("""
    SELECT APPROVAL_STATUS, COUNT(*) AS INVOICE_COUNT, SUM(INVOICE_AMOUNT) AS TOTAL_AMOUNT
    FROM COCO_WORKSHOP.PIPELINE_LAB.SILVER_AP_INVOICES
    GROUP BY APPROVAL_STATUS
    ORDER BY APPROVAL_STATUS
""")

source_data = run_sql("""
    SELECT SOURCE_SYSTEM, COUNT(*) AS RECORD_COUNT, SUM(INVOICE_AMOUNT) AS TOTAL_AMOUNT
    FROM COCO_WORKSHOP.PIPELINE_LAB.SILVER_AP_INVOICES
    GROUP BY SOURCE_SYSTEM
    ORDER BY SOURCE_SYSTEM
""")

# KPI Cards
if not kpi_data.empty:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Invoices", f"{int(kpi_data['TOTAL_INVOICES'].iloc[0]):,}")
    col2.metric(
        "Total Invoice Amount",
        f"${kpi_data['TOTAL_AMOUNT'].iloc[0]:,.2f}",
    )
    col3.metric("Unique Vendors", f"{int(kpi_data['VENDOR_COUNT'].iloc[0]):,}")
    col4.metric("Source Systems", f"{int(kpi_data['SOURCE_COUNT'].iloc[0])}")

# Charts row
chart_col1, chart_col2, chart_col3 = st.columns(3)

with chart_col1:
    if not source_data.empty:
        fig_count = px.bar(
            source_data,
            x="SOURCE_SYSTEM",
            y="RECORD_COUNT",
            title="Record Count by Source System",
            color="SOURCE_SYSTEM",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_count.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_count, use_container_width=True)

with chart_col2:
    if not source_data.empty:
        fig_amount = px.bar(
            source_data,
            x="SOURCE_SYSTEM",
            y="TOTAL_AMOUNT",
            title="Invoice Amount by Source System",
            color="SOURCE_SYSTEM",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_amount.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_amount, use_container_width=True)

with chart_col3:
    if not status_data.empty:
        fig_status = px.pie(
            status_data,
            values="INVOICE_COUNT",
            names="APPROVAL_STATUS",
            title="Approval Status Distribution",
            color_discrete_sequence=["#29B5E8", "#FF6B6B"],
            hole=0.4,
        )
        fig_status.update_layout(plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_status, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# AI Chat Section
# ---------------------------------------------------------------------------
st.subheader("Ask a Question")
st.markdown(
    "Type a question in plain English below, or click one of the suggested questions to get started."
)

# Suggested questions as clickable buttons
st.markdown("**Suggested Questions:**")
suggestion_cols = st.columns(4)
for idx, question in enumerate(SUGGESTED_QUESTIONS[:4]):
    with suggestion_cols[idx]:
        if st.button(question, key=f"top_suggestion_{idx}", use_container_width=True):
            st.session_state.active_suggestion = question

# Second row of suggestions
if len(SUGGESTED_QUESTIONS) > 4:
    suggestion_cols2 = st.columns(3)
    for idx, question in enumerate(SUGGESTED_QUESTIONS[4:]):
        with suggestion_cols2[idx]:
            if st.button(
                question, key=f"top_suggestion_{idx + 4}", use_container_width=True
            ):
                st.session_state.active_suggestion = question

st.divider()

# ---------------------------------------------------------------------------
# Chat History & Input
# ---------------------------------------------------------------------------
# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "active_suggestion" not in st.session_state:
    st.session_state.active_suggestion = None

# Display conversation history
for msg_idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["content"][0]["text"])
        else:
            display_content(content=message["content"], message_index=msg_idx)


def process_question(prompt: str) -> None:
    """Send a question to Cortex Analyst and display the response."""
    # Add user message to history
    user_msg = {"role": "user", "content": [{"type": "text", "text": prompt}]}
    st.session_state.messages.append(user_msg)

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = send_message(
                    prompt=prompt, messages_history=st.session_state.messages[:-1]
                )
                content = response["message"]["content"]
                display_content(
                    content=content, message_index=len(st.session_state.messages)
                )
                st.session_state.messages.append(
                    {"role": "analyst", "content": content}
                )
            except Exception as e:
                error_msg = f"Error communicating with Cortex Analyst: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append(
                    {
                        "role": "analyst",
                        "content": [{"type": "text", "text": error_msg}],
                    }
                )


# Chat input
if user_input := st.chat_input("Ask a question about AP invoices..."):
    process_question(user_input)

# Handle suggestion button clicks
if st.session_state.active_suggestion:
    process_question(st.session_state.active_suggestion)
    st.session_state.active_suggestion = None
    st.rerun()
