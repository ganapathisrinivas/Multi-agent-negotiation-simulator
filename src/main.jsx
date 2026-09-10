import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

/*
 * YOUR API SERVICE
 * All backend communication happens through this file.
 */
import {
  getScenarios,
  getPersonalities,
  getProperties,
  startNegotiation,
  getNegotiationState,
  sendOffer,
  getNegotiationHistory,
  cancelNegotiation,
} from "../frontend/services/negotiation-api.js";

/*
 * YOUR METRICS COMPONENT
 * Negotiation metrics are rendered through your file.
 */
import {
  renderMetrics,
} from "../frontend/components/negotiation-metrics.js";


/* ---------------------------------------------------------
   FALLBACK DATA
--------------------------------------------------------- */

const fallbackScenarios = {
  1: "Land / Plot",
  2: "Apartment / Flat",
  3: "Villa / Independent House",
};

const fallbackPersonalities = {
  1: "Aggressive",
  2: "Collaborative",
  3: "Risk-Averse",
};

const personalityMeta = {
  aggressive: {
    label: "Aggressive",
    icon: "⚡",
  },

  collaborative: {
    label: "Collaborative",
    icon: "🤝",
  },

  risk_averse: {
    label: "Risk-Averse",
    icon: "🛡️",
  },
};


/* ---------------------------------------------------------
   UTILITY FUNCTIONS
--------------------------------------------------------- */

const money = (value) => {
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

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(number);
};


const prettyKey = (key) =>
  String(key)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());


const getValue = (obj, names) => {
  if (!obj) return null;

  const key = Object.keys(obj).find((k) =>
    names.some(
      (name) =>
        k.toLowerCase() === name.toLowerCase()
    )
  );

  return key ? obj[key] : null;
};


/* ---------------------------------------------------------
   MAIN APP
--------------------------------------------------------- */

function App() {

  const [scenarios, setScenarios] =
    useState(fallbackScenarios);

  const [personalities, setPersonalities] =
    useState(fallbackPersonalities);

  const [properties, setProperties] =
    useState([]);

  const [scenario, setScenario] =
    useState(2);

  const [propertyIndex, setPropertyIndex] =
    useState(0);

  const [humanRole, setHumanRole] =
    useState("buyer");

  const [aiPersonality, setAiPersonality] =
    useState("collaborative");

  const [maxRounds, setMaxRounds] =
    useState(10);

  const [session, setSession] =
    useState(null);

  const [message, setMessage] =
    useState("");

  const [offer, setOffer] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  const [propertiesLoading, setPropertiesLoading] =
    useState(false);

  const [error, setError] =
    useState("");


  /* -------------------------------------------------------
     SELECTED PROPERTY
  ------------------------------------------------------- */

  const selectedProperty = useMemo(
    () =>
      properties.find(
        (p) =>
          p.index === Number(propertyIndex)
      ),

    [properties, propertyIndex]
  );


  const propertyData =
    selectedProperty?.property ||
    session?.property ||
    {};


  /* -------------------------------------------------------
     AI ROLE
  ------------------------------------------------------- */

  const aiRole =
    session?.ai_role ||
    (
      humanRole === "buyer"
        ? "seller"
        : "buyer"
    );


  const aiPersonalityLabel =
    personalityMeta[
      session?.ai_personality ||
      aiPersonality
    ]?.label ||
    session?.ai_personality ||
    aiPersonality;


  /* -------------------------------------------------------
     INITIAL DATA
  ------------------------------------------------------- */

  useEffect(() => {
    loadMetadata();
  }, []);


  /* -------------------------------------------------------
     LOAD PROPERTIES WHEN SCENARIO CHANGES
  ------------------------------------------------------- */

  useEffect(() => {
    loadProperties(scenario);
  }, [scenario]);


  /* -------------------------------------------------------
     LOAD SCENARIOS + PERSONALITIES
     THROUGH YOUR API FILE
  ------------------------------------------------------- */

  async function loadMetadata() {

    try {

      const [
        scenarioData,
        personalityData,
      ] = await Promise.all([
        getScenarios(),
        getPersonalities(),
      ]);


      setScenarios(
        scenarioData.scenarios ||
        fallbackScenarios
      );


      setPersonalities(
        personalityData.personalities ||
        fallbackPersonalities
      );

    } catch (err) {

      console.log(
        "Metadata loading failed. Using fallback data.",
        err
      );

    }
  }


  /* -------------------------------------------------------
     LOAD PROPERTIES
     THROUGH YOUR API FILE
  ------------------------------------------------------- */

  async function loadProperties(
    selectedScenario
  ) {

    setPropertiesLoading(true);
    setError("");


    try {

      const data =
        await getProperties(
          selectedScenario,
          0,
          100
        );


      setProperties(
        data.properties || []
      );


      setPropertyIndex(0);

    } catch (err) {

      setProperties([]);

      setError(
        `${err.message} Make sure the FastAPI backend is running on http://127.0.0.1:8000`
      );

    } finally {

      setPropertiesLoading(false);

    }
  }


  /* -------------------------------------------------------
     START NEGOTIATION
     THROUGH YOUR API FILE
  ------------------------------------------------------- */

  async function handleStartNegotiation() {

    setLoading(true);
    setError("");

    setSession(null);
    setMessage("");
    setOffer("");


    try {

      const data =
        await startNegotiation({

          scenario:
            Number(scenario),

          propertyIndex:
            Number(propertyIndex),

          humanRole:
            humanRole,

          aiPersonality:
            aiPersonality,

          maxRounds:
            Number(maxRounds),

        });


      /*
       * Initial AI greeting.
       */
      const initialHistory = [
        {
          round: 0,

          sender:
            `ai_${data.ai_role}`,

          message:
            data.ai_message,

          decision:
            "INITIAL_GREETING",

          offer:
            data.ai_role === "seller"
              ? getValue(
                  data.property,
                  [
                    "Price",
                    "price",
                    "Selling Price",
                    "selling_price",
                  ]
                )
              : null,
        },
      ];


      setSession({
        ...data,

        history:
          initialHistory,

        latestDecision:
          null,
      });


      /*
       * Get the latest backend state.
       *
       * This is useful for your metrics.
       */
      try {

        const latestState =
          await getNegotiationState(
            data.negotiation_id
          );


        setSession((prev) => ({
          ...prev,

          ...latestState,

          history:
            latestState.history ||
            initialHistory,
        }));

      } catch (stateError) {

        console.log(
          "Initial state refresh failed:",
          stateError
        );

      }

    } catch (err) {

      setError(err.message);

    } finally {

      setLoading(false);

    }
  }


  /* -------------------------------------------------------
     SEND MESSAGE / OFFER
     THROUGH YOUR API FILE
  ------------------------------------------------------- */

  async function handleSendMessage(event) {

    event?.preventDefault();


    if (
      !session ||
      session.status !== "active" ||
      !message.trim()
    ) {
      return;
    }


    setLoading(true);
    setError("");


    try {

      const humanOffer =
        offer === ""
          ? null
          : Number(offer);


      /*
       * Backend request goes through YOUR service.
       */
      const data =
        await sendOffer(
          session.negotiation_id,

          message.trim(),

          humanOffer
        );


      /*
       * Human message for UI.
       */
      const humanEntry = {

        round:
          data.round,

        sender:
          `human_${session.human_role}`,

        message:
          data.human_message,

        offer:
          data.human_offer,

      };


      /*
       * AI response for UI.
       */
      const aiEntry = {

        round:
          data.round,

        sender:
          `ai_${session.ai_role}`,

        message:
          data.ai_response?.message,

        offer:
          data.ai_response?.counter_offer,

        decision:
          data.ai_response?.decision,

        reason:
          data.ai_response?.reason,

      };


      /*
       * IMPORTANT:
       *
       * Get complete state again from backend.
       *
       * This ensures the metrics use the
       * latest backend values.
       */
      let latestState = null;


      try {

        latestState =
          await getNegotiationState(
            session.negotiation_id
          );

      } catch (stateError) {

        console.log(
          "Latest state refresh failed:",
          stateError
        );

      }


      setSession((prev) => ({

        ...prev,

        ...(latestState || {}),

        status:
          latestState?.status ??
          data.status,

        history:
          latestState?.history ||
          [
            ...(prev.history || []),
            humanEntry,
            aiEntry,
          ],

        latestDecision:
          data.ai_response,

        round:
          latestState?.round ??
          data.round,

        current_offer:
          latestState?.current_offer ??
          data.ai_response?.counter_offer ??
          data.human_offer ??
          prev.current_offer,

        last_human_offer:
          latestState?.last_human_offer ??
          data.human_offer ??
          prev.last_human_offer,

        last_ai_offer:
          latestState?.last_ai_offer ??
          data.ai_response?.counter_offer ??
          prev.last_ai_offer,

        agreed_price:
          latestState?.agreed_price ??
          (
            data.status === "accepted"
              ? (
                  data.ai_response
                    ?.counter_offer ??
                  data.human_offer
                )
              : prev.agreed_price
          ),

        stagnant_round_count:
          latestState?.stagnant_round_count ??
          prev.stagnant_round_count ??
          0,

      }));


      setMessage("");
      setOffer("");


    } catch (err) {

      setError(err.message);

    } finally {

      setLoading(false);

    }
  }


  /* -------------------------------------------------------
     CANCEL NEGOTIATION
     THROUGH YOUR API FILE
  ------------------------------------------------------- */

  async function handleCancelNegotiation() {

    if (!session) return;


    setLoading(true);
    setError("");


    try {

      const data =
        await cancelNegotiation(
          session.negotiation_id
        );


      setSession((prev) => ({

        ...prev,

        status:
          data.status,

        history: [
          ...(prev.history || []),

          {
            round:
              prev.round,

            sender:
              "system",

            message:
              data.message,
          },
        ],

      }));

    } catch (err) {

      setError(err.message);

    } finally {

      setLoading(false);

    }
  }


  /* -------------------------------------------------------
     REFRESH STATE
     THROUGH YOUR API FILE
  ------------------------------------------------------- */

  async function refreshState() {

    if (!session) return;


    try {

      const data =
        await getNegotiationState(
          session.negotiation_id
        );


      setSession((prev) => ({
        ...prev,
        ...data,
      }));


      /*
       * Also refresh complete history.
       */
      try {

        const historyData =
          await getNegotiationHistory(
            session.negotiation_id
          );


        if (historyData?.history) {

          setSession((prev) => ({
            ...prev,

            history:
              historyData.history,
          }));

        }

      } catch (historyError) {

        console.log(
          "History refresh failed:",
          historyError
        );

      }

    } catch (err) {

      setError(err.message);

    }
  }


  /* -------------------------------------------------------
     STATUS
  ------------------------------------------------------- */

  const status =
    session?.status || "ready";


  const latestDecision =
    session?.latestDecision;


  /* -------------------------------------------------------
     DATA SENT TO YOUR METRICS COMPONENT
  ------------------------------------------------------- */

  const metricsData =
    session || {

      round: 0,

      max_rounds:
        maxRounds,

      status:
        "ready",

      current_offer:
        null,

      last_human_offer:
        null,

      last_ai_offer:
        null,

      agreed_price:
        null,

      stagnant_round_count:
        0,

    };


  /* =======================================================
     UI
  ======================================================= */

  return (

    <div className="app-shell">


      {/* ---------------------------------------------------
         HEADER
      --------------------------------------------------- */}

      <header className="topbar">

        <div>

          <div className="eyebrow">
            AI REAL ESTATE SIMULATION
          </div>

          <h1>
            Negotiation Arena
          </h1>

          <p>
            Practice real-world property negotiation
            with a multi-agent AI.
          </p>

        </div>


        <div
          className={`status-pill ${status}`}
        >

          <span className="status-dot" />

          {status
            .replace(/_/g, " ")
            .toUpperCase()}

        </div>

      </header>


      {/* ---------------------------------------------------
         ERROR
      --------------------------------------------------- */}

      {error && (

        <div className="error-banner">

          <strong>
            Backend message:
          </strong>{" "}

          {error}

        </div>

      )}


      <main className="layout">


        {/* =================================================
           LEFT SIDEBAR
        ================================================= */}

        <aside className="sidebar">


          {/* ------------------------------------------------
             NEGOTIATION SETUP
          ------------------------------------------------ */}

          <section className="panel setup-panel">

            <div className="panel-title">

              <span>01</span>

              Negotiation setup

            </div>


            {/* SCENARIO */}

            <label>

              Scenario

              <select
                value={scenario}

                onChange={(e) => {

                  setScenario(
                    Number(e.target.value)
                  );

                  setSession(null);

                }}
              >

                {Object.entries(
                  scenarios
                ).map(
                  ([key, value]) => (

                    <option
                      key={key}
                      value={key}
                    >
                      {value}
                    </option>

                  )
                )}

              </select>

            </label>


            {/* PROPERTY */}

            <label>

              Property

              <select
                value={propertyIndex}

                disabled={
                  propertiesLoading ||
                  properties.length === 0
                }

                onChange={(e) =>
                  setPropertyIndex(
                    Number(e.target.value)
                  )
                }
              >

                {properties.map(
                  (item) => {

                    const title =
                      getValue(
                        item.property,
                        [
                          "Property Title",
                          "Name",
                          "Property Name",
                        ]
                      ) ||
                      `Property ${
                        item.index + 1
                      }`;

                    return (

                      <option
                        key={item.index}
                        value={item.index}
                      >

                        {item.index + 1}.{" "}

                        {title}

                      </option>

                    );

                  }
                )}

              </select>

            </label>


            {/* ROLE */}

            <label>

              Your role

              <div className="segmented">

                <button
                  type="button"

                  className={
                    humanRole === "buyer"
                      ? "selected"
                      : ""
                  }

                  onClick={() =>
                    setHumanRole("buyer")
                  }
                >
                  Buyer
                </button>


                <button
                  type="button"

                  className={
                    humanRole === "seller"
                      ? "selected"
                      : ""
                  }

                  onClick={() =>
                    setHumanRole("seller")
                  }
                >
                  Seller
                </button>

              </div>

            </label>


            {/* PERSONALITY */}

            <label>

              AI personality

              <select
                value={aiPersonality}

                onChange={(e) =>
                  setAiPersonality(
                    e.target.value
                  )
                }
              >

                {Object.entries(
                  personalities
                ).map(
                  ([key, value]) => {

                    const normalized =
                      String(value)
                        .toLowerCase()
                        .replace(/-/g, "_")
                        .replace(/ /g, "_");

                    return (

                      <option
                        key={key}
                        value={normalized}
                      >
                        {value}
                      </option>

                    );

                  }
                )}

              </select>

            </label>


            {/* MAX ROUNDS */}

            <label>

              Maximum rounds

              <input
                type="number"

                min="1"

                max="50"

                value={maxRounds}

                onChange={(e) =>
                  setMaxRounds(
                    e.target.value
                  )
                }

              />

            </label>


            {/* START */}

            <button
              type="button"

              className="primary-btn"

              onClick={
                handleStartNegotiation
              }

              disabled={
                loading ||
                properties.length === 0
              }
            >

              {loading && !session
                ? "Starting..."
                : "Start negotiation →"}

            </button>


            {/* REFRESH */}

            {session && (

              <button
                type="button"

                className="secondary-btn"

                onClick={
                  refreshState
                }

                disabled={loading}
              >
                Refresh state
              </button>

            )}

          </section>


          {/* ------------------------------------------------
             PROPERTY SNAPSHOT
          ------------------------------------------------ */}

          <section className="panel property-panel">

            <div className="panel-title">

              <span>02</span>

              Property snapshot

            </div>


            <h2>

              {getValue(
                propertyData,
                [
                  "Property Title",
                  "Name",
                  "Property Name",
                ]
              ) ||
                "Selected property"}

            </h2>


            <div className="property-price">

              {money(
                getValue(
                  propertyData,
                  [
                    "Price",
                    "price",
                    "Selling Price",
                    "selling_price",
                    "Property Price",
                  ]
                )
              )}

            </div>


            <div className="location">

              📍{" "}

              {getValue(
                propertyData,
                [
                  "Location",
                  "location",
                  "Address",
                  "address",
                ]
              ) ||
                "Location not provided"}

            </div>


            <div className="property-grid">

              {Object.entries(
                propertyData
              )

                .filter(
                  ([key]) =>
                    ![
                      "Price",
                      "price",
                    ].includes(key)
                )

                .slice(0, 8)

                .map(
                  ([key, value]) => (

                    <div
                      className="property-field"
                      key={key}
                    >

                      <span>
                        {prettyKey(key)}
                      </span>

                      <strong>
                        {String(
                          value ?? "—"
                        )}
                      </strong>

                    </div>

                  )
                )}

            </div>

          </section>

        </aside>


        {/* =================================================
           CENTER NEGOTIATION ARENA
        ================================================= */}

        <section className="arena">


          {/* ARENA HEADER */}

          <div className="arena-header">

            <div>

              <div className="eyebrow">
                LIVE SESSION
              </div>

              <h2>

                {session
                  ? `Session #${session.negotiation_id}`
                  : "Set up your negotiation"}

              </h2>

            </div>


            {session && (

              <div className="round-badge">

                Round{" "}

                {session.round || 1}

                {" / "}

                {session.max_rounds}

              </div>

            )}

          </div>


          {/* AGENTS */}

          <div className="agents-row">

            <AgentCard
              role={humanRole}
              name="You"
              personality="Human"
              active={Boolean(session)}
            />


            <div className="versus">
              VS
            </div>


            <AgentCard
              role={aiRole}
              name="AI Negotiator"
              personality={
                aiPersonalityLabel
              }
              active={Boolean(session)}
            />

          </div>


          {/* TRANSCRIPT */}

          <div className="transcript panel">

            <div className="transcript-head">

              <div>

                <h3>
                  Negotiation transcript
                </h3>

                <span>

                  {session
                    ? "Every offer and AI decision appears here."
                    : "Start a session to begin the conversation."}

                </span>

              </div>


              {session && (

                <button
                  type="button"

                  className="cancel-btn"

                  onClick={
                    handleCancelNegotiation
                  }

                  disabled={
                    loading ||
                    status !== "active"
                  }
                >
                  End session
                </button>

              )}

            </div>


            {/* MESSAGES */}

            <div className="messages">

              {!session ? (

                <div className="empty-state">

                  <div className="empty-icon">
                    💬
                  </div>

                  <h3>
                    Ready when you are
                  </h3>

                  <p>

                    Choose a property,
                    role and AI personality,
                    then start the negotiation.

                  </p>

                </div>

              ) : (

                session.history?.map(
                  (item, index) => (

                    <MessageBubble

                      key={
                        `${index}-${item.timestamp || ""}`
                      }

                      item={item}

                      humanRole={
                        session.human_role
                      }

                      aiRole={
                        session.ai_role
                      }

                    />

                  )
                )

              )}

            </div>


            {/* COMPOSER */}

            {session &&
              status === "active" && (

                <form
                  className="composer"

                  onSubmit={
                    handleSendMessage
                  }
                >

                  <div className="offer-input">

                    <span>
                      ₹
                    </span>

                    <input

                      type="number"

                      min="0"

                      placeholder="Offer amount (optional)"

                      value={offer}

                      onChange={(e) =>
                        setOffer(
                          e.target.value
                        )
                      }

                    />

                  </div>


                  <input

                    className="message-input"

                    placeholder={
                      humanRole === "buyer"
                        ? "Write your offer or negotiation message..."
                        : "Write your asking price or negotiation message..."
                    }

                    value={message}

                    onChange={(e) =>
                      setMessage(
                        e.target.value
                      )
                    }

                  />


                  <button

                    type="submit"

                    className="send-btn"

                    disabled={
                      loading ||
                      !message.trim()
                    }

                  >

                    {loading
                      ? "..."
                      : "Send"}

                  </button>

                </form>

              )}


            {/* RESULT */}

            {session &&
              status !== "active" && (

                <div
                  className={`result-banner ${status}`}
                >

                  <strong>

                    Negotiation{" "}
                    {status}.

                  </strong>

                  {latestDecision?.message

                    ? " Review the final AI decision above."

                    : " Start a new session to negotiate again."

                  }

                </div>

              )}

          </div>

        </section>


        {/* =================================================
           RIGHT SIDEBAR
        ================================================= */}

        <aside className="rightbar">


          {/* AI REASONING */}

          <section className="panel reasoning-panel">

            <div className="panel-title">

              <span>03</span>

              AI reasoning

            </div>


            {latestDecision ? (

              <>

                <div
                  className={`decision ${String(
                    latestDecision.decision
                  ).toLowerCase()}`}
                >

                  {latestDecision.decision}

                </div>


                <h3>
                  Decision analysis
                </h3>


                <p>

                  {latestDecision.reason ||
                    "The AI did not return a reasoning summary for this response."}

                </p>


                <div className="decision-price">

                  <span>
                    Counter offer
                  </span>

                  <strong>

                    {money(
                      latestDecision.counter_offer
                    )}

                  </strong>

                </div>

              </>

            ) : (

              <div className="reasoning-empty">

                <span>
                  ◎
                </span>

                <p>

                  Once the AI responds,
                  its decision, counter-offer
                  and reasoning will appear here.

                </p>

              </div>

            )}

          </section>


          {/* =================================================
             YOUR NEGOTIATION METRICS
             COMING FROM YOUR FILE
          ================================================= */}

          <section className="panel metrics-panel">

            <div className="panel-title">

              <span>04</span>

              Negotiation metrics

            </div>


            <div
              dangerouslySetInnerHTML={{
                __html:
                  renderMetrics(
                    metricsData
                  ),
              }}
            />

          </section>


          {/* TIP */}

          <section className="panel tip-panel">

            <div className="tip-icon">
              ✦
            </div>

            <div>

              <strong>
                Negotiation tip
              </strong>

              <p>

                Make a clear numerical
                offer when possible.
                The backend can also
                extract an offer from
                your natural-language
                message.

              </p>

            </div>

          </section>

        </aside>

      </main>

    </div>
  );
}


/* =========================================================
   AGENT CARD
========================================================= */

function AgentCard({
  role,
  name,
  personality,
  active,
}) {

  const meta =
    personalityMeta[
      String(personality)
        .toLowerCase()
        .replace(/-/g, "_")
    ] || {

      label:
        personality,

      icon:
        "◈",

    };


  return (

    <div
      className={`agent-card ${
        active ? "active" : ""
      }`}
    >

      <div
        className={`avatar ${role}`}
      >

        {role === "buyer"
          ? "B"
          : "S"}

      </div>


      <div>

        <span className="agent-role">
          {role}
        </span>

        <strong>
          {name}
        </strong>

        <small>

          {meta.icon}{" "}
          {meta.label}

        </small>

      </div>

    </div>

  );
}


/* =========================================================
   MESSAGE BUBBLE
========================================================= */

function MessageBubble({
  item,
  humanRole,
  aiRole,
}) {

  const isHuman =
    String(item.sender || "")
      .startsWith("human");


  const isSystem =
    item.sender === "system";


  if (isSystem) {

    return (

      <div className="system-message">

        <span>
          •
        </span>{" "}

        {item.message}

      </div>

    );
  }


  return (

    <div
      className={`message-row ${
        isHuman
          ? "human"
          : "ai"
      }`}
    >

      <div className="message-meta">

        <span>

          {isHuman
            ? "You"
            : `AI ${aiRole}`}

        </span>


        <span>

          Round{" "}
          {item.round}

        </span>

      </div>


      <div className="bubble">

        <p>
          {item.message}
        </p>


        {item.offer !== null &&
          item.offer !== undefined && (

            <div className="offer-chip">

              {isHuman
                ? "Offer"
                : "Counter"}

              {" · "}

              {money(
                item.offer
              )}

            </div>

          )}

      </div>


      {!isHuman &&
        item.decision && (

          <div
            className={`inline-decision ${String(
              item.decision
            ).toLowerCase()}`}
          >

            {item.decision}

          </div>

        )}


      {!isHuman &&
        item.reason && (

          <div className="inline-reason">

            {item.reason}

          </div>

        )}

    </div>

  );
}


/* =========================================================
   REACT ROOT
========================================================= */

createRoot(
  document.getElementById("root")
).render(

  <React.StrictMode>

    <App />

  </React.StrictMode>

);