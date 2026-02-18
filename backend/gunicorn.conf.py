"""
Configuración Gunicorn para producción.
Usar: gunicorn app.main:app -c gunicorn.conf.py
"""
import multiprocessing

# Worker class para ASGI (FastAPI)
worker_class = "uvicorn.workers.UvicornWorker"

# Workers: 2 para 1 vCPU, ajustar según CPU disponibles
workers = min(2, multiprocessing.cpu_count() * 2 + 1)
threads = 2

# Timeout para requests largos (Sheets puede tardar)
timeout = 120

# Keep-alive
keepalive = 5

# Bind
bind = "0.0.0.0:8000"
