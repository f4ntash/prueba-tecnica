# Bitacora de desarrollo

Esta bitacora resume la evolucion del trabajo por etapas. Los nombres de commits reflejan la evolucion logica del proyecto. En el historial actual ya existen commits para las dos primeras etapas; la etapa de autorizaciones esta implementada en el arbol de trabajo, pendiente de commit.

## Etapa 1 - Extraccion y clasificacion

Commit existente:

```text
feat: add PDF extraction and document classification
```

Objetivo: construir una base antes de intentar parsear campos medicos.

Trabajo realizado:

- extraccion nativa de texto con PyMuPDF;
- clasificacion de `prescription`, `medication_authorization` y `unknown`;
- modelos Pydantic iniciales;
- CLI inicial;
- tests unitarios con PDFs temporales.

Problemas encontrados:

- el texto interno no siempre coincidia con la apariencia visual;
- el titulo de autorizacion podia quedar separado por saltos de linea y contenido intermedio;
- `main.py` capturaba excepciones demasiado generales y podia ocultar errores de programacion.

Hipotesis evaluada:

Si el PDF ya contiene texto nativo, podia resolverse una primera etapa sin OCR. Tambien parecia suficiente clasificar por senales del documento, sin parsear todavia los campos.

Decisiones tomadas:

- separar extraccion, clasificacion y parseo;
- usar clasificacion deterministica por palabras clave normalizadas;
- capturar solo errores esperados en la CLI;
- no usar OCR ni LLM en esta etapa.

Validacion:

- tests de extractor y classifier;
- ejecucion manual con `1.pdf` y `2.pdf`.

Pendiente al cierre de la etapa:

- implementar parsers concretos;
- convertir texto clasificado en `MedicalDocument`.

## Etapa 2 - Parser de recetas

Commit existente:

```text
feat: add prescription parser and technical decision log
```

Objetivo: resolver primero un solo tipo de documento y cerrar el flujo completo para recetas tradicionales.

Trabajo realizado:

- `PrescriptionParser`;
- extraccion de paciente, profesional, medicamento, fechas, diagnostico e indicaciones;
- validacion estructural minima de CUIL;
- warnings;
- serializacion JSON desde la CLI;
- tests sinteticos y prueba manual con `1.pdf`;
- documentacion de decisiones tecnicas.

Problemas reales encontrados:

- `Paciente:` y el nombre podian aparecer en lineas separadas;
- `Fecha de vigencia` estaba bien extraida, pero pertenecia a la licencia profesional, no al vencimiento de la receta;
- el CUIL presente en el PDF no tenia formato valido;
- la consola de Windows mostraba `1/d�a`, aunque al inspeccionar el string real PyMuPDF devolvia `í` correctamente.

Hipotesis evaluadas:

Primero trate `Fecha de vigencia` como vencimiento de receta, porque era una fecha parseable. Despues revise el contexto visual y textual y vi que estaba en el bloque profesional. Para `1/d�a`, la primera hipotesis fue texto corrupto en la extraccion; se comprobo inspeccionando el string y los codigos Unicode.

Decisiones tomadas:

- distinguir extraccion sintactica de interpretacion semantica;
- dejar `valid_until` en `null` para receta;
- devolver `cuil = null` con warning cuando el CUIL no tiene 11 digitos;
- configurar stdout de la CLI en UTF-8;
- usar `null` antes que inventar datos.

Validacion:

- tests sinteticos;
- ejecucion manual con `1.pdf`;
- revision manual del JSON resultante.

Pendiente al cierre de la etapa:

- parser de autorizaciones;
- soporte para mas variantes de receta y multiples medicamentos.

## Etapa 3 - Parser de autorizaciones

Commit sugerido:

```text
feat: add medication authorization parser
```

Estado: implementado en el arbol de trabajo, todavia sin commit.

Objetivo: interpretar una autorizacion de medicamentos donde la tabla visual se extrae como secuencia de lineas.

Trabajo realizado:

- `MedicationAuthorizationParser`;
- reconstruccion heuristica de filas tabulares;
- extraccion de paciente, profesional, medicamento, cobertura, cantidad, diagnostico y fechas;
- soporte para multiples filas simples;
- manejo de filas incompletas;
- validacion de porcentajes entre 0 y 100;
- tests sinteticos y prueba manual con `2.pdf`.

Problemas reales encontrados:

- las columnas visuales no se preservan en el texto interno;
- encabezados podian repetirse dentro del bloque;
- una presentacion podia ocupar mas de una linea;
- una fila incompleta no debia contaminar la siguiente;
- los campos opcionales ausentes no debian generar ruido;
- el nombre del medico terminaba con punto final evidente.

Hipotesis evaluada:

La fila podia reconstruirse usando limites y patrones: empezar despues de `CANT. AUT.`, cortar en `MEDICO SOLICITANTE`, detectar codigo de producto, porcentaje y cantidad. Esa estrategia se valido contra textos sinteticos y contra `2.pdf`.

Decisiones tomadas:

- reconstruir por patrones y limites semanticos, no por valores concretos;
- usar `MEDICO SOLICITANTE` como final del bloque de medicamentos;
- no usar `Fecha de Auditoria` como emision ni validez;
- usar `Fecha de Autorizacion` para `issued_at`;
- usar `AUTORIZACION VALIDA HASTA EL` para `valid_until`;
- limpiar solo puntuacion final evidente del profesional;
- agregar warnings solo para datos invalidos o estructuras dudosas;
- continuar despues de una fila incompleta cuando sea posible.

Validacion:

- tests unitarios;
- integracion con PDF temporal generado por PyMuPDF;
- ejecucion manual con `1.pdf` y `2.pdf`;
- verificacion de que el parser de recetas no tuvo regresiones.

Pendiente al cierre de la etapa:

- soportar tablas mas variables;
- evaluar evidencia por campo;
- OCR como fallback para documentos escaneados;
- posible fallback con IA para formatos desconocidos.

## Estado actual

- Ambos documentos de ejemplo funcionan.
- Todos los tests pasan en la ultima validacion realizada durante la implementacion.
- No se usa OCR.
- No se usa LLM en runtime.
- El parser tabular sigue siendo heuristico.
- Formatos muy distintos podrian requerir otro parser, OCR o un fallback con IA.

Nota: si antes de la entrega se cambia el historial real de Git o los nombres de commits, esta bitacora deberia ajustarse para reflejar ese historial y no inventar commits inexistentes.
