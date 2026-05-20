import { useState } from "react";
import { useGoogleLogin } from "@react-oauth/google";
import { Loader2 } from "lucide-react";
import { apiFetch } from "../../lib/api";

interface GmailStatus {
  connected: boolean;
  connected_at: string | null;
  last_polled_at: string | null;
}

export default function GmailConnectButton({
  onConnected,
  onError,
}: {
  onConnected: (status: GmailStatus) => void;
  onError: (msg: string) => void;
}) {
  const [loading, setLoading] = useState(false);

  const googleLogin = useGoogleLogin({
    flow: "auth-code",
    scope: "https://www.googleapis.com/auth/gmail.readonly",
    onSuccess: async (response) => {
      setLoading(true);
      try {
        await apiFetch("/gmail/connect", {
          method: "POST",
          body: JSON.stringify({ code: response.code }),
        });
        const status = await apiFetch<GmailStatus>("/gmail/status");
        onConnected(status);
      } catch {
        onError("Error al conectar Gmail");
      }
      setLoading(false);
    },
    onError: () => {
      onError("Error al conectar con Google");
    },
  });

  return (
    <button
      onClick={() => googleLogin()}
      disabled={loading}
      className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-white border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors disabled:opacity-50"
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        <svg width="16" height="16" viewBox="0 0 48 48">
          <path fill="#4285f4" d="M45.12 24.5c0-1.56-.14-3.06-.4-4.5H24v8.51h11.84c-.51 2.75-2.06 5.08-4.39 6.64v5.52h7.11c4.16-3.83 6.56-9.47 6.56-16.17z" />
          <path fill="#34a853" d="M24 46c5.94 0 10.92-1.97 14.56-5.33l-7.11-5.52c-1.97 1.32-4.49 2.1-7.45 2.1-5.73 0-10.58-3.87-12.31-9.07H4.34v5.7C7.96 41.07 15.4 46 24 46z" />
          <path fill="#fbbc04" d="M11.69 28.18c-.44-1.32-.69-2.73-.69-4.18s.25-2.86.69-4.18v-5.7H4.34A21.99 21.99 0 002 24c0 3.55.85 6.91 2.34 9.88l7.35-5.7z" />
          <path fill="#ea4335" d="M24 10.75c3.23 0 6.13 1.11 8.41 3.29l6.31-6.31C34.91 4.18 29.93 2 24 2 15.4 2 7.96 6.93 4.34 14.12l7.35 5.7c1.73-5.2 6.58-9.07 12.31-9.07z" />
        </svg>
      )}
      Conectar Gmail
    </button>
  );
}
