import { useState, useRef, useEffect } from 'react';
import { Screen } from './shared';
import { apiFetch } from '@/lib/api/client';

interface Message {
  id: string;
  role: 'user' | 'fina';
  text: string;
}

const SUGGESTED_CHIPS = [
  'Resumen del mes',
  '¿Cuánto gasté en súper?',
  '¿Cómo vengo con el presupuesto?',
  'Mis gastos más grandes',
];

export function ChatScreen() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: 'user',
      text: text.trim(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await apiFetch<{ message?: string; response?: string }>('/chat/message', {
        method: 'POST',
        body: JSON.stringify({ message: text.trim() }),
      });
      const finaText = res.response || res.message || 'Listo, ahí te mando la info.';
      setMessages((prev) => [
        ...prev,
        { id: `f-${Date.now()}`, role: 'fina', text: finaText },
      ]);
    } catch {
      // Demo fallback
      await new Promise((r) => setTimeout(r, 400));
      setMessages((prev) => [
        ...prev,
        { id: `f-${Date.now()}`, role: 'fina', text: 'Demo — estoy pensando...' },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const hasText = input.trim().length > 0;

  return (
    <Screen>
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
        {/* Fina header card */}
        <div style={{
          margin: '16px 20px 0',
          background: 'var(--color-accent-dark, #1a1a2e)',
          borderRadius: '16px',
          padding: '16px 18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '12px',
              background: 'var(--color-accent, #c8ff00)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '18px',
              fontWeight: 700,
              color: 'var(--color-accent-dark, #1a1a2e)',
            }}>
              F
            </div>
            <div>
              <div style={{
                fontSize: '16px',
                fontWeight: 600,
                color: '#fff',
              }}>
                Fina
              </div>
              <div style={{
                fontSize: '12px',
                color: 'rgba(255,255,255,0.6)',
              }}>
                Asistente financiero · activo
              </div>
            </div>
          </div>
          <button
            onClick={() => setMessages([])}
            style={{
              background: 'rgba(255,255,255,0.12)',
              border: 'none',
              borderRadius: '8px',
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: 600,
              color: '#fff',
              cursor: 'pointer',
            }}
          >
            Nueva
          </button>
        </div>

        {/* Thread area */}
        <div
          ref={scrollRef}
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '16px 20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            minHeight: 0,
          }}
        >
          {messages.length === 0 && (
            <div style={{
              textAlign: 'center',
              color: 'var(--color-text-tertiary, #999)',
              fontSize: '14px',
              padding: '32px 0',
            }}>
              Preguntale lo que quieras sobre tus finanzas.
            </div>
          )}
          {messages.map((msg) =>
            msg.role === 'user' ? (
              <div key={msg.id} style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <div style={{
                  background: 'var(--color-accent, #c8ff00)',
                  color: 'var(--color-accent-dark, #1a1a2e)',
                  borderRadius: '16px 16px 4px 16px',
                  padding: '10px 14px',
                  maxWidth: '75%',
                  fontSize: '14px',
                  lineHeight: 1.5,
                  fontWeight: 500,
                }}>
                  {msg.text}
                </div>
              </div>
            ) : (
              <div key={msg.id} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                <div style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '8px',
                  background: 'var(--color-accent, #c8ff00)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '11px',
                  fontWeight: 700,
                  color: 'var(--color-accent-dark, #1a1a2e)',
                  flexShrink: 0,
                  marginTop: '2px',
                }}>
                  F
                </div>
                <div style={{
                  background: 'var(--color-surface, #f5f5f5)',
                  color: 'var(--color-text-primary, #1a1a1a)',
                  borderRadius: '16px 16px 16px 4px',
                  padding: '10px 14px',
                  maxWidth: '75%',
                  fontSize: '14px',
                  lineHeight: 1.5,
                }}>
                  {msg.text}
                </div>
              </div>
            )
          )}
          {isLoading && (
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
              <div style={{
                width: '24px',
                height: '24px',
                borderRadius: '8px',
                background: 'var(--color-accent, #c8ff00)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '11px',
                fontWeight: 700,
                color: 'var(--color-accent-dark, #1a1a2e)',
                flexShrink: 0,
                marginTop: '2px',
              }}>
                F
              </div>
              <div style={{
                background: 'var(--color-surface, #f5f5f5)',
                borderRadius: '16px 16px 16px 4px',
                padding: '10px 14px',
                fontSize: '14px',
                color: 'var(--color-text-tertiary, #999)',
              }}>
                Pensando...
              </div>
            </div>
          )}
        </div>

        {/* Suggested chips */}
        {messages.length === 0 && (
          <div style={{
            padding: '0 20px 12px',
            display: 'flex',
            gap: '8px',
            flexWrap: 'wrap',
          }}>
            {SUGGESTED_CHIPS.map((chip) => (
              <button
                key={chip}
                onClick={() => sendMessage(chip)}
                style={{
                  background: 'var(--color-surface, #f5f5f5)',
                  border: '1px solid var(--color-border, #e5e5e5)',
                  borderRadius: '20px',
                  padding: '8px 14px',
                  fontSize: '13px',
                  color: 'var(--color-text-primary, #1a1a1a)',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
              >
                {chip}
              </button>
            ))}
          </div>
        )}

        {/* Composer */}
        <form
          onSubmit={handleSubmit}
          style={{
            padding: '12px 20px',
            paddingBottom: 'calc(12px + env(safe-area-inset-bottom, 0px))',
            borderTop: '1px solid var(--color-border, #e5e5e5)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'var(--color-bg, #fff)',
          }}
        >
          {/* Camera button */}
          <button
            type="button"
            style={{
              background: 'none',
              border: 'none',
              padding: '6px',
              cursor: 'pointer',
              color: 'var(--color-text-tertiary, #999)',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
              <circle cx="12" cy="13" r="4" />
            </svg>
          </button>

          {/* Input */}
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Preguntá a Fina..."
            style={{
              flex: 1,
              border: 'none',
              background: 'var(--color-surface, #f5f5f5)',
              borderRadius: '20px',
              padding: '10px 16px',
              fontSize: '15px',
              color: 'var(--color-text-primary, #1a1a1a)',
              outline: 'none',
            }}
          />

          {/* Mic button */}
          <button
            type="button"
            style={{
              background: 'none',
              border: 'none',
              padding: '6px',
              cursor: 'pointer',
              color: 'var(--color-text-tertiary, #999)',
              display: hasText ? 'none' : 'flex',
              alignItems: 'center',
            }}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
          </button>

          {/* Send button */}
          <button
            type="submit"
            disabled={!hasText || isLoading}
            style={{
              background: hasText ? 'var(--color-accent, #c8ff00)' : 'var(--color-surface, #f5f5f5)',
              border: 'none',
              borderRadius: '50%',
              width: '36px',
              height: '36px',
              display: hasText ? 'flex' : 'none',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: hasText ? 'pointer' : 'default',
              flexShrink: 0,
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--color-accent-dark, #1a1a2e)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="19" x2="12" y2="5" />
              <polyline points="5 12 12 5 19 12" />
            </svg>
          </button>
        </form>
      </div>
    </Screen>
  );
}
