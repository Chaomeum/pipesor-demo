# pipesor-demo

Repositorio de demostración de [Pipesor](https://github.com/pipesor-org), un prototipo AIOps que diagnostica
fallos de pipelines de GitHub Actions. Contiene un servicio mínimo (`orders-api`) con **cinco pipelines
monitorizados** que fallan a propósito. Con ellos se recorre el flujo completo en pocos minutos: captura
automática de los fallos, diagnóstico con LLM y RAG, remediación desde la web de GitHub, verificación con un
check verde y revisión humana del diagnóstico.

**Paso a paso de cada caso: [`CASOS.md`](CASOS.md).**

## Qué muestra

1. **Observabilidad activa sobre varios pipelines.** Un solo push rompe los cinco workflows. La GitHub App
   envía el webhook `workflow_run`, Pipesor captura los runs y abre **un incidente con su diagnóstico por
   pipeline, sin que nadie pida un análisis**. Cada pipeline se registra con una criticidad (crítica, alta,
   media o baja), y la severidad inicial de su incidente la refleja.
2. **Protección de la evidencia antes del LLM.** El despliegue imprime su configuración efectiva, que
   incluye un host interno y una contraseña de demostración. GitHub los muestra en claro. Ingesta los
   enmascara (`[redacted]`) antes de que la evidencia llegue a Log/Event, NLP y el modelo. Son las reglas de
   `BoundedEvidenceProtection`: valores de claves sensibles (`*PASSWORD`, `*SECRET`, `*TOKEN`, `*APIKEY`,
   `ConnectionString`…), direcciones IP, correos y tokens conocidos.
3. **Remediación y verificación** con una edición de una línea en la web de GitHub.
4. **Revisión humana**: el responsable confirma o corrige cada diagnóstico, y queda registrado.

## Los casos

| Caso | Pipeline | Criticidad | Patrón (OE1) | Fallo | Corrección en la web de GitHub |
|---|---|---|---|---|---|
| 1 | `Deploy` | Alta | C06 Probe HTTP sin respuesta | El servicio escucha en `8080`, pero el health check apunta al `8081`. | `deploy/orders-api.env`: `8081` → `8080` |
| 2 | `Staging` | Baja | C07 Probe HTTP con respuesta de error | Coma final en el JSON de configuración: el servicio arranca sin configuración, responde HTTP 500 y la release no se promueve (rollback). | `staging/orders-api.json`, línea 6: quitar la coma de `"exportCsv": false,` |
| 3 | `Release` | Crítica | C02 Ruta de despliegue inexistente | La release invoca `release/Scripts/migrate.sh`, pero el archivo está en `release/scripts/` (Linux distingue mayúsculas). | `release/release.env`: `Scripts` → `scripts` |
| 4 | `Reports` | Media | C11 Sondeo con plazo insuficiente | El servicio tarda unos 8 s en cargar sus plantillas, pero el plazo del probe de arranque es de 5 s. | `reports/reports.env`: `STARTUP_TIMEOUT_SECONDS=5` → `20` |
| 5 | `Tests` | Media | Fuera del inventario (como el control NC-02) | `paid_total` lee `order["amount"]`, pero los pedidos usan `total`: `KeyError: 'amount'`. | `app/server.py`, línea 26: `order["amount"]` → `order["total"]` |

Pipesor solo ve el log del run, no el código del repositorio. Cada run dura entre 10 y 20 segundos.

- **Casos 1 a 4: casos de éxito esperados.** Cada uno reproduce un patrón distinto del inventario de fallos
  (OE1), y en su error el log ya contiene la pista que lleva a la causa. Sus escenarios equivalentes de la
  evaluación (ESC-06, ESC-10, ESC-02 y ESC-05) obtuvieron 2/2 en causa probable en la revisión humana de OE3-I2.
- **Caso 5: diagnóstico parcial esperado.** El log dice `KeyError: 'amount'`, pero nunca menciona el campo
  `total`, así que el modelo duda entre «falta el dato» y «el campo se llama distinto». Sirve para mostrar
  *Corregir* en la revisión humana: el humano valida o corrige al modelo.

En la configuración, `DB_HOST` y `DB_PASSWORD` son valores de demostración: no existe ninguna base de datos y la
contraseña no es un secreto real.

## Workflows

| Workflow | Se ejecuta con los push a `main` que cambian… | ¿Registrar en Pipesor? |
|---|---|---|
| `Deploy` (`deploy.yml`) | `deploy/`, `scripts/deploy.sh` | **Sí**, criticidad alta |
| `Staging` (`staging.yml`) | `staging/`, `scripts/staging.sh` | **Sí**, criticidad baja |
| `Release` (`release.yml`) | `release/`, `scripts/release.sh` | **Sí**, criticidad crítica |
| `Reports` (`reports.yml`) | `reports/`, `scripts/reports.sh` | **Sí**, criticidad media |
| `Tests` (`tests.yml`) | `app/` | **Sí**, criticidad media |
| `Pipesor report` (`pipesor-report.yml`) | Tras cualquier run fallido de los anteriores, obtiene el reporte de diagnóstico mediante OIDC y lo adjunta como artifact y resumen del run. | No |

Todos admiten además ejecución manual (*Run workflow*). Cada corrección dispara solo su propio pipeline, así
que el run verde de una no genera un fallo nuevo en otro.

## Relación con los objetivos del proyecto

| Objetivo | Qué muestra la demo | Evidencia |
|---|---|---|
| **OE1:** caracterizar los fallos, eventos y logs CI/CD frecuentes | Los casos 1 a 4 reproducen cuatro patrones del inventario R01–R03 (11 patrones, 26 eventos): C06, C07, C02 y C11 | [`inventory/failure-types`](https://github.com/pipesor-org/pipesor-validation-scenarios/tree/main/inventory/failure-types) |
| **OE2:** diseñar la arquitectura (ingesta, correlación, RAG, LLM, presentación y requisitos no funcionales) | Cada run fallido recorre la cadena diseñada: webhook `workflow_run` → Ingesta y normalización → Service Bus → Pipeline, Log/Event y NLP → Correlación → Diagnóstico (RAG + LLM) → dashboard y reporte. Requisitos no funcionales visibles: enmascaramiento de secretos e IP antes del LLM, sesión sin tokens en la URL, permisos Configurar y Operar | [Arquitectura y ADR](https://github.com/pipesor-org/pipesor-docs) |
| **OE3:** implementar el prototipo (LLM + RAG, reporte y dashboard) | Diagnóstico en el dashboard con evidencia observada separada de la inferencia, reporte publicado como artifact del workflow, revisión humana y ciclo del incidente | [Informe de validación OE3-I2](https://github.com/pipesor-org/pipesor-docs/blob/main/docs/research/informe-validacion-oe3.md) |

**Resultados de OE3-I2** (corrida oficial del 23/11/2026, revisión humana del 24/11/2026):

| Indicador | Resultado | Meta |
|---|---|---|
| Acierto estricto en la causa probable (revisión humana) | **17/20 = 85 %** (IC Wilson 95 % [0,64; 0,95]) | ≥ 80 % |
| Acierto según el juez LLM (auxiliar) | 18/20 = 90 % | |
| Escenarios de fallo | 10 escenarios × 2 variantes, más controles | 10 |
| Registros de log procesados | 5280 líneas | ≥ 1000 |
| Ejecuciones con el resultado esperado | 28/28; 26/26 diagnósticos y reportes publicados | |
| Recomendaciones (rúbrica de 0 a 2) | pertinencia 1,7; respaldo en evidencia 2,0; seguridad 1,85 | |
| Dashboard | incidente visible 20/20; revisión registrada 20/20 | |

Fuente: [`results/review-2026-11-23-oe3-test-r2`](https://github.com/pipesor-org/pipesor-validation-scenarios/tree/main/results/review-2026-11-23-oe3-test-r2).
OE4, la comparación con el diagnóstico manual y la reducción del TMD, corresponde al siguiente periodo.

## Preparación

Los pasos de preparación, el ensayo de cada caso y la lista de comprobación antes de presentar están en
[`CASOS.md`](CASOS.md).

## Guion sugerido (15 minutos)

| Tiempo | Bloque | Qué hacer y decir |
|---|---|---|
| 0:00–3:00 | Problema y objetivos | Problema del TMD, objetivo general y la tabla OE1–OE3 de arriba. |
| 3:00–4:00 | 1. Inicio de sesión | Abrir el dashboard desplegado → aceptar la política y los términos → *Continuar con GitHub*. Sesión de 1 h y ningún token en la URL. |
| 4:00–5:00 | 2. Workflows monitorizados | *Pipelines*: los cinco workflows registrados, con criticidad crítica, alta, media y baja, y *Monitorización: Activa*. *Añadir workflow monitorizado* para mostrar cómo se conecta uno nuevo. Pipesor solo registra; no modifica GitHub. |
| 5:00–6:00 | 3. Fallos en vivo (opcional) | `python3 scripts/demo_break.py`: un solo push rompe los cinco pipelines. Mostrar en Actions los runs en rojo y abrir la cola de incidentes: aparecen cinco incidentes, cada uno con su severidad, **sin pulsar *Analizar***. Esa es la observabilidad activa. Si no hay tiempo, usar los incidentes preparados. |
| 6:00–8:30 | 4. Diagnóstico y protección | Abrir el incidente de `Deploy`: causa probable, recomendación y limitaciones, marcadas como salida del modelo; extracto y localizador, marcados como evidencia observada. Comparar lado a lado: el log de GitHub muestra `DB_HOST=10.20.4.15` y `DB_PASSWORD=…`, y el extracto de Pipesor muestra `[redacted]`. Mostrar el resumen de `Pipesor report` en el run de GitHub (OE3: reporte). Abrir rápidamente `Release` (crítica) o `Staging`: otro patrón del inventario, otra causa bien identificada. |
| 8:30–11:00 | 5. Remediación | En el incidente de `Deploy`: *Iniciar remediación* → en GitHub, cambiar `8081` por `8080` en `deploy/orders-api.env` → *Commit changes* a `main`. El push lanza solo `Deploy`, que queda en verde en unos 15 s. En el dashboard: *Elige la ejecución de verificación* → el run verde → *Registrar verificación* → *Resolver incidente*. |
| 11:00–12:00 | 6. Revisión humana | En `Deploy`: *Confirmar diagnóstico* → comentario → *Registrar confirmación*. Si hay tiempo, en `Tests`: *Corregir* con la causa real (el campo es `total`). |
| 12:00–15:00 | Resultados | Tabla de resultados de OE3-I2: 85 % de acierto humano frente a la meta del 80 %, rúbrica de las recomendaciones y limitaciones (simulados frente a reales, OE4 pendiente). Preguntas. |

Si `Deploy` fallara el día de la demo, cualquiera de los casos 2 a 4 sirve para los bloques 4 a 6; sus
correcciones están en [`CASOS.md`](CASOS.md).

## Reiniciar la demo

```bash
python3 scripts/demo_break.py                  # los cinco casos
python3 scripts/demo_break.py release staging  # solo algunos: deploy, staging, release, reports, tests
```

El script restaura los fallos en `main` con **un solo commit hecho con tu cuenta**, y ese push lanza los
pipelines de los archivos cambiados. Si un archivo ya estaba en estado de fallo, no lo cambia y lanza ese
workflow con *workflow_dispatch*. En ambos casos, cada pipeline elegido falla una vez y abre un incidente nuevo.

Debe ejecutarse con tu sesión de `gh`, no desde un workflow. Un push o un dispatch hecho con el `GITHUB_TOKEN` de
un workflow no dispara `Pipesor report`, y no se generaría el artifact del reporte.

## Ejecutar en local

```bash
bash scripts/deploy.sh deploy/orders-api.env      # falla: el health check usa el puerto 8081
bash scripts/staging.sh staging/orders-api.json   # falla: HTTP 500 por la coma final
bash scripts/release.sh release/release.env       # falla: release/Scripts/migrate.sh no existe
bash scripts/reports.sh reports/reports.env       # falla: plazo de arranque de 5 s
(cd app && python3 -m unittest -v)                # falla: KeyError: 'amount'
```

Solo requiere Python 3 y curl; no hay dependencias externas.
