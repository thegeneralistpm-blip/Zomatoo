import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata = {
  title: "Zomato AI — Smart Restaurant Recommendations",
  description:
    "AI-powered restaurant recommendation engine. Get personalized dining suggestions based on location, cuisine, budget, and ratings — powered by LLM intelligence.",
  keywords: ["restaurant", "recommendation", "AI", "Zomato", "food", "dining"],
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={inter.variable}>
      <body>{children}</body>
    </html>
  );
}
