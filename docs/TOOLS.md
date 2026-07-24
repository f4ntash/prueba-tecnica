# Herramientas utilizadas

Este proyecto se desarrollo con apoyo de herramientas de IA y herramientas tradicionales de desarrollo. No intento ocultarlo: fueron parte importante del proceso. Al mismo tiempo, las decisiones finales, la revision de resultados y la responsabilidad sobre la entrega son mias.

## ChatGPT 5.5

ChatGPT fue mi principal apoyo durante la prueba, tanto en la parte tecnica como en la organizacion del proceso.

Lo use para:

- discutir arquitectura;
- ordenar ideas antes de implementar;
- revisar decisiones;
- detectar riesgos;
- comparar alternativas;
- preparar prompts para Codex;
- documentar el proceso;
- mantener una forma de trabajo incremental.

Tambien fue un apoyo para bajar ansiedad y concentrarme en resolver cada etapa de manera ordenada. No lo use como reemplazo de revision: las salidas se contrastaron con tests, con los PDFs reales y con inspeccion manual.

## Codex

Codex se uso para implementar cambios definidos por etapas, ejecutar comandos, generar y ampliar tests, revisar archivos, hacer refactorizaciones acotadas y documentar cambios.

La forma de trabajo no fue delegar una solucion completa sin revision. Trabaje con prompts concretos por etapa: primero base de extraccion y clasificacion, despues receta, despues autorizaciones, y luego revisiones semanticas. Cada resultado se reviso con tests y con ejecuciones manuales sobre los PDFs reales.

Las correcciones mas importantes no salieron de aceptar codigo sin mirar. Por ejemplo, `Fecha de vigencia`, el CUIL invalido, el caso `1/día` y la reconstruccion tabular se corrigieron despues de observar la salida y revisar si la interpretacion era correcta.

## Visual Studio Code

Use Visual Studio Code para revisar codigo, navegar el proyecto, trabajar con la terminal, inspeccionar cambios y revisar diffs.

## Python

Python es el lenguaje principal del proyecto. Se uso para la CLI, parsers, modelos y tests.

## PyMuPDF

PyMuPDF se uso para extraer texto nativo de PDFs. Tambien se uso en tests para generar PDFs temporales y validar el flujo sin depender siempre de los documentos reales.

## Pydantic

Pydantic se uso para definir una estructura comun de salida y serializar datos como JSON. Tambien ayuda a que los campos ausentes queden representados de forma explicita como `null`.

## pytest

pytest se uso para tests unitarios y pruebas de integracion pequeñas con PDFs temporales.

## Git y GitHub

Git y GitHub se usan para control de versiones, fork, commits y entrega del proyecto.

## Google y documentacion web

Use documentacion web de forma puntual cuando hizo falta verificar comportamientos o recordar detalles. La prioridad fue consultar documentacion oficial o fuentes tecnicas directas cuando correspondia, por ejemplo para Python, PyMuPDF, Unicode/salida de consola y Git.

No todo el avance dependio de busquedas externas: buena parte del trabajo salio de inspeccionar los PDFs reales, ejecutar el codigo y revisar los resultados.

## Forma de trabajo

El flujo que segui fue:

1. Leer el enunciado y observar los documentos.
2. Formular una hipotesis.
3. Diseñar una etapa pequeña.
4. Usar ChatGPT para discutirla.
5. Pedir a Codex una implementacion acotada.
6. Ejecutar tests.
7. Probar con PDFs reales.
8. Revisar errores tecnicos y semanticos.
9. Documentar decisiones.
10. Repetir.

## Responsabilidad sobre el resultado

Las herramientas de IA ayudaron a acelerar, revisar y ordenar el trabajo. Yo decidi que implementar, revise los cambios, valide los resultados, acepte o descarte propuestas y corregi interpretaciones cuando no eran adecuadas.

La entrega final es responsabilidad mia.
