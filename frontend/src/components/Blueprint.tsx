import { useState } from "react";
import { api } from "../api";
import { Card, Button, Spinner } from "./ui";
import Markdown from "./Markdown";
import ArchitectureDiagram from "./ArchitectureDiagram";

export default function Blueprint({ sessionId }: any) {
  const [bp, setBp] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function load() {
    if (!sessionId) return;
    setBusy(true); setErr("");
    try { setBp(await api.blueprint(sessionId)); }
    catch (e: any) {
      setErr(/404/.test(e.message)
        ? "Run the Workflow Analysis first — the blueprint is generated from it."
        : e.message);
    }
    finally { setBusy(false); }
  }

  function download() {
    if (!bp) return;
    const s = bp.suitability_score || {};
    const roi = bp.roi || {};
    const md = `# AgentSense Blueprint

**Readiness:** ${s.agent_score ?? "-"}/100 (${s.classification ?? "-"}) · Pattern: ${s.recommended_pattern ?? "-"}

## ROI
- Cost saved/yr: $${(roi.cost_saved_per_year || 0).toLocaleString()}
- ROI multiple: ${roi.roi_multiple || 0}x · Payback: ${roi.payback_months || 0} months

## Architecture
${bp.architecture_doc || ""}

## Mermaid Diagram
\`\`\`mermaid
${bp.mermaid_diagram || ""}
\`\`\`

## Cost Estimate
${bp.cost_estimate || ""}

## Roadmap
${bp.roadmap || ""}

## Code Scaffold
\`\`\`python
${bp.code_scaffold || ""}
\`\`\`
`;
    const blob = new Blob([md], { type: "text/markdown" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "AgentSense_Blueprint.md";
    a.click();
  }

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-extrabold">Implementation Blueprint</h1>
          <p className="text-slate-400 mt-1">Architecture, cost, roadmap and starter code — generated from the analysis.</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={load} disabled={!sessionId || busy}>Generate / Fetch</Button>
          {bp && <Button variant="ghost" onClick={download}>⬇ Export .md</Button>}
        </div>
      </header>

      {!sessionId && <Card><p className="text-amber-300 text-sm">⚠️ Run the analysis first.</p></Card>}
      {busy && <Card><Spinner label="Fetching blueprint…" /></Card>}
      {err && <Card><p className="text-rose-300 text-sm">❌ {err}</p></Card>}

      {bp && (
        <>
          <ArchitectureDiagram bp={bp} />
          <Card title="Architecture Document"><Markdown>{bp.architecture_doc || ""}</Markdown></Card>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <Card title="Cost Estimate"><Markdown>{bp.cost_estimate || ""}</Markdown></Card>
            <Card title="Roadmap"><Markdown>{bp.roadmap || ""}</Markdown></Card>
          </div>
          <Card title="Code Scaffold">
            <pre className="text-xs text-slate-200 bg-black/40 rounded-xl p-4 overflow-x-auto">{bp.code_scaffold}</pre>
          </Card>
          {bp.mermaid_diagram && (
            <details className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <summary className="cursor-pointer text-sm font-semibold text-violet-300">Show raw Mermaid source</summary>
              <pre className="text-xs text-emerald-200/90 bg-black/40 rounded-xl p-4 overflow-x-auto mt-3">{bp.mermaid_diagram}</pre>
            </details>
          )}
        </>
      )}
    </div>
  );
}
