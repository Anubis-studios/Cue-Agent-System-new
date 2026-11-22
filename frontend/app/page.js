"use client";
import { useState, useEffect } from "react";
import { API_BASE } from "@/lib/api";

export default function Home() {
  const [msg, setMsg] = useState("");
  const [reply, setReply] = useState("");
  const [provider, setProvider] = useState("");
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState([]);
  const [useTools, setUseTools] = useState(true);

  useEffect(() => {
    const saved = localStorage.getItem("cue_history");
    if (saved) setHistory(JSON.parse(saved));
  }, []);

  useEffect(() => {
    localStorage.setItem("cue_history", JSON.stringify(history.slice(-20)));
  }, [history]);

  async function send() {
    if (!msg.trim()) return;
    setBusy(true); setReply(""); setProvider("");
    const userMessage = msg; setMsg("");
    
    try {
      const res = await fetch(`${API_BASE}/api/chat/default`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage, use_tools: useTools }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Request failed");
      const data = await res.json();
      setReply(data.reply); setProvider(data.provider);
      setHistory(prev => [...prev, 
        { role: "user", content: userMessage, timestamp: new Date().toISOString() },
        { role: "assistant", content: data.reply, provider: data.provider, timestamp: new Date().toISOString() }
      ]);
    } catch (e) { setReply(`Error: ${e.message}`); setProvider("error"); } 
    finally { setBusy(false); }
  }

  function clearHistory() { setHistory([]); localStorage.removeItem("cue_history"); }

  return (
    <main className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center border-b border-gray-800 pb-4">
        <div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">Cue Agent System</h1>
          <p className="text-gray-400 mt-1">Multi-agent AI with free LLM providers</p>
        </div>
        <button onClick={clearHistory} className="px-3 py-1 text-sm bg-gray-800 hover:bg-gray-700 rounded">Clear History</button>
      </div>

      <div className="flex gap-4 items-center bg-gray-900/50 p-4 rounded-lg border border-gray-800">
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" checked={useTools} onChange={(e) => setUseTools(e.target.checked)} className="w-4 h-4" />
          <span className="text-sm text-gray-300">Enable Tools</span>
        </label>
      </div>

      {history.length > 0 && (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {history.map((item, idx) => (
            <div key={idx} className={`p-4 rounded-lg border ${item.role === "user" ? "bg-gray-900/70 border-gray-800 ml-12" : "bg-indigo-900/20 border-indigo-800/50 mr-12"}`}>
              <div className="flex justify-between items-start mb-2">
                <span className={`text-xs font-semibold ${item.role === "user" ? "text-gray-400" : "text-indigo-400"}`}>
                  {item.role === "user" ? "You" : `AI (${item.provider || "unknown"})`}
                </span>
                <span className="text-xs text-gray-600">{new Date(item.timestamp).toLocaleTimeString()}</span>
              </div>
              <div className="text-sm whitespace-pre-wrap">{item.content}</div>
            </div>
          ))}
        </div>
      )}

      <div className="space-y-3">
        <textarea className="w-full p-4 rounded-lg bg-gray-900 border border-gray-700 focus:border-indigo-500 focus:outline-none resize-none" 
          rows={4} value={msg} onChange={(e) => setMsg(e.target.value)} 
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }}} 
          placeholder="Ask your agents anything..." disabled={busy} />
        
        <div className="flex justify-between items-center">
          <div className="text-xs text-gray-500">
            {provider && <span className="px-2 py-1 bg-gray-800 rounded">Last provider: <span className="text-indigo-400">{provider}</span></span>}
          </div>
          <button className="px-6 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-lg hover:from-indigo-500 hover:to-purple-500 disabled:opacity-50 transition-all font-medium" 
            onClick={send} disabled={busy || !msg.trim()}>
            {busy ? "Thinking..." : "Send"}
          </button>
        </div>
      </div>

      {reply && !history.length && (
        <div className="p-4 rounded-lg bg-indigo-900/20 border border-indigo-800/50">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-semibold text-indigo-400">AI ({provider})</span>
          </div>
          <div className="text-sm whitespace-pre-wrap">{reply}</div>
        </div>
      )}

      <footer className="text-center text-xs text-gray-600 pt-8 border-t border-gray-800">Powered by free LLM providers</footer>
    </main>
  );
}
