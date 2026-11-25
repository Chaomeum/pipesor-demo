# Casos de la demo, paso a paso

Cinco casos, uno por pipeline. Los casos 1 a 4 son **casos de éxito esperados**: cada uno reproduce un patrón
del inventario de fallos (OE1), y el log contiene la pista que lleva a la causa. El caso 5 muestra un
diagnóstico **parcial**, útil para enseñar la corrección humana.

| Caso | Pipeline | Criticidad | Patrón | Se rompe con | Archivo que se corrige |
|---|---|---|---|---|---|
| 1 | `Deploy` | Alta | C06 | `python3 scripts/demo_break.py deploy` | `deploy/orders-api.env` |
| 2 | `Staging` | Baja | C07 | `python3 scripts/demo_break.py staging` | `staging/orders-api.json` |
| 3 | `Release` | Crítica | C02 | `python3 scripts/demo_break.py release` | `release/release.env` |
| 4 | `Reports` | Media | C11 | `python3 scripts/demo_break.py reports` | `reports/reports.env` |
| 5 | `Tests` | Media | Fuera del inventario | `python3 scripts/demo_break.py tests` | `app/server.py` |

## 0. Preparación (una vez)

1. **PostgreSQL de dev encendido.** Si se apagó, enciéndelo y espera uno o dos minutos a que los servicios se
   reconecten:
   ```bash
   az postgres flexible-server start -g rg-pipesor-dev -n pg-pipesor-dev-04f339b7
   ```
2. **GitHub App `pipesor-dev`** instalada con acceso a `pipesor-demo`, y la variable del repositorio
   `PIPESOR_RECOMMENDATION_URL` definida (Settings → Secrets and variables → Actions → Variables).
3. **Registrar los pipelines** en el dashboard: *Pipelines* → *Añadir workflow monitorizado* → repositorio
   `pipesor-demo` → el workflow → criticidad → *Monitorización: Activa*. Uno por uno:

   | Workflow | Criticidad |
   |---|---|
   | `Deploy` | Alta |
   | `Staging` | Baja |
   | `Release` | Crítica |
   | `Reports` | Media |
   | `Tests` | Media |

   No registres `Pipesor report`. Registrar exige ser administrador del repositorio.
4. **Concederte Operar** en cada pipeline (sección *Personas*). Sin Operar no se pueden registrar la
   remediación ni la revisión.
5. **Sesión de `gh`** en tu terminal (`gh auth status`). `demo_break.py` la usa para hacer el push con tu
   cuenta.

> Los runs que fallaron **antes** de registrar un pipeline no abren incidente. Después de registrarlo, rómpelo
> con `demo_break.py` para obtener uno.

## Flujo común a todos los casos

Cada caso se recorre igual. Lo que cambia es el archivo y la línea que se corrigen.

1. **Provocar el fallo.** En tu terminal, desde la raíz del repositorio:
   ```bash
   python3 scripts/demo_break.py <caso>
   ```
   En unos 20 s el run queda en rojo en *Actions*.
2. **Esperar el incidente.** En 30–60 s aparece en la cola del dashboard, con su diagnóstico, sin pulsar
   *Analizar*. A la vez, el run de `Pipesor report` en GitHub adjunta el reporte como artifact y como resumen.
3. **Revisar el diagnóstico.** Abrir el incidente: causa probable, recomendación y limitaciones (salida del
   modelo), y el extracto con su localizador (evidencia observada).
4. **Iniciar remediación.** Pulsar *Iniciar remediación* **antes** de editar en GitHub. La verificación solo
   acepta runs exitosos iniciados después de ese momento.
5. **Corregir en la web de GitHub.** Abrir el archivo del caso → lápiz (*Edit this file*) → hacer el cambio →
   *Commit changes…* → *Commit directly to the `main` branch* → *Commit changes*.
6. **Esperar el check verde.** El push lanza solo el pipeline del caso, que queda en verde en 10–20 s.
7. **Verificar y resolver.** En el incidente: *Elige la ejecución de verificación* → el run verde →
   *Registrar verificación* → *Resolver incidente*.
8. **Revisión humana.** *Confirmar diagnóstico* (o *Corregir*, si la causa no es la correcta) → comentario →
   registrar. La revisión deja de estar *Pendiente* en la lista de incidentes.
9. **Dejarlo listo otra vez.** `python3 scripts/demo_break.py <caso>` vuelve a romperlo y abre un incidente
   nuevo.

## Caso 1: `Deploy`, health check al puerto equivocado (C06)

- **Qué pasa:** `orders-api` arranca en el puerto `8080`, pero el health check posterior al despliegue
  consulta el `8081`. Los tres intentos fallan y el despliegue termina con error.
- **Qué muestra el log de GitHub:**
  ```
  [orders-api] listening on http://localhost:8080
  Verifying deployment: GET http://localhost:8081/health
  curl: (7) Failed to connect to localhost port 8081 ...
  Error: post-deployment verification could not reach orders-api at http://localhost:8081/health
  ```
- **Diagnóstico esperado:** el health check apunta a un puerto distinto del que usa el servicio. Corregir
  `HEALTHCHECK_URL` para usar el `8080`.
- **Protección de la evidencia:** el log de GitHub muestra `DB_HOST=10.20.4.15` y
  `DB_PASSWORD=demo-only-not-a-real-secret`. En el extracto de Pipesor ambos aparecen como `[redacted]`.
  Es el caso para mostrar la protección.
- **Corrección:** `deploy/orders-api.env`, línea `HEALTHCHECK_URL=http://localhost:8081/health` → cambiar
  `8081` por `8080`.
- **Revisión sugerida:** *Confirmar*.

## Caso 2: `Staging`, configuración inválida y rollback (C07)

- **Qué pasa:** el JSON de configuración de staging tiene una coma final. El servicio no carga su
  configuración, responde HTTP 500 al probe de arranque y la release no se promueve: staging sigue con la
  versión anterior (rollback).
- **Qué muestra el log de GitHub:**
  ```
  Startup probe: GET http://localhost:8090/health -> HTTP 500
  [orders-api …] fail: Application startup exception: invalid configuration staging/orders-api.json:
    Illegal trailing comma before end of object: line 6 column 23 (char 110)
  Rollback: release … not promoted; staging keeps the current release
  Error: startup probe returned HTTP 500 for orders-api … in staging; rollback complete
  ```
- **Diagnóstico esperado:** la coma final en `staging/orders-api.json` (línea 6) impide cargar la
  configuración y provoca el HTTP 500. Quitar la coma.
- **Corrección:** `staging/orders-api.json`, línea 6: `"exportCsv": false,` → `"exportCsv": false` (borrar
  la coma).
- **Revisión sugerida:** *Confirmar*.

## Caso 3: `Release`, ruta del script con mayúscula equivocada (C02)

- **Qué pasa:** la release ejecuta sus migraciones con `release/Scripts/migrate.sh`, pero el archivo está en
  `release/scripts/migrate.sh`. En Linux las rutas distinguen mayúsculas, así que el script no existe y la
  release no se publica. Es el pipeline de criticidad **crítica**.
- **Qué muestra el log de GitHub:**
  ```
  Release bundle:
    release/release.env
    release/scripts/migrate.sh
  Running database migrations: bash release/Scripts/migrate.sh
  bash: release/Scripts/migrate.sh: No such file or directory
  Error: database migrations failed for orders-api release …; release not published
  ```
- **Diagnóstico esperado:** la ruta invocada usa `Scripts` con mayúscula, mientras que el bundle contiene
  `scripts`. Corregir `MIGRATION_SCRIPT`.
- **Corrección:** `release/release.env`, línea `MIGRATION_SCRIPT=release/Scripts/migrate.sh` → cambiar
  `Scripts` por `scripts`.
- **Revisión sugerida:** *Confirmar*. Si el diagnóstico propone renombrar el directorio en vez de corregir la
  ruta, la causa sigue siendo correcta.

## Caso 4: `Reports`, plazo de arranque demasiado corto (C11)

- **Qué pasa:** `orders-reports` carga cuatro plantillas al arrancar (unos 8 s) y, mientras tanto, su
  `/health` responde 503. El probe de arranque solo espera 5 s, así que se rinde antes de que el servicio
  esté listo.
- **Qué muestra el log de GitHub:**
  ```
  STARTUP_TIMEOUT_SECONDS=5
  startup probe: HTTP 503 after 1s
  …
  startup probe: HTTP 503 after 5s
  [orders-reports] info: loading report templates 3/4
  Error: orders-reports was not ready within the 5s startup deadline (last probe HTTP 503)
  ```
- **Diagnóstico esperado:** el servicio sigue arrancando (carga de plantillas) cuando vence el plazo de 5 s
  del probe. Ampliar `STARTUP_TIMEOUT_SECONDS`.
- **Corrección:** `reports/reports.env`, línea `STARTUP_TIMEOUT_SECONDS=5` → cambiar `5` por `20`. Usa
  exactamente `20`: `demo_break.py` busca ese valor para volver a romperlo.
- **Revisión sugerida:** *Confirmar*.

## Caso 5: `Tests`, campo equivocado (diagnóstico parcial)

- **Qué pasa:** `paid_total` lee `order["amount"]`, pero los pedidos guardan el importe en `total`. Una prueba
  unitaria falla con `KeyError`.
- **Qué muestra el log de GitHub:**
  ```
  File ".../app/server.py", line 26, in <genexpr>
      paid = sum(order["amount"] for order in orders if order["status"] == "PAID")
  KeyError: 'amount'
  FAILED (errors=1)
  ```
- **Diagnóstico esperado:** apunta a la línea correcta, pero suele dudar entre «falta el campo en los datos» y
  «el campo tiene otro nombre», porque el log nunca menciona `total`.
- **Corrección:** `app/server.py`, línea 26: `order["amount"]` → `order["total"]`.
- **Revisión sugerida:** *Corregir*, con un comentario como: «La causa es que `paid_total` lee `amount`, pero
  los pedidos usan el campo `total`; los datos son correctos.» Muestra que el responsable valida o corrige al
  modelo, y que eso queda registrado.

## Antes de presentar

- [ ] PostgreSQL encendido y el dashboard carga.
- [ ] Los cinco pipelines registrados, con *Monitorización: Activa* y Operar concedido.
- [ ] `python3 scripts/demo_break.py` ejecutado: cinco runs en rojo y cinco incidentes abiertos con
      diagnóstico.
- [ ] Cada run fallido tiene su `Pipesor report` en verde, con el artifact `pipesor-report-…`.
- [ ] Pestañas abiertas: el dashboard, *Actions* del repositorio y `deploy/orders-api.env` en GitHub.

## Si algo no sale

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| El run falla, pero no aparece el incidente | El pipeline no está registrado o no está en *Activa*, o el run es anterior al registro | Revisar el registro y volver a ejecutar `demo_break.py <caso>` |
| Ningún incidente nuevo y `Pipesor report` espera hasta agotar el plazo | PostgreSQL apagado o servicios sin reconectar | Encender PostgreSQL y esperar unos minutos |
| El run verde no aparece en *Elige la ejecución de verificación* | El run empezó antes de *Iniciar remediación*, o es un *Re-run* del run fallido | Hacer otro commit de la corrección, o lanzar el workflow con *Run workflow* |
| `demo_break.py` dice *neither the fixed nor the failing text was found* | La corrección se hizo con otro valor | Dejar el archivo con el valor corregido de este documento y volver a ejecutarlo |
| `Pipesor report` no se ejecutó | El run lo lanzó el `GITHUB_TOKEN` de un workflow | Romper siempre con `demo_break.py` desde tu terminal |
