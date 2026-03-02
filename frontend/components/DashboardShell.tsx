"use client";

import { AppNav } from "@/components/AppNav";
import { AuthPanel } from "@/components/AuthPanel";
import { CompanyWorkspace } from "@/components/CompanyWorkspace";
import { useAnalysis } from "@/components/AnalysisContext";

export function DashboardShell() {
  const { analysis } = useAnalysis();

  return (
    <div className="shell">
      <section className="hero">
        <div className="eyebrow">Next.js + FastAPI + Postgres</div>
        <div className="topbar">
          <div>
            <h1>Institutional-style research platform, built as a real product.</h1>
            <p>
              This frontend is the replacement path for the old Streamlit shell: proper auth,
              typed API calls, deployable frontend hosting on Vercel, and a backend that keeps
              your Python modeling engine intact.
            </p>
          </div>
          <div className="panel soft">
            <div className="metricLabel">Stack</div>
            <div className="metricValue">Next.js / FastAPI / Postgres / Clerk</div>
          </div>
          <AuthPanel />
        </div>
      </section>

      <AppNav />

      <section className="metrics">
        <div className="metricCard">
          <div className="metricLabel">Frontend</div>
          <div className="metricValue">App Router</div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Backend</div>
          <div className="metricValue">Typed REST API</div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Auth</div>
          <div className="metricValue">Clerk-ready</div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Persistence</div>
          <div className="metricValue">Postgres-ready</div>
        </div>
      </section>

      <section className="grid">
        <CompanyWorkspace />

        <div className="panel">
          <h2>Analysis Summary</h2>
          {!analysis ? (
            <p className="subtle">
              Run a company analysis to see the backend response shape that the full website will
              render into overview, model, market, and export workspaces.
            </p>
          ) : (
            <>
              <table className="table">
                <thead>
                  <tr>
                    <th>Scenario</th>
                    <th>Revenue</th>
                    <th>EBITDA</th>
                    <th>Net Income</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(analysis.scenarios).map(([name, scenario]) => (
                    <tr key={name}>
                      <td>{name}</td>
                      <td>${scenario.revenue_final_year.toLocaleString()}</td>
                      <td>${scenario.ebitda_final_year.toLocaleString()}</td>
                      <td>${scenario.net_income_final_year.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div className="grid" style={{ marginTop: 18 }}>
                <div className="panel soft">
                  <h3>Historical Coverage</h3>
                  <p className="subtle">Annual rows: {analysis.historical_annual.length}</p>
                  <p className="subtle">Quarterly rows: {analysis.historical_quarterly.length}</p>
                </div>
                <div className="panel soft">
                  <h3>Profile Layer</h3>
                  <p className="subtle">{analysis.company_name ?? analysis.ticker}</p>
                  <p className="subtle">
                    Move to the Model and Market pages to see the active company rendered into more
                    specific workflows.
                  </p>
                </div>
              </div>
            </>
          )}
        </div>
      </section>
    </div>
  );
}
