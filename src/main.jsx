import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = "/api";

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
  aggressive: { label: "Aggressive", icon: "⚡" },
  collaborative: { label: "Collaborative", icon: "🤝" },
  risk_averse: { label: "Risk-Averse", icon: "🛡️" },
};

const money = (value) => {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
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
    names.some((name) => k.toLowerCase() === name.toLowerCase())
  );
  return key ? obj[key] : null;
};

function App() {
  const [scenarios, setScenarios] = useState(fallbackScenarios);
  const [personalities, setPersonalities] = useState(fallbackPersonalities);
  const [properties, setProperties] = useState([]);

  const [scenario, setScenario] = useState(2);
  const [propertyIndex, setPropertyIndex] = useState(0);
  const [humanRole, setHumanRole] = useState("buyer");
  const [aiPersonality, setAiPersonality] = useState("collaborative");
  const [maxRounds, setMaxRounds] = useState(10);

  const [session, setSession] = useState(null);
  const [message, setMessage] = useState("");
  const [offer, setOffer] = useState("");
  const [loading, setLoading] = useState(false);
  const [propertiesLoading, setPropertiesLoading] = useState(false);
  const [error, setError] = useState("");

  const selectedProperty = useMemo(
    () => properties.find((p) => p.index === Number(propertyIndex)),
    [properties, propertyIndex]
  );

  const propertyData = selectedProperty?.property || session?.property || {};

  const aiRole = session?.ai_role || (humanRole === "buyer" ? "seller" : "buyer");
  const aiPersonalityLabel =
    personalityMeta[session?.ai_personality || aiPersonality]?.label ||
    session?.ai_personality ||
    aiPersonality;

  useEffect(() => {
    loadMetadata();
  }, []);

  useEffect(() => {
    loadProperties(scenario);
  }, [scenario]);

  async function loadMetadata() {
    try {
      const [scenarioRes, personalityRes] = await Promise.all([
        fetch(`${API}/scenarios`),
        fetch(`${API}/personalities`),
      ]);

      if (scenarioRes.ok) {
        const data = await scenarioRes.json();
        setScenarios(data.scenarios || fallbackScenarios);
      }

      if (personalityRes.ok) {
        const data = await personalityRes.json();
        setPersonalities(data.personalities || fallbackPersonalities);
      }
    } catch {
      // Fallback values keep the UI usable if the backend is not running yet.
    }
  }

  async function loadProperties(selectedScenario) {
    setPropertiesLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API}/properties?scenario=${selectedScenario}&start=0&limit=100`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to load properties.");
      }

      setProperties(data.properties || []);
      setPropertyIndex(0);
    } catch (err) {
      setProperties([]);
      setError(
        `${err.message} Start the FastAPI backend on http://127.0.0.1:8000 if it is not running.`
      );
    } finally {
      setPropertiesLoading(false);
    }
  }

  async function startNegotiation() {
    setLoading(true);
    setError("");
    setSession(null);
    setMessage("");
    setOffer("");

    try {
      const response = await fetch(`${API}/negotiations/practice`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scenario: Number(scenario),
          property_index: Number(propertyIndex),
          human_role: humanRole,
          ai_personality: aiPersonality,
          max_rounds: Number(maxRounds),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not start negotiation.");
      }

      setSession({
        ...data,
        history: [
          {
            round: 0,
            sender: `ai_${data.ai_role}`,
            message: data.ai_message,
            decision: "INITIAL_GREETING",
            offer: data.ai_role === "seller"
              ? getValue(data.property, ["Price", "price", "Selling Price", "selling_price"])
              : null,
          },
        ],
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function sendMessage(event) {
    event?.preventDefault();
    if (!session || session.status !== "active" || !message.trim()) return;

    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API}/negotiations/${session.negotiation_id}/message`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: message.trim(),
            offer: offer === "" ? null : Number(offer),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to send message.");
      }

      const humanEntry = {
        round: data.round,
        sender: `human_${session.human_role}`,
        message: data.human_message,
        offer: data.human_offer,
      };

      const aiEntry = {
        round: data.round,
        sender: `ai_${session.ai_role}`,
        message: data.ai_response.message,
        offer: data.ai_response.counter_offer,
        decision: data.ai_response.decision,
        reason: data.ai_response.reason,
      };

      setSession((prev) => ({
        ...prev,
        status: data.status,
        history: [...(prev.history || []), humanEntry, aiEntry],
        latestDecision: data.ai_response,
        round: data.round,
      }));

      setMessage("");
      setOffer("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function cancelNegotiation() {
    if (!session) return;

    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API}/negotiations/${session.negotiation_id}/cancel`,
        { method: "POST" }
      );
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to cancel negotiation.");
      }

      setSession((prev) => ({
        ...prev,
        status: data.status,
        history: [
          ...(prev.history || []),
          {
            round: prev.round,
            sender: "system",
            message: data.message,
          },
        ],
      }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function refreshState() {
    if (!session) return;

    try {
      const response = await fetch(
        `${API}/negotiations/${session.negotiation_id}`
      );
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Unable to refresh state.");
      setSession((prev) => ({ ...prev, ...data }));
    } catch (err) {
      setError(err.message);
    }
  }

  const status = session?.status || "ready";
  const latestDecision = session?.latestDecision;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <div className="eyebrow">AI REAL ESTATE SIMULATION</div>
          <h1>Negotiation Arena</h1>
          <p>Practice real-world property negotiation with a multi-agent AI.</p>
        </div>
        <div className={`status-pill ${status}`}>
          <span className="status-dot" />
          {status.replace("_", " ").toUpperCase()}
        </div>
      </header>

      {error && (
        <div className="error-banner">
          <strong>Backend message:</strong> {error}
        </div>
      )}

      <main className="layout">
        <aside className="sidebar">
          <section className="panel setup-panel">
            <div className="panel-title">
              <span>01</span>
              Negotiation setup
            </div>

            <label>
              Scenario
              <select
                value={scenario}
                onChange={(e) => {
                  setScenario(Number(e.target.value));
                  setSession(null);
                }}
              >
                {Object.entries(scenarios).map(([key, value]) => (
                  <option key={key} value={key}>
                    {value}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Property
              <select
                value={propertyIndex}
                disabled={propertiesLoading || properties.length === 0}
                onChange={(e) => setPropertyIndex(Number(e.target.value))}
              >
                {properties.map((item) => {
                  const title =
                    getValue(item.property, [
                      "Property Title",
                      "Name",
                      "Property Name",
                    ]) || `Property ${item.index + 1}`;
                  return (
                    <option key={item.index} value={item.index}>
                      {item.index + 1}. {title}
                    </option>
                  );
                })}
              </select>
            </label>

            <label>
              Your role
              <div className="segmented">
                <button
                  className={humanRole === "buyer" ? "selected" : ""}
                  onClick={() => setHumanRole("buyer")}
                >
                  Buyer
                </button>
                <button
                  className={humanRole === "seller" ? "selected" : ""}
                  onClick={() => setHumanRole("seller")}
                >
                  Seller
                </button>
              </div>
            </label>

            <label>
              AI personality
              <select
                value={aiPersonality}
                onChange={(e) => setAiPersonality(e.target.value)}
              >
                {Object.entries(personalities).map(([key, value]) => (
                  <option key={key} value={String(value).toLowerCase().replace(/-/g, "_").replace(/ /g, "_")}>
                    {value}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Maximum rounds
              <input
                type="number"
                min="1"
                max="50"
                value={maxRounds}
                onChange={(e) => setMaxRounds(e.target.value)}
              />
            </label>

            <button
              className="primary-btn"
              onClick={startNegotiation}
              disabled={loading || properties.length === 0}
            >
              {loading && !session ? "Starting..." : "Start negotiation →"}
            </button>

            {session && (
              <button
                className="secondary-btn"
                onClick={refreshState}
                disabled={loading}
              >
                Refresh state
              </button>
            )}
          </section>

          <section className="panel property-panel">
            <div className="panel-title">
              <span>02</span>
              Property snapshot
            </div>

            <h2>
              {getValue(propertyData, [
                "Property Title",
                "Name",
                "Property Name",
              ]) || "Selected property"}
            </h2>

            <div className="property-price">
              {money(
                getValue(propertyData, [
                  "Price",
                  "price",
                  "Selling Price",
                  "selling_price",
                  "Property Price",
                ])
              )}
            </div>

            <div className="location">
              📍{" "}
              {getValue(propertyData, [
                "Location",
                "location",
                "Address",
                "address",
              ]) || "Location not provided"}
            </div>

            <div className="property-grid">
              {Object.entries(propertyData)
                .filter(([key]) => !["Price", "price"].includes(key))
                .slice(0, 8)
                .map(([key, value]) => (
                  <div className="property-field" key={key}>
                    <span>{prettyKey(key)}</span>
                    <strong>{String(value ?? "—")}</strong>
                  </div>
                ))}
            </div>
          </section>
        </aside>

        <section className="arena">
          <div className="arena-header">
            <div>
              <div className="eyebrow">LIVE SESSION</div>
              <h2>
                {session
                  ? `Session #${session.negotiation_id}`
                  : "Set up your negotiation"}
              </h2>
            </div>

            {session && (
              <div className="round-badge">
                Round {session.round || 1} / {session.max_rounds}
              </div>
            )}
          </div>

          <div className="agents-row">
            <AgentCard
              role={humanRole}
              name="You"
              personality="Human"
              active={Boolean(session)}
            />
            <div className="versus">VS</div>
            <AgentCard
              role={aiRole}
              name="AI Negotiator"
              personality={aiPersonalityLabel}
              active={Boolean(session)}
            />
          </div>

          <div className="transcript panel">
            <div className="transcript-head">
              <div>
                <h3>Negotiation transcript</h3>
                <span>
                  {session
                    ? "Every offer and AI decision appears here."
                    : "Start a session to begin the conversation."}
                </span>
              </div>
              {session && (
                <button
                  className="cancel-btn"
                  onClick={cancelNegotiation}
                  disabled={loading || status !== "active"}
                >
                  End session
                </button>
              )}
            </div>

            <div className="messages">
              {!session ? (
                <div className="empty-state">
                  <div className="empty-icon">💬</div>
                  <h3>Ready when you are</h3>
                  <p>
                    Choose a property, role and AI personality, then start the
                    negotiation.
                  </p>
                </div>
              ) : (
                session.history?.map((item, index) => (
                  <MessageBubble
                    key={`${index}-${item.timestamp || ""}`}
                    item={item}
                    humanRole={session.human_role}
                    aiRole={session.ai_role}
                  />
                ))
              )}
            </div>

            {session && status === "active" && (
              <form className="composer" onSubmit={sendMessage}>
                <div className="offer-input">
                  <span>₹</span>
                  <input
                    type="number"
                    min="0"
                    placeholder="Offer amount (optional)"
                    value={offer}
                    onChange={(e) => setOffer(e.target.value)}
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
                  onChange={(e) => setMessage(e.target.value)}
                />
                <button className="send-btn" disabled={loading || !message.trim()}>
                  {loading ? "..." : "Send"}
                </button>
              </form>
            )}

            {session && status !== "active" && (
              <div className={`result-banner ${status}`}>
                <strong>Negotiation {status}.</strong>
                {latestDecision?.message
                  ? " Review the final AI decision above."
                  : " Start a new session to negotiate again."}
              </div>
            )}
          </div>
        </section>

        <aside className="rightbar">
          <section className="panel reasoning-panel">
            <div className="panel-title">
              <span>03</span>
              AI reasoning
            </div>

            {latestDecision ? (
              <>
                <div className={`decision ${String(latestDecision.decision).toLowerCase()}`}>
                  {latestDecision.decision}
                </div>
                <h3>Decision analysis</h3>
                <p>
                  {latestDecision.reason ||
                    "The AI did not return a reasoning summary for this response."}
                </p>

                <div className="decision-price">
                  <span>Counter offer</span>
                  <strong>
                    {money(latestDecision.counter_offer)}
                  </strong>
                </div>
              </>
            ) : (
              <div className="reasoning-empty">
                <span>◎</span>
                <p>
                  Once the AI responds, its decision, counter-offer and
                  reasoning will appear here.
                </p>
              </div>
            )}
          </section>

          <section className="panel metrics-panel">
            <div className="panel-title">
              <span>04</span>
              Negotiation metrics
            </div>

            <Metric
              label="Reference price"
              value={money(session?.reference_price || getValue(propertyData, ["Price", "price"]))}
            />
            <Metric
              label="Current offer"
              value={money(session?.current_offer)}
            />
            <Metric
              label="Last human offer"
              value={money(session?.last_human_offer)}
            />
            <Metric
              label="Last AI offer"
              value={money(session?.last_ai_offer)}
            />
            <Metric
              label="Agreed price"
              value={money(session?.agreed_price)}
            />
            <Metric
              label="Stagnant rounds"
              value={session?.stagnant_round_count ?? 0}
            />
          </section>

          <section className="panel tip-panel">
            <div className="tip-icon">✦</div>
            <div>
              <strong>Negotiation tip</strong>
              <p>
                Make a clear numerical offer when possible. The backend can
                also extract an offer from your natural-language message.
              </p>
            </div>
          </section>
        </aside>
      </main>
    </div>
  );
}

function AgentCard({ role, name, personality, active }) {
  const meta =
    personalityMeta[String(personality).toLowerCase().replace(/-/g, "_")] ||
    { label: personality, icon: "◈" };

  return (
    <div className={`agent-card ${active ? "active" : ""}`}>
      <div className={`avatar ${role}`}>
        {role === "buyer" ? "B" : "S"}
      </div>
      <div>
        <span className="agent-role">{role}</span>
        <strong>{name}</strong>
        <small>
          {meta.icon} {meta.label}
        </small>
      </div>
    </div>
  );
}

function MessageBubble({ item, humanRole, aiRole }) {
  const isHuman = String(item.sender || "").startsWith("human");
  const isSystem = item.sender === "system";

  if (isSystem) {
    return (
      <div className="system-message">
        <span>•</span> {item.message}
      </div>
    );
  }

  return (
    <div className={`message-row ${isHuman ? "human" : "ai"}`}>
      <div className="message-meta">
        <span>{isHuman ? "You" : `AI ${aiRole}`}</span>
        <span>Round {item.round}</span>
      </div>
      <div className="bubble">
        <p>{item.message}</p>
        {item.offer !== null && item.offer !== undefined && (
          <div className="offer-chip">
            {isHuman ? "Offer" : "Counter"} · {money(item.offer)}
          </div>
        )}
      </div>
      {!isHuman && item.decision && (
        <div className={`inline-decision ${String(item.decision).toLowerCase()}`}>
          {item.decision}
        </div>
      )}
      {!isHuman && item.reason && (
        <div className="inline-reason">{item.reason}</div>
      )}
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);