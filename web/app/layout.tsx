import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "GameTable",
  description: "Self-hosted virtual tabletop for D&D",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "system-ui, sans-serif", background: "#11131a", color: "#e8e8ea" }}>
        {children}
      </body>
    </html>
  );
}
