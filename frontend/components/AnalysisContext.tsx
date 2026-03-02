"use client";

import { createContext, useContext, useState, useTransition } from "react";

import { analyzeTicker, AnalysisResponse, searchCompanies, SearchResult } from "@/lib/api";

type AnalysisContextValue = {
  query: string;
  results: SearchResult[];
  analysis: AnalysisResponse | null;
  error: string;
  isPending: boolean;
  setQueryValue: (value: string) => void;
  runSearch: (value: string) => void;
  runAnalysis: (ticker: string) => void;
  clearAnalysis: () => void;
};

const AnalysisContext = createContext<AnalysisContextValue | null>(null);

export function AnalysisProvider({ children }: { children: React.ReactNode }) {
  const [query, setQuery] = useState("AAPL");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  function runSearch(value: string) {
    setQuery(value);
    if (!value.trim()) {
      setResults([]);
      return;
    }
    startTransition(() => {
      void (async () => {
        try {
          const payload = await searchCompanies(value);
          setResults(payload);
          setError("");
        } catch {
          setError("Search is unavailable right now.");
        }
      })();
    });
  }

  function runAnalysis(ticker: string) {
    startTransition(() => {
      void (async () => {
        try {
          const payload = await analyzeTicker(ticker);
          setAnalysis(payload);
          setQuery(ticker);
          setError("");
        } catch {
          setError("Analysis failed. Check API connectivity and provider keys.");
        }
      })();
    });
  }

  return (
    <AnalysisContext.Provider
      value={{
        query,
        results,
        analysis,
        error,
        isPending,
        setQueryValue: setQuery,
        runSearch,
        runAnalysis,
        clearAnalysis: () => setAnalysis(null),
      }}
    >
      {children}
    </AnalysisContext.Provider>
  );
}

export function useAnalysis() {
  const context = useContext(AnalysisContext);
  if (!context) {
    throw new Error("useAnalysis must be used within AnalysisProvider.");
  }
  return context;
}
