"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect, useState, useTransition } from "react";

import { createSavedAnalysis, deleteSavedAnalysis, listSavedAnalyses, SavedAnalysisRecord, updateSavedAnalysis } from "@/lib/api";
import { AppNav } from "@/components/AppNav";

export function AnalysesView() {
  const { getToken } = useAuth();
  const [records, setRecords] = useState<SavedAnalysisRecord[]>([]);
  const [title, setTitle] = useState("Starter Analysis");
  const [ticker, setTicker] = useState("AAPL");
  const [notes, setNotes] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    startTransition(() => {
      void (async () => {
        const token = await getToken();
        if (!token) return;
        const payload = await listSavedAnalyses(token);
        setRecords(payload);
      })();
    });
  }, [getToken]);

  function saveRecord() {
    startTransition(() => {
      void (async () => {
        const token = await getToken();
        if (!token) return;
        const body = {
          id: editingId ?? `analysis-${Date.now()}`,
          ticker,
          title,
          assumptions: { projection_years: 5 },
          output_summary: { status: "draft" },
          notes,
        };
        const payload = editingId
          ? await updateSavedAnalysis(token, editingId, body)
          : await createSavedAnalysis(token, body);
        setRecords((current) =>
          editingId ? current.map((record) => (record.id === editingId ? payload : record)) : [payload, ...current]
        );
        setEditingId(null);
        setTitle("Starter Analysis");
        setTicker("AAPL");
        setNotes("");
      })();
    });
  }

  function startEdit(record: SavedAnalysisRecord) {
    setEditingId(record.id);
    setTitle(record.title);
    setTicker(record.ticker);
    setNotes(record.notes ?? "");
  }

  function removeRecord(analysisId: string) {
    startTransition(() => {
      void (async () => {
        const token = await getToken();
        if (!token) return;
        await deleteSavedAnalysis(token, analysisId);
        setRecords((current) => current.filter((record) => record.id !== analysisId));
        if (editingId === analysisId) {
          setEditingId(null);
          setTitle("Starter Analysis");
          setTicker("AAPL");
          setNotes("");
        }
      })();
    });
  }

  return (
    <div className="shell">
      <div className="hero">
        <div className="eyebrow">Saved analyses</div>
        <h1>Persist company work instead of losing it between sessions.</h1>
        <p>The backend now has authenticated Postgres routes for user-owned analysis records.</p>
      </div>
      <AppNav />
      <div className="grid">
        <div className="panel">
          <h2>{editingId ? "Edit Analysis Record" : "Create Analysis Record"}</h2>
          <div className="field">
            <label>Title</label>
            <input value={title} onChange={(event) => setTitle(event.target.value)} />
          </div>
          <div className="field">
            <label>Ticker</label>
            <input value={ticker} onChange={(event) => setTicker(event.target.value)} />
          </div>
          <div className="field">
            <label>Notes</label>
            <input value={notes} onChange={(event) => setNotes(event.target.value)} />
          </div>
          <div className="buttonRow">
            <button className="button" onClick={saveRecord} disabled={isPending}>
              {isPending ? "Saving..." : editingId ? "Update Analysis" : "Save Analysis"}
            </button>
            {editingId ? (
              <button
                className="button secondary"
                onClick={() => {
                  setEditingId(null);
                  setTitle("Starter Analysis");
                  setTicker("AAPL");
                  setNotes("");
                }}
              >
                Cancel
              </button>
            ) : null}
          </div>
        </div>
        <div className="panel">
          <h2>Your Saved Analyses</h2>
          <div className="list">
            {records.map((record) => (
              <div className="listItem" key={record.id}>
                <strong>{record.title}</strong>
                <div className="subtle">{record.ticker}</div>
                <div className="subtle">{record.notes || "No notes yet."}</div>
                <div className="buttonRow" style={{ marginTop: 10 }}>
                  <button className="button secondary" onClick={() => startEdit(record)}>
                    Edit
                  </button>
                  <button className="button secondary" onClick={() => removeRecord(record.id)}>
                    Delete
                  </button>
                </div>
              </div>
            ))}
            {!records.length ? <p className="subtle">No saved analyses yet.</p> : null}
          </div>
        </div>
      </div>
    </div>
  );
}
