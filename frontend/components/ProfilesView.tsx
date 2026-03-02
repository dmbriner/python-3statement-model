"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect, useState, useTransition } from "react";

import { AppNav } from "@/components/AppNav";
import { ApiProfileRecord, createApiProfile, deleteApiProfile, listApiProfiles, updateApiProfile } from "@/lib/api";

export function ProfilesView() {
  const { getToken } = useAuth();
  const [profiles, setProfiles] = useState<ApiProfileRecord[]>([]);
  const [name, setName] = useState("Personal Keys");
  const [alphaKey, setAlphaKey] = useState("");
  const [fmpKey, setFmpKey] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    startTransition(() => {
      void (async () => {
        const token = await getToken();
        if (!token) return;
        const payload = await listApiProfiles(token);
        setProfiles(payload);
      })();
    });
  }, [getToken]);

  function saveProfile() {
    startTransition(() => {
      void (async () => {
        const token = await getToken();
        if (!token) return;
        const body = {
          id: editingId ?? `profile-${Date.now()}`,
          name,
          provider_keys: {
            ALPHA_VANTAGE_API_KEY: alphaKey,
            FMP_API_KEY: fmpKey,
          },
        };
        const payload = editingId
          ? await updateApiProfile(token, editingId, body)
          : await createApiProfile(token, body);
        setProfiles((current) =>
          editingId ? current.map((profile) => (profile.id === editingId ? payload : profile)) : [payload, ...current]
        );
        setEditingId(null);
        setName("Personal Keys");
        setAlphaKey("");
        setFmpKey("");
      })();
    });
  }

  function startEdit(profile: ApiProfileRecord) {
    setEditingId(profile.id);
    setName(profile.name);
    setAlphaKey(String(profile.provider_keys.ALPHA_VANTAGE_API_KEY ?? ""));
    setFmpKey(String(profile.provider_keys.FMP_API_KEY ?? ""));
  }

  function removeProfile(profileId: string) {
    startTransition(() => {
      void (async () => {
        const token = await getToken();
        if (!token) return;
        await deleteApiProfile(token, profileId);
        setProfiles((current) => current.filter((profile) => profile.id !== profileId));
        if (editingId === profileId) {
          setEditingId(null);
          setName("Personal Keys");
          setAlphaKey("");
          setFmpKey("");
        }
      })();
    });
  }

  return (
    <div className="shell">
      <div className="hero">
        <div className="eyebrow">API Profiles</div>
        <h1>User-owned provider key presets.</h1>
        <p>
          This replaces the old global/shared key model with authenticated, database-backed API
          profiles tied to each user.
        </p>
      </div>
      <AppNav />
      <div className="grid">
        <div className="panel">
          <h2>{editingId ? "Edit API Profile" : "Create API Profile"}</h2>
          <div className="field">
            <label>Name</label>
            <input value={name} onChange={(event) => setName(event.target.value)} />
          </div>
          <div className="field">
            <label>Alpha Vantage Key</label>
            <input value={alphaKey} onChange={(event) => setAlphaKey(event.target.value)} />
          </div>
          <div className="field">
            <label>FMP Key</label>
            <input value={fmpKey} onChange={(event) => setFmpKey(event.target.value)} />
          </div>
          <div className="buttonRow">
            <button className="button" onClick={saveProfile} disabled={isPending}>
              {isPending ? "Saving..." : editingId ? "Update Profile" : "Save Profile"}
            </button>
            {editingId ? (
              <button
                className="button secondary"
                onClick={() => {
                  setEditingId(null);
                  setName("Personal Keys");
                  setAlphaKey("");
                  setFmpKey("");
                }}
              >
                Cancel
              </button>
            ) : null}
          </div>
        </div>
        <div className="panel">
          <h2>Saved API Profiles</h2>
          <div className="list">
            {profiles.map((profile) => (
              <div className="listItem" key={profile.id}>
                <strong>{profile.name}</strong>
                <div className="subtle">{Object.keys(profile.provider_keys).join(", ") || "No providers"}</div>
                <div className="buttonRow" style={{ marginTop: 10 }}>
                  <button className="button secondary" onClick={() => startEdit(profile)}>
                    Edit
                  </button>
                  <button className="button secondary" onClick={() => removeProfile(profile.id)}>
                    Delete
                  </button>
                </div>
              </div>
            ))}
            {!profiles.length ? <p className="subtle">No saved profiles yet.</p> : null}
          </div>
        </div>
      </div>
    </div>
  );
}
