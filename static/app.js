let rawDeals = [];
let displayedDeals = [];
let chartInstance = null;
let currentSortColumn = "signing_date";
let currentSortAsc = false;
let activeDrillKey = null;

document.addEventListener("DOMContentLoaded", () => {
    initDashboard();
});

async function initDashboard() {
    await Promise.all([
        loadForecastData(),
        loadReconciliation(),
        loadQualityFindings(),
        loadChanges()
    ]);
}

async function loadForecastData() {
    const country = document.getElementById("filterCountry").value;
    const clientSubType = document.getElementById("filterClientSubType").value;
    const signingCategory = document.getElementById("filterSigningCat").value;
    const ut15 = document.getElementById("filterUt15").value;
    const groupBy = document.getElementById("filterGroupBy").value;

    const params = new URLSearchParams({
        country,
        client_sub_type: clientSubType,
        signing_category: signingCategory,
        ut_level_15: ut15,
        group_by: groupBy
    });

    try {
        const res = await fetch(`/forecast?${params.toString()}`);
        if (!res.ok) throw new Error("Failed to load forecast data");
        const data = await res.json();

        // 1. Update KPIs
        document.getElementById("kpiTotalAcv").textContent = formatCurrency(data.summary.grand_total_acv);
        document.getElementById("kpiDealCount").textContent = data.summary.deal_count.toLocaleString();
        document.getElementById("kpiAvgDealSize").textContent = formatCurrency(data.summary.avg_deal_size);

        // 2. Render Chart
        renderChart(data.grouped_data, groupBy);

        // 3. Render Table
        rawDeals = data.deals || [];
        applyDealFiltersAndRender();

    } catch (err) {
        console.error("Error loading forecast:", err);
    }
}

async function loadReconciliation() {
    const badge = document.getElementById("reconBadge");
    const badgeText = document.getElementById("reconBadgeText");
    const summaryBox = document.getElementById("reconSummaryBox");
    const detailsBody = document.getElementById("reconDetailsBody");

    try {
        const [recRes, detRes] = await Promise.all([
            fetch("/reconciliation"),
            fetch("/reconciliation/details")
        ]);

        const recData = await recRes.json();
        const detData = await detRes.json();

        // Update badge
        badge.className = "status-badge";
        if (recData.status === "MATCH") {
            badge.classList.add("badge-success");
            badgeText.textContent = `Sales Cloud: MATCH`;
        } else if (recData.status === "UNAVAILABLE") {
            badge.classList.add("badge-warning");
            badgeText.textContent = `Sales Cloud: Not Verified`;
        } else {
            badge.classList.add("badge-danger");
            badgeText.textContent = `Sales Cloud: ${recData.report_label} (${recData.affected_orders_count} Variances)`;
        }

        // Summary Box
        summaryBox.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                <div><strong>Status:</strong> ${recData.status} (Report Label: <span class="badge-dot" style="display:inline-block;"></span> <strong>${recData.report_label}</strong>)</div>
                <div><strong>Forecast Total:</strong> ${formatCurrency(recData.forecast_total_usd)}</div>
                <div><strong>Sales Cloud SoR Total:</strong> ${formatCurrency(recData.sales_cloud_total_usd)}</div>
                <div><strong>Net Variance:</strong> ${formatCurrency(recData.variance_usd)}</div>
                <div><strong>Affected Deals:</strong> ${recData.affected_orders_count}</div>
            </div>
        `;

        // Details Table
        if (detData.variances && detData.variances.length > 0) {
            detailsBody.innerHTML = detData.variances.map(v => `
                <tr>
                    <td><code>${escapeHtml(v.sales_order_num)}</code></td>
                    <td>${escapeHtml(v.customer_name || "")}</td>
                    <td>${v.forecast_acv !== null ? formatCurrency(v.forecast_acv) : "<span class='text-muted'>—</span>"}</td>
                    <td>${v.sales_cloud_acv !== null ? formatCurrency(v.sales_cloud_acv) : "<span class='text-muted'>—</span>"}</td>
                    <td><span class="status-badge ${v.variance_type === 'ATTRIBUTE_MISMATCH' ? 'badge-warning' : 'badge-danger'}">${v.variance_type}</span></td>
                    <td>${escapeHtml(v.details)}</td>
                </tr>
            `).join("");
        } else {
            detailsBody.innerHTML = `<tr><td colspan="6" class="text-center" style="color: #42be65;">✓ All forecast records match Sales Cloud System of Record.</td></tr>`;
        }

    } catch (err) {
        console.error("Error loading reconciliation:", err);
    }
}

async function loadQualityFindings() {
    const badge = document.getElementById("qualityBadge");
    const badgeText = document.getElementById("qualityBadgeText");
    const box = document.getElementById("qualitySummaryBox");

    try {
        const res = await fetch("/quality");
        const data = await res.json();

        badge.className = "status-badge";
        if (data.status === "PASS") {
            badge.classList.add("badge-success");
            badgeText.textContent = "Data Quality: PASS";
        } else {
            badge.classList.add("badge-warning");
            badgeText.textContent = `Quality: WARNING (${data.duplicates_count + data.missing_coverage_id_count + data.invalid_acv_count} issues)`;
        }

        box.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                <div style="display: flex; gap: 1.5rem; flex-wrap: wrap;">
                    <div><strong>Duplicate Orders:</strong> ${data.duplicates_count} (${data.duplicate_orders.join(", ") || "None"})</div>
                    <div><strong>Missing Coverage IDs:</strong> ${data.missing_coverage_id_count}</div>
                    <div><strong>Zero / Negative ACV:</strong> ${data.invalid_acv_count}</div>
                    <div><strong>DoD Total Swing:</strong> ${data.dod_swing_pct}% ${data.swing_flagged ? "<span style='color:#f1c21b;'>(Flagged)</span>" : ""}</div>
                </div>
                ${data.issues.length > 0 ? `
                    <div style="background: rgba(241,194,27,0.1); border-left: 3px solid #f1c21b; padding: 0.5rem 0.75rem;">
                        <strong>Audit Alerts:</strong>
                        <ul style="margin-left: 1.25rem; margin-top: 0.25rem;">
                            ${data.issues.map(i => `<li>${escapeHtml(i)}</li>`).join("")}
                        </ul>
                    </div>
                ` : `<p style="color: #42be65;">✓ All 4 automated quality checks passed cleanly.</p>`}
            </div>
        `;

    } catch (err) {
        console.error("Error loading quality findings:", err);
    }
}

async function loadChanges() {
    const deltaEl = document.getElementById("kpiDodDelta");
    const pctEl = document.getElementById("kpiDodPct");
    const box = document.getElementById("changesSummaryBox");

    try {
        const res = await fetch("/changes?since=yesterday");
        const data = await res.json();

        const sign = data.net_acv_change >= 0 ? "+" : "";
        deltaEl.textContent = `${sign}${formatCurrency(data.net_acv_change)}`;
        pctEl.textContent = `${sign}${data.pct_change}% vs. Yesterday`;

        box.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem;">
                <div>
                    <h3 style="font-size: 0.9rem; margin-bottom: 0.5rem; color: #42be65;">+ Newly Added Deals (${data.added_deals.length})</h3>
                    <ul style="font-size: 0.8rem; line-height: 1.6; max-height: 180px; overflow-y: auto;">
                        ${data.added_deals.length > 0 ? data.added_deals.map(d => `<li><code>${d.sales_order_num}</code>: ${d.customer_name} (${formatCurrency(d.acv)})</li>`).join("") : "<li>None</li>"}
                    </ul>
                </div>
                <div>
                    <h3 style="font-size: 0.9rem; margin-bottom: 0.5rem; color: #ff8389;">- Removed Deals (${data.removed_deals.length})</h3>
                    <ul style="font-size: 0.8rem; line-height: 1.6; max-height: 180px; overflow-y: auto;">
                        ${data.removed_deals.length > 0 ? data.removed_deals.map(d => `<li><code>${d.sales_order_num}</code>: ${d.customer_name} (${formatCurrency(d.acv)})</li>`).join("") : "<li>None</li>"}
                    </ul>
                </div>
                <div>
                    <h3 style="font-size: 0.9rem; margin-bottom: 0.5rem; color: #78a9ff;">Δ ACV Modified Deals (${data.modified_deals.length})</h3>
                    <ul style="font-size: 0.8rem; line-height: 1.6; max-height: 180px; overflow-y: auto;">
                        ${data.modified_deals.length > 0 ? data.modified_deals.map(d => `<li><code>${d.sales_order_num}</code>: ${formatCurrency(d.yesterday_acv)} → ${formatCurrency(d.today_acv)} (Δ ${formatCurrency(d.delta)})</li>`).join("") : "<li>None</li>"}
                    </ul>
                </div>
            </div>
        `;

    } catch (err) {
        console.error("Error loading changes:", err);
    }
}

function renderChart(groupedData, groupBy) {
    const ctx = document.getElementById("forecastChart").getContext("2d");
    if (chartInstance) {
        chartInstance.destroy();
    }

    const labels = groupedData.map(d => d.group_key);
    const values = groupedData.map(d => d.total_acv);

    chartInstance = new Chart(ctx, {
        type: groupBy === "ut_level_30" ? "bar" : "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "New Signings ACV ($)",
                data: values,
                backgroundColor: "#0f62fe",
                hoverBackgroundColor: "#78a9ff",
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => ` ACV: ${formatCurrency(ctx.raw)}`
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: "#27344d" },
                    ticks: { color: "#9aa7bd", font: { size: 11 } }
                },
                y: {
                    grid: { color: "#27344d" },
                    ticks: {
                        color: "#9aa7bd",
                        callback: (val) => "$" + (val >= 1e6 ? (val / 1e6).toFixed(1) + "M" : (val / 1e3).toFixed(0) + "k")
                    }
                }
            },
            onClick: (evt, elements) => {
                if (elements.length > 0) {
                    const idx = elements[0].index;
                    const clickedKey = labels[idx];
                    drillDownToKey(clickedKey, groupBy);
                }
            }
        }
    });
}

function drillDownToKey(key, groupBy) {
    activeDrillKey = { key, groupBy };
    document.getElementById("activeDrillFilter").style.display = "flex";
    document.getElementById("drillFilterText").textContent = `Drill-down: ${key}`;
    applyDealFiltersAndRender();
}

function clearDrillDown() {
    activeDrillKey = null;
    document.getElementById("activeDrillFilter").style.display = "none";
    applyDealFiltersAndRender();
}

function applyDealFiltersAndRender() {
    let filtered = [...rawDeals];

    // Apply active drill-down filter
    if (activeDrillKey) {
        if (activeDrillKey.groupBy === "ut_level_30") {
            filtered = filtered.filter(d => d.ut_level_30_dscr === activeDrillKey.key);
        } else if (activeDrillKey.groupBy === "day") {
            filtered = filtered.filter(d => d.signing_date === activeDrillKey.key);
        }
    }

    // Apply table search input
    const term = (document.getElementById("dealSearchInput").value || "").toLowerCase().trim();
    if (term) {
        filtered = filtered.filter(d =>
            (d.sales_order_num || "").toLowerCase().includes(term) ||
            (d.customer_name || "").toLowerCase().includes(term) ||
            (d.ut_level_30_dscr || "").toLowerCase().includes(term) ||
            (d.coverage_id || "").toLowerCase().includes(term)
        );
    }

    // Apply sorting
    filtered.sort((a, b) => {
        let va = a[currentSortColumn];
        let vb = b[currentSortColumn];
        if (typeof va === "number" && typeof vb === "number") {
            return currentSortAsc ? va - vb : vb - va;
        }
        va = (va || "").toString();
        vb = (vb || "").toString();
        return currentSortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
    });

    displayedDeals = filtered;
    renderDealsTable();
}

function renderDealsTable() {
    const tbody = document.getElementById("dealsTableBody");
    const countBadge = document.getElementById("tableCountBadge");
    countBadge.textContent = `Showing ${displayedDeals.length.toLocaleString()} deals`;

    if (displayedDeals.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">No deals match the selected criteria.</td></tr>`;
        return;
    }

    tbody.innerHTML = displayedDeals.map(d => `
        <tr>
            <td><code>${escapeHtml(d.sales_order_num || "")}</code></td>
            <td>${escapeHtml(d.signing_date || "")}</td>
            <td>${escapeHtml(d.customer_name || "")}</td>
            <td>${escapeHtml(d.ut_level_30_dscr || "")}</td>
            <td>${escapeHtml(d.coverage_id || "—")}</td>
            <td class="text-right" style="font-weight: 600;">${formatCurrency(d.saas_acv_usd_at_plan)}</td>
        </tr>
    `).join("");
}

function handleDealSearch() {
    applyDealFiltersAndRender();
}

function sortDeals(column) {
    if (currentSortColumn === column) {
        currentSortAsc = !currentSortAsc;
    } else {
        currentSortColumn = column;
        currentSortAsc = true;
    }
    applyDealFiltersAndRender();
}

function applyFilters() {
    clearDrillDown();
    loadForecastData();
}

function resetFilters() {
    document.getElementById("filterCountry").value = "United States";
    document.getElementById("filterClientSubType").value = "Select T Activate";
    document.getElementById("filterSigningCat").value = "New Signings";
    document.getElementById("filterUt15").value = "Data Platform";
    document.getElementById("filterGroupBy").value = "day";
    applyFilters();
}

function switchTab(tabId) {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
    event.target.classList.add("active");
    document.getElementById(tabId).classList.add("active");
}

function exportData(format) {
    const country = document.getElementById("filterCountry").value;
    const clientSubType = document.getElementById("filterClientSubType").value;
    const signingCategory = document.getElementById("filterSigningCat").value;
    const ut15 = document.getElementById("filterUt15").value;

    const params = new URLSearchParams({
        format: format,
        country,
        client_sub_type: clientSubType,
        signing_category: signingCategory,
        ut_level_15: ut15
    });

    window.location.href = `/forecast/export?${params.toString()}`;
}

function formatCurrency(val) {
    const num = parseFloat(val) || 0;
    return num.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
