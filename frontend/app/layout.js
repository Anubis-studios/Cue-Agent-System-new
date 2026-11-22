export const metadata = { title: "Cue Agent System", description: "Multi-agent AI platform" };
export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-950 text-gray-100">{children}</body>
    </html>
  );
}
