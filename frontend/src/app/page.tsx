import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center space-y-6">
        <h1 className="text-4xl font-bold text-gray-900">GCIS CoA Automation</h1>
        <p className="text-lg text-gray-600">
          Cannabis Certificate of Analysis processing &amp; buyer marketplace
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/admin"
            className="px-6 py-3 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition"
          >
            Admin Dashboard
          </Link>
        </div>
      </div>
    </main>
  );
}
