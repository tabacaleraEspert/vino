# Release v0.1 – Definition of Done

**Tag:** `v0.1.0`  
**Branch:** `release/0.1` (hotfix-only)

---

## Criterios de aceptación

### 1. Login
- [ ] Login funcional (auth básico o demo)
- [ ] Usuario puede iniciar sesión y acceder a la app
- [ ] Sesión persistente o token válido

### 2. Endpoints core
- [ ] `/health` – health check
- [ ] `/auth/*` – autenticación
- [ ] `/bootstrap` – datos iniciales
- [ ] `/movimientos` – CRUD movimientos
- [ ] `/categorias`, `/subcategorias`, `/reglas` – catálogo
- [ ] `/comercios` – comercios
- [ ] `/views` – vistas agregadas
- [ ] `/presupuestos` – presupuestos

### 3. Deploy reproducible
- [ ] CI/CD en GitHub Actions
- [ ] Backend desplegado en Azure Web App
- [ ] Frontend desplegado en Azure Static Web Apps
- [ ] Deploy desde `main` documentado y funcional

### 4. Variables en Azure
- [ ] Configuración vía Application Settings (Azure)
- [ ] Sin valores hardcodeados sensibles
- [ ] `.env.example` documenta variables necesarias

### 5. Sin secretos en repo
- [ ] `.gitignore` incluye: `.env`, `backend/creds/`, `*.json` sensibles
- [ ] Secretos solo en GitHub Secrets / Azure Key Vault
- [ ] No hay credenciales en historial de commits

---

## Política de la rama `release/0.1`

- **Uso:** Solo hotfixes críticos para v0.1
- **Flujo:** `release/0.1` → fix → merge a `main` → nuevo tag patch (ej. `v0.1.1`)
- **No incluir:** nuevas features; ir a `main` para v0.2+

---

## Checklist pre-release

Antes de considerar v0.1 cerrada:

1. [ ] Todos los criterios anteriores verificados
2. [ ] Tag `v0.1.0` creado
3. [ ] Branch `release/0.1` creada desde el tag
4. [ ] Documentación de deploy actualizada
