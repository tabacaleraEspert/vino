#!/bin/sh
# Comando de arranque para producción (Azure Web App, etc.)
# Configurar en Azure: Startup Command = ./run.sh o el comando directo abajo
exec gunicorn app.main:app -c gunicorn.conf.py
