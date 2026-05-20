import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../../lib/api";
import {
  MessageCircle,
  ArrowDownLeft,
  ArrowUpRight,
  Brain,
  Receipt,
  Tag,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Filter,
} from "lucide-react";

interface PipelineEvent {
  ts: string;
  event: string;
  user_id: number | null;
  gmail: string | null;
  [key: string]: unknown;
}

const WPP_EVENTS = [
  "wpp_incoming",
  "wpp_intent",
  "wpp_expense",
  "wpp_recategorize",
  "wpp_reply",
  "wpp_outgoing",
];

const EVENT_CONFIG: Record<
  string,
  { label: string; icon: typeof MessageCircle; color: string; bg: string }
> = {
  wpp_incoming: {
    label: "Mensaje Recibido",
    icon: ArrowDownLeft,
    color: "text-blue-600",
    bg: "bg-blue-50 border-blue-200",
  },
  wpp_intent: {
    label: "Intent",
    icon: Brain,
    color: "text-violet-600",
    bg: "bg-violet-50 border-violet-200",
  },
  wpp_expense: {
    label: "Gasto Registrado",
    icon: Receipt,
    color: "text-emerald-600",
    bg: "bg-emerald-50 border-emerald-200",
  },
  wpp_recategorize: {
    label: "Recategorizado",
    icon: Tag,
    color: "text-orange-600",
    bg: "bg-orange-50 border-orange-200",
  },
  wpp_reply: {
    label: "Respuesta",
    icon: ArrowUpRight,
    color: "text-green-600",
    bg: "bg-green-50 border-green-200",
  },
  wpp_outgoing: {
    label: "Enviado",
    icon: ArrowUpRight,
    color: "text-gray-600",
    bg: "bg-gray-50 border-gray-200",
  },
};

const DEFAULT_CFG = {
  label: "Event",
  icon: MessageCircle,
  color: "text-gray-600",
  bg: "bg-gray-50 border-gray-200",
};

function IntentBadge({ intent }: { intent: string }) {
  const colors: Record<string, string> = {
    DATA: "bg-emerald-100 text-emerald-700",
    QUERY: "bg-blue-100 text-blue-700",
    SUGERENCIAS: "bg-violet-100 text-violet-700",
    CATEGORIZACION: "bg-orange-100 text-orange-700",
    ONBOARDING: "bg-yellow-100 text-yellow-700",
    OTHER: "bg-gray-100 text-gray-500",
  };
  const intentKey = String(intent).replace("Intent.", "").toUpperCase();
  return (
    <span className={`px-1.5 py-0.5 text-[10px] font-bold rounded ${colors[intentKey] ?? "bg-gray-100 text-gray-500"}`}>
      {intentKey}
    </span>
  );
}

function WppEventCard({ ev }: { ev: PipelineEvent }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = EVENT_CONFIG[ev.event] ?? DEFAULT_CFG;
  const Icon = cfg.icon;

  const ts = new Date(ev.ts);
  const timeStr = ts.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const dateStr = ts.toLocaleDateString("es-AR", { day: "numeric", month: "short" });

  let summary = "";
  if (ev.event === "wpp_incoming") {
    summary = String(ev.body ?? "").slice(0, 100);
    if (ev.has_media) summary = `[Media: ${ev.media_type}] ${summary}`;
  } else if (ev.event === "wpp_intent") {
    const cmd = ev.command_match ? " (comando)" : " (IA)";
    summary = `${ev.intent}${cmd} — "${String(ev.body_preview ?? "").slice(0, 60)}"`;
  } else if (ev.event === "wpp_expense") {
    summary = `$${Number(ev.monto ?? 0).toLocaleString("es-AR")} ${ev.comercio ?? ""} → ${ev.categoria ?? ""}`;
    if (ev.cuotas) summary += ` (${ev.cuotas} cuotas)`;
    if (ev.split) summary += ` (split ${ev.split})`;
  } else if (ev.event === "wpp_recategorize") {
    summary = `Mov #${ev.movimiento_id} → ${ev.new_categoria}`;
  } else if (ev.event === "wpp_reply") {
    summary = String(ev.reply_preview ?? "").slice(0, 100);
  } else if (ev.event === "wpp_outgoing") {
    const to = String(ev.to ?? "").replace("whatsapp:", "");
    summary = `→ ${to} ${ev.success ? "" : "FALLO"} ${String(ev.body_preview ?? ev.template ?? "")}`.trim();
  }

  const details = Object.entries(ev).filter(([k]) => !["ts", "event", "user_id", "gmail"].includes(k));

  return (
    <div className={`border rounded-xl overflow-hidden ${cfg.bg}`}>
      <button onClick={() => setExpanded(!expanded)} className="w-full flex items-start gap-3 p-3 text-left">
        <div className={`mt-0.5 ${cfg.color}`}>
          <Icon className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className={`text-xs font-bold ${cfg.color}`}>{cfg.label}</span>
            {ev.event === "wpp_intent" && ev.intent && <IntentBadge intent={String(ev.intent)} />}
            {ev.event === "wpp_expense" && (
              <span className="px-1.5 py-0.5 text-[10px] font-bold rounded bg-green-100 text-green-700">
                ${Number(ev.monto ?? 0).toLocaleString("es-AR")}
              </span>
            )}
            {ev.event === "wpp_outgoing" && (
              <span className={`px-1.5 py-0.5 text-[10px] font-bold rounded ${ev.success ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>
                {ev.success ? "OK" : "FAIL"}
              </span>
            )}
          </div>
          <p className="text-xs text-gray-700 truncate">{summary}</p>
          <div className="flex items-center gap-2 mt-1 text-[10px] text-gray-400">
            <span>{dateStr} {timeStr}</span>
            {ev.gmail && <span>• {String(ev.gmail).split("@")[0]}</span>}
          </div>
        </div>
        <div className="mt-1 text-gray-400">
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </div>
      </button>
      {expanded && details.length > 0 && (
        <div className="border-t border-white/50 bg-white/60 px-3 py-2">
          <pre className="text-[11px] text-gray-600 whitespace-pre-wrap overflow-x-auto max-h-60">
            {JSON.stringify(Object.fromEntries(details), null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

const FILTER_TYPES = [
  { value: "", label: "Todos" },
  { value: "wpp_incoming", label: "Recibidos" },
  { value: "wpp_intent", label: "Intent" },
  { value: "wpp_expense", label: "Gastos" },
  { value: "wpp_recategorize", label: "Recat." },
  { value: "wpp_reply", label: "Replies" },
  { value: "wpp_outgoing", label: "Enviados" },
];

export function WhatsAppLog() {
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [filterUser, setFilterUser] = useState("");
  const [filterType, setFilterType] = useState("");

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    try {
      // Fetch all WPP events by querying multiple types, or all and filter client-side
      const params = new URLSearchParams();
      if (filterUser) params.set("user_id", filterUser);
      if (filterType) params.set("event_type", filterType);
      params.set("limit", "100");
      const res = await apiFetch<{ events: PipelineEvent[] }>(
        `/admin/pipeline-log?${params.toString()}`
      );
      // Filter to only WPP events if no specific type filter
      const filtered = filterType
        ? res.events
        : res.events.filter((e) => WPP_EVENTS.includes(e.event));
      setEvents(filtered);
    } catch {
      // silent
    }
    setLoading(false);
  }, [filterUser, filterType]);

  useEffect(() => { fetchEvents(); }, [fetchEvents]);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(fetchEvents, 10_000);
    return () => clearInterval(id);
  }, [autoRefresh, fetchEvents]);

  const users = Array.from(
    new Map(events.filter((e) => e.user_id && e.gmail).map((e) => [e.user_id, e.gmail]))
  );

  // Stats summary
  const incoming = events.filter((e) => e.event === "wpp_incoming").length;
  const expenses = events.filter((e) => e.event === "wpp_expense").length;
  const outgoing = events.filter((e) => e.event === "wpp_outgoing").length;

  return (
    <div className="space-y-3">
      {/* Stats bar */}
      <div className="flex gap-2">
        <div className="flex-1 bg-blue-50 rounded-lg px-3 py-2 text-center">
          <p className="text-lg font-bold text-blue-700">{incoming}</p>
          <p className="text-[10px] text-blue-500 font-medium">Recibidos</p>
        </div>
        <div className="flex-1 bg-emerald-50 rounded-lg px-3 py-2 text-center">
          <p className="text-lg font-bold text-emerald-700">{expenses}</p>
          <p className="text-[10px] text-emerald-500 font-medium">Gastos</p>
        </div>
        <div className="flex-1 bg-gray-50 rounded-lg px-3 py-2 text-center">
          <p className="text-lg font-bold text-gray-700">{outgoing}</p>
          <p className="text-[10px] text-gray-500 font-medium">Enviados</p>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-2 flex-wrap">
        <button onClick={fetchEvents} disabled={loading}
          className="p-2 rounded-lg bg-white shadow-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50">
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
        <button onClick={() => setAutoRefresh(!autoRefresh)}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium ${autoRefresh ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
          Auto {autoRefresh ? "ON" : "OFF"}
        </button>
        <div className="flex items-center gap-1 ml-auto">
          <Filter className="w-3 h-3 text-gray-400" />
          <select value={filterUser} onChange={(e) => setFilterUser(e.target.value)}
            className="text-xs border rounded-lg px-2 py-1.5 bg-white">
            <option value="">Todos</option>
            {users.map(([id, gmail]) => (
              <option key={id} value={String(id)}>{String(gmail).split("@")[0]}</option>
            ))}
          </select>
          <select value={filterType} onChange={(e) => setFilterType(e.target.value)}
            className="text-xs border rounded-lg px-2 py-1.5 bg-white">
            {FILTER_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
      </div>

      <p className="text-xs text-gray-400">{events.length} eventos WhatsApp</p>

      {events.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <MessageCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">Sin actividad de WhatsApp</p>
          <p className="text-xs mt-1">Los eventos aparecen cuando llegan mensajes o se envian notificaciones</p>
        </div>
      ) : (
        <div className="space-y-2">
          {events.map((ev, i) => <WppEventCard key={`${ev.ts}-${i}`} ev={ev} />)}
        </div>
      )}
    </div>
  );
}
