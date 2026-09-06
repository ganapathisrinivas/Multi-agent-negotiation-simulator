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


function formatStatus(status) {
    if (!status) {
        return "UNKNOWN";
    }

    return status
        .replace("_", " ")
        .toUpperCase();
}


function renderMetrics(data) {
    if (!data) {
        return `
            <div class="negotiation-metrics">
                <p>No negotiation data available.</p>
            </div>
        `;
    }

    return `
        <div class="negotiation-metrics">

            <div class="metric-card">
                <span class="metric-label">
                    Round
                </span>

                <span class="metric-value">
                    ${data.round} / ${data.max_rounds}
                </span>
            </div>


            <div class="metric-card">
                <span class="metric-label">
                    Status
                </span>

                <span class="metric-value">
                    ${formatStatus(data.status)}
                </span>
            </div>


            <div class="metric-card">
                <span class="metric-label">
                    Current Offer
                </span>

                <span class="metric-value">
                    ${formatCurrency(data.current_offer)}
                </span>
            </div>


            <div class="metric-card">
                <span class="metric-label">
                    Your Offer
                </span>

                <span class="metric-value">
                    ${formatCurrency(data.last_human_offer)}
                </span>
            </div>


            <div class="metric-card">
                <span class="metric-label">
                    AI Offer
                </span>

                <span class="metric-value">
                    ${formatCurrency(data.last_ai_offer)}
                </span>
            </div>


            <div class="metric-card">
                <span class="metric-label">
                    Agreed Price
                </span>

                <span class="metric-value">
                    ${formatCurrency(data.agreed_price)}
                </span>
            </div>


            ${
                data.status === "deadlocked"
                    ? `
                        <div class="deadlock-message">
                            <strong>Deadlock Reason</strong>

                            <p>
                                ${
                                    data.deadlock_reason ||
                                    "Negotiation reached a deadlock."
                                }
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
    formatCurrency,
    formatStatus
};
