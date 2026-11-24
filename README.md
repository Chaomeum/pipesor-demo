# pipesor-demo

Repositorio de demostración de [Pipesor](https://github.com/pipesor-org), un prototipo AIOps que diagnostica
fallos de pipelines de GitHub Actions. Contiene un servicio mínimo (`orders-api`) con **dos pipelines
monitorizados** que fallan a propósito. Con ellos se recorre el flujo completo en pocos minutos: captura
automática de los fallos, diagnóstico con LLM y RAG, remediación desde la web de GitHub, verificación con un
check verde y revisión humana del diagnóstico.

## Qué muestra

1. **Observabilidad activa sobre varios pipelines.** Un solo push rompe los dos workflows. La GitHub App envía
   el webhook `workflow_run`, Pipesor captura ambos runs y abre **dos incidentes con su diagnóstico sin que
   nadie pida un análisis**. Cada pipeline se registra con una criticidad distinta, y la severidad inicial de
   su incidente la refleja.
2. **Protección de la evidencia antes del LLM.** El despliegue imprime su configuración efectiva, que
   incluye un host interno y una contraseña de demostración. GitHub los muestra en claro. Ingesta los
   enmascara (`[redacted]`) antes de que la evidencia llegue a Log/Event, NLP y el modelo. Son las reglas de
   `BoundedEvidenceProtection`: valores de claves sensibles (`*PASSWORD`, `*SECRET`, `*TOKEN`, `*APIKEY`,
   `ConnectionString`…), direcciones IP, correos y tokens conocidos.
3. **Remediación y verificación** con una edición de una línea en la web de GitHub.

## Los fallos

| Pipeline | Criticidad sugerida | Fallo | Corrección en la web de GitHub |
|---|---|---|---|
| `Deploy` | Alta | El servicio escucha en `8080`, pero el health check de `deploy/orders-api.env` apunta al `8081`. El log muestra `listening on http://localhost:8080` y `Failed to connect to localhost port 8081`. | En `deploy/orders-api.env`, cambiar `8081` por `8080`. |
| `Tests` | Media | `paid_total` lee `order["amount"]`, pero los pedidos usan el campo `total`: `KeyError: 'amount'` en `app/server.py`, línea 23. | En `app/server.py`, cambiar `order["amount"]` por `order["total"]`. |

Pipesor solo ve el log del run, no el código del repositorio. Cada run dura entre 10 y 20 segundos.

- **`Deploy`** corresponde al patrón **C06 «Probe HTTP sin respuesta / conectividad»** del inventario de fallos
  (OE1). Su escenario equivalente en la evaluación, ESC-06, obtuvo la máxima puntuación en la revisión humana:
  causa, pertinencia, respaldo en evidencia y seguridad.
- **`Tests`** es un fallo de prueba unitaria. Queda fuera de los patrones del inventario, como el control
  NC-02 de la evaluación. Sirve para mostrar que Pipesor diagnostica también fallos generales de CI.

En la configuración, `DB_HOST` y `DB_PASSWORD` son valores de demostración: no existe ninguna base de datos y la
contraseña no es un secreto real.

## Workflows

| Workflow | Propósito | ¿Registrar en Pipesor? |
|---|---|---|
| `Deploy` (`deploy.yml`) | Despliega el servicio en el runner y comprueba su health check. Se ejecuta con los push a `main` que cambian `deploy/` o `scripts/deploy.sh`, y manualmente. | **Sí** |
| `Tests` (`tests.yml`) | Pruebas unitarias. Se ejecuta con los push a `main` que cambian `app/`, y manualmente. | **Sí** |
| `Pipesor report` (`pipesor-report.yml`) | Tras un `Deploy` o un `Tests` fallido, obtiene el reporte de diagnóstico mediante OIDC y lo adjunta como artifact y resumen del run. | No |

Cada corrección dispara solo su propio pipeline. Así, el run verde de una no genera un fallo nuevo en el otro.

## Relación con los objetivos del proyecto

| Objetivo | Qué muestra la demo | Evidencia |
|---|---|---|
| **OE1:** caracterizar los fallos, eventos y logs CI/CD frecuentes | `Deploy` reproduce el patrón C06 del inventario R01–R03 (11 patrones, 26 eventos) | [`inventory/failure-types/C06.json`](https://github.com/pipesor-org/pipesor-validation-scenarios/blob/main/inventory/failure-types/C06.json) |
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

## Preparación (una vez, antes de la demo)

1. **Instalar la GitHub App `pipesor-dev`** en este repositorio (Settings → GitHub Apps, o desde la página de la
   App → *Configure*), con acceso a `pipesor-demo`.
2. **Variable del repositorio** `PIPESOR_RECOMMENDATION_URL` con la URL pública del servicio de Recomendación del
   despliegue (Settings → Secrets and variables → Actions → Variables).
3. **Registrar los dos workflows** en el dashboard: *Pipelines* → *Añadir workflow monitorizado* → repositorio
   `pipesor-demo` → `Deploy` con criticidad alta, y después `Tests` con criticidad media. En ambos,
   *Monitorización: Activa*. Registrar exige ser administrador del repositorio.
4. **Concederte Operar** en cada pipeline (sección *Personas*). Configurar no incluye Operar, y sin Operar no se
   pueden registrar la remediación ni la revisión.
5. **Ensayo.** Ejecuta en tu terminal `python3 scripts/demo_break.py`, que usa tu sesión de `gh`. En unos
   20 s fallan los dos runs. En aproximadamente un minuto aparecen los dos incidentes con su diagnóstico, y
   `Pipesor report` adjunta un reporte a cada uno. Recorre el guion completo una vez.
6. **Antes de presentar,** corrige `Tests` si lo corregiste solo en el ensayo, y vuelve a ejecutar
   `demo_break.py` para dejar los dos incidentes abiertos. También puedes ejecutarlo en vivo, en el bloque 3.

## Guion sugerido (15 minutos)

| Tiempo | Bloque | Qué hacer y decir |
|---|---|---|
| 0:00–3:00 | Problema y objetivos | Problema del TMD, objetivo general y la tabla OE1–OE3 de arriba. |
| 3:00–4:00 | 1. Inicio de sesión | Abrir el dashboard desplegado → aceptar la política y los términos → *Continuar con GitHub*. Sesión de 1 h y ningún token en la URL. |
| 4:00–5:00 | 2. Workflows monitorizados | *Pipelines*: los dos workflows registrados, con criticidad distinta y *Monitorización: Activa*. *Añadir workflow monitorizado* para mostrar cómo se conecta uno nuevo. Pipesor solo registra; no modifica GitHub. |
| 5:00–6:00 | 3. Fallos en vivo (opcional) | `python3 scripts/demo_break.py`: un solo push rompe ambos pipelines. Mostrar en Actions los dos runs en rojo y abrir la cola de incidentes del dashboard: aparecen dos incidentes **sin pulsar *Analizar***. Esa es la observabilidad activa. Si no hay tiempo, usar los incidentes preparados. |
| 6:00–8:30 | 4. Diagnóstico y protección | Abrir el incidente de `Deploy`: causa probable, recomendación y limitaciones, marcadas como salida del modelo; extracto y localizador, marcados como evidencia observada. Comparar lado a lado: el log de GitHub muestra `DB_HOST=10.20.4.15` y `DB_PASSWORD=…`, y el extracto de Pipesor muestra `[redacted]`, porque el modelo nunca recibió esos valores. Mostrar el resumen de `Pipesor report` en el run de GitHub (OE3: reporte). Mencionar el incidente de `Tests` como segundo pipeline. |
| 8:30–11:00 | 5. Remediación | En el incidente de `Deploy`: *Iniciar remediación* → en GitHub, abrir `deploy/orders-api.env` → lápiz (*Edit*) → cambiar `8081` por `8080` → *Commit changes* directamente a `main`. El push lanza solo `Deploy`, que queda en verde en unos 15 s. En el dashboard: *Elige la ejecución de verificación* → seleccionar el run verde → *Registrar verificación* → *Resolver incidente*. |
| 11:00–12:00 | 6. Revisión humana | *Confirmar diagnóstico* → comentario → *Registrar confirmación*. El estado del incidente en la lista pasa de *Pendiente* a *Confirmado*. |
| 12:00–15:00 | Resultados | Tabla de resultados de OE3-I2: 85 % de acierto humano frente a la meta del 80 %, rúbrica de las recomendaciones y limitaciones (simulados frente a reales, OE4 pendiente). Preguntas. |

Notas para el guion:

- La verificación solo acepta ejecuciones **exitosas** del mismo workflow **iniciadas después** de *Iniciar
  remediación*. Por eso se pulsa *Iniciar remediación* antes de editar en GitHub. Un *Re-run* del run fallido
  usa el mismo commit y volvería a fallar.
- Resolver el incidente (decisión operativa) y validar el diagnóstico (revisión humana) son pasos
  independientes; pueden hacerse en cualquier orden.
- El diagnóstico tarda alrededor de 30–60 s después de que falla el run. Si el bloque 3 se hace en vivo,
  aprovecha esa espera para explicar la arquitectura (OE2).

## Reiniciar la demo

```bash
python3 scripts/demo_break.py
```

El script restaura los dos fallos en `main` con **un solo commit hecho con tu cuenta**, y ese push lanza
`Deploy` y `Tests`. Si un archivo ya estaba en estado de fallo, no lo cambia y lanza ese workflow con
*workflow_dispatch*. En ambos casos, cada pipeline falla una vez y abre un incidente nuevo.

Debe ejecutarse con tu sesión de `gh`, no desde un workflow. Un push o un dispatch hecho con el `GITHUB_TOKEN` de
un workflow no dispara `Pipesor report`, y no se generaría el artifact del reporte.

## Ejecutar en local

```bash
(cd app && python3 -m unittest -v)                 # falla con KeyError: 'amount'
bash scripts/deploy.sh deploy/orders-api.env   # falla con el puerto 8081
```

Solo requiere Python 3 y curl; no hay dependencias externas.
