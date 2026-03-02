"use client";

import { AppNav } from "@/components/AppNav";
import { CompanyWorkspace } from "@/components/CompanyWorkspace";
import { useAnalysis } from "@/components/AnalysisContext";

function renderCell(value: unknown) {
  if (typeof value === "number") {
    return value.toLocaleString();
  }
  return String(value ?? "—");
}

export function ModelView() {
  const { analysis } = useAnalysis();
  const annualRows = analysis?.historical_annual ?? [];
  const latestAnnual = annualRows[annualRows.length - 1];
  const latestRevenue = typeof latestAnnual?.revenue === "number" ? latestAnnual.revenue : null;
  const latestCogs = typeof latestAnnual?.cogs === "number" ? latestAnnual.cogs : null;
  const latestOpex = typeof latestAnnual?.opex === "number" ? latestAnnual.opex : null;
  const grossMargin =
    latestRevenue && latestCogs !== null ? ((latestRevenue - latestCogs) / latestRevenue) * 100 : null;
  const opexRatio = latestRevenue && latestOpex !== null ? (latestOpex / latestRevenue) * 100 : null;

  return (
    <div className="shell">
      <div className="hero">
        <div className="eyebrow">Model Workspace</div>
        <h1>Historicals and scenarios in one place.</h1>
        <p>
          This page starts replacing the old Streamlit model tabs with a dedicated model workspace
          in Next.js.
        </p>
      </div>
      <AppNav />
      <div className="grid">
        <CompanyWorkspace />
        <div className="panel">
          <h2>Scenario Outputs</h2>
          {!analysis ? (
            <p className="subtle">Analyze a company first.</p>
          ) : (
            <div className="list">
              {Object.entries(analysis.scenarios).map(([name, scenario]) => (
                <div className="listItem" key={name}>
                  <strong>{name}</strong>
                  <div className="subtle">Revenue: ${scenario.revenue_final_year.toLocaleString()}</div>
                  <div className="subtle">EBITDA: ${scenario.ebitda_final_year.toLocaleString()}</div>
                  <div className="subtle">Net Income: ${scenario.net_income_final_year.toLocaleString()}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="metrics" style={{ marginTop: 24 }}>
        <div className="metricCard">
          <div className="metricLabel">Latest Revenue</div>
          <div className="metricValue">{latestRevenue !== null ? `$${latestRevenue.toLocaleString()}` : "—"}</div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Gross Margin</div>
          <div className="metricValue">{grossMargin !== null ? `${grossMargin.toFixed(1)}%` : "—"}</div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">OpEx / Revenue</div>
          <div className="metricValue">{opexRatio !== null ? `${opexRatio.toFixed(1)}%` : "—"}</div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Quarterly Rows</div>
          <div className="metricValue">{analysis ? analysis.historical_quarterly.length : "—"}</div>
        </div>
      </div>
      <div className="panel" style={{ marginTop: 24 }}>
        <h2>Annual Historical Preview</h2>
        {!analysis ? (
          <p className="subtle">Analyze a company first.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                {Object.keys(analysis.historical_annual[0] ?? {}).slice(0, 8).map((key) => (
                  <th key={key}>{key}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {analysis.historical_annual.slice(0, 5).map((row, index) => (
                <tr key={`${row.year ?? "row"}-${index}`}>
                  {Object.entries(row)
                    .slice(0, 8)
                    .map(([key, value]) => (
                      <td key={key}>{renderCell(value)}</td>
                    ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div className="panel" style={{ marginTop: 24 }}>
        <h2>Quarterly Historical Preview</h2>
        {!analysis ? (
          <p className="subtle">Analyze a company first.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                {Object.keys(analysis.historical_quarterly[0] ?? {}).slice(0, 8).map((key) => (
                  <th key={key}>{key}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {analysis.historical_quarterly.slice(0, 5).map((row, index) => (
                <tr key={`${row.period_end ?? "quarter"}-${index}`}>
                  {Object.entries(row)
                    .slice(0, 8)
                    .map(([key, value]) => (
                      <td key={key}>{renderCell(value)}</td>
                    ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
