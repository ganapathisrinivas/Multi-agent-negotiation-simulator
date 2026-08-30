function renderMetrics(data) {
    return `
        <div class="metrics">
            <p>Round: ${data.round} / ${data.max_rounds}</p>
            <p>Status: ${data.status}</p>
            <p>Current Offer: ${data.current_offer}</p>
            <p>Your Offer: ${data.last_human_offer}</p>
            <p>AI Offer: ${data.last_ai_offer}</p>
            <p>Agreed Price: ${data.agreed_price}</p>
        </div>
    `;
}

export { renderMetrics };
