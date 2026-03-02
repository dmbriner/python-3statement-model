import { AppNav } from "@/components/AppNav";
import { AnalysesView } from "@/components/AnalysesView";

export default function AnalysesPage() {
  const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

  if (!clerkEnabled) {
    return (
      <>
        <AppNav />
        <div className="shell">
          <div className="panel">
            <h2>Clerk configuration required</h2>
            <p className="subtle">Add `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY` to enable saved analyses.</p>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <AnalysesView />
    </>
  );
}
