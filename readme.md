# Lector de recetas medicas digitales

Proyecto incremental en Python para leer documentos medicos digitales en PDF, extraer texto nativo, detectar el tipo de documento y estructurar recetas tradicionales y autorizaciones de medicamentos como JSON validado con Pydantic.

La idea central es separar extraccion, clasificacion e interpretacion. El problema no es solamente sacar texto de un PDF, sino convertir documentos medicos heterogeneos en una estructura comun sin inventar datos.

## Estado Actual

Implementado:

- extraccion nativa de PDF con PyMuPDF;
- clasificacion deterministica de `prescription`, `medication_authorization` y `unknown`;
- parser de receta tradicional;
- parser de autorizacion de medicamentos;
- modelos Pydantic;
- CLI con salida JSON;
- warnings para campos invalidos o inciertos;
- tests unitarios e integracion con PDF temporal.

Pendiente:

- OCR para PDFs escaneados;
- uso de LLMs para formatos desconocidos;
- multiples medicamentos por receta;
- niveles de confianza o revision humana;
- almacenamiento de evidencia por campo.

## Arquitectura

```text
src/
  main.py
  extractor.py
  classifier.py
  models.py
  parsers/
    base.py
    prescription.py
    authorization.py

tests/
  test_classifier.py
  test_extractor.py
  test_prescription_parser.py
  test_authorization_parser.py

docs/
  DECISIONS.md
  DEVELOPMENT_LOG.md
  TOOLS.md
```

## Proceso de Resolucion

La bitacora tecnica con las decisiones reales tomadas durante la implementacion esta en [docs/DECISIONS.md](docs/DECISIONS.md).

Ahi se documenta, entre otras cosas, por que `Fecha de vigencia` no se usa como vencimiento de receta, como se reconstruye la tabla de autorizacion, como se maneja el CUIL invalido y que paso con el caso visual `1/día`.

## Proceso y Herramientas

La entrega incluye documentacion del proceso porque una parte central de la resolucion fue observar, formular hipotesis, validar resultados y corregir interpretaciones, ademas de escribir el codigo.

- [Bitacora de desarrollo](docs/DEVELOPMENT_LOG.md)
- [Decisiones tecnicas](docs/DECISIONS.md)
- [Herramientas utilizadas](docs/TOOLS.md)

## Instalacion

Requisitos:

- Python 3.11 o superior
- Windows PowerShell

Crear y activar entorno virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instalar dependencias:

```powershell
pip install -r requirements.txt
```

## Uso

Ejecutar con una receta:

```powershell
python -m src.main .\1.pdf
```

Salida conceptual:

```json
{
  "document_type": "prescription",
  "patient": {
    "name": "Nombre del paciente",
    "dni": "12345678",
    "cuil": null,
    "birth_date": "1980-01-15",
    "gender": "Femenino"
  },
  "professional": {
    "name": "Nombre profesional",
    "license": "12345"
  },
  "medications": [
    {
      "name": "Medicamento",
      "active_ingredient": null,
      "dosage": "500 MG",
      "presentation": "Comprimidos x 30",
      "quantity": 1.0,
      "instructions": "Indicacion textual",
      "coverage_percentage": null
    }
  ],
  "diagnosis": "Diagnostico textual",
  "issued_at": "2026-07-14",
  "valid_until": null,
  "warnings": []
}
```

Ejecutar con una autorizacion:

```powershell
python -m src.main .\2.pdf
```

La salida usa la misma estructura `MedicalDocument`, con `document_type` igual a `medication_authorization`.

## Parser de Recetas

El parser usa etiquetas del documento y estructura cercana, no valores concretos del PDF.

Extrae:

- paciente: nombre, DNI, CUIL, sexo y fecha de nacimiento;
- profesional: nombre y matricula;
- medicamento principal: nombre, dosis, presentacion, cantidad e indicaciones;
- documento: diagnostico, fecha de emision, tipo y warnings.

Decisiones actuales:

- `Fecha de vigencia` no se mapea a `valid_until` porque en `1.pdf` pertenece al bloque profesional.
- CUIL se acepta solo si, al quitar guiones y espacios, quedan 11 digitos.
- `Marca sugerida` no se mezcla con el nombre del medicamento.
- Los campos ausentes o no confiables quedan como `null`.
- Los reemplazos de texto solo se hacen para patrones conocidos y verificables.

## Warnings

La salida no agrega warnings por cualquier `null`.

- Ausencia esperable de un campo opcional: `null` sin warning.
- Campo presente pero invalido: `null` o valor conservado con warning.
- Estructura importante que no se puede reconstruir: warning.
- Documento incompatible con el parser: excepcion y mensaje claro.

## Parser de Autorizaciones

El parser de autorizaciones trabaja sobre una tabla que PyMuPDF extrae como una secuencia de lineas. Usa encabezados como `NOMBRE COMERCIAL`, `MONODROGA`, `COBERT.` y `CANT. AUT.`, y corta el bloque al llegar a `MEDICO SOLICITANTE`.

Extrae:

- paciente desde `AFILIADO:`, usando delimitadores como `OBLIG.`, `IVA`, `PLAN:`, `EDAD:` o `EMP.:`;
- profesional desde `MEDICO SOLICITANTE:`;
- diagnostico desde `DIAGNOSTICO:`, prefiriendo la descripcion cuando hay codigo;
- fecha de autorizacion/emision como `issued_at`;
- `AUTORIZACION VALIDA HASTA EL` como `valid_until`;
- medicamento autorizado: nombre comercial, monodroga, dosis, presentacion, cobertura y cantidad.

Limitaciones del parseo tabular:

- asume que la fila de medicamento queda como secuencia: codigo, nombre comercial, monodroga, cobertura y cantidad;
- soporta el caso observado y textos sinteticos similares, incluyendo mas de una fila simple;
- no cubre tablas complejas con celdas largas partidas de forma ambigua;
- si no puede reconstruir una fila con confianza, devuelve menos datos y agrega warnings.

## Tests

```powershell
pytest
```

Los tests no dependen de los PDFs reales para cubrir la logica principal. Usan textos sinteticos y un PDF temporal generado con PyMuPDF.

## Limitaciones

- Los parsers cubren los formatos observados, no todos los formatos posibles.
- El parseo tabular de autorizaciones es heuristico.
- No usa OCR.
- No usa LLMs.
- Soporta filas simples de medicamentos; los casos tabulares complejos siguen siendo limitados.
- No hace validacion clinica ni normalizacion farmacologica.
- En produccion no deberian registrarse datos medicos sensibles en logs.

## Proximos Pasos

- Fortalecer multiples medicamentos con tablas mas variables.
- Evaluar si corresponde agregar `suggested_brand`.
- Incorporar OCR como fallback para documentos escaneados.
- Evaluar LLMs solo para formatos desconocidos, con salida validada y controles de privacidad.
