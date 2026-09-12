import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

/*
 * API SERVICE
 *
 * Human vs AI and AI vs AI backend communication
 * is handled through negotiation-api.js.
 */
import {
  getScenarios,
  getPersonalities,
  getProperties,
  startNegotiation as startHumanVsAi,
  startAiVsAi,
  getNegotiationState,
  sendOffer,
  getNegotiationHistory,
  cancelNegotiation,
  downloadTranscript,
  downloadSummaryReport,
} from "../frontend/services/negotiation-api.js";

/*
 * METRICS COMPONENT
 */
import {
  renderMetrics,
} from "../frontend/components/negotiation-metrics.js";


/* =========================================================
   FALLBACK DATA
========================================================= */

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


/* =========================================================
   UTILITY FUNCTIONS
========================================================= */

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

  return new Intl.NumberFormat(
    "en-IN",
    {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }
  ).format(number);

};


const prettyKey = (key) =>
  String(key)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());


const getValue = (obj, names) => {

  if (!obj) {
    return null;
  }

  const key = Object.keys(obj).find((k) =>
    names.some(
      (name) =>
        k.toLowerCase() === name.toLowerCase()
    )
  );

  return key ? obj[key] : null;

};


/* =========================================================
   PERSONALITY HELPERS
========================================================= */

function getPersonalityLabel(value) {

  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return "Unknown";
  }

  /*
   * Backend AI-vs-AI endpoint uses:
   * 1 = Aggressive
   * 2 = Collaborative
   * 3 = Risk-Averse
   */
  const numericMap = {
    1: "Aggressive",
    2: "Collaborative",
    3: "Risk-Averse",
  };

  if (
    numericMap[
      Number(value)
    ]
  ) {
    return numericMap[
      Number(value)
    ];
  }

  const normalized =
    String(value)
      .toLowerCase()
      .replace(/-/g, "_")
      .replace(/ /g, "_");

  return (
    personalityMeta[
      normalized
    ]?.label ||
    String(value)
  );

}


/* =========================================================
   STATUS HELPERS
========================================================= */

function normalizeStatus(status) {

  const value =
    String(status || "")
      .toLowerCase();

  if (
    value === "agreement_reached" ||
    value === "accepted"
  ) {
    return "accepted";
  }

  if (
    value === "deadlock" ||
    value === "deadlocked"
  ) {
    return "deadlocked";
  }

  if (
    value === "rejected"
  ) {
    return "rejected";
  }

  if (
    value === "cancelled" ||
    value === "canceled"
  ) {
    return "cancelled";
  }

  return value || "ready";

}


/* =========================================================
   EXTRACT PRICE FROM AI MESSAGE
========================================================= */

/*
 * AI-vs-AI backend history contains the agent message.
 * The exact offer may also appear inside the message text.
 *
 * This helper tries to find prices such as:
 *
 * Buyer Offer: ₹50,00,000
 * COUNTEROFFER: ₹50,00,000
 * ACCEPTED OFFER: ₹50,00,000
 */
function extractPriceFromText(text) {

  if (!text) {
    return null;
  }

  const value = String(text);

  /* -------------------------------------------------------
     LAKHS
     Example: ₹71.18 lakhs
     71.18 × 100000 = ₹71,18,000
  ------------------------------------------------------- */

  const lakhMatch = value.match(
    /₹?\s*([\d,]+(?:\.\d+)?)\s*(?:lakhs?|lakh)\b/i
  );

  if (lakhMatch) {

    const number = Number(
      lakhMatch[1].replace(/,/g, "")
    );

    if (Number.isFinite(number)) {
      return number * 100000;
    }
  }

  /* -------------------------------------------------------
     CRORES
     Example: ₹2 crore
     2 × 10000000 = ₹2,00,00,000
  ------------------------------------------------------- */

  const croreMatch = value.match(
    /₹?\s*([\d,]+(?:\.\d+)?)\s*(?:crores?|crore)\b/i
  );

  if (croreMatch) {

    const number = Number(
      croreMatch[1].replace(/,/g, "")
    );

    if (Number.isFinite(number)) {
      return number * 10000000;
    }
  }

  /* -------------------------------------------------------
     DIRECT RUPEE VALUE
     Examples:
       ₹71,18,000
       Buyer Offer: ₹71,18,000
       COUNTEROFFER: ₹71,18,000
  ------------------------------------------------------- */

  const patterns = [

    /(?:buyer\s+offer|seller\s+offer)\s*:\s*₹?\s*([\d,]+(?:\.\d+)?)/i,

    /(?:counteroffer|counter\s+offer|accepted\s+offer|offer)\s*:\s*₹?\s*([\d,]+(?:\.\d+)?)/i,

    /₹\s*([\d,]+(?:\.\d+)?)/i,

  ];

  for (const pattern of patterns) {

    const match = value.match(pattern);

    if (match) {

      const number = Number(
        String(match[1]).replace(/,/g, "")
      );

      if (Number.isFinite(number)) {
        return number;
      }
    }
  }

  return null;
}

/* =========================================================
   NORMALIZE AI-VS-AI HISTORY
========================================================= */

function normalizeAiVsAiHistory(
  negotiationHistory = []
) {

  return negotiationHistory.map(
    (item, index) => {

      const agent =
        String(
          item.agent || ""
        ).toLowerCase();

      const isBuyer =
        agent.includes("buyer");

      const isSeller =
        agent.includes("seller");

      const sender =
        isBuyer
          ? "ai_buyer"
          : isSeller
            ? "ai_seller"
            : "system";

      const offer =
        extractPriceFromText(
          item.message
        );

      return {

        ...item,

        round:
          item.round ??
          0,

        sender,

        message:
          item.message ||
          "",

        offer,

        decision:
          item.decision ||
          null,

        reason:
          item.reason ||
          null,

        historyIndex:
          index,

      };

    }
  );

}


/* =========================================================
   EXTRACT LAST BUYER / SELLER OFFERS
========================================================= */

function getLastAgentOffers(
  history = []
) {

  let buyerOffer =
    null;

  let sellerOffer =
    null;

  /*
   * Search from the end so that
   * the latest offer wins.
   */
  for (
    let index =
      history.length - 1;
    index >= 0;
    index -= 1
  ) {

    const item =
      history[index];

    if (
      buyerOffer === null &&
      item.sender === "ai_buyer" &&
      item.offer !== null &&
      item.offer !== undefined
    ) {

      buyerOffer =
        item.offer;

    }

    if (
      sellerOffer === null &&
      item.sender === "ai_seller" &&
      item.offer !== null &&
      item.offer !== undefined
    ) {

      sellerOffer =
        item.offer;

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
   CLIENT EXPORT FORMATTERS (FALLBACK & ZERO-LATENCY)
========================================================= */

function triggerBrowserBlobDownload(content, filename, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

function formatClientTranscriptText(session, propertyData) {
  const propTitle = propertyData?.title || propertyData?.["Property Title"] || propertyData?.Property_Name || "Real Estate Property";
  const propLoc = propertyData?.Location || propertyData?.location || propertyData?.City || "N/A";
  const propArea = propertyData?.Total_Area || propertyData?.area || propertyData?.Area || "N/A";
  const refPrice = money(session.reference_price);
  const statusStr = (session.status || "UNKNOWN").toUpperCase();
  const agreedStr = session.agreed_price !== null && session.agreed_price !== undefined ? money(session.agreed_price) : "No Agreement";
  const modeStr = session.mode === "ai_ai" ? "AI vs AI Simulation" : "Human vs AI Practice";
  
  const sep = "=".repeat(80);
  const subSep = "-".repeat(80);
  const lines = [
    sep,
    "                   REAL ESTATE NEGOTIATION TRANSCRIPT",
    sep,
    `Negotiation ID   : ${session.negotiation_id}`,
    `Mode             : ${modeStr}`,
    `Generated At     : ${new Date().toLocaleString()}`,
    `Property Title   : ${propTitle}`,
    `Location         : ${propLoc}`,
    `Total Area       : ${propArea}`,
    `Reference Price  : ${refPrice}`,
    `Final Status     : ${statusStr}`,
    `Agreed Price     : ${agreedStr}`,
    `Rounds Completed : ${session.round || 0} / ${session.max_rounds || 10}`,
    sep,
    "",
    "DIALOGUE HISTORY:",
    ""
  ];

  (session.history || []).forEach((item) => {
    let speaker = item.sender || item.agent || "Participant";
    if (speaker.includes("human_buyer")) speaker = "Human (Buyer)";
    else if (speaker.includes("human_seller")) speaker = "Human (Seller)";
    else if (speaker.includes("ai_buyer") || speaker === "Buyer Agent") speaker = "Buyer Agent";
    else if (speaker.includes("ai_seller") || speaker === "Seller Agent") speaker = "Seller Agent";
    
    lines.push(subSep);
    lines.push(`[ROUND ${item.round ?? 0}] ${speaker.toUpperCase()}`);
    if (item.decision) lines.push(`Decision : ${item.decision}`);
    if (item.offer !== null && item.offer !== undefined) lines.push(`Offer    : ${money(item.offer)}`);
    lines.push(`Message  :\n  ${item.message || ""}`);
    if (item.reason) lines.push(`Reasoning: ${item.reason}`);
    lines.push("");
  });

  lines.push(sep);
  lines.push("                        END OF TRANSCRIPT");
  lines.push(sep);
  return lines.join("\n");
}

function formatClientTranscriptMarkdown(session, propertyData) {
  const propTitle = propertyData?.title || propertyData?.["Property Title"] || propertyData?.Property_Name || "Real Estate Property";
  const propLoc = propertyData?.Location || propertyData?.location || propertyData?.City || "N/A";
  const propArea = propertyData?.Total_Area || propertyData?.area || propertyData?.Area || "N/A";
  const refPrice = money(session.reference_price);
  const statusStr = (session.status || "UNKNOWN").toUpperCase();
  const agreedStr = session.agreed_price !== null && session.agreed_price !== undefined ? money(session.agreed_price) : "No Agreement";
  const modeStr = session.mode === "ai_ai" ? "AI vs AI Simulation" : "Human vs AI Practice";

  const lines = [
    `# 📜 Negotiation Transcript`,
    `**Session ID:** \`${session.negotiation_id}\`  `,
    `**Mode:** ${modeStr}  `,
    `**Generated:** ${new Date().toLocaleString()}  \n`,
    `## 📌 Property & Session Details`,
    `- **Property:** ${propTitle}`,
    `- **Location:** ${propLoc}`,
    `- **Area:** ${propArea}`,
    `- **Reference Price:** ${refPrice}`,
    `- **Final Outcome:** \`${statusStr}\``,
    `- **Agreed Price:** **${agreedStr}**`,
    `- **Rounds Completed:** ${session.round || 0} of ${session.max_rounds || 10}\n`,
    `---`,
    `## 💬 Round-by-Round Dialogue Log\n`
  ];

  (session.history || []).forEach((item) => {
    let speaker = item.sender || item.agent || "Participant";
    if (speaker.includes("human_buyer")) speaker = "Human (Buyer)";
    else if (speaker.includes("human_seller")) speaker = "Human (Seller)";
    else if (speaker.includes("ai_buyer") || speaker === "Buyer Agent") speaker = "Buyer Agent";
    else if (speaker.includes("ai_seller") || speaker === "Seller Agent") speaker = "Seller Agent";

    lines.push(`### Round ${item.round ?? 0} • ${speaker}`);
    if (item.decision) lines.push(`**Decision:** \`${item.decision}\`  `);
    if (item.offer !== null && item.offer !== undefined) lines.push(`**Offer:** \`${money(item.offer)}\`  `);
    lines.push(`\n> ${item.message || ""}\n`);
    if (item.reason) lines.push(`*Strategic Rationale:* ${item.reason}\n`);
    lines.push("");
  });

  lines.push(`---`, `*End of Transcript — Real Estate Negotiation Arena*`);
  return lines.join("\n");
}

function formatClientSummaryReportMarkdown(session, propertyData) {
  const propTitle = propertyData?.title || propertyData?.["Property Title"] || propertyData?.Property_Name || "Real Estate Property";
  const propLoc = propertyData?.Location || propertyData?.location || propertyData?.City || "N/A";
  const propArea = propertyData?.Total_Area || propertyData?.area || propertyData?.Area || "N/A";
  const propBhk = propertyData?.Bedrooms || propertyData?.BHK || propertyData?.bhk || "N/A";
  const propDesc = propertyData?.Description || propertyData?.description || "N/A";
  const refPrice = money(session.reference_price);
  const agreedStr = session.agreed_price !== null && session.agreed_price !== undefined ? money(session.agreed_price) : "N/A (No Agreement)";
  const statusStr = (session.status || "UNKNOWN").toUpperCase();
  const modeStr = session.mode === "ai_ai" ? "AI vs AI Simulation" : "Human vs AI Practice";

  const lines = [
    `# 📊 Real Estate Negotiation Summary Report`,
    `> **Session ID:** \`${session.negotiation_id}\` | **Mode:** ${modeStr} | **Date:** ${new Date().toLocaleString()}\n`,
    `## 🏆 1. Executive Summary`,
    `| Metric | Value |`,
    `| :--- | :--- |`,
    `| **Final Status** | \`${statusStr}\` |`,
    `| **Agreed Price** | **${agreedStr}** |`,
    `| **Reference / Listing Price** | ${refPrice} |`,
    `| **Rounds Utilized** | ${session.round || 0} / ${session.max_rounds || 10} |`
  ];

  if (session.deadlock_reason) {
    lines.push(`| **Impasse / Deadlock Reason** | *${session.deadlock_reason}* |`);
  }

  lines.push(
    "",
    `## 🏡 2. Property Overview`,
    `- **Property Name:** ${propTitle}`,
    `- **Location:** ${propLoc}`,
    `- **Area & Configuration:** ${propArea} | ${propBhk} BHK`,
    `- **Description Snippet:** *${String(propDesc).slice(0, 200)}...*`,
    "",
    `## 📈 3. Offer & Counteroffer Progression`,
    `| Round | Speaker | Action / Decision | Offer | Snippet |`,
    `| :---: | :--- | :---: | :---: | :--- |`
  );

  let hasOffers = false;
  (session.history || []).forEach((item) => {
    if (item.offer !== null && item.offer !== undefined) {
      hasOffers = true;
      let speaker = item.sender || item.agent || "Participant";
      if (speaker.includes("human")) speaker = "Human";
      else if (speaker.includes("buyer")) speaker = "Buyer Agent";
      else if (speaker.includes("seller")) speaker = "Seller Agent";
      const snippet = (item.message || "").replace(/[\r\n]+/g, " ").slice(0, 60);
      lines.push(`| ${item.round ?? 0} | ${speaker} | \`${item.decision || "OFFER"}\` | **${money(item.offer)}** | ${snippet}... |`);
    }
  });

  if (!hasOffers) {
    lines.push(`*No numeric offers were exchanged during this session.*`);
  }

  lines.push(
    "",
    `## 💡 4. Strategic Observations`,
    session.status === "accepted" || session.status === "agreement_reached"
      ? `✅ **Successful Deal:** The parties successfully converged to an agreed price of **${agreedStr}** within ${session.round || 0} rounds.`
      : session.status === "deadlocked"
      ? `⚠️ **Negotiation Deadlock:** The parties reached an impasse without further concession. ${session.deadlock_reason || ""}`
      : `ℹ️ **Negotiation Concluded:** Session completed with status \`${statusStr}\`.`,
    "",
    `---`,
    `*Generated by AI-Driven Multi-Agent Negotiation Training & Simulation Platform*`
  );

  return lines.join("\n");
}

function formatClientSummaryReportText(session, propertyData) {
  const propTitle = propertyData?.title || propertyData?.["Property Title"] || propertyData?.Property_Name || "Real Estate Property";
  const propLoc = propertyData?.Location || propertyData?.location || propertyData?.City || "N/A";
  const propArea = propertyData?.Total_Area || propertyData?.area || propertyData?.Area || "N/A";
  const propBhk = propertyData?.Bedrooms || propertyData?.BHK || propertyData?.bhk || "N/A";
  const refPrice = money(session.reference_price);
  const agreedStr = session.agreed_price !== null && session.agreed_price !== undefined ? money(session.agreed_price) : "N/A (No Agreement)";
  const statusStr = (session.status || "UNKNOWN").toUpperCase();
  const modeStr = session.mode === "ai_ai" ? "AI vs AI Simulation" : "Human vs AI Practice";

  const sep = "=".repeat(80);
  const subSep = "-".repeat(80);
  const lines = [
    sep,
    "                 REAL ESTATE NEGOTIATION SUMMARY REPORT",
    sep,
    `Negotiation ID   : ${session.negotiation_id}`,
    `Mode             : ${modeStr}`,
    `Generated At     : ${new Date().toLocaleString()}`,
    `Final Outcome    : ${statusStr}`,
    `Rounds Used      : ${session.round || 0} of ${session.max_rounds || 10}`,
    sep,
    "",
    "1. PROPERTY PROFILE",
    `   Property Title: ${propTitle}`,
    `   Location      : ${propLoc}`,
    `   Area / Config : ${propArea} | ${propBhk} BHK`,
    `   Reference Val : ${refPrice}`,
    "",
    "2. FINANCIAL OUTCOME",
    `   Reference Price : ${refPrice}`,
    `   Agreed Price    : ${agreedStr}`,
  ];

  if (session.deadlock_reason) {
    lines.push(`   Deadlock Reason : ${session.deadlock_reason}`);
  }

  lines.push("", "3. OFFERS TIMELINE", subSep);
  lines.push(`${"Rnd".padEnd(4)} | ${"Speaker".padEnd(24)} | ${"Decision".padEnd(12)} | ${"Offer".padEnd(18)}`);
  lines.push(subSep);

  (session.history || []).forEach((item) => {
    if (item.offer !== null && item.offer !== undefined) {
      let speaker = item.sender || item.agent || "Participant";
      if (speaker.includes("human")) speaker = "Human";
      else if (speaker.includes("buyer")) speaker = "Buyer Agent";
      else if (speaker.includes("seller")) speaker = "Seller Agent";
      lines.push(`${String(item.round ?? 0).padEnd(4)} | ${speaker.slice(0, 24).padEnd(24)} | ${String(item.decision || "OFFER").slice(0, 12).padEnd(12)} | ${money(item.offer).padEnd(18)}`);
    }
  });

  lines.push(sep, "                      END OF SUMMARY REPORT", sep);
  return lines.join("\n");
}


/* =========================================================
   MAIN APP
========================================================= */

function App() {

  /* -------------------------------------------------------
     BACKEND METADATA
  ------------------------------------------------------- */

  const [scenarios, setScenarios] =
    useState(
      fallbackScenarios
    );

  const [personalities, setPersonalities] =
    useState(
      fallbackPersonalities
    );

  const [properties, setProperties] =
    useState([]);


  /* -------------------------------------------------------
     NEGOTIATION SETUP
  ------------------------------------------------------- */

  const [scenario, setScenario] =
    useState(2);

  const [propertyIndex, setPropertyIndex] =
    useState(0);

  /*
   * NEW:
   *
   * human_ai = Human vs AI
   * ai_ai    = AI vs AI
   */
  const [negotiationMode, setNegotiationMode] =
    useState("human_ai");


  /* -------------------------------------------------------
     HUMAN VS AI SETTINGS
  ------------------------------------------------------- */

  const [humanRole, setHumanRole] =
    useState("buyer");

  const [aiPersonality, setAiPersonality] =
    useState("collaborative");


  /* -------------------------------------------------------
     AI VS AI SETTINGS
  ------------------------------------------------------- */

  const [buyerPersonality, setBuyerPersonality] =
    useState(2);

  const [sellerPersonality, setSellerPersonality] =
    useState(2);


  /* -------------------------------------------------------
     COMMON SETTINGS
  ------------------------------------------------------- */

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
     DOWNLOAD STATES
  ------------------------------------------------------- */

  const [downloadingTranscript, setDownloadingTranscript] =
    useState(false);

  const [downloadingReport, setDownloadingReport] =
    useState(false);

  const [transcriptMenuOpen, setTranscriptMenuOpen] =
    useState(false);

  const [reportMenuOpen, setReportMenuOpen] =
    useState(false);


  /* =======================================================
     SELECTED PROPERTY
  ======================================================= */

  const selectedProperty =
    useMemo(

      () =>
        properties.find(
          (p) =>
            p.index ===
            Number(propertyIndex)
        ),

      [
        properties,
        propertyIndex,
      ]

    );


  const propertyData =
    selectedProperty?.property ||
    session?.property ||
    {};


  /* =======================================================
     AI ROLE
  ======================================================= */

  const aiRole =
    session?.mode === "ai_ai"
      ? "seller"
      : session?.ai_role ||
        (
          humanRole === "buyer"
            ? "seller"
            : "buyer"
        );


  /* =======================================================
     HUMAN VS AI PERSONALITY LABEL
  ======================================================= */

  const aiPersonalityLabel =
    getPersonalityLabel(
      session?.ai_personality ||
      aiPersonality
    );


  /* =======================================================
     INITIAL LOAD
  ======================================================= */

  useEffect(() => {

    loadMetadata();

  }, []);


  /* =======================================================
     LOAD PROPERTIES WHEN SCENARIO CHANGES
  ======================================================= */

  useEffect(() => {

    loadProperties(
      scenario
    );

  }, [scenario]);


  /* =======================================================
     LOAD SCENARIOS + PERSONALITIES
  ======================================================= */

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


  /* =======================================================
     LOAD PROPERTIES
  ======================================================= */

  async function loadProperties(
    selectedScenario
  ) {

    setPropertiesLoading(
      true
    );

    setError("");


    try {

      const data =
        await getProperties(
          selectedScenario,
          0,
          100
        );


      setProperties(
        data.properties ||
        []
      );


      setPropertyIndex(
        0
      );

    } catch (err) {

      setProperties([]);

      setError(

        `${err.message} Make sure the FastAPI backend is running on http://127.0.0.1:8000`

      );

    } finally {

      setPropertiesLoading(
        false
      );

    }

  }


  /* =======================================================
     START HUMAN VS AI
  ======================================================= */

  async function runHumanVsAi() {

    const data =
      await startHumanVsAi({

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

        round:
          0,

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

      mode:
        "human_ai",

      history:
        initialHistory,

      latestDecision:
        null,

    });


    /*
     * Get the latest backend state.
     *
     * This keeps metrics synchronized with
     * the backend state.
     */
    try {

      const latestState =
        await getNegotiationState(
          data.negotiation_id
        );


      setSession(
        (prev) => ({

          ...prev,

          ...latestState,

          mode:
            "human_ai",

          history:
            latestState.history ||
            initialHistory,

        })
      );

    } catch (stateError) {

      console.log(
        "Initial state refresh failed:",
        stateError
      );

    }

  }


  /* =======================================================
     START AI VS AI
  ======================================================= */

  async function runAiVsAi() {

    /*
     * AI-vs-AI endpoint is a complete simulation.
     *
     * Backend runs Buyer Agent and Seller Agent
     * automatically and returns the complete result.
     */
    const data =
      await startAiVsAi({

        scenario:
          Number(scenario),

        propertyIndex:
          Number(propertyIndex),

        buyerPersonality:
          Number(buyerPersonality),

        sellerPersonality:
          Number(sellerPersonality),

        maxRounds:
          Number(maxRounds),

      });


    /*
     * Convert backend history into the same format
     * used by the React transcript.
     */
    const normalizedHistory =
      normalizeAiVsAiHistory(
        data.negotiation_history ||
        []
      );


    const agentOffers =
      getLastAgentOffers(
        normalizedHistory
      );


    /*
     * Current offer:
     *
     * Prefer the latest parsed buyer/seller offer.
     */
    const currentOffer =
      agentOffers.sellerOffer ??
      agentOffers.buyerOffer ??
      data.agreed_price ??
      null;


    /*
     * Backend can return:
     *
     * AGREEMENT_REACHED
     * DEADLOCK
     * REJECTED
     *
     * Convert to UI-friendly values.
     */
    const normalizedStatus =
      normalizeStatus(
        data.status
      );


    /*
     * Build a session object so the same
     * UI can display the simulation.
     */
    const aiSession = {

      mode:
        "ai_ai",

      negotiation_id:
        data.negotiation_id ||
        `ai-ai-${Date.now()}`,

      status:
        normalizedStatus,

      original_status:
        data.status,

      round:
        Number(maxRounds),

      max_rounds:
        Number(maxRounds),

      human_role:
        null,

      ai_role:
        null,

      ai_personality:
        null,

      buyer_personality:
        data.buyer_personality,

      seller_personality:
        data.seller_personality,

      property:
        data.property,

      reference_price:
        getValue(
          data.property,
          [
            "Price",
            "price",
            "Selling Price",
            "selling_price",
            "Property Price",
          ]
        ),

      current_offer:
        currentOffer,

      last_buyer_offer:
        agentOffers.buyerOffer,

      last_seller_offer:
        agentOffers.sellerOffer,

      agreed_price:
        data.agreed_price,

      stagnant_round_count:
        data.stalled_rounds ??
        data.current_state?.stalled_rounds ??
        data.current_state?.stagnant_round_count ??
        0,

      deadlock_reason:
        data.current_state
          ?.deadlock_reason ??
        (
          normalizedStatus ===
          "deadlocked"
            ? "Buyer and Seller stopped making meaningful progress."
            : null
        ),

      history:
        normalizedHistory,

      latestDecision:
        null,

      simulation_result:
        data,

    };


    setSession(
      aiSession
    );

  }


  /* =======================================================
     START SELECTED NEGOTIATION MODE
  ======================================================= */

  async function handleStartNegotiation() {

    setLoading(
      true
    );

    setError("");

    setSession(
      null
    );

    setMessage("");

    setOffer("");


    try {

      if (
        negotiationMode ===
        "ai_ai"
      ) {

        await runAiVsAi();

      } else {

        await runHumanVsAi();

      }

    } catch (err) {

      setError(
        err.message
      );

    } finally {

      setLoading(
        false
      );

    }

  }


  /* =======================================================
     SEND HUMAN MESSAGE / OFFER
  ======================================================= */

  async function handleSendMessage(
    event
  ) {

    event?.preventDefault();


    /*
     * AI-vs-AI does not use the human composer.
     */
    if (
      session?.mode ===
      "ai_ai"
    ) {

      return;

    }


    if (
      !session ||
      session.status !==
        "active" ||
      !message.trim()
    ) {

      return;

    }


    setLoading(
      true
    );

    setError("");


    try {

      const humanOffer =
        offer === ""

          ? null

          : Number(
              offer
            );


      /*
       * Send through YOUR API SERVICE.
       */
      const data =
        await sendOffer(

          session.negotiation_id,

          message.trim(),

          humanOffer

        );


      /*
       * Human message.
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
       * AI response.
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
       * Get complete latest state.
       *
       * This ensures metrics use backend state.
       */
      let latestState =
        null;


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


      setSession(
        (prev) => ({

          ...prev,

          ...(latestState || {}),

          mode:
            "human_ai",

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
              data.status ===
              "accepted"

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

          deadlock_reason:
            latestState?.deadlock_reason ??
            prev.deadlock_reason ??
            null,

        })
      );


      setMessage("");

      setOffer("");


    } catch (err) {

      setError(
        err.message
      );

    } finally {

      setLoading(
        false
      );

    }

  }


  /* =======================================================
     CANCEL HUMAN VS AI NEGOTIATION
  ======================================================= */

  async function handleCancelNegotiation() {

    if (!session) {
      return;
    }


    /*
     * AI-vs-AI simulation has already finished.
     * There is no human-controlled active session to cancel.
     */
    if (
      session.mode ===
      "ai_ai"
    ) {

      return;

    }


    setLoading(
      true
    );

    setError("");


    try {

      const data =
        await cancelNegotiation(
          session.negotiation_id
        );


      setSession(
        (prev) => ({

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

        })
      );

    } catch (err) {

      setError(
        err.message
      );

    } finally {

      setLoading(
        false
      );

    }

  }


  /* =======================================================
     REFRESH HUMAN VS AI STATE
  ======================================================= */

  async function refreshState() {

    if (!session) {
      return;
    }


    /*
     * Current AI-vs-AI endpoint returns the complete
     * simulation in one response, so there is no need
     * to poll it here.
     */
    if (
      session.mode ===
      "ai_ai"
    ) {

      return;

    }


    try {

      const data =
        await getNegotiationState(
          session.negotiation_id
        );


      setSession(
        (prev) => ({

          ...prev,

          ...data,

          mode:
            "human_ai",

        })
      );


      /*
       * Also refresh complete history.
       */
      try {

        const historyData =
          await getNegotiationHistory(
            session.negotiation_id
          );


        if (
          historyData?.history
        ) {

          setSession(
            (prev) => ({

              ...prev,

              history:
                historyData.history,

            })
          );

        }

      } catch (historyError) {

        console.log(
          "History refresh failed:",
          historyError
        );

      }

    } catch (err) {

      setError(
        err.message
      );

    }

  }


  /* =======================================================
     DOWNLOAD TRANSCRIPT HANDLER
  ======================================================= */

  async function handleDownloadTranscript(format = "txt") {
    if (!session?.negotiation_id) {
      return;
    }

    setDownloadingTranscript(true);
    setError("");

    try {
      await downloadTranscript(session.negotiation_id, format);
    } catch (err) {
      console.warn("Backend transcript download failed; using client-side fallback:", err);

      try {
        if (format === "json") {
          const jsonData = JSON.stringify({
            negotiation_id: session.negotiation_id,
            mode: session.mode,
            status: session.status,
            round: session.round,
            max_rounds: session.max_rounds,
            property: propertyData,
            agreed_price: session.agreed_price,
            reference_price: session.reference_price,
            history: session.history || []
          }, null, 2);
          triggerBrowserBlobDownload(
            jsonData,
            `negotiation_transcript_${session.negotiation_id}.json`,
            "application/json"
          );
        } else if (format === "md" || format === "markdown") {
          const mdContent = formatClientTranscriptMarkdown(session, propertyData);
          triggerBrowserBlobDownload(
            mdContent,
            `negotiation_transcript_${session.negotiation_id}.md`,
            "text/markdown; charset=utf-8"
          );
        } else {
          const txtContent = formatClientTranscriptText(session, propertyData);
          triggerBrowserBlobDownload(
            txtContent,
            `negotiation_transcript_${session.negotiation_id}.txt`,
            "text/plain; charset=utf-8"
          );
        }
      } catch (fallbackError) {
        setError("Failed to download transcript: " + fallbackError.message);
      }
    } finally {
      setDownloadingTranscript(false);
    }
  }


  /* =======================================================
     DOWNLOAD SUMMARY REPORT HANDLER
  ======================================================= */

  async function handleDownloadSummaryReport(format = "md") {
    if (!session?.negotiation_id) {
      return;
    }

    setDownloadingReport(true);
    setError("");

    try {
      await downloadSummaryReport(session.negotiation_id, format);
    } catch (err) {
      console.warn("Backend summary report download failed; using client-side fallback:", err);

      try {
        if (format === "json") {
          const jsonData = JSON.stringify({
            negotiation_id: session.negotiation_id,
            mode: session.mode,
            status: session.status,
            round: session.round,
            max_rounds: session.max_rounds,
            property: propertyData,
            agreed_price: session.agreed_price,
            reference_price: session.reference_price,
            history: session.history || []
          }, null, 2);
          triggerBrowserBlobDownload(
            jsonData,
            `negotiation_summary_report_${session.negotiation_id}.json`,
            "application/json"
          );
        } else if (format === "txt") {
          const txtContent = formatClientSummaryReportText(session, propertyData);
          triggerBrowserBlobDownload(
            txtContent,
            `negotiation_summary_report_${session.negotiation_id}.txt`,
            "text/plain; charset=utf-8"
          );
        } else {
          const mdContent = formatClientSummaryReportMarkdown(session, propertyData);
          triggerBrowserBlobDownload(
            mdContent,
            `negotiation_summary_report_${session.negotiation_id}.md`,
            "text/markdown; charset=utf-8"
          );
        }
      } catch (fallbackError) {
        setError("Failed to download summary report: " + fallbackError.message);
      }
    } finally {
      setDownloadingReport(false);
    }
  }


  /* =======================================================
     STATUS
  ======================================================= */

  const status =
    session?.status ||
    "ready";


  const latestDecision =
    session?.latestDecision;


  /* =======================================================
     METRICS DATA
  ======================================================= */

  const metricsData =
    session ||
    {

      round:
        0,

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

      last_buyer_offer:
        null,

      last_seller_offer:
        null,

      agreed_price:
        null,

      stagnant_round_count:
        0,

    };


  const metricsMode =
    session?.mode ===
    "ai_ai"

      ? "ai_ai"

      : "human_ai";


  /* =======================================================
     AGENT DISPLAY DATA
  ======================================================= */

  const isAiVsAi =
    negotiationMode ===
      "ai_ai" ||
    session?.mode ===
      "ai_ai";


  const displayedBuyerPersonality =
    session?.mode ===
      "ai_ai"

      ? getPersonalityLabel(
          session.buyer_personality
        )

      : "Human";


  const displayedSellerPersonality =
    session?.mode ===
      "ai_ai"

      ? getPersonalityLabel(
          session.seller_personality
        )

      : aiPersonalityLabel;


  /* =======================================================
     UI
  ======================================================= */

  return (

    <div className="app-shell">


      {/* ===================================================
         HEADER
      =================================================== */}

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


      {/* ===================================================
         ERROR
      =================================================== */}

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


          {/* =================================================
             NEGOTIATION SETUP
          ================================================= */}

          <section className="panel setup-panel">

            <div className="panel-title">

              <span>
                01
              </span>

              Negotiation setup

            </div>


            {/* =============================================
               MODE
            ============================================= */}

            <label>

              Negotiation mode

              <select

                value={
                  negotiationMode
                }

                onChange={
                  (e) => {

                    const newMode =
                      e.target.value;

                    setNegotiationMode(
                      newMode
                    );

                    /*
                     * Start with a clean session
                     * whenever the mode changes.
                     */
                    setSession(
                      null
                    );

                    setMessage("");

                    setOffer("");

                    setError("");

                  }
                }

              >

                <option
                  value="human_ai"
                >
                  Human vs AI
                </option>

                <option
                  value="ai_ai"
                >
                  AI vs AI
                </option>

              </select>

            </label>


            {/* =============================================
               SCENARIO
            ============================================= */}

            <label>

              Scenario

              <select

                value={
                  scenario
                }

                onChange={
                  (e) => {

                    setScenario(
                      Number(
                        e.target.value
                      )
                    );

                    setSession(
                      null
                    );

                  }
                }

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


            {/* =============================================
               PROPERTY
            ============================================= */}

            <label>

              Property

              <select

                value={
                  propertyIndex
                }

                disabled={

                  propertiesLoading ||
                  properties.length === 0

                }

                onChange={
                  (e) =>
                    setPropertyIndex(
                      Number(
                        e.target.value
                      )
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
                        key={
                          item.index
                        }
                        value={
                          item.index
                        }
                      >

                        {item.index + 1}.{" "}

                        {title}

                      </option>

                    );

                  }
                )}

              </select>

            </label>


            {/* =================================================
               HUMAN VS AI SETTINGS
            ================================================= */}

            {!isAiVsAi && (

              <>

                {/* YOUR ROLE */}

                <label>

                  Your role

                  <div
                    className="segmented"
                  >

                    <button
                      type="button"

                      className={
                        humanRole ===
                        "buyer"
                          ? "selected"
                          : ""
                      }

                      onClick={() =>
                        setHumanRole(
                          "buyer"
                        )
                      }

                    >
                      Buyer
                    </button>


                    <button
                      type="button"

                      className={
                        humanRole ===
                        "seller"
                          ? "selected"
                          : ""
                      }

                      onClick={() =>
                        setHumanRole(
                          "seller"
                        )
                      }

                    >
                      Seller
                    </button>

                  </div>

                </label>


                {/* AI PERSONALITY */}

                <label>

                  AI personality

                  <select

                    value={
                      aiPersonality
                    }

                    onChange={
                      (e) =>
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
                            .replace(
                              /-/g,
                              "_"
                            )
                            .replace(
                              / /g,
                              "_"
                            );

                        return (

                          <option
                            key={key}
                            value={
                              normalized
                            }
                          >
                            {value}
                          </option>

                        );

                      }
                    )}

                  </select>

                </label>

              </>

            )}


            {/* =================================================
               AI VS AI SETTINGS
            ================================================= */}

            {isAiVsAi && (

              <>

                {/* BUYER PERSONALITY */}

                <label>

                  Buyer AI personality

                  <select

                    value={
                      buyerPersonality
                    }

                    onChange={
                      (e) =>
                        setBuyerPersonality(
                          Number(
                            e.target.value
                          )
                        )
                    }

                  >

                    <option value="1">
                      Aggressive
                    </option>

                    <option value="2">
                      Collaborative
                    </option>

                    <option value="3">
                      Risk-Averse
                    </option>

                  </select>

                </label>


                {/* SELLER PERSONALITY */}

                <label>

                  Seller AI personality

                  <select

                    value={
                      sellerPersonality
                    }

                    onChange={
                      (e) =>
                        setSellerPersonality(
                          Number(
                            e.target.value
                          )
                        )
                    }

                  >

                    <option value="1">
                      Aggressive
                    </option>

                    <option value="2">
                      Collaborative
                    </option>

                    <option value="3">
                      Risk-Averse
                    </option>

                  </select>

                </label>

              </>

            )}


            {/* =================================================
               MAXIMUM ROUNDS
            ================================================= */}

            <label>

              Maximum rounds

              <input

                type="number"

                min="1"

                max="50"

                value={
                  maxRounds
                }

                onChange={
                  (e) =>
                    setMaxRounds(
                      e.target.value
                    )
                }

              />

            </label>


            {/* =================================================
               START BUTTON
            ================================================= */}

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

              {loading

                ? (
                    isAiVsAi
                      ? "Running AI simulation..."
                      : "Starting..."
                  )

                : (
                    isAiVsAi
                      ? "Run AI vs AI →"
                      : "Start negotiation →"
                  )

              }

            </button>


            {/* =================================================
               REFRESH
            ================================================= */}

            {session &&
              !isAiVsAi && (

                <button

                  type="button"

                  className="secondary-btn"

                  onClick={
                    refreshState
                  }

                  disabled={
                    loading
                  }

                >

                  Refresh state

                </button>

              )}

          </section>


          {/* =================================================
             PROPERTY SNAPSHOT
          ================================================= */}

          <section className="panel property-panel">

            <div className="panel-title">

              <span>
                02
              </span>

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

                .slice(
                  0,
                  8
                )

                .map(
                  ([key, value]) => (

                    <div
                      className="property-field"
                      key={key}
                    >

                      <span>
                        {prettyKey(
                          key
                        )}
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
           CENTER ARENA
        ================================================= */}

        <section className="arena">


          {/* =================================================
             ARENA HEADER
          ================================================= */}

          <div className="arena-header">

            <div>

              <div className="eyebrow">

                {isAiVsAi
                  ? "AI VS AI SIMULATION"
                  : "LIVE SESSION"}

              </div>

              <h2>

                {session

                  ? `Session #${session.negotiation_id}`

                  : (
                      isAiVsAi
                        ? "Set up AI vs AI simulation"
                        : "Set up your negotiation"
                    )

                }

              </h2>

            </div>


            {session && (

              <div
                className="round-badge"
              >

                {session.mode ===
                "ai_ai"

                  ? `Simulation • ${session.round || session.max_rounds} rounds`

                  : (
                      <>
                        Round{" "}
                        {session.round || 1}
                        {" / "}
                        {session.max_rounds}
                      </>
                    )

                }

              </div>

            )}

          </div>


          {/* =================================================
             AGENTS
          ================================================= */}

          <div className="agents-row">


            {isAiVsAi ? (

              <>

                <AgentCard

                  role="buyer"

                  name="AI Buyer"

                  personality={
                    displayedBuyerPersonality
                  }

                  active={
                    Boolean(
                      session
                    )
                  }

                />


                <div className="versus">
                  VS
                </div>


                <AgentCard

                  role="seller"

                  name="AI Seller"

                  personality={
                    displayedSellerPersonality
                  }

                  active={
                    Boolean(
                      session
                    )
                  }

                />

              </>

            ) : (

              <>

                <AgentCard

                  role={
                    humanRole
                  }

                  name="You"

                  personality="Human"

                  active={
                    Boolean(
                      session
                    )
                  }

                />


                <div className="versus">
                  VS
                </div>


                <AgentCard

                  role={
                    aiRole
                  }

                  name="AI Negotiator"

                  personality={
                    aiPersonalityLabel
                  }

                  active={
                    Boolean(
                      session
                    )
                  }

                />

              </>

            )}

          </div>


          {/* =================================================
             TRANSCRIPT
          ================================================= */}

          <div className="transcript panel">

            <div
              className="transcript-head"
            >

              <div>

                <h3>
                  {isAiVsAi
                    ? "AI vs AI negotiation transcript"
                    : "Negotiation transcript"
                  }
                </h3>

                <span>

                  {session

                    ? (
                        isAiVsAi
                          ? "Buyer Agent and Seller Agent completed the simulation automatically."
                          : "Every offer and AI decision appears here."
                      )

                    : (
                        isAiVsAi
                          ? "Choose two AI personalities and run the simulation."
                          : "Start a session to begin the conversation."
                      )

                  }

                </span>

              </div>


              <div className="transcript-actions">

                {session && session.history && session.history.length > 0 && (
                  <div className="download-dropdown-wrap">
                    <button
                      type="button"
                      className="download-btn secondary"
                      onClick={() => setTranscriptMenuOpen(!transcriptMenuOpen)}
                      disabled={downloadingTranscript}
                      title="Export negotiation transcript"
                    >
                      <span>📄</span>
                      <span>
                        {downloadingTranscript ? "Exporting..." : "Export Transcript"}
                      </span>
                      <span className="dropdown-arrow">▾</span>
                    </button>

                    {transcriptMenuOpen && (
                      <div className="dropdown-menu">
                        <button
                          type="button"
                          className="dropdown-item"
                          onClick={() => {
                            setTranscriptMenuOpen(false);
                            handleDownloadTranscript("txt");
                          }}
                        >
                          <div className="item-title">Plain Text (.txt)</div>
                          <div className="item-desc">Clean conversation log</div>
                        </button>
                        <button
                          type="button"
                          className="dropdown-item"
                          onClick={() => {
                            setTranscriptMenuOpen(false);
                            handleDownloadTranscript("md");
                          }}
                        >
                          <div className="item-title">Markdown (.md)</div>
                          <div className="item-desc">GitHub-flavored markdown</div>
                        </button>
                        <button
                          type="button"
                          className="dropdown-item"
                          onClick={() => {
                            setTranscriptMenuOpen(false);
                            handleDownloadTranscript("json");
                          }}
                        >
                          <div className="item-title">Structured JSON (.json)</div>
                          <div className="item-desc">Full session & history payload</div>
                        </button>
                      </div>
                    )}
                  </div>
                )}

                {session &&
                  !isAiVsAi && (

                    <button

                      type="button"

                      className="cancel-btn"

                      onClick={
                        handleCancelNegotiation
                      }

                      disabled={

                        loading ||
                        status !==
                          "active"

                      }

                    >
                      End session
                    </button>

                  )}

              </div>

            </div>


            {/* =================================================
               MESSAGES
            ================================================= */}

            <div className="messages">

              {!session ? (

                <div
                  className="empty-state"
                >

                  <div
                    className="empty-icon"
                  >
                    💬
                  </div>

                  <h3>
                    Ready when you are
                  </h3>

                  <p>

                    {isAiVsAi

                      ? "Choose a property and two AI personalities, then run the simulation."

                      : "Choose a property, role and AI personality, then start the negotiation."

                    }

                  </p>

                </div>

              ) : (

                session.history?.map(
                  (item, index) => (

                    <MessageBubble

                      key={
                        `${index}-${item.timestamp || ""}-${item.historyIndex || ""}`
                      }

                      item={
                        item
                      }

                      humanRole={
                        session.human_role
                      }

                      aiRole={
                        session.ai_role
                      }

                      aiVsAi={
                        session.mode ===
                        "ai_ai"
                      }

                    />

                  )
                )

              )}

            </div>


            {/* =================================================
               HUMAN COMPOSER
            ================================================= */}

            {session &&
              !isAiVsAi &&
              status ===
                "active" && (

                <form

                  className="composer"

                  onSubmit={
                    handleSendMessage
                  }

                >

                  <div
                    className="offer-input"
                  >

                    <span>
                      ₹
                    </span>

                    <input

                      type="number"

                      min="0"

                      placeholder="Offer amount (optional)"

                      value={
                        offer
                      }

                      onChange={
                        (e) =>
                          setOffer(
                            e.target.value
                          )
                      }

                    />

                  </div>


                  <input

                    className="message-input"

                    placeholder={

                      humanRole ===
                      "buyer"

                        ? "Write your offer or negotiation message..."

                        : "Write your asking price or negotiation message..."

                    }

                    value={
                      message
                    }

                    onChange={
                      (e) =>
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


            {/* =================================================
               AI VS AI RESULT
            ================================================= */}

            {session &&
              isAiVsAi && (

                <div
                  className={`result-banner ${status}`}
                >

                  <div>
                    <strong>

                      AI vs AI simulation{" "}
                      {status
                        .replace(
                          /_/g,
                          " "
                        )
                        .toUpperCase()}.

                    </strong>

                    {session.agreed_price !==
                      null &&
                      session.agreed_price !==
                      undefined && (

                      <span>

                        {" "}
                        Agreed price:{" "}

                        {money(
                          session.agreed_price
                        )}

                      </span>

                    )}
                  </div>

                  <div className="completion-actions">
                    <button
                      type="button"
                      className="download-btn secondary"
                      onClick={() => handleDownloadTranscript("txt")}
                      disabled={downloadingTranscript}
                    >
                      <span>📄</span> Export Transcript
                    </button>

                    <button
                      type="button"
                      className="download-btn primary"
                      onClick={() => handleDownloadSummaryReport("html")}
                      disabled={downloadingReport}
                    >
                      <span>📊</span> Download Summary Report
                    </button>
                  </div>

                </div>

              )}


            {/* =================================================
               HUMAN VS AI RESULT
            ================================================= */}

            {session &&
              !isAiVsAi &&
              status !==
                "active" && (

                <div
                  className={`result-banner ${status}`}
                >

                  <div>
                    <strong>

                      Negotiation{" "}
                      {status}.

                    </strong>

                    {latestDecision?.message

                      ? " Review the final AI decision above."

                      : " Start a new session to negotiate again."

                    }
                  </div>

                  <div className="completion-actions">
                    <button
                      type="button"
                      className="download-btn secondary"
                      onClick={() => handleDownloadTranscript("txt")}
                      disabled={downloadingTranscript}
                    >
                      <span>📄</span> Export Transcript
                    </button>

                    <button
                      type="button"
                      className="download-btn primary"
                      onClick={() => handleDownloadSummaryReport("html")}
                      disabled={downloadingReport}
                    >
                      <span>📊</span> Download Summary Report
                    </button>
                  </div>

                </div>

              )}

          </div>

        </section>


        {/* =================================================
           RIGHT SIDEBAR
        ================================================= */}

        <aside className="rightbar">


          {/* =================================================
             AI REASONING / RESULT
          ================================================= */}

          <section className="panel reasoning-panel">

            <div
              className="panel-title"
            >

              <span>
                03
              </span>

              {isAiVsAi
                ? "AI simulation result"
                : "AI reasoning"}

            </div>


            {isAiVsAi ? (

              session ? (

                <>

                  <div
                    className={`decision ${status}`}
                  >

                    {status
                      .replace(
                        /_/g,
                        " "
                      )
                      .toUpperCase()}

                  </div>


                  <h3>
                    AI vs AI summary
                  </h3>


                  <p>

                    Buyer AI personality:{" "}
                    <strong>
                      {getPersonalityLabel(
                        session.buyer_personality
                      )}
                    </strong>

                    <br />

                    Seller AI personality:{" "}
                    <strong>
                      {getPersonalityLabel(
                        session.seller_personality
                      )}
                    </strong>

                  </p>


                  <div
                    className="decision-price"
                  >

                    <span>
                      Agreed price
                    </span>

                    <strong>

                      {money(
                        session.agreed_price
                      )}

                    </strong>

                  </div>

                </>

              ) : (

                <div
                  className="reasoning-empty"
                >

                  <span>
                    ◎
                  </span>

                  <p>

                    Run the AI vs AI simulation
                    to see the final result.

                  </p>

                </div>

              )

            ) : (

              latestDecision ? (

                <>

                  <div
                    className={`decision ${String(
                      latestDecision.decision
                    ).toLowerCase()}`}
                  >

                    {
                      latestDecision.decision
                    }

                  </div>


                  <h3>
                    Decision analysis
                  </h3>


                  <p>

                    {
                      latestDecision.reason ||
                      "The AI did not return a reasoning summary for this response."
                    }

                  </p>


                  <div
                    className="decision-price"
                  >

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

                <div
                  className="reasoning-empty"
                >

                  <span>
                    ◎
                  </span>

                  <p>

                    Once the AI responds,
                    its decision, counter-offer
                    and reasoning will appear here.

                  </p>

                </div>

              )

            )}

          </section>


          {/* =================================================
             NEGOTIATION METRICS
          ================================================= */}

          <section className="panel metrics-panel">

            <div
              className="panel-title"
            >

              <span>
                04
              </span>

              Negotiation metrics

            </div>


            <div
              dangerouslySetInnerHTML={{
                __html:
                  renderMetrics(
                    metricsData,
                    metricsMode
                  ),
              }}
            />

          </section>


          {/* =================================================
             NEGOTIATION SUMMARY REPORT PANEL
          ================================================= */}

          {session && (
            <section className="panel report-panel">

              <div
                className="panel-title"
              >

                <span>
                  05
                </span>

                Summary Report

              </div>

              <div className="report-box">

                <div className="report-info">
                  <strong>Executive Summary Report</strong>
                  <p>
                    Download a comprehensive summary report with property details, agent profiles, deal metrics, and round-by-round offer progression.
                  </p>
                </div>

                <div className="download-dropdown-wrap full-width">
                  <button
                    type="button"
                    className="download-btn primary full-width"
                    onClick={() => setReportMenuOpen(!reportMenuOpen)}
                    disabled={downloadingReport}
                    title="Download negotiation summary report"
                  >
                    <span>📊</span>
                    <span>
                      {downloadingReport ? "Generating Report..." : "Download Summary Report"}
                    </span>
                    <span className="dropdown-arrow">▾</span>
                  </button>

                  {reportMenuOpen && (
                    <div className="dropdown-menu full-width">
                      <button
                        type="button"
                        className="dropdown-item"
                        onClick={() => {
                          setReportMenuOpen(false);
                          handleDownloadSummaryReport("md");
                        }}
                      >
                        <div className="item-title">Markdown Report (.md)</div>
                        <div className="item-desc">Structured tables & formatted text</div>
                      </button>
                      <button
                        type="button"
                        className="dropdown-item"
                        onClick={() => {
                          setReportMenuOpen(false);
                          handleDownloadSummaryReport("txt");
                        }}
                      >
                        <div className="item-title">Plain Text (.txt)</div>
                        <div className="item-desc">ASCII table & plain report</div>
                      </button>
                      <button
                        type="button"
                        className="dropdown-item"
                        onClick={() => {
                          setReportMenuOpen(false);
                          handleDownloadSummaryReport("json");
                        }}
                      >
                        <div className="item-title">Structured JSON (.json)</div>
                        <div className="item-desc">Complete analytics payload</div>
                      </button>
                    </div>
                  )}
                </div>

              </div>

            </section>
          )}


          {/* =================================================
             TIP
          ================================================= */}

          <section className="panel tip-panel">

            <div className="tip-icon">
              ✦
            </div>

            <div>

              <strong>
                Negotiation tip
              </strong>

              <p>

                {isAiVsAi

                  ? "AI vs AI runs automatically. Review the transcript, offers, final status and agreed price."

                  : "Make a clear numerical offer when possible. The backend can also extract an offer from your natural-language message."

                }

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
      String(
        personality
      )
        .toLowerCase()
        .replace(
          /-/g,
          "_"
        )
    ] || {

      label:
        personality,

      icon:
        "◈",

    };


  return (

    <div
      className={`agent-card ${
        active
          ? "active"
          : ""
      }`}
    >

      <div
        className={`avatar ${role}`}
      >

        {role ===
        "buyer"

          ? "B"

          : "S"

        }

      </div>


      <div>

        <span
          className="agent-role"
        >
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
  aiVsAi = false,
}) {

  const sender =
    String(
      item.sender || ""
    );


  const isHuman =
    sender.startsWith(
      "human"
    );


  const isSystem =
    sender === "system";


  const isBuyerAi =
    sender ===
    "ai_buyer";


  const isSellerAi =
    sender ===
    "ai_seller";


  /* -------------------------------------------------------
     SYSTEM MESSAGE
  ------------------------------------------------------- */

  if (isSystem) {

    return (

      <div
        className="system-message"
      >

        <span>
          •
        </span>{" "}

        {item.message}

      </div>

    );

  }


  /* -------------------------------------------------------
     DISPLAY NAME
  ------------------------------------------------------- */

  let speakerName =
    "AI";


  if (aiVsAi) {

    if (
      isBuyerAi
    ) {

      speakerName =
        "AI Buyer";

    } else if (
      isSellerAi
    ) {

      speakerName =
        "AI Seller";

    } else {

      speakerName =
        item.agent ||
        "AI";

    }

  } else {

    speakerName =
      isHuman

        ? "You"

        : `AI ${aiRole}`;

  }


  /* -------------------------------------------------------
     OFFER LABEL
  ------------------------------------------------------- */

  let offerLabel =
    "Offer";


  if (
    !isHuman
  ) {

    offerLabel =
      "Counter";

  }


  if (
    aiVsAi
  ) {

    offerLabel =
      isBuyerAi
        ? "Buyer Offer"
        : isSellerAi
          ? "Seller Offer"
          : "Offer";

  }


  return (

    <div
      className={`message-row ${
        isHuman ||
        isBuyerAi
          ? "human"
          : "ai"
      }`}
    >

      <div
        className="message-meta"
      >

        <span>
          {speakerName}
        </span>


        <span>

          Round{" "}
          {item.round}

        </span>

      </div>


      <div
        className="bubble"
      >

        <p>
          {item.message}
        </p>


        {item.offer !==
          null &&
          item.offer !==
          undefined && (

            <div
              className="offer-chip"
            >

              {offerLabel}

              {" · "}

              {money(
                item.offer
              )}

            </div>

          )}

      </div>


      {!aiVsAi &&
        !isHuman &&
        item.decision && (

          <div
            className={`inline-decision ${String(
              item.decision
            ).toLowerCase()}`}
          >

            {item.decision}

          </div>

        )}


      {!aiVsAi &&
        !isHuman &&
        item.reason && (

          <div
            className="inline-reason"
          >

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
  document.getElementById(
    "root"
  )
).render(

  <React.StrictMode>

    <App />

  </React.StrictMode>

);
