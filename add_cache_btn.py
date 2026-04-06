import re

with open("app/templates/dashboard.html", "r") as f:
    content = f.read()

# Add clear cache button
buttons_html = """    <div class="d-flex gap-2">
        <button id="clearCacheBtn" class="btn btn-outline-danger" title="Delete this chat from the database to force re-parsing next time">Delete Analysis Cache</button>
        <a href="{{ url_for('main.upload_file') }}" class="btn btn-outline-secondary">Analyze another chat</a>
    </div>"""

content = re.sub(
    r'<a href="\{\{ url_for\(\'main.upload_file\'\) \}\}" class="btn btn-outline-secondary">Analyze another chat</a>',
    buttons_html,
    content,
)

# Add event listener for clearCacheBtn
clear_cache_js = """    const clearCacheBtn = document.getElementById("clearCacheBtn");
    if (clearCacheBtn) {
        clearCacheBtn.addEventListener("click", () => {
            if (!confirm("Are you sure you want to delete this analysis? You will need to upload the text file again to view these graphs.")) {
                return;
            }
            clearCacheBtn.disabled = true;
            clearCacheBtn.textContent = "Deleting...";
            fetch(`/api/chat/${chatId}/delete`, { method: "POST" })
                .then((res) => res.json())
                .then((data) => {
                    if (data.success) {
                        alert("Chat analysis deleted successfully.");
                        window.location.href = "/";
                    } else {
                        alert("Failed to delete chat.");
                        clearCacheBtn.disabled = false;
                        clearCacheBtn.textContent = "Delete Analysis Cache";
                    }
                })
                .catch(() => {
                    alert("Network error.");
                    clearCacheBtn.disabled = false;
                    clearCacheBtn.textContent = "Delete Analysis Cache";
                });
        });
    }

    const applyBtn = document.getElementById("applyFilters");"""

content = content.replace(
    '    const applyBtn = document.getElementById("applyFilters");', clear_cache_js
)

# Add descriptions to charts
content = content.replace(
    '<div id="responseHeatmap" class="chart-box mt-3"></div>',
    '<div id="responseHeatmap" class="chart-box mt-3"></div>\n            <p class="text-muted small mt-1">Average time elapsed between a message and the first reply by another person.</p>',
)
content = content.replace(
    '<div id="conversationStarters" class="chart-box mt-3"></div>',
    '<div id="conversationStarters" class="chart-box mt-3"></div>\n            <p class="text-muted small mt-1">Counts messages that were sent after a gap of at least 1 hour of silence.</p>',
)
content = content.replace(
    '<div id="affinityHeatmap" class="chart-box"></div>',
    '<div id="affinityHeatmap" class="chart-box"></div>\n            <p class="text-muted small mt-1">Affinity measures how often person A replies to person B relative to their overall reply rate.</p>',
)
content = content.replace(
    '<div id="correlationHeatmap" class="chart-box mt-3"></div>',
    '<div id="correlationHeatmap" class="chart-box mt-3"></div>\n            <p class="text-muted small mt-1">Pearson correlation of daily message counts between pairs of people.</p>',
)
content = content.replace(
    '<div id="topicsHeatmap" class="chart-box"></div>',
    '<div id="topicsHeatmap" class="chart-box"></div>\n            <p class="text-muted small mt-1">Extracted using TF-IDF and Non-Negative Matrix Factorization (NMF) to find underlying word clusters.</p>',
)


with open("app/templates/dashboard.html", "w") as f:
    f.write(content)
