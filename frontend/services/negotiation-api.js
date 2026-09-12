const API_BASE_URL =
    "http://127.0.0.1:8000";


/* =========================================================
   COMMON REQUEST FUNCTION
========================================================= */

async function requestJson(
    url,
    options = {}
) {

    const response =
        await fetch(
            url,
            options
        );


    const text =
        await response.text();


    let data = {};


    try {

        data =
            text
                ? JSON.parse(text)
                : {};

    } catch {

        throw new Error(
            `Backend returned invalid data (${response.status}).`
        );

    }


    if (!response.ok) {

        throw new Error(

            data.detail ||

            data.message ||

            `Request failed: ${response.status}`

        );

    }


    return data;
}


/* =========================================================
   GET SCENARIOS
========================================================= */

async function getScenarios() {

    return requestJson(
        `${API_BASE_URL}/scenarios`
    );

}


/* =========================================================
   GET PERSONALITIES
========================================================= */

async function getPersonalities() {

    return requestJson(
        `${API_BASE_URL}/personalities`
    );

}


/* =========================================================
   GET PROPERTIES
========================================================= */

async function getProperties(
    scenario,
    start = 0,
    limit = 100
) {

    return requestJson(

        `${API_BASE_URL}/properties?scenario=${scenario}&start=${start}&limit=${limit}`

    );

}


/* =========================================================
   START HUMAN VS AI NEGOTIATION
========================================================= */

async function startNegotiation(
    options = {}
) {

    const {

        scenario = 2,

        propertyIndex = 0,

        humanRole = "buyer",

        aiPersonality =
            "collaborative",

        maxRounds = 10,

    } = options;


    return requestJson(

        `${API_BASE_URL}/negotiations/practice`,

        {

            method:
                "POST",

            headers: {

                "Content-Type":
                    "application/json",

            },

            body:
                JSON.stringify({

                    scenario:
                        Number(scenario),

                    property_index:
                        Number(propertyIndex),

                    human_role:
                        humanRole,

                    ai_personality:
                        aiPersonality,

                    max_rounds:
                        Number(maxRounds),

                }),

        }

    );

}


/* =========================================================
   START AI VS AI SIMULATION
========================================================= */

async function startAiVsAi(
    options = {}
) {

    const {

        scenario = 2,

        propertyIndex = 0,

        buyerPersonality = 2,

        sellerPersonality = 2,

        maxRounds = 10,

    } = options;


    return requestJson(

        `${API_BASE_URL}/negotiations`,

        {

            method:
                "POST",

            headers: {

                "Content-Type":
                    "application/json",

            },

            body:
                JSON.stringify({

                    scenario:
                        Number(scenario),

                    buyer_personality:
                        Number(buyerPersonality),

                    seller_personality:
                        Number(sellerPersonality),

                    property_index:
                        Number(propertyIndex),

                    max_rounds:
                        Number(maxRounds),

                }),

        }

    );

}


/* =========================================================
   GET CURRENT NEGOTIATION STATE
========================================================= */

async function getNegotiationState(
    negotiationId
) {

    return requestJson(

        `${API_BASE_URL}/negotiations/${negotiationId}`

    );

}


/* =========================================================
   SEND MESSAGE / OFFER
========================================================= */

async function sendOffer(
    negotiationId,
    message,
    offer = null
) {

    return requestJson(

        `${API_BASE_URL}/negotiations/${negotiationId}/message`,

        {

            method:
                "POST",

            headers: {

                "Content-Type":
                    "application/json",

            },

            body:
                JSON.stringify({

                    message:
                        message,

                    offer:
                        offer,

                }),

        }

    );

}


/* =========================================================
   GET COMPLETE HISTORY
========================================================= */

async function getNegotiationHistory(
    negotiationId
) {

    return requestJson(

        `${API_BASE_URL}/negotiations/${negotiationId}/history`

    );

}


/* =========================================================
   CANCEL NEGOTIATION
========================================================= */

async function cancelNegotiation(
    negotiationId
) {

    return requestJson(

        `${API_BASE_URL}/negotiations/${negotiationId}/cancel`,

        {

            method:
                "POST",

        }

    );

}


/* =========================================================
   EXPORT
========================================================= */

export {

    getScenarios,

    getPersonalities,

    getProperties,

    startNegotiation,

    startAiVsAi,

    getNegotiationState,

    sendOffer,

    getNegotiationHistory,

    cancelNegotiation,

};
