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
   NORMALIZE AI-VS-AI OFFER
   AI-vs-AI backend/frontend values may arrive as lakhs.
   Example:
       126       -> ₹1,26,00,000
       71.18     -> ₹71,18,000

   Human-vs-AI values remain unchanged because they are
   already handled as rupee amounts.
========================================================= */

function normalizeAiOffer(
    value,
    mode
) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return null;
    }

    const number = Number(value);

    if (!Number.isFinite(number)) {
        return value;
    }

    /*
     * AI-vs-AI offer values such as 126, 96.67,
     * 71.18 represent lakhs.
     *
     * Full rupee values are much larger, so only
     * convert the smaller AI-vs-AI values.
     */
    if (
        mode === "ai_ai" &&
        Math.abs(number) < 100000
    ) {
        return number * 100000;
    }

    return number;
}


/* =========================================================
   GET BUYER OFFER
========================================================= */

function getBuyerOffer(
    data,
    mode
) {

    const value =
        data?.last_buyer_offer ??
        data?.buyer_last_offer ??
        data?.current_state?.last_buyer_offer ??
        data?.current_state?.buyer_last_offer ??
        data?.last_human_offer ??
        data?.buyer_offer ??
        data?.current_state?.buyer_offer ??
        null;

    return normalizeAiOffer(
        value,
        mode
    );
}


/* =========================================================
   GET SELLER OFFER
========================================================= */

function getSellerOffer(
    data,
    mode
) {

    const value =
        data?.last_seller_offer ??
        data?.seller_last_offer ??
        data?.current_state?.last_seller_offer ??
        data?.current_state?.seller_last_offer ??
        data?.last_ai_offer ??
        data?.seller_offer ??
        data?.current_state?.seller_offer ??
        null;

    return normalizeAiOffer(
        value,
        mode
    );
}


/* =========================================================
   GET CURRENT OFFER
========================================================= */

function getCurrentOffer(
    data,
    mode
) {

    const value =
        data?.current_offer ??
        data?.current_state?.current_offer ??
        null;

    return normalizeAiOffer(
        value,
        mode
    );
}


/* =========================================================
   GET AGREED PRICE
   Agreed price is already a full rupee value.
========================================================= */

function getAgreedPrice(data) {

    return (
        data?.agreed_price ??
        data?.current_state?.agreed_price ??
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
       NO DATA
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
       MODE
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

    const currentOffer =
        formatCurrency(
            getCurrentOffer(
                data,
                mode
            )
        );


    /* -----------------------------------------------------
       BUYER / HUMAN OFFER
    ----------------------------------------------------- */

    const buyerOffer =
        formatCurrency(
            getBuyerOffer(
                data,
                mode
            )
        );


    /* -----------------------------------------------------
       SELLER / AI OFFER
    ----------------------------------------------------- */

    const sellerOffer =
        formatCurrency(
            getSellerOffer(
                data,
                mode
            )
        );


    /* -----------------------------------------------------
       AGREED PRICE
    ----------------------------------------------------- */

    const agreedPrice =
        formatCurrency(
            getAgreedPrice(data)
        );


    /* -----------------------------------------------------
       LABELS
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
       METRICS UI
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