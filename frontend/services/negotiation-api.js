const API_BASE = "http://localhost:8000";

async function getNegotiation(id) {
    const response = await fetch(
        `${API_BASE}/negotiations/${id}`
    );

    return await response.json();
}

async function sendOffer(id, message, offer) {
    const response = await fetch(
        `${API_BASE}/negotiations/${id}/message`,
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

    return await response.json();
}

export {
    getNegotiation,
    sendOffer
};
