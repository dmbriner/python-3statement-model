"use client";

import { useAnalysis } from "@/components/AnalysisContext";

export function CompanyWorkspace() {
  const { query, results, error, isPending, setQueryValue, runSearch, runAnalysis, clearAnalysis } = useAnalysis();

  return (
    <div className="panel">
      <h2>Company Workspace</h2>
      <div className="field">
        <label htmlFor="ticker">Search ticker or company</label>
        <input
          id="ticker"
          value={query}
          onChange={(event) => {
            setQueryValue(event.target.value);
            runSearch(event.target.value);
          }}
          placeholder="AAPL, Microsoft, BRK.B..."
        />
      </div>
      <div className="buttonRow">
        <button className="button" onClick={() => runAnalysis(query)} disabled={isPending}>
          {isPending ? "Loading..." : "Analyze"}
        </button>
        <button className="button secondary" onClick={clearAnalysis}>
          Clear
        </button>
      </div>
      {error ? <p className="subtle">{error}</p> : null}
      <div className="list" style={{ marginTop: 16 }}>
        {results.slice(0, 6).map((result) => (
          <button className="listItem" key={result.symbol} onClick={() => runAnalysis(result.symbol)}>
            <strong>{result.name}</strong>
            <div className="subtle">
              {result.symbol} • {result.exchange}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
