"""
Render Mermaid diagrams to PNG images for the workshop presentation.

Usage:
    pip install playwright
    python -m playwright install chromium
    python render_diagrams.py

Output: docs/images/*.png
"""
import asyncio
import os
from playwright.async_api import async_playwright

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "images")

# Each diagram: (filename, mermaid_code, width, height)
DIAGRAMS = [
    (
        "coco_overview.png",
        """graph LR
    CLI["Cortex Code CLI<br/><i>Terminal / IDE</i>"]:::entry
    SS["Cortex Code<br/><i>Snowsight</i>"]:::entry
    AGENT["CoCo AI Agent<br/><i>Plans, Writes, Executes</i>"]:::core
    SF["Snowflake<br/><i>Your Data + Compute</i>"]:::sf
    RBAC["RBAC<br/><i>Your Identity</i>"]:::sf

    CLI --> AGENT
    SS --> AGENT
    AGENT --> SF
    AGENT --> RBAC

    classDef entry fill:#29B5E8,stroke:#1B7FA3,color:#fff
    classDef core fill:#2ecc71,stroke:#27ae60,color:#fff
    classDef sf fill:#9b59b6,stroke:#8e44ad,color:#fff""",
        1200, 400,
    ),
    (
        "workshop_flow.png",
        """graph LR
    D1["Demo 1<br/><b>Pipeline Builder</b><br/>Create Dynamic Table"]:::d1
    D2["Demo 2<br/><b>Pipeline Maintenance</b><br/>Onboard from PRD"]:::d2
    D3["Demo 3<br/><b>Cortex Agent</b><br/>NL Analytics"]:::d3

    D1 -->|"evolve"| D2
    D2 -->|"consume"| D3

    classDef d1 fill:#e67e22,stroke:#d35400,color:#fff
    classDef d2 fill:#3498db,stroke:#2980b9,color:#fff
    classDef d3 fill:#2ecc71,stroke:#27ae60,color:#fff""",
        1200, 350,
    ),
    (
        "demo1_flow.png",
        """graph LR
    SAP[("SAP<br/>15 invoices")]:::bronze
    ORA[("Oracle<br/>15 invoices")]:::bronze
    DISC["Data Discovery<br/><i>CoCo profiles tables</i>"]:::step
    PLAN["Plan Mode<br/><i>Review before execute</i>"]:::step
    DT[["SILVER_AP_INVOICES<br/><i>Dynamic Table</i>"]]:::silver

    SAP --> DISC
    ORA --> DISC
    DISC --> PLAN
    PLAN --> DT

    classDef bronze fill:#e67e22,stroke:#d35400,color:#fff
    classDef step fill:#34495e,stroke:#2c3e50,color:#fff
    classDef silver fill:#3498db,stroke:#2980b9,color:#fff""",
        1200, 400,
    ),
    (
        "demo2_flow.png",
        """graph LR
    PRD["PRD Files<br/><i>3 CSVs</i>"]:::input
    GAP["Gap Analysis<br/><i>Auto-detected</i>"]:::step
    OQ["Open Questions<br/><i>Surfaced for review</i>"]:::step
    DDL["DDL Generated<br/><i>4-source DT</i>"]:::output
    VAL["Validation<br/><i>5 proof queries</i>"]:::output

    PRD --> GAP --> OQ --> DDL --> VAL

    classDef input fill:#e67e22,stroke:#d35400,color:#fff
    classDef step fill:#9b59b6,stroke:#8e44ad,color:#fff
    classDef output fill:#2ecc71,stroke:#27ae60,color:#fff""",
        1300, 350,
    ),
    (
        "demo3_flow.png",
        """graph LR
    USER["Business User<br/><i>'Top vendors by spend?'</i>"]:::user
    AGENT["Cortex Agent<br/><i>AP Analytics Assistant</i>"]:::agent
    SV{{"Semantic View<br/><i>7 metrics, 7 VQRs</i>"}}:::sv
    SQL["SQL Generated<br/><i>Cortex Analyst</i>"]:::step
    RESULT["Answer + Chart<br/><i>Structured results</i>"]:::output

    USER --> AGENT --> SV --> SQL --> RESULT

    classDef user fill:#34495e,stroke:#2c3e50,color:#fff
    classDef agent fill:#2ecc71,stroke:#27ae60,color:#fff
    classDef sv fill:#9b59b6,stroke:#8e44ad,color:#fff
    classDef step fill:#3498db,stroke:#2980b9,color:#fff
    classDef output fill:#e67e22,stroke:#d35400,color:#fff""",
        1300, 350,
    ),
    (
        "cost_flow.png",
        """graph LR
    PROMPT["Your Prompt<br/><i>Input tokens</i>"]:::input
    MODEL["AI Model<br/><i>Inference</i>"]:::core
    RESP["Response<br/><i>Output tokens</i>"]:::output
    CREDITS["Credits Charged<br/><i>Per million tokens</i>"]:::billing
    WH["Warehouse<br/><i>SQL execution</i>"]:::separate

    PROMPT --> MODEL --> RESP --> CREDITS
    MODEL -.->|"executes SQL"| WH

    classDef input fill:#3498db,stroke:#2980b9,color:#fff
    classDef core fill:#2ecc71,stroke:#27ae60,color:#fff
    classDef output fill:#9b59b6,stroke:#8e44ad,color:#fff
    classDef billing fill:#e67e22,stroke:#d35400,color:#fff
    classDef separate fill:#34495e,stroke:#2c3e50,color:#fff""",
        1200, 400,
    ),
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
  <style>
    body {{ margin: 0; padding: 40px; background: #1B2A4A; display: flex; justify-content: center; align-items: center; min-height: calc(100vh - 80px); }}
    .mermaid {{ display: flex; justify-content: center; }}
  </style>
</head>
<body>
  <div class="mermaid">
    {mermaid_code}
  </div>
  <script>mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});</script>
</body>
</html>"""


async def render_all():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()

        for filename, mermaid_code, width, height in DIAGRAMS:
            output_path = os.path.join(OUTPUT_DIR, filename)
            html_content = HTML_TEMPLATE.format(mermaid_code=mermaid_code)

            # Write temp HTML
            temp_html = os.path.join(OUTPUT_DIR, "_temp_diagram.html")
            with open(temp_html, "w", encoding="utf-8") as f:
                f.write(html_content)

            page = await browser.new_page(viewport={"width": width, "height": height})
            await page.goto(f"file:///{temp_html.replace(os.sep, '/')}")
            await page.wait_for_timeout(2500)
            await page.screenshot(path=output_path)
            await page.close()

            print(f"  Rendered: {filename} ({width}x{height})")

        # Cleanup temp file
        if os.path.exists(temp_html):
            os.remove(temp_html)

        await browser.close()

    print(f"\nAll diagrams saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(render_all())
