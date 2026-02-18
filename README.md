# Vino - Finanzas Personales

Aplicación de finanzas personales con backend FastAPI y frontend React.

## Requisitos

- Python 3.11+
- Node.js 18+
- npm o pnpm

## Desarrollo

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

El API estará en http://127.0.0.1:8000

### Frontend

```bash
cd frontend
npm install
npm run dev
```

El frontend estará en http://localhost:5173

### Flujo

1. Inicia el backend en el puerto 8000
2. Inicia el frontend (usa proxy a /api → backend)
3. Abre http://localhost:5173
4. Inicia sesión con cualquier usuario/contraseña (el backend en modo demo acepta cualquiera)
