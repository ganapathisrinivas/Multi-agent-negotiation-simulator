import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity, Bot, Building2, Clock3, Gauge, History, Home, Pause, Play,
  RotateCcw, Settings2, ShieldCheck, Sparkles, Target, TrendingDown,
  TrendingUp, Users, CheckCircle2, XCircle, ChevronRight
} from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import "./styles.css";

const initialRounds = [
  { round: 1, seller: 85, buyer: 75 },
  { round: 2, seller: 84, buyer: 77 },
  { round: 3, seller: 82, buyer: 78 },
  { round: 4, seller: 82, buyer: 79 },
];

const scriptedRounds = [
  { agent: "seller", title: "Initial Offer", amount: 85, text: "The property is in a high-demand area and has recently renovated interiors.", rationale: "Start near the asking price and test the buyer's willingness to negotiate." },
  { agent: "buyer", title: "Counter Offer", amount: 75, text: "Comparable properties suggest a lower market range, so the buyer is starting conservatively.", rationale: "Anchor below the asking price while leaving enough room for future concessions." },
  { agent: "seller", title: "Counter Offer", amount: 82, text: "The seller is willing to make a limited concession because of the buyer's seriousness.", rationale: "Protect the seller's target while signaling that a deal is possible." },
  { agent: "buyer", title: "Counter Offer", amount: 79, text: "The buyer increases the offer while keeping within the approved budget.", rationale: "Move closer to the seller without revealing the maximum approved budget." },
  { agent: "seller", title: "Counter Offer", amount: 81, text: "The seller narrows the gap after reviewing the buyer's latest position.", rationale: "A smaller concession is justified because the gap is closing." },
  { agent: "buyer", title: "Counter Offer", amount: 80, text: "The buyer makes a final balanced move based on market value and budget.", rationale: "Reach the buyer's preferred ceiling to maximize the probability of agreement." },
  { agent: "seller", title: "Final Offer", amount: 80, text: "The seller accepts the buyer's position and is ready to close at ₹80L.", rationale: "The price is close enough to the seller's reservation point to justify closing." },
];

const agentData = {
  seller:{name:"Seller Agent", icon:"🏠", tone:"orange", stance:"Firm", score:76, target:"₹82L", role:"Property Owner"},
  buyer:{name:"Buyer Agent", icon:"🧑", tone:"blue", stance:"Flexible", score:62, target:"₹80L", role:"Buyer Representative"},
  broker:{name:"Broker Agent", icon:"🤝", tone:"purple", stance:"Neutral", score:50, target:"₹80L", role:"Mediator"},
  evaluator:{name:"Evaluator", icon:"📊", tone:"green", stance:"Analytical", score:88, target:"₹80L", role:"Outcome Judge"},
};

function money(v){ return `₹${v},00,000`; }

function AgentCard({type, active, onClick}) {
  const a = agentData[type];
  return <button className={`agent-card ${active ? "active": ""}`} onClick={onClick}>
    <span className={`avatar ${a.tone}`}>{a.icon}</span>
    <span className="agent-copy"><strong>{a.name}</strong><small>{a.role}</small><span className="mini-bar"><i style={{width:`${a.score}%`}} /></span></span>
    <span className="stance">{a.stance}</span>
  </button>;
}

function TranscriptItem({item}) {
  const a = agentData[item.agent];
  return <div className={`message ${item.agent}`}>
    <div className="message-head"><span className={`avatar tiny ${a.tone}`}>{a.icon}</span><strong>{a.name}</strong><span className="time">{item.time}</span></div>
    <div className="message-body">
      <div className="message-top"><span className="pill">{item.title}</span><strong>{money(item.amount)}</strong></div>
      <p>{item.text}</p>
      <div className="message-rationale"><Sparkles size={12}/><span><b>Decision factor:</b> {item.rationale}</span></div>
    </div>
  </div>;
}

function App(){
  const [activeAgent,setActiveAgent] = useState("seller");
  const [running,setRunning] = useState(false);
  const [round,setRound] = useState(4);
  const [tab,setTab] = useState("arena");
  const [speed,setSpeed] = useState(2);
  const [finished,setFinished] = useState(false);

  const transcript = useMemo(() => scriptedRounds.slice(0, Math.min(round, scriptedRounds.length)).map((m,i)=>({...m,time:`11:${String(2+i).padStart(2,"0")}`})), [round]);
  const offers = useMemo(() => {
    const result = [...initialRounds];
    if(round >= 5) result.push({round:5,seller:81,buyer:79});
    if(round >= 6) result.push({round:6,seller:81,buyer:80});
    if(round >= 7) result.push({round:7,seller:80,buyer:80});
    return result.filter(x => x.round <= Math.max(4, round));
  }, [round]);
  const current = offers[offers.length - 1];
  const gap = Math.max(0,current.seller-current.buyer);
  const status = finished ? "Agreement reached" : gap <= 1 ? "Agreement likely" : "Negotiation active";
  const progress = Math.min(100, Math.round((round/7)*100));

  const nextRound=()=>{
    if(round < 7) setRound(r=>r+1);
    else { setRound(7); setFinished(true); setRunning(false); }
  };
  const reset=()=>{setRound(1);setFinished(false);setRunning(false);setActiveAgent("seller")};

  return <div className="app">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Home size={19}/></div><div><b>RealNegotiate</b><small>Multi-Agent Simulator</small></div></div>
      <div className="side-section"><span className="side-label">WORKSPACE</span>
        {[["dashboard","Dashboard",Gauge],["properties","Properties",Building2],["agents","Agents",Bot],["arena","Negotiation Arena",Activity],["history","History",History]].map(([id,label,Icon])=><button key={id} className={tab===id?"nav active":"nav"} onClick={()=>setTab(id)}><Icon size={18}/>{label}</button>)}
      </div>
      <div className="side-section"><span className="side-label">LIVE AGENTS</span>{Object.keys(agentData).map(k=><AgentCard key={k} type={k} active={activeAgent===k} onClick={()=>setActiveAgent(k)}/>)}</div>
      <div className="sidebar-bottom"><button className="nav"><Settings2 size={18}/>Simulation Settings</button><div className="user-chip"><div className="user-avatar">S</div><div><b>Simulator</b><small>Admin workspace</small></div></div></div>
    </aside>

    <main className="main">
      <header className="topbar"><div><div className="eyebrow">SESSION / RN-2048</div><h1>Negotiation Arena</h1></div><div className="top-actions"><span className="live"><i/> LIVE</span><button className="icon-btn"><Clock3 size={17}/></button><button className="avatar user">S</button></div></header>

      {tab!=="arena" ? <div className="placeholder"><Sparkles size={34}/><h2>{tab[0].toUpperCase()+tab.slice(1)}</h2><p>The workspace is ready. Open Negotiation Arena to run the multi-agent simulation.</p><button onClick={()=>setTab("arena")}>Open Arena <ChevronRight size={15}/></button></div> :
      <div className="content">
        <section className="arena-col">
          <div className="arena-header"><div><span className="section-kicker">PROPERTY NEGOTIATION</span><h2>3 BHK Apartment · Hyderabad</h2></div><div className="round"><span>ROUND</span><b>{round}</b><small>/ 7</small></div></div>
          <div className="progress-wrap"><div className="progress-label"><span>Negotiation progress</span><b>{progress}%</b></div><div className="progress-track"><i style={{width:`${progress}%`}}/></div></div>
          <div className="status-strip"><div><span>ASKING PRICE</span><b>₹85L</b></div><div><span>CURRENT SELLER</span><b>₹{current.seller}L</b></div><div><span>CURRENT BUYER</span><b>₹{current.buyer}L</b></div><div><span>PRICE GAP</span><b className={gap<=1?"good":""}>₹{gap}L</b></div></div>

          <div className="transcript">
            {transcript.map((m,i)=><TranscriptItem item={m} key={i}/>)}
            {!finished && <div className="typing"><span className="avatar tiny purple">🤝</span><span>Broker Agent is evaluating the latest offer</span><i/><i/><i/></div>}
          </div>

          <div className="control-panel">
            <div className="control-title"><div><b>Simulation Control</b><small>Run the agents round-by-round</small></div><span className={`status-dot ${finished?"complete":""}`}><i/> {status}</span></div>
            <div className="controls"><button className="primary" onClick={()=>setRunning(!running)} disabled={finished}>{running?<Pause size={17}/>:<Play size={17}/>} {running?"Pause":"Start Simulation"}</button><button onClick={nextRound} disabled={finished}>Next Round</button><button onClick={reset}><RotateCcw size={16}/> Reset</button><label>Speed <select value={speed} onChange={e=>setSpeed(e.target.value)}><option>1</option><option>2</option><option>4</option></select>x</label></div>
          </div>

          {finished && <div className="agreement-card"><div className="agreement-icon"><CheckCircle2 size={25}/></div><div><span className="section-kicker">NEGOTIATION COMPLETE</span><h2>Agreement Reached</h2><p>Both agents converged on a mutually acceptable price.</p></div><div className="final-price"><span>FINAL PRICE</span><b>₹80,00,000</b></div></div>}
        </section>

        <aside className="right-col">
          <div className="panel property"><div className="property-image"><div className="image-overlay">VERIFIED PROPERTY</div><div className="building">⌂</div></div><div className="panel-pad"><div className="panel-head"><div><span className="section-kicker">PROPERTY</span><h3>Modern 3 BHK Residence</h3></div><ShieldCheck size={19}/></div><div className="property-location">Gachibowli · Hyderabad</div><div className="price-row"><div><span>Asking Price</span><b>₹85,00,000</b></div><div><span>Market Estimate</span><b>₹81,50,000</b></div></div><div className="facts"><span><b>1,850</b> sq.ft</span><span><b>3</b> Beds</span><span><b>2</b> Baths</span></div></div></div>

          <div className="panel stance-panel"><div className="panel-pad"><div className="panel-head"><div><span className="section-kicker">ACTIVE AGENT</span><h3>{agentData[activeAgent].name}</h3></div><span className={`avatar ${agentData[activeAgent].tone}`}>{agentData[activeAgent].icon}</span></div><div className="stance-line"><span>STANCE</span><b>{agentData[activeAgent].stance}</b></div><div className="stance-track"><span style={{left:`${agentData[activeAgent].score}%`}}/></div><div className="stance-labels"><span>Flexible</span><span>Firm</span></div><div className="factor"><span>Market value</span><b>90%</b><i><em style={{width:"90%"}}/></i></div><div className="factor"><span>Concession room</span><b>40%</b><i><em style={{width:"40%"}}/></i></div><div className="factor"><span>Closing pressure</span><b>30%</b><i><em style={{width:"30%"}}/></i></div><div className="reason"><Sparkles size={15}/><div><b>Decision rationale</b><p>{scriptedRounds[Math.min(round-1, scriptedRounds.length-1)].rationale}</p></div></div></div></div>

          <div className="panel chart-panel"><div className="panel-pad"><div className="panel-head"><div><span className="section-kicker">OFFER MOVEMENT</span><h3>Price convergence</h3></div><TrendingDown size={18}/></div><div className="chart"><ResponsiveContainer width="100%" height={165}><LineChart data={offers}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="round" tickFormatter={v=>`R${v}`}/><YAxis domain={[70,90]} tickFormatter={v=>`₹${v}L`}/><Tooltip formatter={(v)=>[`₹${v}L`]} labelFormatter={v=>`Round ${v}`}/><Line type="monotone" dataKey="seller" strokeWidth={3} dot={{r:3}}/><Line type="monotone" dataKey="buyer" strokeWidth={3} dot={{r:3}}/></LineChart></ResponsiveContainer></div><div className="legend"><span><i className="seller-dot"/>Seller</span><span><i className="buyer-dot"/>Buyer</span></div></div></div>

          <div className="panel stance-history"><div className="panel-pad"><div className="panel-head"><div><span className="section-kicker">STANCE EVOLUTION</span><h3>Seller position</h3></div><TrendingUp size={18}/></div><div className="history-row"><span>R1</span><b>Firm</b><i style={{width:"90%"}}/></div><div className="history-row"><span>R3</span><b>Firm</b><i style={{width:"76%"}}/></div><div className="history-row"><span>R5</span><b>Moderate</b><i style={{width:"61%"}}/></div><div className="history-row"><span>R7</span><b>Flexible</b><i style={{width:"50%"}}/></div></div></div>
        </aside>
      </div>}
    </main>
  </div>;
}

createRoot(document.getElementById("root")).render(<App/>);
