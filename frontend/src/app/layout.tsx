import type { Metadata } from "next";
import { Outfit, Inter, Great_Vibes } from "next/font/google";
import { GlobalHeader } from "@/components/GlobalHeader";
import { QueryProvider } from "@/providers/QueryProvider";
import { NavLockProvider } from "@/hooks/useNavLock";
import styles from "./AmbientBackground.module.css";
import "./globals.css";

const outfit = Outfit({
  subsets: ["latin"],
  weight: ["200", "300", "400", "500", "600", "700"],
  variable: "--font-outfit",
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-inter",
});

const greatVibes = Great_Vibes({
  subsets: ["latin"],
  weight: ["400"],
  variable: "--font-great-vibes",
});

export const metadata: Metadata = {
  title: "Bittensor Arena",
  description: "Multi-model Bittensor agentic evaluation platform",
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={`${outfit.variable} ${inter.variable} ${greatVibes.variable} min-h-screen antialiased relative font-sans`} suppressHydrationWarning>
        <div className={styles.ambient}>
          <div className={styles.blob} />
          <div className={styles.noise} />
          <div className={styles.vignette} />
        </div>
        <QueryProvider>
          <NavLockProvider>
            <GlobalHeader />
            {children}
          </NavLockProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
