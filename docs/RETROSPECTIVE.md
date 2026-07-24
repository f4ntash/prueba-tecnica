# Retrospectiva

Esta retrospectiva resume el cierre del proyecto desde una mirada practica: que funciono, que ajustaria si empezara de nuevo y que aprendizajes me llevo de esta implementacion.

## Que salio bien

La implementacion incremental fue una buena decision. Empezar por extraccion y clasificacion antes de parsear campos permitio construir una base clara y probar el flujo completo de a poco.

La separacion entre extraccion, clasificacion y parseo ayudo a mantener el codigo explicable. Cuando aparecio un problema, fue mas facil ubicar si pertenecia a lectura del PDF, deteccion del tipo de documento o interpretacion semantica.

Ese orden tambien evito mezclar dos problemas distintos desde el primer dia. La receta y la autorizacion comparten un modelo de salida, pero no tienen la misma forma interna. Separarlas por parser hizo que cada regla tuviera un contexto claro.

Tambien funciono bien escribir tests temprano. Los tests sinteticos permitieron cubrir casos concretos sin depender siempre de los PDFs reales, y las pruebas manuales con `1.pdf` y `2.pdf` ayudaron a detectar problemas que los textos fabricados no mostraban.

La validacion contra documentos reales fue clave. Ahi aparecieron diferencias importantes: etiquetas separadas de sus valores, tablas visuales extraidas como lineas, fechas bien extraidas pero semanticamente mal ubicadas, y problemas de salida en consola.

Me sirvio mucho alternar entre tests y ejecuciones manuales. Los tests daban confianza para no romper casos ya definidos; los PDFs reales mostraban si la solucion tenia sentido frente al documento que habia que entregar.

Documentar decisiones durante el proceso tambien sumo mucho. `docs/DECISIONS.md` y la bitacora de desarrollo permiten reconstruir por que se tomo cada camino, no solo ver el resultado final.

Otro punto positivo fue revisar la salida desde una perspectiva semantica, no solo tecnica. El caso de `Fecha de vigencia` es el mejor ejemplo: la fecha estaba bien parseada, pero significaba otra cosa.

El uso de herramientas de IA tambien ayudo. ChatGPT y Codex aceleraron la organizacion, la implementacion y la revision, pero el avance real dependio de mirar los PDFs, ejecutar el codigo, revisar resultados y corregir interpretaciones.

La documentacion de herramientas tambien me parece una parte valiosa del cierre. El uso de IA fue real y relevante, pero quedo integrado a una forma de trabajo revisada y validada, no como una delegacion ciega.

## Que haria distinto si empezara de nuevo

Inspeccionaria desde el comienzo la representacion Unicode real de los strings, ademas de mirar la salida visual de la consola. El caso `1/día` mostro que la consola puede sugerir un problema de extraccion que no esta realmente en el string.

Definiria antes una politica compartida de warnings. La regla final quedo clara: ausencia esperable no genera warning, dato presente pero invalido si, estructura importante no reconstruible tambien. Haberla definido antes hubiera evitado ajustes posteriores.

Tambien separaria desde el principio los warnings por severidad o tipo, aunque siguieran siendo strings simples. No haria un sistema complejo, pero si dejaria mas explicito si el aviso viene de validacion, estructura o texto potencialmente dañado.

Tambien registraria ejemplos de texto extraido desde la primera etapa. Tener capturas del texto interno junto a la observacion visual facilita explicar por que algunas reglas existen.

Diseñaria algunas utilidades comunes de normalizacion un poco antes, pero sin sobreabstraer. La tentacion de crear helpers generales muy temprano puede complicar un proyecto chico, aunque algunas funciones compartidas simples habrian sido utiles.

Revisaria antes la semantica de etiquetas como `Fecha de vigencia`. El error no fue tecnico, sino de interpretacion: asumir que una etiqueta significaba lo mismo en cualquier bloque del documento.

Para la autorizacion, miraria antes la pagina renderizada junto con el texto extraido. Ver tabla visual y texto interno al mismo tiempo ayuda a entender que informacion se conserva y que informacion se pierde.

## Que aprendi

El layout visual de un PDF no representa necesariamente su orden interno. En `2.pdf`, una tabla clara para una persona se convirtio en una secuencia de lineas para el extractor.

Extraer texto no equivale a interpretar significado. El proyecto obligo a separar "esta cadena existe" de "esta cadena corresponde a este campo".

Tambien aprendi que una salida aparentemente correcta puede esconder una decision dudosa. `valid_until` parecia razonable hasta que revise donde estaba ubicada la fecha.

Una solucion deterministica puede ser mejor que un LLM cuando el formato es acotado y hay etiquetas suficientes. En este caso, reglas simples fueron mas faciles de explicar, probar y corregir.

`null` y warnings son decisiones importantes. No son detalles de salida: ayudan a no inventar datos y a mostrar incertidumbre de manera honesta.

Los tests sinteticos son necesarios, pero no reemplazan la validacion con documentos reales. Los PDFs reales expusieron problemas de orden interno, codificacion, contexto y semantica.

La IA puede acelerar el proceso, pero sigue siendo necesario revisar, decidir y validar. En esta prueba, las herramientas ayudaron a avanzar con mas orden, pero la responsabilidad de aceptar o corregir cada resultado siguio siendo mia.

El cierre tambien me dejo una idea clara: una entrega tecnica no se compone solo de codigo funcionando. En un problema de extraccion e interpretacion, explicar el camino recorrido es parte de demostrar que la solucion es confiable.

Esa explicacion final tambien ayuda a mostrar los limites actuales sin que parezcan descuidos: son parte del alcance elegido.
