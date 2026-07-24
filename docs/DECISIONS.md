# Decisiones de implementacion

Este documento resume como fui resolviendo la prueba tecnica. La idea es dejar visible el razonamiento: que observe, que supuse, como lo comprobe y que cambie.

## 1. Primer recorte del problema

Al leer el enunciado, entendi que el problema no era solo "leer PDFs". El objetivo era convertir documentos medicos con formatos distintos en una estructura comun, sin asumir que todos tienen el mismo diseno.

Por eso arranque por un pipeline chico:

1. extraer texto nativo del PDF;
2. clasificar el tipo de documento;
3. aplicar un parser especifico solo cuando el tipo esta identificado;
4. devolver modelos Pydantic con campos ausentes como `null`.

Ese recorte tambien hacia la solucion mas facil de explicar en entrevista: cada parte tiene una responsabilidad concreta.

## 2. Lo que mostraron los dos PDFs

Al inspeccionar `1.pdf`, vi una receta tradicional. El texto interno traia etiquetas utiles: `Paciente:`, `CUIL:`, `DNI:`, `Sexo:`, `F.Nacimiento:`, `Rp/.`, `Diagnostico:`, `Indicaciones:` y `Emitida:`.

Al inspeccionar `2.pdf`, vi una autorizacion de medicamentos con estructura tabular. Un detalle importante fue que el titulo visual no salia como una frase continua: PyMuPDF extraia `AUTORIZACION DE` y mas adelante `MEDICAMENTOS`. Eso obligo a que la clasificacion tolerara texto intercalado, sin hardcodear valores del ejemplo.

## 3. Pipeline implementado

Separe el codigo en:

- `extractor.py`: valida el archivo, abre el PDF con PyMuPDF y extrae texto.
- `classifier.py`: clasifica con reglas deterministicas y normalizacion de texto.
- `parsers/`: contiene parsers por tipo de documento.
- `models.py`: define la estructura comun con Pydantic.
- `main.py`: conecta todo y muestra JSON o errores claros.

Elegir extraccion nativa antes que OCR fue una decision practica: los PDFs ya tenian texto. OCR queda como fallback para documentos escaneados, no como primer paso.

Tambien evite usar un LLM al principio. Para estos documentos habia etiquetas claras y reglas simples suficientes. Usar un LLM en esta etapa hubiera agregado variabilidad y preguntas de privacidad sin resolver un problema real todavia.

## 4. Implementacion incremental de receta

Implemente primero solo `PrescriptionParser`. La autorizacion quedo pendiente porque `2.pdf` es tabular y requiere otro tipo de reglas.

El parser de receta usa etiquetas y estructura, no numeros de linea ni valores concretos. Por ejemplo:

- si `Paciente:` no tiene valor en la misma linea, toma la siguiente linea util;
- debajo de `Rp/.` busca el bloque de medicamento;
- ignora `Marca sugerida:` para no confundir marca comercial con medicamento principal;
- convierte fechas `DD/MM/YYYY` a `date`;
- valida cantidades cuando aparecen despues de `Envases`.

Los tests principales usan textos sinteticos con nombres, medicamentos y fechas distintos a los PDFs reales. El PDF real se usa como prueba manual, no como base de todos los tests.

## 5. Diferencias entre lo visual y el texto extraido

`1.pdf` dejo claras varias diferencias:

- `Paciente:` aparece separado del nombre.
- El medicamento aparece como varias lineas: `Envases`, cantidad, nombre, dosis/presentacion y marca sugerida.
- Algunas lineas administrativas o de firma aparecen al final del texto extraido, aunque visualmente esten en otra zona.
- `Fecha de vigencia` aparece cerca de datos del profesional, no como vencimiento de receta.

Esta fue una de las lecciones principales: extraer bien una cadena no significa haberla interpretado bien.

## 6. Error semantico: `Fecha de vigencia`

En una primera version, `Fecha de vigencia:` se mapeo a `MedicalDocument.valid_until`. La extraccion era correcta: la fecha estaba en el texto y podia parsearse.

Al revisar el contexto, vi que esa fecha estaba inmediatamente despues de datos como `Licencia Sanitaria Federal`. Eso la ubica en el bloque profesional. Entonces no correspondia usarla como vencimiento de la receta.

La correccion fue dejar `valid_until` en `null` para esta etapa y agregar un test que asegure que una fecha de vigencia profesional no se interpreta como vencimiento del documento.

## 7. CUIL presente pero invalido

En `1.pdf`, `CUIL:` se extrae como `0`. No es un campo ausente: esta presente, pero no tiene formato valido.

Implemente una validacion minima y explicable:

- quitar guiones y espacios;
- aceptar solamente 11 digitos;
- no implementar todavia el algoritmo de digito verificador.

Si el valor no cumple esa estructura, el parser devuelve `cuil = null` y agrega un warning. Asi la salida distingue entre ausencia e invalidez.

## 8. Diagnostico de `1/d�a`

En la prueba manual, la consola mostro `Indicaciones` como `1/d�a`. Mi primera hipotesis fue que PyMuPDF habia extraido texto corrupto.

Para comprobarlo inspeccione el string real y sus codigos Unicode. Ahi aparecio que PyMuPDF devolvia la `í` correctamente; el problema estaba en como Windows estaba mostrando stdout. La correccion real para `1.pdf` fue configurar la salida de la CLI en UTF-8.

Tambien deje una normalizacion conservadora para campos ya extraidos, pero no fue esa normalizacion la que corrigio el caso real de `1.pdf`. Esa funcion existe para reemplazos conocidos y verificables, por ejemplo `d�a` hacia `día`. Si aparece un patron desconocido con `�`, se conserva el texto y se agrega un warning.

## 9. `null` y warnings

Uso `null` cuando un dato no aparece o no se puede afirmar con confianza. Ejemplos actuales:

- `valid_until` queda `null` porque no hay vencimiento de receta identificado.
- `cuil` queda `null` si el valor presente no tiene 11 digitos.
- `active_ingredient` y `coverage_percentage` quedan `null` porque la receta no trae etiquetas claras para esos campos.

Los warnings comunican incertidumbre sin romper todo el parseo. Hoy se usan para campos importantes faltantes, fechas invalidas, CUIL invalido y texto danado no corregible.

La regla que quedo en el proyecto es esta:

- ausencia esperable de un campo opcional: `null` sin warning;
- campo presente pero invalido: `null` o valor conservado con warning;
- estructura importante que no puede reconstruirse: warning;
- documento incompatible con el parser: excepcion.

## 10. Implementacion de autorizaciones

Despues de dejar estable la receta, implemente `MedicationAuthorizationParser` usando `2.pdf` como validacion manual.

Primero inspeccione el texto interno y despues renderice el PDF para mirar la tabla visual. Visualmente hay una fila con columnas: codigo, nombre comercial, monodroga, cobertura y cantidad autorizada. En el texto interno, PyMuPDF lo entrega como lineas consecutivas:

- encabezados separados: `CODIGO`, `NOMBRE COMERCIAL`, `MONODROGA`, `COBERT.`, `CANT. AUT.`;
- luego una secuencia de valores: codigo, nombre comercial con dosis/presentacion, monodroga, porcentaje y cantidad;
- despues aparecen `MEDICO SOLICITANTE` y `DIAGNOSTICO`.

La hipotesis fue reconstruir la fila con esos limites: empezar despues de `CANT. AUT.`, cortar en `MEDICO SOLICITANTE`, detectar el codigo con un patron tipo `numero - numero`, detectar cobertura por `%` y cantidad como numero.

Al probar con `2.pdf`, esa estrategia alcanzo para extraer el medicamento sin hardcodear valores. Tambien confirme dos decisiones semanticas:

- `Fecha de Autorizacion` es la mejor candidata para `issued_at`;
- `Fecha de Auditoria` existe, pero no representa emision ni validez;
- `AUTORIZACION VALIDA HASTA EL` corresponde a `valid_until`.

Para el paciente, la linea `AFILIADO:` mezcla numero de afiliado, nombre y condicion impositiva. Por eso el parser corta el nombre usando delimitadores como `OBLIG.`, `IVA`, `PLAN:`, `EDAD:` o `EMP.:`. Si no aparece un delimitador claro, devuelve `null` y warning.

`DNI Afiliado` aparece vacio en `2.pdf`; queda `null` sin inventar un DNI.

Antes de cerrar esta etapa, revise algunos bordes del parser:

- el nombre del profesional salia como `MEDICO MEDICO.` y se normalizo quitando solo puntuacion final evidente, sin tocar puntos internos como iniciales;
- los encabezados repetidos dentro de la tabla se ignoran;
- una fila incompleta agrega warning y no impide parsear la siguiente;
- la cobertura se valida entre 0 y 100;
- la cantidad se toma solo despues de la cobertura, para no confundirla con codigo de producto ni porcentaje.

## 11. Estado actual

Implementado:

- extraccion nativa con PyMuPDF;
- clasificacion deterministica;
- parser de receta tradicional;
- parser de autorizacion de medicamentos;
- modelos Pydantic;
- CLI con JSON;
- warnings;
- tests unitarios e integracion con PDF temporal.

Todavia no implementado:

- OCR;
- LLM;
- niveles de confianza;
- revision humana;
- almacenamiento de evidencia por campo.

## 12. Riesgos y siguientes pasos

La solucion actual funciona para los dos formatos observados, pero todavia es limitada:

- soporta filas simples de medicamentos, incluso mas de una;
- reconstruye la tabla de autorizacion con heuristicas simples;
- depende de etiquetas conocidas;
- no normaliza medicamentos contra un catalogo;
- no debe registrar datos medicos sensibles en produccion.

El siguiente paso natural seria soportar multiples medicamentos y mas variantes de tabla. Despues, OCR podria entrar solo como fallback cuando la extraccion nativa no devuelva texto suficiente.

## 13. Relacion con sistemas de IA

Esta prueba toca problemas que tambien aparecen al construir sistemas con IA: no inventar campos ausentes, validar salidas estructuradas, separar extraccion de interpretacion y hacer visible la incertidumbre.

Si en el futuro se incorpora un LLM para formatos desconocidos, no deberia ser la primera opcion si reglas simples alcanzan. Tendria que devolver una estructura definida, validarse con Pydantic, conservar evidencia del texto fuente y marcar campos de baja confianza para revision. Ademas, no se deberian enviar datos medicos sensibles a proveedores externos sin controles de privacidad adecuados.
