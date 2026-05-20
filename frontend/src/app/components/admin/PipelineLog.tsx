import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../../lib/api";
import {
  Mail,
  Brain,
  ArrowDownToLine,
  MessageCircle,
  AlertTriangle,
  BarChart3,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Filter,
  Search,
} from "lucide-react";

interface PipelineEvent {
  ts: string;
  event: string;
  user_id: number | null;
  gmail: string | null;
  [key: string]: unknown;
}

const EVENT_CONFIG: Record<
  string,
  { label: string; icon: typeof Mail; color: string; bg: string }
> = {
  gmail_query: {
    label: "Gmail Query",
    icon: Search,
    color: "text-blue-600",
    bg: "bg-blue-50 border-blue-200",
  },
  email_found: {
    label: "Email",
    icon: Mail,
    color: "text-blue-600",
    bg: "bg-blue-50 border-blue-200",
  },
  extraction_result: {
    label: "GPT Extraction",
    icon: Brain,
    color: "text-violet-600",
    bg: "bg-violet-50 border-violet-200",
  },
  ingest_result: {
    label: "Ingest",
    icon: ArrowDownToLine,
    color: "text-emerald-600",
    bg: "bg-emerald-50 border-emerald-200",
  },
  whatsapp_sent: {
    label: "WhatsApp",
    icon: MessageCircle,
    color: "text-green-600",
    bg: "bg-green-50 border-green-200",
  },
  poll_summary: {
    label: "Poll Summary",
    icon: BarChart3,
    color: "text-gray-600",
    bg: "bg-gray-50 border-gray-200",
  },
  gmail_error: {
    label: "Error",
    icon: AlertTriangle,
    color: "text-red-600",
    bg: "bg-red-50 border-red-200",
  },
  pipeline_error: {
    label: "Error",
    icon: AlertTriangle,
    color: "text-red-600",
    bg: "bg-red-50 border-red-200",
  },
};

const DEFAULT_CONFIG = {
  label: "Event",
  icon: BarChart3,
  color: "text-gray-600",
  bg: "bg-gray-50 border-gray-200",
};

function StatusBadge({ status }: { status: string }) {
  if (status === "creado")
    return (
      <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-green-100 text-green-700">
        CREADO
      </span>
    );
  if (status?.includes("duplicado"))
    return (
      <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-yellow-100 text-yellow-700">
        DUPLICADO
      </span>
    );
  if (status === "error")
    return (
      <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-red-100 text-red-700">
        ERROR
      </span>
    );
  return (
    <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-600">
      {status}
    </span>
  );
}

function EventCard({ ev }: { ev: PipelineEvent }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = EVENT_CONFIG[ev.event] ?? DEFAULT_CONFIG;
  const Icon = cfg.icon;

  const ts = new Date(ev.ts);
  const timeStr = ts.toLocaleTimeString("es-AR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  const dateStr = ts.toLocaleDateString("es-AR", {
    day: "numeric",
    month: "short",
  });

  // Build summary line based on event type
  let summary = "";
  if (ev.event === "gmail_query") {
    summary = `${ev.messages_found ?? 0} emails encontrados`;
  } else if (ev.event === "email_found") {
    const matched = ev.matched_filter ? "MATCH" : "skip";
    summary = `${ev.subject ?? ""} [${matched}]`;
  } else if (ev.event === "extraction_result") {
    const ext = ev.extraction as Record<string, unknown> | undefined;
    if (ext?.datos_completos) {
      summary = `$${Number(ext.monto ?? 0).toLocaleString("es-AR")} — ${ext.comercio_raw ?? ""}`;
    } else {
      summary = `Incompleto: ${ext?.dato_faltante ?? "sin datos"}`;
    }
  } else if (ev.event === "ingest_result") {
    summary = `${ev.comercio ?? ""} — $${Number(ev.monto ?? 0).toLocaleString("es-AR")}`;
  } else if (ev.event === "whatsapp_sent") {
    summary = ev.success ? "Enviado" : `Fallo: ${ev.error ?? ""}`;
  } else if (ev.event === "poll_summary") {
    summary = `proc=${ev.processed ?? 0} new=${ev.created ?? 0} dup=${ev.duplicated ?? 0} err=${ev.errors ?? 0}`;
  } else if (ev.event === "gmail_error" || ev.event === "pipeline_error") {
    summary = String(ev.error ?? "");
  }

  // Detail data (everything except ts, event, user_id, gmail)
  const details = Object.entries(ev).filter(
    ([k]) => !["ts", "event", "user_id", "gmail"].includes(k)
  );

  return (
    <div className={`border rounded-xl overflow-hidden ${cfg.bg}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start gap-3 p-3 text-left"
      >
        <div className={`mt-0.5 ${cfg.color}`}>
          <Icon className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className={`text-xs font-bold ${cfg.color}`}>{cfg.label}</span>
            {ev.event === "ingest_result" && ev.status && (
              <StatusBadge status={String(ev.status)} />
            )}
            {ev.event === "email_found" && (
              <span
                className={`px-1.5 py-0.5 text-[10px] font-bold rounded ${
                  ev.matched_filter
                    ? "bg-green-100 text-green-700"
                    : "bg-gray-200 text-gray-500"
                }`}
              >
                {ev.matched_filter ? "MATCH" : "SKIP"}
              </span>
            )}
            {ev.event === "extraction_result" && (
              <span
                className={`px-1.5 py-0.5 text-[10px] font-bold rounded ${
                  (ev.extraction as any)?.datos_completos
                    ? "bg-green-100 text-green-700"
                    : "bg-red-100 text-red-600"
                }`}
              >
                {(ev.extraction as any)?.datos_completos ? "OK" : "FAIL"}
              </span>
            )}
            {ev.event === "whatsapp_sent" && (
              <span
                className={`px-1.5 py-0.5 text-[10px] font-bold rounded ${
                  ev.success
                    ? "bg-green-100 text-green-700"
                    : "bg-red-100 text-red-600"
                }`}
              >
                {ev.success ? "SENT" : "FAIL"}
              </span>
            )}
          </div>
          <p className="text-xs text-gray-700 truncate">{summary}</p>
          <div className="flex items-center gap-2 mt-1 text-[10px] text-gray-400">
            <span>{dateStr} {timeStr}</span>
            {ev.gmail && <span>• {ev.gmail}</span>}
          </div>
        </div>
        <div className="mt-1 text-gray-400">
          {expanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </div>
      </button>
      {expanded && details.length > 0 && (
        <div className="border-t border-white/50 bg-white/60 px-3 py-2">
          <pre className="text-[11px] text-gray-600 whitespace-pre-wrap overflow-x-auto max-h-60">
            {JSON.stringify(
              Object.fromEntries(details),
              null,
              2
            )}
          </pre>
        </div>
      )}
    </div>
  );
}

const EVENT_TYPES = [
  { value: "", label: "Todos" },
  { value: "gmail_query", label: "Gmail Query" },
  { value: "email_found", label: "Email" },
  { value: "extraction_result", label: "GPT" },
  { value: "ingest_result", label: "Ingest" },
  { value: "whatsapp_sent", label: "WhatsApp" },
  { value: "poll_summary", label: "Summary" },
  { value: "gmail_error", label: "Error" },
  { value: "pipeline_error", label: "Error Pipeline" },
];

export function PipelineLog() {
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [filterUser, setFilterUser] = useState("");
  const [filterType, setFilterType] = useState("");

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterUser) params.set("user_id", filterUser);
      if (filterType) params.set("event_type", filterType);
      params.set("limit", "100");
      const qs = params.toString();
      const res = await apiFetch<{ events: PipelineEvent[] }>(
        `/admin/pipeline-log${qs ? `?${qs}` : ""}`
      );
      setEvents(res.events);
    } catch {
      // silently fail — will retry on next tick
    }
    setLoading(false);
  }, [filterUser, filterType]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(fetchEvents, 10_000);
    return () => clearInterval(id);
  }, [autoRefresh, fetchEvents]);

  // Unique users from events
  const users = Array.from(
    new Map(
      events
        .filter((e) => e.user_id && e.gmail)
        .map((e) => [e.user_id, e.gmail])
    )
  );

  return (
    <div className="space-y-3">
      {/* Controls */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={fetchEvents}
          disabled={loading}
          className="p-2 rounded-lg bg-white shadow-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
        <button
          onClick={() => setAutoRefresh(!autoRefresh)}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium ${
            autoRefresh
              ? "bg-green-100 text-green-700"
              : "bg-gray-100 text-gray-500"
          }`}
        >
          Auto {autoRefresh ? "ON" : "OFF"}
        </button>
        <div className="flex items-center gap-1 ml-auto">
          <Filter className="w-3 h-3 text-gray-400" />
          <select
            value={filterUser}
            onChange={(e) => setFilterUser(e.target.value)}
            className="text-xs border rounded-lg px-2 py-1.5 bg-white"
          >
            <option value="">Todos</option>
            {users.map(([id, gmail]) => (
              <option key={id} value={String(id)}>
                {String(gmail).split("@")[0]}
              </option>
            ))}
          </select>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="text-xs border rounded-lg px-2 py-1.5 bg-white"
          >
            {EVENT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Event count */}
      <p className="text-xs text-gray-400">
        {events.length} eventos {autoRefresh && "• auto-refresh 10s"}
      </p>

      {/* Events timeline */}
      {events.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <BarChart3 className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">Sin eventos en el buffer</p>
          <p className="text-xs mt-1">
            Los eventos aparecen cuando corre el poller de Gmail
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {events.map((ev, i) => (
            <EventCard key={`${ev.ts}-${i}`} ev={ev} />
          ))}
        </div>
      )}
    </div>
  );
}
