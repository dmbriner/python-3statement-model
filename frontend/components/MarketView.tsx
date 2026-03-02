"use client";

import { useState, useTransition } from "react";

import { AppNav } from "@/components/AppNav";
import { CompanyWorkspace } from "@/components/CompanyWorkspace";
import { useAnalysis } from "@/components/AnalysisContext";
import { exportWorkbook } from "@/lib/api";

function downloadBase64(fileName: string, contentBase64: string) {
  const bytes = Uint8Array.from(atob(contentBase64), (char) => char.charCodeAt(0));
  const blob = new Blob([bytes], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function MarketView() {
  const { analysis } = useAnalysis();
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  function handleExport() {
    if (!analysis) return;
    startTransition(() => {
      void (async () => {
        try {
          const file = await exportWorkbook(analysis.ticker);
          downloadBase64(file.fileName, file.contentBase64);
          setError("");
        } catch {
          setError("Export failed.");
        }
      })();
    });
  }

  return (
    <div className="shell">
      <div className="hero">
        <div className="eyebrow">Market Workspace</div>
        <h1>Profile, exports, and research-facing workflow.</h1>
        <p>
          This page starts replacing the old research and export tabs with a proper market-facing
          workspace in Next.js.
        </p>
      </div>
      <AppNav />
      <div className="grid">
        <CompanyWorkspace />
        <div className="panel">
          <h2>Active Company Profile</h2>
          {!analysis ? (
            <p className="subtle">Analyze a company first.</p>
          ) : (
            <>
              <div className="list">
                <div className="listItem">
                  <strong>{analysis.company_name ?? analysis.ticker}</strong>
                  <div className="subtle">Ticker: {analysis.ticker}</div>
                </div>
                {Object.entries(analysis.profile ?? {})
                  .slice(0, 8)
                  .map(([key, value]) => (
                    <div className="listItem" key={key}>
                      <strong>{key}</strong>
                      <div className="subtle">{String(value ?? "—")}</div>
                    </div>
                  ))}
              </div>
              <div className="buttonRow" style={{ marginTop: 16 }}>
                <button className="button" onClick={handleExport} disabled={isPending}>
                  {isPending ? "Exporting..." : "Download Workbook"}
                </button>
              </div>
              {error ? <p className="subtle">{error}</p> : null}
            </>
          )}
        </div>
      </div>
      <div className="grid" style={{ marginTop: 24 }}>
        <div className="panel">
          <h2>Valuation Snapshot</h2>
          {!analysis?.valuation ? (
            <p className="subtle">Analyze a company first.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Method</th>
                  <th>Per Share</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>DCF</td>
                  <td>${analysis.valuation.dcf_per_share?.toFixed(2) ?? "—"}</td>
                </tr>
                <tr>
                  <td>Trading Comps</td>
                  <td>${analysis.valuation.comps_per_share?.toFixed(2) ?? "—"}</td>
                </tr>
                <tr>
                  <td>Precedents</td>
                  <td>${analysis.valuation.precedents_per_share?.toFixed(2) ?? "—"}</td>
                </tr>
                <tr>
                  <td>LBO</td>
                  <td>${analysis.valuation.lbo_per_share?.toFixed(2) ?? "—"}</td>
                </tr>
              </tbody>
            </table>
          )}
        </div>
        <div className="panel">
          <h2>Research Snapshot</h2>
          {!analysis?.research ? (
            <p className="subtle">Analyze a company first.</p>
          ) : (
            <div className="list">
              <div className="listItem">
                <strong>Provider</strong>
                <div className="subtle">{analysis.research.provider ?? "Not available"}</div>
              </div>
              <div className="listItem">
                <strong>Peers Returned</strong>
                <div className="subtle">{analysis.research.peer_count}</div>
              </div>
              {analysis.research.peers.slice(0, 4).map((peer) => (
                <div className="listItem" key={peer.symbol}>
                  <strong>
                    {peer.symbol} • {peer.name}
                  </strong>
                  <div className="subtle">
                    EV/Revenue: {peer.ev_revenue?.toFixed(1) ?? "—"}x | EV/EBITDA: {peer.ev_ebitda?.toFixed(1) ?? "—"}x
                  </div>
                </div>
              ))}
              {analysis.research.precedent_titles.slice(0, 3).map((title) => (
                <div className="listItem" key={title}>
                  <strong>Precedent</strong>
                  <div className="subtle">{title}</div>
                </div>
              ))}
              {analysis.research.analyst_snapshot ? (
                <div className="listItem">
                  <strong>Analyst Snapshot</strong>
                  <div className="subtle">
                    {Object.entries(analysis.research.analyst_snapshot)
                      .slice(0, 4)
                      .map(([key, value]) => `${key}: ${String(value ?? "—")}`)
                      .join(" | ")}
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
