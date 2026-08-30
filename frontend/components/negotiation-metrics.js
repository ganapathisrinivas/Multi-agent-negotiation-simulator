const API_BASE_URL = "http://localhost:8000";


// Start a Human vs AI negotiation
async function startNegotiation({
    scenario = 2,
    propertyIndex = 0,
    humanRole = "buyer",
    aiPersonality = "collaborative",
    maxRounds = 10
} = {}) {

    const response = await fetch(
        `${API_BASE_URL}/negotiations/practice`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                scenario,
                property_index: propertyIndex,
                human_role: humanRole,
                ai_personality: aiPersonality,
                max_rounds: maxRounds
            })
        }
    );

    if (!response.ok) {
        throw new Error(
            `Failed to start negotiation: ${response.status}`
        );
    }

    return await response.json();
}


// Get current negotiation state
async function getNegotiationState(negotiationId) {

    const response = await fetch(
        `${API_BASE_URL}/negotiations/${negotiationId}`
    );

    if (!response.ok) {
        throw new Error(
            `Failed to get negotiation state: ${response.status}`
        );
    }

    return await response.json();
}


// Send human message / offer
async function sendOffer(
    negotiationId,
    message,
    offer = null
) {

    const response = await fetch(
        `${API_BASE_URL}/negotiations/${negotiationId}/message`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message,
                offer
            })
        }
    );

    if (!response.ok) {
        throw new Error(
            `Failed to send offer: ${response.status}`
        );
    }

    return await response.json();
}


// Get negotiation history
async function getNegotiationHistory(negotiationId) {

    const response = await fetch(
        `${API_BASE_URL}/negotiations/${negotiationId}/history`
    );

    if (!response.ok) {
        throw new Error(
            `Failed to get negotiation history: ${response.status}`
        );
    }

    return await response.json();
}


// Cancel negotiation
async function cancelNegotiation(negotiationId) {

    const response = await fetch(
        `${API_BASE_URL}/negotiations/${negotiationId}/cancel`,
        {
            method: "POST"
        }
    );

    if (!response.ok) {
        throw new Error(
            `Failed to cancel negotiation: ${response.status}`
        );
    }

    return await response.json();
}


export {
    startNegotiation,
    getNegotiationState,
    sendOffer,
    getNegotiationHistory,
    cancelNegotiation
};
