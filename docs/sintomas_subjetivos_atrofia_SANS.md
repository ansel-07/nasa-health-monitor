# Síntomas subjetivos: atrofia muscular y SANS

Guía de autoinforme para la app del hackatón. Versión: 14/11/2026.

## Alcance

Estas preguntas recogen **lo que siente o percibe el astronauta**, algo que no puede deducirse directamente de un reloj, un pulsómetro u otro sensor convencional. Algunas manifestaciones pueden contrastarse con pruebas clínicas, pero la experiencia subjetiva se obtiene preguntando al astronauta.

**No confundir síntoma con medición:** «siento menos fuerza» no equivale a una pérdida medida con dinamómetro; «veo borroso» no equivale a una refracción o agudeza visual concreta. Los síntomas no confirman por sí solos ninguna de estas enfermedades.

Las preguntas, identificadores y reglas de triaje siguientes son **propuestas de implementación**, no un cuestionario validado ni un protocolo oficial de NASA.

## 1. Atrofia muscular / descondicionamiento muscular

Comparar siempre con una actividad familiar y semejante. La fuerza y resistencia pueden medirse, pero estas preguntas evalúan su **percepción**, no su valor físico. NASA describe deterioro del tamaño, fuerza y resistencia muscular y sus consecuencias funcionales. [1]

| ID | Sensación subjetiva | Pregunta para el astronauta | Interpretación en la app |
|---|---|---|---|
| `MUS_01` | Debilidad percibida | ¿Sientes que tus músculos responden con menos fuerza de lo habitual al realizar la misma tarea? | Vigilancia si es gradual, leve y no hay señales de alarma. No convertir la respuesta en newtons. |
| `MUS_02` | Fatiga muscular precoz | ¿Sientes que tus músculos se agotan antes de lo habitual con una actividad comparable? | Vigilar persistencia y relación con ejercicio, descanso e ingesta. |
| `MUS_03` | Mayor esfuerzo percibido | ¿La misma tarea te exige más esfuerzo muscular que antes, aunque puedas completarla? | Registrar el cambio percibido; no confundir con frecuencia cardiaca o potencia. |
| `MUS_04` | Pesadez muscular | ¿Notas las piernas, los brazos o la espalda inusualmente pesados o difíciles de mover? | Sensación inespecífica; interpretar según gravedad efectiva, traje y actividad. |
| `MUS_05` | Recuperación insuficiente percibida | ¿Sientes que tus músculos siguen agotados después del descanso que normalmente te permite recuperarte? | Vigilar repetición y repercusión funcional; no diagnostica pérdida de masa. |
| `MUS_06` | Tirantez, molestias o dolor muscular | ¿Notas tirantez, molestias o dolor muscular distintos de lo habitual? | Registrar localización y contexto. **No es un signo específico de atrofia**; puede requerir estudiar sobrecarga o lesión. |

No presentar estas sensaciones como exclusivas de atrofia: también pueden relacionarse con fatiga general, sueño insuficiente, alimentación, adaptación gravitatoria u otra enfermedad. Un síntoma aislado requiere contexto.

## 2. SANS: cambios visuales percibidos

NASA utiliza cuestionarios de percepción visual además de pruebas instrumentales. Incluyen cambios de visión de cerca y lejos, fluctuaciones, distorsión y otras experiencias visuales. [2,3]

| ID | Percepción subjetiva | Pregunta para el astronauta | Interpretación en la app |
|---|---|---|---|
| `VIS_01` | Visión borrosa de cerca | ¿Percibes las letras o detalles cercanos menos nítidos que antes, usando tu corrección habitual? | Vigilancia si el cambio es leve y gradual; registrar gafas utilizadas. |
| `VIS_02` | Visión borrosa a media o larga distancia | ¿Notas menos claridad al mirar pantallas, instrumentos u objetos a media o larga distancia? | Registrar distancia y condiciones. No es específico de SANS. |
| `VIS_03` | Fluctuación de la nitidez | ¿Sientes que la nitidez de tu visión cambia durante el día o entre tareas similares? | Registrar cuándo ocurre y si persiste; no atribuir automáticamente a SANS. |
| `VIS_04` | Cambio de comodidad con las gafas | ¿Sientes que tus gafas habituales ya no te permiten leer o trabajar con la misma comodidad? | Registrar la percepción y la corrección usada; no inferir dioptrías. |
| `VIS_05` | Dificultad percibida en luz tenue | ¿Percibes más dificultad de lo habitual para distinguir detalles con poca iluminación? | Comparar condiciones semejantes; requiere contexto y valoración si persiste. |
| `VIS_06` | Alteración de profundidad percibida | ¿Sientes que te cuesta más juzgar distancias o la posición de los objetos? | Valorar seguridad de la tarea y adaptación sensorial; no es específico de SANS. |

**SANS puede presentar hallazgos estructurales sin molestias perceptibles.** Responder «no» a todas las preguntas no sustituye OCT, evaluación ocular ni controles programados. Los criterios publicados incluyen cambios anatómicos y funcionales. [4]

## 3. Señales de alarma comunicadas por el astronauta

Son experiencias que pueden comenzar como un autoinforme. **Su presencia activa atención médica inmediata en la propuesta de la app**, sin esperar una medición o repetir el cuestionario. No son diagnósticos de atrofia o SANS.

| ID | Pregunta de alarma | Acción propuesta |
|---|---|---|
| `ALM_01` | ¿Has notado una pérdida súbita de visión o una zona nueva oscura, vacía o ausente en lo que ves? | Detener la tarea de riesgo y avisar inmediatamente al responsable médico. Un defecto de campo nuevo requiere evaluación. [4] |
| `ALM_02` | ¿Ves de forma nueva las líneas torcidas, letras deformadas o una distorsión en el centro de la visión? | Atención inmediata; la distorsión central figura entre los impactos funcionales de SANS. [4] |
| `ALM_03` | ¿Notas una debilidad que ha aparecido de golpe o que te impide moverte con seguridad? | Atención inmediata y asistencia; buscar una causa aguda, sin atribuirla a atrofia crónica. |
| `ALM_04` | ¿Tienes dolor intenso nuevo acompañado de cambios visuales, debilidad marcada o dificultad para realizar una tarea básica? | Atención inmediata para determinar la causa; no tratarlo como una molestia rutinaria. |

Una nueva visión doble o una cefalea intensa con síntomas neurológicos también requiere valoración urgente. No etiquetar estas manifestaciones automáticamente como SANS.

## 4. Cómo recoger las respuestas

Para cada síntoma:

- `present`: `yes`, `no` o `unknown`. **Una respuesta ausente no equivale a «no».**
- `symptom_id`: identificador de las tablas.
- `onset`: momento de inicio y si fue súbito o gradual.
- `trend`: mejora, estable o empeora.
- `location`: músculo/lado; para visión, ojo derecho, izquierdo, ambos o no identificado. No pedir pruebas que retrasen una urgencia.
- `impact`: `none`, `no_task_change`, `task_adapted` o `task_not_completed`.
- `intensity`: opcional, de 0 a 10, como valoración personal; **no es una medición fisiológica ni un umbral de urgencia validado**.
- `context`: ejercicio, descanso, traje, gafas, iluminación, fase de misión y gravedad efectiva.
- `notes`: descripción libre en palabras del astronauta.

La valoración funcional se inspira en las categorías del cuestionario visual NASA: cambio sin repercusión en actividades, necesidad de adaptación o interferencia importante. Su extensión a síntomas musculares es una propuesta del proyecto. [2]

### Reglas mínimas de triaje propuestas

1. **Una señal de alarma prevalece sobre cualquier respuesta leve:** mostrar `medical_urgency` y activar el circuito médico.
2. Sin alarmas, uno o más síntomas leves → `surveillance`: registrar, comunicar y seguir evolución.
3. Una tarea crítica no completada exige valoración inmediata de seguridad, aunque la intensidad declarada sea baja.
4. No sumar síntomas para diagnosticar ni transformar puntuaciones subjetivas en z-scores de fuerza, OCT o refracción.
5. No cerrar una urgencia automáticamente porque desaparezca una respuesta o el sensor vuelva al rango.

## Fuentes

1. [NASA — Risk of Reduced Physical Performance Capabilities Due to Reduced Muscle Size, Strength, and Endurance](https://www.nasa.gov/directorates/esdmd/hhp/muscle-risk/). Fundamenta las dimensiones musculares; no valida las preguntas propuestas.
2. [NASA — Evidence Report: Risk of Spaceflight Associated Neuro-ocular Syndrome](https://humanresearchroadmap.nasa.gov/Evidence/reports/SANS.pdf). Apartado del cuestionario visual en vuelo: percepciones y repercusión funcional; referencia histórica.
3. [NASA NTRS — Development of an In Flight Vision Self-Assessment Questionnaire for Long Duration Space Missions](https://ntrs.nasa.gov/citations/20100039152). Uso de autoinforme visual como complemento de las pruebas.
4. [NASA NTRS — SANS: 2023 Clinical Update](https://ntrs.nasa.gov/citations/20220014606). Hallazgos anatómicos y efectos funcionales, incluidos pérdida de campo y distorsión central.

Fuentes consultadas el 14/11/2026. La redacción de preguntas y el triaje son elaboración para el prototipo; necesitan revisión clínica antes de uso real.
