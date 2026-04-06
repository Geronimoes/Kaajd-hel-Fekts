import re

with open("app/templates/dashboard.html", "r") as f:
    content = f.read()

# Requirement 2: Add "Download Full Report" button
btn_html = """                <a href="{{ url_for('main.export_results', analysis_id=analysis_id) }}" class="btn btn-primary" title="Download ZIP with all CSV, JSON, and graphs">Download Full Report (ZIP)</a>
            </div>"""
content = re.sub(
    r'</div>\s*</div>\s*<div class="tab-pane fade" id="tab-activity"',
    btn_html
    + '\n        </div>\n\n        <div class="tab-pane fade" id="tab-activity"',
    content,
)

# Requirement 4: Improve mobile Plotly UX
# Add dragmode: false and fixedrange: isMobile()
plot_config_repl = """    const isMobile = () => window.matchMedia("(max-width: 768px)").matches;
    const plotConfig = {
        responsive: true,
        displaylogo: false,
        modeBarButtonsToRemove: ["select2d", "lasso2d", "autoScale2d", "zoom2d", "pan2d"],
        scrollZoom: false
    };
    const baseLayout = (title, extra = {}) => ({
        title,
        dragmode: false,
        margin: { t: 52, l: 46, r: 16, b: isMobile() ? 72 : 52 },
        legend: {
            orientation: isMobile() ? "h" : "v",
            y: isMobile() ? -0.3 : 1,
            x: isMobile() ? 0 : 1
        },
        hovermode: "closest",
        xaxis: { fixedrange: isMobile() },
        yaxis: { fixedrange: isMobile() },
        ...extra,
        // Ensure deep merge of xaxis/yaxis if extra provides them
        xaxis: { fixedrange: isMobile(), ...extra.xaxis },
        yaxis: { fixedrange: isMobile(), ...extra.yaxis }
    });"""

content = re.sub(
    r"const isMobile = \(\) => window\.matchMedia.*?const baseLayout = .*?\.\.\.extra\s*\}\);",
    plot_config_repl,
    content,
    flags=re.DOTALL,
)

with open("app/templates/dashboard.html", "w") as f:
    f.write(content)
