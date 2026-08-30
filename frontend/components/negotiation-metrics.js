function formatCurrency(value) {

    if (value === null || value === undefined) {
        return "—";
    }

    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0
    }).format(value);
}


function renderMetrics(data) {

    const status = data.status || "unknown";

    return `
        <div class="negotiation-metrics">

            <div class="metric-card">
                <span class="metric-label">Round</span>
                <strong>
                    ${data.round} / ${data.max_rounds}
                </strong>
            </div>


            <div class="metric-card">
                <span class="metric-label">Status</span>
                <strong class="status-${status}">
                    ${status.toUpperCase()}
                </strong>
            </div>


            <div class="metric-card">
                <span class="metric-label">Current Offer</span>
                <strong>
                    ${formatCurrency(data.current_offer)}
                </strong>
            </div>


            <div class="metric-card">
                <span class="metric-label">Your Offer</span>
                <strong>
                    ${formatCurrency(data.last_human_offer)}
                </strong>
            </div>


            <div class="metric-card">
                <span class="metric-label">AI Offer</span>
                <strong>
                    ${formatCurrency(data.last_ai_offer)}
                </strong>
            </div>


            <div class="metric-card">
                <span class="metric-label">Agreed Price</span>
                <strong>
                    ${formatCurrency(data.agreed_price)}
                </strong>
            </div>


            ${
                status === "deadlocked"
                    ? `
                        <div class="deadlock-message">
                            <strong>Deadlock Reason</strong>
                            <p>
                                ${data.deadlock_reason || "Negotiation reached a deadlock."}
                            </p>
                        </div>
                    `
                    : ""
            }

        </div>
    `;
}


export {
    renderMetrics,
    formatCurrency
};
