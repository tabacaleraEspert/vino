# Fina — Product Brief
> Metodología: The MND130 Way. Primero decidimos, después construimos.
> Última actualización: 08/06/2026

---

## 1. PROBLEMA

Las personas no tenemos el hábito de registrar y categorizar en qué gastamos, lo que nos hace perdernos en entender en qué se nos va la plata y no cumplir con metas de ahorro, o con reservas de dinero para algún gasto puntual.

Existen apps en el mercado, pero todas tienen muchas fricciones. Las más destacadas son la manualidad para registrar y categorizar gastos, y la lectura de la información para tomar buenas decisiones. Los números en general, pero sobre todo las finanzas, son muy fríos y complicados de leer para tomar decisiones inteligentes.

Además, la volatilidad del tipo de cambio y la inflación en Argentina — nuestro mercado inicial — presenta un desafío adicional para que las personas cuiden su economía.

Fina resuelve la fricción del registro automatizando la captura desde Gmail y WhatsApp, sin que el usuario tenga que hacer nada. Y resuelve la fricción de la lectura siendo **prescriptiva**: no muestra números fríos, dice qué hacer. No "gastaste $X" sino "no compres esto, ya vas al 90% de tu presupuesto en ocio".

---

## 2. USUARIO

**Perfil principal:** Ignacio, 25-40 años, profesional argentino con ingresos medios-altos.

- Gana bien pero no sabe adónde va la plata al final del mes
- Usa WhatsApp todo el día — es su canal natural
- Tiene cuenta bancaria en BBVA o Santander, usa MercadoPago
- Odia cargar cosas manualmente, no es técnico pero es exigente con el diseño
- No es un ahorrador obsesivo — quiere **control sin esfuerzo**
- Confía más en una recomendación clara que en un dashboard lleno de gráficos

**Lo que NO es el usuario:** el contador que ya lleva Excel, el estudiante sin ingresos fijos, el que busca inversiones.

---

## 3. SCOPE

### ✅ Qué va en el MVP (hoy)
- Captura automática de gastos desde Gmail (BBVA, Santander, MercadoPago)
- Registro manual de gastos vía WhatsApp en lenguaje natural
- Categorización manual por el usuario — el usuario asigna y ajusta sus reglas
- Soporte de múltiples monedas: ARS y USD
- Presupuestos mensuales por categoría
- Consultas en lenguaje natural vía WhatsApp ("¿cuánto gasté esta semana?")
- Web app para ver movimientos, categorías y presupuestos
- Feedback claro al usuario: qué gastos quedaron sin categorizar, estado de sus presupuestos, confirmación de cada movimiento registrado
- Multi-usuario (cada uno con su cuenta y sus datos)

### ❌ Qué NO va — nunca o no ahora
- **Pagos reales o transferencias desde la app** — esto no va en ninguna versión de Fina
- Gastos compartidos / split entre usuarios — primer feature post-MVP
- Importación de extractos PDF/Excel — segundo feature post-MVP (mismo nivel que gastos grupales)
- App nativa (iOS/Android) — por ahora es PWA
- Categorización con IA automática — feature premium de versiones futuras, no va en v1
- Notificaciones push — por ahora todo vía WhatsApp

### 🔮 Post-MVP (en orden de prioridad)
1. **Gastos compartidos** — roommates, viajes, grupos
2. **Importación de extractos** PDF/Excel — mismo nivel de prioridad que gastos grupales
3. **Categorización IA automática** — feature premium pago
4. App nativa iOS/Android
5. Recordatorios y alertas proactivas

---

## 4. PANTALLAS Y ESTADOS

### Web App
| Pantalla | Qué hace |
|----------|----------|
| **Home / Dashboard** | Resumen del mes: gastado vs presupuesto, últimos movimientos |
| **Movimientos** | Lista completa, filtros por fecha/categoría, editar/eliminar |
| **Categorías** | Ver y editar categorías y subcategorías propias |
| **Comercios** | Ver reglas de categorización, editar las que quedaron como "Otros" |
| **Presupuestos** | Definir límites mensuales por categoría |
| **Perfil** | Conectar Gmail, datos personales, WhatsApp |

### Estados clave del sistema
- **Movimiento sin categoría** → aparece en "Otros / Gastos no categorizados", el usuario lo asigna manualmente
- **Gmail conectado / desconectado** → el poller solo corre si hay refresh token válido
- **Ventana WhatsApp 24h** → Twilio solo puede mandar mensajes freeform si el usuario escribió en las últimas 24h
- **Regla AUTO** → creada automáticamente cuando llega un comercio nuevo, con confianza="AUTO" hasta que el usuario la categorice

---

## 5. DATOS

### Entidades principales
| Entidad | Descripción |
|---------|-------------|
| `MaestroUsuarios` | Usuario con Gmail, WhatsApp, refresh token de Google |
| `movimientos` | Cada gasto o ingreso con monto, fecha, categoría, origen |
| `Categoria` | Categorías del usuario (Alimentación, Transporte, etc.) |
| `SubCategoria` | Subcategorías dentro de cada categoría |
| `ReglaComercio` | Regla que mapea un comercio a una categoría (confianza: AUTO / MANUAL) |
| `Presupuestos` | Límite mensual por categoría por usuario |

### Orígenes de un movimiento
- `Gmail` — capturado automáticamente por el poller
- `WhatsApp` — registrado por el usuario en lenguaje natural
- `Manual` — cargado desde la web app

### Categoría por defecto
Comercios nuevos sin regla → **"Otros" (id=6) / "Gastos no categorizados" (id=42)**

---

## 6. STACK

| Capa | Tecnología |
|------|-----------|
| **Backend** | Python 3 · FastAPI 0.115 · SQLAlchemy 2.0 async |
| **Base de datos** | Neon PostgreSQL (serverless) |
| **Frontend** | React 18 · React Router 7 · Vite 6 · Tailwind CSS 4 · shadcn/ui · PWA |
| **Auth** | JWT 30 días · bcrypt · Google OAuth · Apple Sign-In |
| **IA** | OpenAI GPT-4.1-mini (extracción de gastos, queries, WhatsApp) · Whisper (audio) |
| **WhatsApp** | Twilio Sandbox (+1 570 909-1218) |
| **Deploy backend** | Google Cloud Run (`ahorros-backend`, `us-central1`) |
| **Deploy frontend** | Firebase Hosting (`ahorros-app-46e0e.web.app`) |
| **Gmail** | Google OAuth + Gmail API (poller interno cada ~90s) |

### Decisiones técnicas tomadas
- **Sin n8n** — el poller de Gmail es interno al backend Python
- **Sin Azure** — migrado a GCP + Neon
- **Sin AI merchant identifier** — removido por decisión de producto (Wave 2 premium)
- **Sin Google Sheets** — todo en Postgres

---

## 7. RIESGOS

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|-----------|
| Twilio Sandbox no escala a producción | Alta | Alto | Migrar a número Twilio real + templates aprobados por Meta |
| Gmail OAuth tokens expiran / se revocan | Media | Alto | Manejo de errores + notificación al usuario para reconectar |
| GPT extrae montos incorrectos | Media | Medio | Prompt ajustado + el usuario puede editar movimientos |
| Dedup race condition (poller + manual) | Alta | Medio | Agregar UNIQUE constraint en `(Id_usuario, Origen_Id)` — **pendiente** |
| Emails bancarios cambian formato HTML | Media | Medio | Ajuste de prompts + truncado generoso (8000 chars) |
| Ventana 24h de WhatsApp corta el flujo | Alta | Medio | Templates de Twilio para notificaciones fuera de ventana |
| Costo GPT escala con usuarios | Baja (hoy) | Alto (futuro) | Monitorear — actualmente ~3 calls por movimiento máximo |

---

## 8. CRITERIOS DE ÉXITO

### MVP (fase actual — testers internos)
- [ ] Un gasto de Gmail llega como WhatsApp en menos de 3 minutos
- [ ] El usuario puede consultar "¿cuánto gasté esta semana?" y recibir respuesta correcta
- [ ] Los comercios nuevos quedan en "Otros" y el usuario puede categorizarlos desde la app
- [ ] Cero pérdida de movimientos (dedup funcionando)
- [ ] Los 2 usuarios activos (Ignacio + Davor) tienen datos correctos en su dashboard

### Wave 1 (primeros usuarios externos)
- [ ] Onboarding completo sin ayuda: crear cuenta → conectar Gmail → primer gasto capturado
- [ ] Retención semana 2: el usuario sigue usando la app sin que nadie lo llame
- [ ] NPS > 7 entre los primeros 10 usuarios
- [ ] Menos de 1 movimiento duplicado por semana por usuario

### Métricas a mirar
- Movimientos creados por día por usuario
- % de movimientos en "Otros" (sin categorizar) — objetivo: bajar a <20%
- Tiempo desde email bancario → movimiento en app
- Mensajes WhatsApp respondidos correctamente

---

## PENDIENTES TÉCNICOS (al 08/06/2026)

- [ ] **UNIQUE constraint** en `movimientos(Id_usuario, Origen_Id)` para resolver race condition de dedup
- [ ] **Vista de comercios sin categorizar** — sección en la app que muestre los recientes con confianza="AUTO"
- [ ] **Twilio número real** — Davor configura webhook en Console Sandbox Settings
- [ ] **Gmail de Davor** — Davor conecta su cuenta para empezar a capturar sus gastos (Santander)
- [ ] **Templates WhatsApp** — para notificaciones fuera de ventana 24h

---

*Este documento es la fuente de verdad del producto. Se actualiza antes de arrancar cada fase nueva.*
