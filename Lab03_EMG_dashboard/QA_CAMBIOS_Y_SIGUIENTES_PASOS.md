# Guía QA: cambios de robustez del dashboard EMG

## 1. Propósito de este documento

Este documento explica, con lenguaje sencillo pero técnico, los cambios de calidad realizados en el proyecto Dashboard EMG · BioForja.

Está pensado para que una persona de QA junior pueda:

- entender qué problema se encontró;
- explicar por qué se hizo cada cambio;
- saber cómo comprobar que el cambio funciona;
- identificar qué aspectos todavía necesitan revisión.

El objetivo no es agregar criterios clínicos. El objetivo es que el software falle de forma clara cuando recibe datos inválidos y que no produzca números que parezcan válidos cuando no lo son.

## 2. Alcance y archivos protegidos

Se trabajó únicamente sobre:

- `src/emg_dashboard/data_validation.py`
- `src/emg_dashboard/preprocessing_metrics.py`
- `src/emg_dashboard/metrics.py`
- `src/emg_dashboard/visualization.py`
- los tests de esos módulos dentro de `tests/`

No se modificaron:

- `src/emg_dashboard/io.py`;
- ningún archivo bajo `data/raw/`;
- el formato TDF;
- las firmas públicas del lector ni el contrato de columnas;
- `app.py`.

La razón es preservar la fuente original de datos y el contrato de carga. Si se detecta un problema en el lector TDF, debe documentarse como recomendación separada y no corregirse dentro de estos cambios.

## 3. Principio QA aplicado

En cada función se buscó responder tres preguntas:

1. ¿Qué entradas son válidas?
2. ¿Qué debe ocurrir con una entrada inválida?
3. ¿El resultado podría parecer correcto aunque realmente sea engañoso?

Cuando una entrada no puede producir un resultado confiable, el comportamiento esperado es lanzar `ValueError` con un mensaje comprensible. En visualización, donde es razonable continuar, se conserva la figura y se alinean las series para evitar un crash.

## 4. Cambios en validación de datos

### `sampling_report`

Se agregó validación para:

- rechazar una frecuencia de muestreo (`fs`) no positiva o no finita;
- exigir la columna `time_s`;
- rechazar un DataFrame sin tiempos válidos;
- contar correctamente los tiempos duplicados.

Antes, el uso de `.unique()` eliminaba los duplicados antes de contarlos. Eso hacía que el reporte indicara cero duplicados incluso cuando la entrada original los tenía.

#### Por qué importa

Un `fs` inválido altera todas las conversiones entre muestras y segundos. Los tiempos vacíos o duplicados pueden indicar un problema de adquisición o de preparación del DataFrame.

### `channel_quality`

Se conservaron sus métricas de calidad y se cubrió explícitamente el caso de una señal completamente NaN. Ese caso se reporta como canal no válido, con fracción válida igual a cero.

### `detect_powerline_interference`

Se validan:

- `fs` positivo y finito;
- frecuencia objetivo positiva;
- tolerancia no negativa;
- umbral de razón positivo.

Las señales muy cortas siguen devolviendo un resultado seguro (`has_noise=False`) porque no hay suficientes muestras para estimar una evidencia espectral confiable.

#### Por qué importa

La función se usa para decidir si existe evidencia de interferencia de red. No debe convertir parámetros absurdos en un resultado aparentemente válido.

## 5. Cambios en preprocesamiento

Se agregó un helper interno para validar antes de llamar a `sosfiltfilt`.

Ahora se rechazan explícitamente:

- `fs` inválida;
- señales vacías;
- señales con NaN o infinitos;
- arreglos que no son unidimensionales;
- señales demasiado cortas para el filtro.

También se agregaron validaciones para:

- `0 < low_hz < high_hz < fs/2` en el pasabanda;
- notch dentro de `(0, fs/2)`;
- ancho de banda notch positivo;
- `0 < cutoff_hz < fs/2` en la envolvente.

`remove_dc` ahora exige una señal finita y calcula la media normal, en lugar de propagar silenciosamente NaN mediante `nanmean`.

#### Por qué importa

Los filtros de SciPy necesitan suficientes muestras para funcionar. Si la señal es demasiado corta, el error original puede ser técnico y poco entendible. El guard devuelve un mensaje orientado a la causa: la señal no alcanza la longitud mínima segura.

El rechazo de NaN evita que una etapa produzca un vector completo de NaN que luego llegue a las métricas sin una explicación clara.

## 6. Cambios en métricas

### RMS móvil

Se agregaron controles para:

- señales vacías;
- ventanas no finitas;
- ventanas no positivas.

La política existente para NaN se conserva: las ventanas sin muestras válidas producen NaN, no cero. Esto evita interpretar un bloque de datos faltantes como silencio muscular.

### Activaciones

Se validan:

- `baseline_seconds` positivo;
- multiplicador de umbral no negativo;
- duración mínima y separación de unión no negativas;
- umbral finito.

Una envolvente completamente no válida ya no genera un umbral inventado.

### Resumen por segmento

`segment_summary` exige que la señal filtrada y la envolvente tengan la misma longitud.

#### Por qué importa

Si las señales no representan las mismas muestras, combinar sus métricas puede producir un resumen internamente inconsistente.

### Sensibilidad de ventanas

Se conserva el comportamiento de devolver resultados vacíos (`n=0` y métricas NaN) cuando una ventana es mayor que la señal. Esto permite mostrar que no hay suficientes datos sin inventar una estimación.

## 7. Cambios en visualización

Se agregó una alineación simple de series:

- `signal_figure` recorta tiempo, cruda, filtrada y envolvente a la longitud común mínima;
- `trend_figure` alinea sus ejes `x` e `y`;
- `spectrum_figure` alinea frecuencia y potencia.

Las series vacías o con NaN no provocan un crash por longitudes incompatibles.

#### Por qué importa

La visualización debe representar los datos disponibles sin romper toda la aplicación por una diferencia accidental de longitud. El recorte evita que Plotly reciba pares `x/y` incompatibles. No corrige la causa original; solo hace segura la presentación.

## 8. Tests agregados

Los tests usan señales sintéticas y fixtures implícitos, por lo que no dependen de archivos TDF reales.

Se cubrieron:

- `fs` inválida;
- tiempos duplicados y vacíos;
- señal plana;
- NaN parcial y total;
- interferencia de 60 Hz con razón baja y alta;
- señal corta para filtros;
- NaN en preprocesamiento;
- cortes inválidos;
- ventana RMS inválida o mayor que la señal;
- seno puro para MDF;
- MDF con segmento corto, plano o con NaN;
- iEMG proporcional a duración;
- `%MVC` sin referencia;
- activaciones con duración mínima y desplazamiento temporal;
- resumen que conserva el motivo de fallo de MDF;
- sensibilidad de ventanas;
- visualizaciones con datos vacíos y longitudes distintas.

## 9. Resultado de verificación

La batería completa ejecutada fue:

```powershell
$env:PYTHONPATH="src"
.venv\Scripts\python.exe -m pytest -q
```

Resultado verificado:

```text
46 passed
```

También se ejecutó Ruff sobre los módulos y tests modificados, sin errores.

## 10. Cómo explicarlo en una revisión QA

Una explicación breve y clara sería:

> Se reforzó el pipeline para que valide sus entradas antes de filtrar o calcular métricas. Las señales cortas, inválidas o con datos faltantes ya no se convierten silenciosamente en resultados engañosos. Se agregaron pruebas sintéticas para verificar filtros, métricas, activaciones y visualizaciones. No se tocó el lector TDF ni la data cruda, por lo que se conserva el contrato original del proyecto.

## 11. Segunda iteración de QA: exportación y trazabilidad

En una revisión más amplia del proyecto se analizaron también `data_filtration.py` y `data_compilation.py`. Se encontraron y corrigieron estos puntos.

### Rutas configurables para probar sin tocar datos reales

`process_and_save_signals` ahora acepta `raw_dir` y `processed_dir`. `process_and_export_summary` acepta `data_dir` y `output_dir`.

Esto conserva los valores por defecto usados por la aplicación, pero permite probar el pipeline con carpetas temporales. QA puede crear archivos sintéticos y comprobar las salidas sin leer ni modificar `data/raw/`.

### Trazabilidad en CSV procesados

Los CSV generados por `data_filtration.py` ahora conservan:

- `session`;
- `event`;
- las etapas de señal ya existentes.

Antes se conservaban tiempo y canal, pero se perdían sesión y evento. Eso dificultaba relacionar una muestra procesada con su origen y con la fase de la tarea.

### Validación de exportación JSON

`export_metadata_to_json` ahora rechaza:

- metadatos que no sean un diccionario;
- valores de `indent` negativos o no enteros.

También permite elegir explícitamente la carpeta de salida durante una prueba. El comportamiento por defecto continúa escribiendo en `results/`.

### Validación adicional de métricas

Se agregaron guards para:

- `nperseg` no entero o no finito;
- `window_s` cero, negativo o no finito;
- `t0` no finito;
- envolventes que no sean arreglos unidimensionales;
- duraciones y separaciones de activación no finitas.

También se validó `overlap` al inicio de `window_sensitivity`, y `channel_quality` conserva ahora el mismo conjunto de claves incluso cuando todo el canal es NaN. Esto hace más estable el consumo del resultado por el dashboard y por exportaciones automáticas.

Esto evita errores técnicos poco claros o resultados silenciosamente vacíos.

### Nuevos tests de exportación

Se creó `tests/test_exports.py` con pruebas que verifican:

- preservación de `session` y `event`;
- escritura de CSV procesado;
- comportamiento ante carpeta raw vacía;
- escritura del resumen JSON en una ruta temporal;
- validación de argumentos de exportación.

## 12. Resultado de la segunda verificación

La batería completa ahora ejecuta:

```text
51 passed
```

Además, Ruff pasa sobre `src` y `tests` sin errores, y `compileall` confirma que los módulos Python compilan correctamente.

## 13. Mejoras de calidad recomendadas a continuación

Estas ideas no forman parte de los cambios ya aplicados; son el siguiente backlog QA.

### Prioridad alta

1. Agregar tests para `data_filtration.py` y `data_compilation.py` usando DataFrames pequeños y directorios temporales. Verificar columnas exportadas, metadatos y comportamiento ante datos vacíos.
2. Crear tests de contrato para confirmar que los módulos permitidos consumen exactamente las columnas `time_s`, `emg`, `channel`, `session` y `event`.
3. Marcar cualquier prueba que use archivos TDF reales como `@pytest.mark.integration`, para que la suite unitaria siga siendo independiente de `data/raw/`.
4. Añadir una configuración de cobertura (`pytest-cov`) si el entorno del curso ya la permite; si no, usar cobertura manual sobre las ramas de error más importantes.

### Prioridad media

5. Centralizar las validaciones repetidas de señales y parámetros para evitar que distintos módulos tengan mensajes o reglas inconsistentes.
6. Añadir tests de propiedades: las etapas deben conservar longitud, `rectify` nunca debe devolver valores negativos y `remove_dc` debe dejar media cercana a cero.
7. Probar reproducibilidad: ejecutar dos veces las métricas sintéticas y verificar resultados idénticos.
8. Añadir tests de regresión para señales con amplitud muy pequeña, amplitud muy grande, una sola activación, varias activaciones separadas y activaciones unidas por `merge_gap_s`.

### Prioridad baja

9. Documentar en README la longitud mínima recomendada para el filtrado y para MDF.
10. Revisar mensajes de error y codificación de caracteres para que se muestren correctamente en español.
11. Añadir una prueba ligera de importación de `app.py` o una prueba de humo de Streamlit, sin cargar datos reales ni iniciar un servidor permanente.

## 14. Límites que deben mantenerse

- No inferir diagnóstico, lesión, fatiga confirmada ni umbrales clínicos.
- No reemplazar NaN por cero cuando eso pueda interpretarse como ausencia de actividad.
- No modificar `io.py` ni `data/raw/` como parte de esta línea de trabajo.
- No hacer que una prueba pase únicamente porque se saltó silenciosamente.
