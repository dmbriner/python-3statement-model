"use client";

import { SignedIn, SignedOut, SignInButton, UserButton } from "@clerk/nextjs";

export function AuthPanel() {
  const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

  return (
    <div className="panel soft">
      {!clerkEnabled ? (
        <div className="subtle">Add Clerk keys to enable sign-in.</div>
      ) : (
        <>
          <SignedIn>
            <UserButton afterSignOutUrl="/" />
          </SignedIn>
          <SignedOut>
            <SignInButton mode="modal">
              <button className="button">Sign In</button>
            </SignInButton>
          </SignedOut>
        </>
      )}
    </div>
  );
}
