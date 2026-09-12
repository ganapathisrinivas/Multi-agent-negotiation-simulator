/* =========================================================
   MILESTONE 4 - PART 1
   NEGOTIATION OUTCOME SCREEN
========================================================= */

function formatMoney(value) {
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

function formatStatus(value) {
  if (!value) {
    return "COMPLETED";
  }

  return String(value)
    .replace(/_/g, " ")
    .toUpperCase();
}


/* =========================================================
   BUILD CONCESSION TIMELINE
========================================================= */

function buildConcessionTimeline(session) {

  const history =
    Array.isArray(session?.history)
      ? session.history
      : [];

  const rounds = {};


  history.forEach((item) => {

    if (!item) {
      return;
    }


    const round =
      Number(item.round);


    if (
      !Number.isFinite(round) ||
      round <= 0
    ) {
      return;
    }


    if (!rounds[round]) {

      rounds[round] = {
        round,
        buyerOffer: null,
        sellerOffer: null,
      };

    }


    const sender =
      String(
        item.sender ||
        item.agent ||
        ""
      ).toLowerCase();


    const offer =
      item.offer !== null &&
      item.offer !== undefined &&
      item.offer !== ""
        ? Number(item.offer)
        : null;


    if (
      offer === null ||
      !Number.isFinite(offer)
    ) {
      return;
    }


    /* -----------------------------------------
       AI VS AI
    ----------------------------------------- */

    if (
      sender.includes("ai_buyer") ||
      sender.includes("buyer")
    ) {

      rounds[round].buyerOffer =
        offer;

      return;
    }


    if (
      sender.includes("ai_seller") ||
      sender.includes("seller")
    ) {

      rounds[round].sellerOffer =
        offer;

      return;
    }


    /* -----------------------------------------
       HUMAN VS AI
    ----------------------------------------- */

    if (
      sender.includes("human_buyer")
    ) {

      rounds[round].buyerOffer =
        offer;

      return;
    }


    if (
      sender.includes("human_seller")
    ) {

      rounds[round].sellerOffer =
        offer;

      return;
    }

  });


  return Object.values(rounds)
    .sort(
      (a, b) =>
        a.round - b.round
    );

}


/* =========================================================
   GET LAST OFFER
========================================================= */

function getLastOffers(timeline) {

  let buyerOffer = null;
  let sellerOffer = null;


  for (
    let index =
      timeline.length - 1;
    index >= 0;
    index -= 1
  ) {

    const item =
      timeline[index];


    if (
      buyerOffer === null &&
      item.buyerOffer !== null
    ) {

      buyerOffer =
        item.buyerOffer;

    }


    if (
      sellerOffer === null &&
      item.sellerOffer !== null
    ) {

      sellerOffer =
        item.sellerOffer;

    }


    if (
      buyerOffer !== null &&
      sellerOffer !== null
    ) {

      break;

    }

  }


  return {
    buyerOffer,
    sellerOffer,
  };

}


/* =========================================================
   OUTCOME SCREEN
========================================================= */

export default function OutcomeScreen({
  session
}) {

  if (!session) {
    return null;
  }


  const status =
    String(
      session.status ||
      "completed"
    ).toLowerCase();


  const statusLabel =
    formatStatus(
      session.status
    );


  const timeline =
    buildConcessionTimeline(
      session
    );


  const maxRounds =
    Number(
      session.max_rounds
    );


  const sessionRound =
    Number(
      session.round
    );


  const roundsElapsed =
    Number.isFinite(
      sessionRound
    ) &&
    sessionRound > 0
      ? sessionRound
      : timeline.length;


  const agreedPrice =
    session.agreed_price ??
    null;


  const lastOffers =
    getLastOffers(
      timeline
    );


  const buyerSatisfaction =
    session.buyer_objective_satisfaction ??
    session.buyer_satisfaction ??
    session.objective_satisfaction?.buyer ??
    null;


  const sellerSatisfaction =
    session.seller_objective_satisfaction ??
    session.seller_satisfaction ??
    session.objective_satisfaction?.seller ??
    null;


  const property =
    session.property || {};


  const propertyName =
    property["Property Title"] ||
    property.Name ||
    property.name ||
    session.property_name ||
    "Selected Property";


  const scenario =
    session.scenario_name ||
    session.scenario ||
    "Real Estate Negotiation";


  const mode =
    session.mode === "ai_ai"
      ? "AI vs AI"
      : "Human vs AI";


  const buyerPersonality =
    session.buyer_personality_label ||
    session.buyer_personality ||
    (
      session.human_role === "buyer"
        ? "Human"
        : "AI"
    );


  const sellerPersonality =
    session.seller_personality_label ||
    session.seller_personality ||
    (
      session.human_role === "seller"
        ? "Human"
        : "AI"
    );


  return (

    <section className="outcome-screen">

      {/* =================================================
         OUTCOME HEADER
      ================================================= */}

      <div className="outcome-header">

        <div className="outcome-title-area">

          <div className="outcome-trophy">
            ✓
          </div>


          <div>

            <div className="outcome-eyebrow">
              NEGOTIATION OUTCOME
            </div>


            <h2>
              Negotiation Completed
            </h2>


            <p>
              Final result of the negotiation
            </p>

          </div>

        </div>


        <div
          className={`outcome-final-status ${status}`}
        >
          ● {statusLabel}
        </div>

      </div>


      {/* =================================================
         FINAL AGREEMENT TERMS
      ================================================= */}

      <div className="outcome-panel">

        <div className="outcome-panel-heading">

          <span className="outcome-heading-icon">
            ₹
          </span>

          <div>

            <h3>
              Final Agreement Terms
            </h3>

            <p>
              Key details from the completed negotiation
            </p>

          </div>

        </div>


        <div className="agreement-grid">

          <div className="agreement-item">

            <span>
              AGREED PRICE
            </span>

            <strong>
              {formatMoney(
                agreedPrice
              )}
            </strong>

          </div>


          <div className="agreement-item">

            <span>
              PROPERTY
            </span>

            <strong>
              {propertyName}
            </strong>

          </div>


          <div className="agreement-item">

            <span>
              SCENARIO
            </span>

            <strong>
              {scenario}
            </strong>

          </div>


          <div className="agreement-item">

            <span>
              ROUNDS ELAPSED
            </span>

            <strong>

              {roundsElapsed}

              {Number.isFinite(
                maxRounds
              ) && maxRounds > 0
                ? ` / ${maxRounds}`
                : ""
              }

            </strong>

          </div>

        </div>

      </div>


      {/* =================================================
         CONCESSION TIMELINE
      ================================================= */}

      <div className="outcome-panel">

        <div className="outcome-panel-heading">

          <span className="outcome-heading-icon">
            ↗
          </span>

          <div>

            <h3>
              Concession Timeline
            </h3>

            <p>
              How buyer and seller offers changed
              across the negotiation
            </p>

          </div>

        </div>


        {timeline.length === 0 ? (

          <div className="timeline-empty">

            No negotiation offer history is available.

          </div>

        ) : (

          <div className="timeline-table">

            <div className="timeline-header">

              <span>
                ROUND
              </span>

              <span>
                BUYER OFFER
              </span>

              <span>
                SELLER OFFER
              </span>

              <span>
                GAP
              </span>

            </div>


            {timeline.map(
              (item) => {

                const gap =
                  item.buyerOffer !== null &&
                  item.sellerOffer !== null
                    ? Math.abs(
                        item.sellerOffer -
                        item.buyerOffer
                      )
                    : null;


                return (

                  <div
                    className="timeline-row"
                    key={
                      item.round
                    }
                  >

                    <strong>
                      {item.round}
                    </strong>


                    <span>
                      {formatMoney(
                        item.buyerOffer
                      )}
                    </span>


                    <span>
                      {formatMoney(
                        item.sellerOffer
                      )}
                    </span>


                    <span>
                      {gap === null
                        ? "—"
                        : formatMoney(gap)
                      }
                    </span>

                  </div>

                );

              }
            )}

          </div>

        )}

      </div>


      {/* =================================================
         OBJECTIVE SATISFACTION
      ================================================= */}

      <div className="outcome-panel">

        <div className="outcome-panel-heading">

          <span className="outcome-heading-icon">
            ★
          </span>

          <div>

            <h3>
              Objective Satisfaction
            </h3>

            <p>
              How well each agent's objective
              was satisfied
            </p>

          </div>

        </div>


        <div className="satisfaction-grid">

          {/* BUYER */}

          <div className="satisfaction-card">

            <div className="satisfaction-header">

              <div>

                <span>
                  BUYER
                </span>

                <strong>
                  {buyerPersonality}
                </strong>

              </div>


              <b>

                {buyerSatisfaction === null
                  ? "—"
                  : `${buyerSatisfaction}%`
                }

              </b>

            </div>


            <div className="satisfaction-track">

              {buyerSatisfaction !== null && (

                <div
                  className="satisfaction-fill buyer"
                  style={{
                    width: `${Math.min(
                      100,
                      Math.max(
                        0,
                        Number(
                          buyerSatisfaction
                        )
                      )
                    )}%`,
                  }}
                />

              )}

            </div>

          </div>


          {/* SELLER */}

          <div className="satisfaction-card">

            <div className="satisfaction-header">

              <div>

                <span>
                  SELLER
                </span>

                <strong>
                  {sellerPersonality}
                </strong>

              </div>


              <b>

                {sellerSatisfaction === null
                  ? "—"
                  : `${sellerSatisfaction}%`
                }

              </b>

            </div>


            <div className="satisfaction-track">

              {sellerSatisfaction !== null && (

                <div
                  className="satisfaction-fill seller"
                  style={{
                    width: `${Math.min(
                      100,
                      Math.max(
                        0,
                        Number(
                          sellerSatisfaction
                        )
                      )
                    )}%`,
                  }}
                />

              )}

            </div>

          </div>

        </div>


        {buyerSatisfaction === null &&
          sellerSatisfaction === null && (

            <div className="satisfaction-note">

              Objective satisfaction scores are
              waiting for backend score data.

            </div>

          )}

      </div>


      {/* =================================================
         SUMMARY
      ================================================= */}

      <div className="outcome-summary">

        <div>

          <span>
            MODE
          </span>

          <strong>
            {mode}
          </strong>

        </div>


        <div>

          <span>
            FINAL BUYER OFFER
          </span>

          <strong>
            {formatMoney(
              lastOffers.buyerOffer
            )}
          </strong>

        </div>


        <div>

          <span>
            FINAL SELLER OFFER
          </span>

          <strong>
            {formatMoney(
              lastOffers.sellerOffer
            )}
          </strong>

        </div>


        <div>

          <span>
            SESSION
          </span>

          <strong>
            {session.negotiation_id ||
             "Completed"
            }
          </strong>

        </div>

      </div>

    </section>

  );

}