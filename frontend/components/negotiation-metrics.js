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


    const number =
        Number(value);


    if (!Number.isFinite(number)) {

        return String(value);

    }


    return new Intl.NumberFormat(

        "en-IN",

        {

            style:
                "currency",

            currency:
                "INR",

            maximumFractionDigits:
                0,

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

        .replace(
            /_/g,
            " "
        )

        .toUpperCase();

}


/* =========================================================
   ESCAPE HTML
========================================================= */

function escapeHtml(value) {

    return String(value ?? "")

        .replace(
            /&/g,
            "&amp;"
        )

        .replace(
            /</g,
            "&lt;"
        )

        .replace(
            />/g,
            "&gt;"
        )

        .replace(
            /"/g,
            "&quot;"
        )

        .replace(
            /'/g,
            "&#039;"
        );

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
   RENDER NEGOTIATION METRICS
========================================================= */

function renderMetrics(data) {

    /* -----------------------------------------------------
       NO ACTIVE SESSION
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
                    "Your Offer",
                    "—"
                )}

                ${metricHtml(
                    "AI Offer",
                    "—"
                )}

                ${metricHtml(
                    "Agreed Price",
                    "—"
                )}

                ${metricHtml(
                    "Stagnant Rounds",
                    "0"
                )}

            </div>

        `;

    }


    /* -----------------------------------------------------
       BACKEND METRIC VALUES
    ----------------------------------------------------- */

    const round =
        data.round ?? "—";


    const maxRounds =
        data.max_rounds ?? "—";


    const status =
        formatStatus(
            data.status
        );


    const currentOffer =
        formatCurrency(
            data.current_offer
        );


    const humanOffer =
        formatCurrency(
            data.last_human_offer
        );


    const aiOffer =
        formatCurrency(
            data.last_ai_offer
        );


    const agreedPrice =
        formatCurrency(
            data.agreed_price
        );


    const stagnantRounds =
        data.stagnant_round_count ??
        0;


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
                "Your Offer",
                humanOffer
            )}


            ${metricHtml(
                "AI Offer",
                aiOffer
            )}


            ${metricHtml(
                "Agreed Price",
                agreedPrice
            )}


            ${metricHtml(
                "Stagnant Rounds",
                String(
                    stagnantRounds
                )
            )}


            ${
                data.status ===
                "deadlocked"

                    ? `

                        <div class="deadlock-message">

                            <strong>
                                Deadlock Reason
                            </strong>

                            <p>

                                ${escapeHtml(
                                    data.deadlock_reason ||
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