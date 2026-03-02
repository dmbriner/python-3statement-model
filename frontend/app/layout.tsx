import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";

import { AnalysisProvider } from "@/components/AnalysisContext";
import "./globals.css";

export const metadata: Metadata = {
  title: "3-Statement Platform",
  description: "Professional equity research, 3-statement modeling, and valuation platform.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  const content = (
    <html lang="en">
      <body>
        <AnalysisProvider>{children}</AnalysisProvider>
      </body>
    </html>
  );

  if (!publishableKey) {
    return content;
  }

  return <ClerkProvider publishableKey={publishableKey}>{content}</ClerkProvider>;
}
