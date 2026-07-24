# Lector de recetas medicas digitales

## Objetivo

Este proyecto prepara la primera etapa de una prueba tecnica en Python para leer documentos medicos digitales en PDF, extraer su texto nativo, detectar el tipo de documento y dejar una arquitectura simple para incorporar parsers especificos mas adelante.

El problema no es solamente extraer texto de un PDF, sino convertir documentos medicos heterogeneos en una estructura comun, sin asumir que todos tienen el mismo diseno.

## Problema identificado

Los documentos medicos pueden tener formatos distintos. En los ejemplos del repositorio hay al menos dos variantes:

- una receta medica tradicional;
- una autorizacion de medicamentos con formato tabular.

Por eso la solucion separa tres responsabilidades:

- extraccion del texto del PDF;
- clasificacion del tipo de documento;
- parseo estructurado segun el formato detectado.

## Arquitectura

```text
src/
  __init__.py
  main.py
  extractor.py
  classifier.py
  models.py
  parsers/
    __init__.py
    base.py
    prescription.py
    authorization.py

tests/
  test_classifier.py
  test_extractor.py

examples/
requirements.txt
README.md
.gitignore
```

## Decisiones de diseno

La extraccion, la clasificacion y el parseo estan separados para evitar una funcion grande y dificil de mantener. Esta division permite probar cada parte de forma aislada y agregar nuevos tipos de documento sin reescribir el flujo principal.

La clasificacion inicial es deterministica y basada en palabras clave. Normaliza mayusculas, tildes y espacios repetidos para reconocer textos equivalentes sin depender del orden exacto de todas las lineas.

En esta etapa se usa extraccion nativa con PyMuPDF y no OCR. La extraccion nativa es mas rapida, barata y auditable que OCR cuando el PDF ya contiene texto. OCR deberia ser un fallback para documentos escaneados o imagenes sin capa de texto.

Todavia no se usa un LLM porque primero conviene tener un pipeline explicable, testeable y deterministico. En el futuro, un LLM podria ayudar con formatos desconocidos, pero su salida tendria que validarse con Pydantic.

Nunca deben inventarse datos faltantes. Los campos ausentes deberian representarse como `null`. En produccion tambien deberian evitarse logs con informacion medica sensible.

## Instalacion

Requisitos:

- Python 3.11 o superior
- Windows PowerShell

Crear y activar un entorno virtual en Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instalar dependencias:

```powershell
pip install -r requirements.txt
```

## Uso

Ejecutar la CLI con un PDF:

```powershell
python -m src.main .\1.pdf
```

Ejemplo de salida:

```text
Tipo detectado: prescription
```

Para una autorizacion de medicamentos:

```text
Tipo detectado: medication_authorization
```

Si el archivo no existe, no es PDF, esta corrupto o no tiene texto extraible, el programa muestra un error claro y devuelve un codigo de salida distinto de cero.

## Tests

Ejecutar:

```powershell
pytest
```

Los tests cubren:

- clasificacion de recetas con `Receta:` y `Rp/.`;
- clasificacion de autorizaciones con y sin tilde;
- tolerancia a mayusculas, minusculas y espacios repetidos;
- contenido desconocido;
- texto vacio, que se clasifica como `unknown`;
- errores de extraccion por archivo inexistente y extension invalida;
- PDF valido con texto;
- PDF valido sin texto extraible.

## Limitaciones actuales

- No extrae campos estructurados todavia.
- No interpreta tablas.
- No usa OCR para PDFs escaneados.
- No usa LLMs para formatos no conocidos.
- La clasificacion depende de palabras clave iniciales.

## Proximos pasos

- Implementar `PrescriptionParser`.
- Implementar `MedicationAuthorizationParser`.
- Mapear datos extraidos a los modelos Pydantic.
- Agregar validaciones de fechas, matriculas, documentos y cantidades.
- Incorporar OCR como fallback para documentos escaneados.
- Evaluar un LLM para formatos desconocidos, siempre validando la salida estructurada.
