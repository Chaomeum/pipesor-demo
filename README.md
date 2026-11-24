# pipesor-demo

Repositorio de demostración de [Pipesor](https://github.com/pipesor-org), un prototipo AIOps que diagnostica
fallos de pipelines de GitHub Actions. Contiene un servicio mínimo (`orders-api`) cuyo workflow **Deploy** falla
a propósito en la verificación posterior al despliegue. Con él se recorre el flujo completo en pocos minutos:
captura del fallo, diagnóstico con LLM y RAG, remediación desde la web de GitHub, verificación con un check
verde y revisión humana del diagnóstico.

## El fallo

`deploy/orders-api.env` publica el servicio en el puerto `8080`, pero el health check apunta al `8081`:

```env
SERVICE_PORT=8080
HEALTHCHECK_URL=http://localhost:8081/health   # ← la corrección es 8080
```

El log del paso **Deploy and verify** muestra ambos datos: el servicio escucha en `8080` y la sonda no
consigue conexión en `8081`. Pipesor solo ve ese log, no el código del repositorio. Una ejecución dura unos
20 segundos.

Este fallo corresponde al patrón **C06 «Probe HTTP sin respuesta / conectividad»** del inventario de fallos
(OE1). El escenario equivalente de la evaluación, ESC-06, obtuvo la máxima puntuación en la revisión humana
(causa, pertinencia, respaldo en evidencia y seguridad).

## Workflows

| Workflow | Propósito | ¿Registrar en Pipesor? |
|---|---|---|
| `Deploy` (`deploy.yml`) | Pruebas unitarias, despliegue en el runner y health check. Se ejecuta con cada push a `main` que cambie `app/`, `deploy/` o `scripts/`, y manualmente. | **Sí, solo este** |
| `Pipesor report` (`pipesor-report.yml`) | Tras un `Deploy` fallido, obtiene el reporte de diagnóstico mediante OIDC y lo adjunta como artifact y resumen del run. | No |
| `Demo reset` (`demo-reset.yml`) | Restaura el puerto erróneo en `main` y lanza `Deploy` para generar un nuevo incidente. | No |

## Relación con los objetivos del proyecto

| Objetivo | Qué muestra la demo | Evidencia |
|---|---|---|
| **OE1:** caracterizar los fallos, eventos y logs CI/CD frecuentes | El fallo reproduce el patrón C06 del inventario R01–R03: 11 patrones y 26 eventos | [`inventory/failure-types/C06.json`](https://github.com/pipesor-org/pipesor-validation-scenarios/blob/main/inventory/failure-types/C06.json) |
| **OE2:** diseñar la arquitectura (ingesta, correlación, RAG, LLM, presentación y requisitos no funcionales) | El run fallido recorre la cadena diseñada: webhook `workflow_run` → Ingesta y normalización → Service Bus → Pipeline, Log/Event y NLP → Correlación → Diagnóstico (RAG + LLM) → dashboard y reporte | [Arquitectura y ADR](https://github.com/pipesor-org/pipesor-docs) |
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
3. **Registrar el workflow** en el dashboard: *Pipelines* → *Añadir workflow monitorizado* → repositorio
   `pipesor-demo` → workflow `Deploy`. Registrar exige ser administrador del repositorio.
4. **Concederte Operar** en el pipeline (sección *Personas*). Configurar no incluye Operar, y sin Operar no se
   pueden registrar la remediación ni la revisión.
5. **Ensayo:** ejecuta `Demo reset` (Actions → Demo reset → Run workflow). En unos 20 s falla `Deploy`; en
   aproximadamente un minuto aparece el incidente con su diagnóstico, y `Pipesor report` adjunta el reporte.
   Recorre el guion completo una vez y vuelve a ejecutar `Demo reset` para dejar un incidente abierto.

## Guion sugerido (15 minutos)

| Tiempo | Bloque | Qué hacer y decir |
|---|---|---|
| 0:00–3:00 | Problema y objetivos | Problema del TMD, objetivo general y la tabla OE1–OE3 de arriba. |
| 3:00–4:00 | 1. Inicio de sesión | Abrir el dashboard desplegado → aceptar la política y los términos → *Continuar con GitHub*. Sesión de 1 h y ningún token en la URL. |
| 4:00–5:00 | 2. Workflows monitorizados | *Pipelines* → *Añadir workflow monitorizado*: mostrar `pipesor-demo` y el workflow `Deploy` ya registrado. Pipesor solo registra; no modifica GitHub. |
| 5:00–6:30 | 3. Fallo en vivo (opcional) | Actions → `Demo reset` → *Run workflow*. Mientras corre, mostrar el log del run fallido: el servicio escucha en 8080 y la sonda usa 8081. Si no hay tiempo, usar el incidente preparado en el ensayo. |
| 6:30–8:30 | 4. Diagnóstico | Abrir el incidente: causa probable, recomendación y limitaciones, marcadas como salida del modelo; extracto y localizador, marcados como evidencia observada; fuentes de conocimiento. Mostrar el artifact y el resumen de `Pipesor report` en GitHub (OE3: reporte). |
| 8:30–11:00 | 5. Remediación | *Iniciar remediación* → en GitHub, abrir `deploy/orders-api.env` → lápiz (*Edit*) → cambiar `8081` por `8080` → *Commit changes* directamente a `main`. El push lanza `Deploy` y en unos 20 s aparece el check verde. En el dashboard: *Elige la ejecución de verificación* → seleccionar el run verde → *Registrar verificación* → *Resolver incidente*. |
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

Actions → **Demo reset** → *Run workflow*. Restaura `HEALTHCHECK_URL` con el puerto `8081` en `main` y lanza
`Deploy`, que falla y abre un incidente nuevo. Desmarca *Dispatch Deploy after the reset* si solo quieres
restaurar el archivo.

## Ejecutar en local

```bash
(cd app && python3 -m unittest -v)
bash scripts/deploy.sh deploy/orders-api.env   # falla con el puerto 8081
```

Solo requiere Python 3 y curl; no hay dependencias externas.
