/* =========================================================
   FORMAT CURRENCY
========================================================= */

function formatCurrency(value) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return "—";
    }

    const number = Number(value);

    if (!Number.isFinite(number)) {
        return String(value);
    }

    return new Intl.NumberFormat(
        "en-IN",
        {
            style: "currency",
            currency: "INR",
            maximumFractionDigits: 0,
        }
    ).format(number);
}


/* =========================================================
   FORMAT STATUS
========================================================= */

function formatStatus(status) {

    if (!status) {
        return "UNKNOWN";
    }

    return String(status)
        .replace(/_/g, " ")
        .toUpperCase();
}


/* =========================================================
   ESCAPE HTML
========================================================= */

function escapeHtml(value) {

    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


/* =========================================================
   CREATE ONE METRIC ROW
========================================================= */

function metricHtml(
    label,
    value
) {

    return `

        <div class="metric">

            <span>
                ${escapeHtml(label)}
            </span>

            <strong>
                ${escapeHtml(value)}
            </strong>

        </div>

    `;
}


/* =========================================================
   GET BUYER OFFER
   Supports Human-vs-AI and AI-vs-AI data.
========================================================= */

function getBuyerOffer(data) {

    return (
        data?.buyer_offer ??
        data?.last_buyer_offer ??
        data?.buyer_last_offer ??
        data?.current_state?.buyer_offer ??
        data?.current_state?.last_buyer_offer ??
        data?.current_state?.buyer_last_offer ??
        data?.last_human_offer ??
        null
    );
}


/* =========================================================
   GET SELLER OFFER
   Supports Human-vs-AI and AI-vs-AI data.
========================================================= */

function getSellerOffer(data) {

    return (
        data?.seller_offer ??
        data?.last_seller_offer ??
        data?.seller_last_offer ??
        data?.current_state?.seller_offer ??
        data?.current_state?.last_seller_offer ??
        data?.current_state?.seller_last_offer ??
        data?.last_ai_offer ??
        null
    );
}


/* =========================================================
   GET DEADLOCK REASON
========================================================= */

function getDeadlockReason(data) {

    return (
        data?.deadlock_reason ??
        data?.current_state?.deadlock_reason ??
        data?.deadlock?.reason ??
        data?.current_state?.deadlock?.reason ??
        null
    );
}


/* =========================================================
   RENDER NEGOTIATION METRICS
========================================================= */

function renderMetrics(
    data,
    mode = "human_ai"
) {

    /* -----------------------------------------------------
       NO ACTIVE DATA
    ----------------------------------------------------- */

    if (!data) {

        return `

            <div class="negotiation-metrics">

                ${metricHtml(
                    "Round",
                    "—"
                )}

                ${metricHtml(
                    "Status",
                    "READY"
                )}

                ${metricHtml(
                    "Current Offer",
                    "—"
                )}

                ${metricHtml(
                    mode === "ai_ai"
                        ? "Buyer Offer"
                        : "Your Offer",
                    "—"
                )}

                ${metricHtml(
                    mode === "ai_ai"
                        ? "Seller Offer"
                        : "AI Offer",
                    "—"
                )}

                ${metricHtml(
                    "Agreed Price",
                    "—"
                )}

            </div>

        `;
    }


    /* -----------------------------------------------------
       DETERMINE MODE
    ----------------------------------------------------- */

    const isAiVsAi =
        mode === "ai_ai";


    /* -----------------------------------------------------
       ROUND
    ----------------------------------------------------- */

    const round =
        data.round ??
        data.current_state?.round ??
        "—";


    const maxRounds =
        data.max_rounds ??
        data.current_state?.max_rounds ??
        "—";


    /* -----------------------------------------------------
       STATUS
    ----------------------------------------------------- */

    const statusValue =
        data.status ??
        data.current_state?.status;


    const status =
        formatStatus(
            statusValue
        );


    /* -----------------------------------------------------
       CURRENT OFFER
    ----------------------------------------------------- */

    const currentOfferValue =
        data.current_offer ??
        data.current_state?.current_offer ??
        null;


    const currentOffer =
        formatCurrency(
            currentOfferValue
        );


    /* -----------------------------------------------------
       BUYER / HUMAN OFFER
    ----------------------------------------------------- */

    const buyerOffer =
        formatCurrency(
            getBuyerOffer(data)
        );


    /* -----------------------------------------------------
       SELLER / AI OFFER
    ----------------------------------------------------- */

    const sellerOffer =
        formatCurrency(
            getSellerOffer(data)
        );


    /* -----------------------------------------------------
       AGREED PRICE
    ----------------------------------------------------- */

    const agreedPrice =
        formatCurrency(

            data.agreed_price ??
            data.current_state?.agreed_price

        );


    /* -----------------------------------------------------
       OFFER LABELS
    ----------------------------------------------------- */

    const firstOfferLabel =
        isAiVsAi
            ? "Buyer Offer"
            : "Your Offer";


    const secondOfferLabel =
        isAiVsAi
            ? "Seller Offer"
            : "AI Offer";


    /* -----------------------------------------------------
       DEADLOCK REASON
    ----------------------------------------------------- */

    const deadlockReason =
        getDeadlockReason(data);


    /* -----------------------------------------------------
       RETURN METRICS UI
    ----------------------------------------------------- */

    return `

        <div class="negotiation-metrics">

            ${metricHtml(
                "Round",
                `${round} / ${maxRounds}`
            )}


            ${metricHtml(
                "Status",
                status
            )}


            ${metricHtml(
                "Current Offer",
                currentOffer
            )}


            ${metricHtml(
                firstOfferLabel,
                buyerOffer
            )}


            ${metricHtml(
                secondOfferLabel,
                sellerOffer
            )}


            ${metricHtml(
                "Agreed Price",
                agreedPrice
            )}


            ${
                String(statusValue).toLowerCase() === "deadlocked"

                    ? `

                        <div class="deadlock-message">

                            <strong>
                                Deadlock Reason
                            </strong>

                            <p>

                                ${escapeHtml(
                                    deadlockReason ||
                                    "Negotiation reached a deadlock."
                                )}

                            </p>

                        </div>

                    `

                    : ""

            }

        </div>

    `;
}


/* =========================================================
   EXPORT
========================================================= */

export {

    renderMetrics,

    formatCurrency,

    formatStatus,

};
