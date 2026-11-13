# Estructura del proyecto · NASA Space Apps 2026

Basada en el esquema de la pizarra (Juan Carlos) y en las decisiones del viernes 13 por la tarde. Documento interno del equipo, en español: **traducir o borrar antes de entregar**, porque el repo será público y todo lo que vea el jurado va en inglés. La referencia técnica vigente es el `AGENTS.md`; si algo no coincide, manda el `AGENTS.md`.

Equipo: Gonzalo (producto y pruebas), Edu (ciencia y salud), Ansel (arquitectura, integración y mascota), Fran (datos y gráficas), Juan Carlos (detectar), Javi (actuar).

Las marcas **⚠️ FALTA DETALLE · Persona** señalan huecos que no se han dejado en blanco por descuido: los tiene que cerrar esa persona. La lista completa está en la sección 8.

---

## 1. Decisiones tomadas

| Tema | Decisión |
|---|---|
| Stack | Python 3.12 + Streamlit + pandas + Plotly. Sin otras librerías. |
| Astronautas | Varios. Cada uno tiene su línea base pre-espacio. Se elige quién eres al entrar. |
| Medidas | Mixto: misión simulada con un reloj que avanza + entrada manual + medidas que piden los pasos de un protocolo. |
| Confirmar | Cuando salta un trigger, se pide **repetir la medida**. Solo si la repetición también salta se abre el problema. |
| Gravedad | El **trigger fija la gravedad inicial**; los **pasos del protocolo pueden subirla o bajarla**. |
| Entorno | **Ajusta los umbrales del trigger** y **elige ramas del protocolo** (incluido el retraso de comunicación). |
| Problemas simultáneos | **Uno activo a la vez** por astronauta. Los demás quedan como pendientes. |
| Alcance P0 | **2 problemas** con protocolo completo. |
| Mascota | Una cara animada (inspirada en un llavero con pantalla OLED) **narra** las pantallas del astronauta: bocadillo de texto, expresiones y voz del navegador en inglés. **Habla, no escucha**: se responde con teclado y botones. Dibujada en código (SVG/CSS). La programa Ansel. |
| Dónde sale la mascota | Grande en Inicio, Check-in y Protocolo. Pequeña en una columna junto a la gráfica cuando esas pantallas enseñan una. No sale en el histórico (Trends). |
| Idioma | Todo en inglés, también la voz. |

---

## 2. El modelo en una página

```
 Medidas ──► Datos ──► Trigger ──► Confirmar ──► Episodio ──► Protocolo ──► Fin
 (sim, manual,  (pre-espacio   (z respecto a   (repetir la    (problema +    (pasos: acción,
  protocolo)     = línea base;  la línea base   medida; si no  gravedad +     medida, decisión,
                 misión)        + límites       se repite,     entorno)       cambiar gravedad,
                                absolutos,      falsa alarma)                 contactar Tierra)
                                según entorno)
                       ▲                                              │
                       └────────── las medidas del protocolo ◄────────┘
                                   también se guardan como datos
```

Conceptos:

- **Indicador**: una magnitud medible (pulso, tensión sistólica, tensión diastólica, glucosa, temperatura, horas de sueño, ánimo). La tensión se guarda como **dos indicadores** (`bp_systolic`, `bp_diastolic`) para que todo sea «un valor por fila».
- **Medida**: un valor de un indicador para un astronauta en un instante. Fase `preflight` (pre-espacio) o `mission`.
- **Línea base**: media y desviación típica de las medidas `preflight` de ese astronauta para ese indicador.
- **Entorno**: dónde está la misión (p. ej. ISS, Luna, Marte). Tiene gravedad y retraso de comunicación, y puede cambiar umbrales.
- **Problema**: uno de una **lista cerrada** definida en configuración, con sus reglas de trigger y su protocolo.
- **Gravedad**: nivel ordenado. Provisional: `inactive < mild < moderate < severe`. ⚠️ FALTA DETALLE · Edu: lista definitiva y qué significa cada nivel.
- **Episodio**: una instancia de un problema en un astronauta: cuándo saltó, con qué gravedad, en qué paso del protocolo va y cómo terminó. Es lo que conecta todo.
- **Protocolo**: el diagrama de flujo de un problema. **Un archivo por problema**; la gravedad y el entorno no generan protocolos distintos, sino **ramas** dentro del mismo diagrama.

---

## 3. Ciclo de vida de un episodio

```
             trigger salta
 (ninguno) ───────────────► pending_confirmation
                                  │
              repetición también  │  repetición ya no
              salta               │  salta
                    ┌─────────────┴──────────────┐
                    ▼                            ▼
                 active                      dismissed
                    │                    (falsa alarma, queda
                    │ pasos del           en el historial)
                    │ protocolo
                    ▼
     resolved  /  monitoring  /  handed_over
     (se acabó)  (vigilar, sin   (en manos del médico
                  más pasos)       de a bordo o de Tierra)
```

Reglas:

1. **Uno activo a la vez.** Si salta otro trigger mientras hay un episodio `pending_confirmation` o `active`, se guarda en la lista de **pendientes** y se muestra un aviso. Al cerrar el episodio actual, se ofrece el pendiente de mayor gravedad (que vuelve a pasar por confirmar).
   ⚠️ FALTA DETALLE · Gonzalo: qué ve el astronauta si el pendiente es más grave que el activo (¿botón para cambiar de problema?). Para el P0 basta el aviso.
2. **Confirmar** pide repetir **el mismo indicador** que disparó. Cada problema tiene un `confirm_wait_min` (espera antes de repetir; la AHA, por ejemplo, pide repetir la tensión a los 5 min). En la demo hay un botón «Simular espera».
   La gravedad inicial del episodio es la que da la **medida de confirmación**, no la primera.
   ⚠️ FALTA DETALLE · Edu: `confirm_wait_min` de cada problema.
3. El **historial simulado no abre episodios**. Los triggers solo se evalúan sobre medidas **nuevas**: las que entran a mano y las que aparecen al avanzar el reloj de misión.

---

## 4. Formatos de datos y configuración

Todo lo que vea el jurado y todo el código, en inglés. Los valores `TODO_EDU` son marcadores: **ningún número médico sale de la IA**.

### 4.1 Medidas · `data/measurements.csv` (dueño: Fran)

```
timestamp,astronaut,indicator,value,unit,phase,source
2027-03-01T08:00:00,a1,heart_rate,62,bpm,preflight,simulated
2027-04-10T08:00:00,a1,bp_systolic,128,mmHg,mission,manual
2027-04-10T08:07:00,a1,bp_systolic,131,mmHg,mission,protocol
```

- `phase`: `preflight` | `mission`.
- `source`: `simulated` | `manual` | `protocol`.
- Amplía el contrato de la guía (`timestamp, astronaut, indicator, value, unit`) con `phase` y `source`.

### 4.2 Astronautas y misión (dueño: Fran; valores de entorno: Edu)

`data/astronauts.csv`
```
id,name,role
a1,Alex Doe,Commander
```

`config/mission.json`
```json
{
  "name": "TODO",
  "start": "2027-04-01T00:00:00",
  "environment": "mars",
  "astronauts": ["a1", "a2", "a3"]
}
```

### 4.3 Indicadores · `config/indicators.json` (dueños: Edu contenido, Gonzalo textos)

```json
{
  "heart_rate": {
    "name": "Resting heart rate",
    "unit": "bpm",
    "how_to_measure": "TODO_GONZALO",
    "why_it_matters": "TODO_EDU",
    "source": "TODO_EDU"
  }
}
```

### 4.4 Entornos · `config/environments.json` (dueño: Edu)

```json
{
  "iss":  { "name": "International Space Station", "gravity_g": "TODO_EDU", "comm_delay_min": "TODO_EDU", "source": "TODO_EDU" },
  "moon": { "name": "Lunar base",                  "gravity_g": "TODO_EDU", "comm_delay_min": "TODO_EDU", "source": "TODO_EDU" },
  "mars": { "name": "Mars base",                   "gravity_g": "TODO_EDU", "comm_delay_min": "TODO_EDU", "source": "TODO_EDU" }
}
```

`comm_delay_min` es el retraso **en un sentido**. La guía da hasta 20 min para Marte.
⚠️ FALTA DETALLE · Edu: lista de entornos y valores con fuente.

### 4.5 Problemas y triggers · `config/problems.json` (dueño: Edu)

```json
{
  "problem_id_1": {
    "name": "TODO",
    "description": "TODO_EDU",
    "hrp_risk": "TODO_EDU (riesgo del Human Research Program al que corresponde)",
    "confirm_wait_min": "TODO_EDU",
    "protocol": "protocols/problem_id_1.json",
    "triggers": [
      { "severity": "mild",     "when": { "indicator": "heart_rate", "z_above": "TODO_EDU" } },
      { "severity": "moderate", "when": { "indicator": "heart_rate", "above": "TODO_EDU" } },
      { "severity": "moderate", "when": { "indicator": "heart_rate", "above": "TODO_EDU" }, "environments": ["mars"] }
    ],
    "source": "TODO_EDU"
  }
}
```

Reglas de evaluación:

- Un trigger puede llevar `environments`: solo vale en esos entornos. Sin ese campo, vale en todos. **Así es como el entorno ajusta los umbrales.**
- Si encajan varios triggers del mismo problema, gana **la gravedad más alta**.
- Si `when` necesita varios indicadores a la vez, se escribe `{ "all": [cond, cond] }` o `{ "any": [cond, cond] }`.

### 4.6 Lenguaje de condiciones (común a triggers y protocolos)

Un solo evaluador (`core/conditions.py`) entiende estas claves, que se pueden combinar con `all` y `any`:

| Clave | Significado |
|---|---|
| `indicator` + `above` / `below` | Valor absoluto de la última medida de ese indicador. |
| `indicator` + `z_above` / `z_below` | z-score respecto a la línea base del astronauta. |
| `var` + `above` / `below` / `z_above` / `z_below` | Igual, pero sobre un valor guardado en un paso `measure` del protocolo. |
| `severity_at_least` / `severity_is` | Gravedad actual del episodio. |
| `environment_in` | Lista de entornos. |
| `answer` + `equals` | Respuesta a un paso `question`. |

### 4.7 Protocolos · `config/protocols/<problem_id>.json` (dueño: Edu contenido; formato: Ansel)

Un grafo de nodos con un nodo de inicio. Tipos de nodo:

| Tipo | Qué hace en pantalla | Campos |
|---|---|---|
| `info` | Muestra una explicación. | `text`, `next` |
| `action` | Pide al astronauta que haga algo (p. ej. hidratarse). Botones «Done» / «I can't». | `text`, `wait_min?`, `next`, `next_if_cannot?`, `source` |
| `measure` | Pide una medida. Se guarda en `measurements.csv` con `source=protocol` y en una variable. | `indicator`, `save_as`, `text?`, `next` |
| `question` | Pregunta cerrada (síntomas, sí/no). | `text`, `save_as`, `options: {valor: next}` |
| `decision` | Ramifica sin preguntar nada, según condiciones. | `branches: [{if, next}]`, `default` |
| `set_severity` | Sube o baja la gravedad del episodio. | `severity`, `next` |
| `contact` | Avisa al médico de a bordo o a los médicos de vuelo en Tierra; muestra cuándo llegaría la respuesta según el retraso del entorno. | `target: crew_medical_officer \| flight_surgeon`, `text`, `next` |
| `end` | Cierra el episodio. | `outcome: resolved \| monitoring \| handed_over`, `text` |

Ejemplo de **forma** (el contenido es de relleno):

```json
{
  "problem": "problem_id_1",
  "start": "route",
  "nodes": {
    "route": { "type": "decision",
               "branches": [ { "if": { "severity_at_least": "severe" }, "next": "contact_ground" } ],
               "default": "explain" },
    "explain":   { "type": "info",    "text": "TODO_EDU", "next": "do_action" },
    "do_action": { "type": "action",  "text": "TODO_EDU", "wait_min": "TODO_EDU",
                   "source": "TODO_EDU", "next": "remeasure", "next_if_cannot": "contact_ground" },
    "remeasure": { "type": "measure", "indicator": "heart_rate", "save_as": "hr_after", "next": "check" },
    "check":     { "type": "decision",
                   "branches": [ { "if": { "var": "hr_after", "z_above": "TODO_EDU" }, "next": "escalate" } ],
                   "default": "done" },
    "escalate":  { "type": "set_severity", "severity": "severe", "next": "contact_ground" },
    "contact_ground": { "type": "contact", "target": "flight_surgeon", "text": "TODO_EDU", "next": "wait_and_monitor" },
    "wait_and_monitor": { "type": "end", "outcome": "handed_over", "text": "TODO_EDU" },
    "done":      { "type": "end", "outcome": "resolved", "text": "TODO_EDU" }
  }
}
```

Reglas para Edu al escribir protocolos:
- Todo nodo con contenido de salud lleva `source`.
- El **retraso de comunicación** se usa en ramas `environment_in`: en Marte, antes de `contact` conviene que haya pasos autónomos («el amarillo debe dar instrucciones claras», como dice la guía).
- El protocolo **orienta, no diagnostica**.

⚠️ FALTA DETALLE · Edu (con Gonzalo para la redacción): contenido completo de los 2 protocolos, primero en una tabla o un dibujo, después en JSON.

### 4.8 Episodios · `data/episodes.json` (dueño de lectura y escritura: Fran)

```json
{
  "id": "ep-0001",
  "astronaut": "a1",
  "problem": "problem_id_1",
  "environment": "mars",
  "status": "active",
  "severity_initial": "moderate",
  "severity": "severe",
  "trigger": { "indicator": "heart_rate", "value": 112, "z": 3.4, "measured_at": "2027-04-10T08:00:00" },
  "current_node": "contact_ground",
  "vars": { "hr_after": 115 },
  "log": [ { "at": "2027-04-10T08:12:00", "node": "do_action", "input": "done" } ],
  "opened_at": "2027-04-10T08:05:00",
  "closed_at": null,
  "outcome": null
}
```

Más una lista `pending` de triggers en espera por astronauta (mismo archivo o `data/pending.json`, lo decide Fran).

Nota de despliegue: en Streamlit Community Cloud lo que la app escribe en disco se pierde al reiniciar. Para la demo vale; habrá un botón **«Reset demo»** que restaura los datos iniciales.

---

## 5. Código: archivos, dueños y contratos

### 5.1 Árbol del repo

```
app.py                         Ansel   Inicio: elegir astronauta y entorno, saludo de la mascota, Reset demo
pages/
  1_Check_in.py                Juan Carlos   Formulario de medidas, aviso de trigger y paso de confirmar (con mascota)
  2_Protocol.py                Javi   El protocolo activo, paso a paso (con mascota)
  3_Trends.py                  Fran   Histórico con bandas de color y línea base personal (sin mascota)
  4_Mission_log.py             (P1)    Historial de episodios y falsas alarmas · dueño por decidir
core/
  models.py                    Ansel   Constantes: gravedades, estados, tipos de nodo, expresiones de la mascota
  config.py                    Ansel   Cargar y validar los JSON de config/
  mascot.py                    Ansel   La mascota: cara, expresiones, bocadillo y voz
  data.py                      Fran   Medidas, línea base, astronautas, episodios (leer y guardar)
  mission.py                   Fran   Reloj de misión simulado: hora actual, avanzar
  charts.py                    Fran   Gráficas reutilizables (en Trends y, en pequeño, en Check-in)
  conditions.py                Juan Carlos   Evaluador común de condiciones (sección 4.6)
  triggers.py                  Juan Carlos   Evaluar una medida nueva contra los problemas
  episodes.py                  Juan Carlos   Abrir, confirmar, descartar, pendientes, regla de uno a la vez
  protocol_engine.py           Javi   Paso actual y avanzar con la respuesta del astronauta
config/
  mission.json  indicators.json  environments.json  problems.json         Edu (formato: Ansel)
  protocols/<problem_id>.json                                             Edu (formato: Ansel)
data/
  astronauts.csv  measurements.csv  episodes.json  (+ copia inicial para Reset demo)   Fran
scripts/generate_data.py       Fran   Genera pre-espacio y misión simulada, con el escenario de la demo
tests/                         Ansel organiza; cada constructor añade los de su parte
AGENTS.md  CLAUDE.md (@AGENTS.md)  README.md  LICENSE (MIT)  requirements.txt        Ansel
```

Reparto en una frase:
- **Juan Carlos · Funcionalidad A, detectar:** de que entra una medida a que hay un episodio confirmado.
- **Javi · Funcionalidad B, actuar:** del episodio confirmado a que se cierra.
- **Fran · Funcionalidad C, datos y tendencias:** todo lo que se guarda, la línea base, la misión simulada y las gráficas.
- **Ansel · Mascota:** la cara que narra las pantallas del astronauta.

### 5.2 Contratos

La versión vigente, con la mascota (`mascot.say(text, mood, size)`) y las gráficas (`charts.indicator_chart(astronaut, indicator, compact)`), está en la sección 7 del `AGENTS.md`. Esta es la primera versión, como referencia:

```python
# core/models.py
SEVERITIES = ["inactive", "mild", "moderate", "severe"]   # provisional, Edu
EPISODE_STATUSES = ["pending_confirmation", "active", "resolved", "monitoring",
                    "handed_over", "dismissed"]

# core/config.py
load_indicators() -> dict
load_environments() -> dict
load_problems() -> dict
load_protocol(problem_id: str) -> dict
validate_all() -> list[str]          # lista de errores; vacía si todo está bien

# core/data.py
load_astronauts() -> pd.DataFrame
load_measurements(astronaut: str | None = None, indicator: str | None = None,
                  phase: str | None = None) -> pd.DataFrame
add_measurement(m: dict) -> None     # dict con las columnas de 4.1
get_baseline(astronaut: str, indicator: str) -> dict   # {"mean", "std", "n"}
z_score(astronaut: str, indicator: str, value: float) -> float | None
load_episodes(astronaut: str | None = None) -> list[dict]
save_episode(episode: dict) -> None  # crea o sustituye por id
get_open_episode(astronaut: str) -> dict | None   # pending_confirmation o active
reset_demo() -> None

# core/mission.py
now() -> datetime
advance(hours: int = 24) -> list[dict]   # medidas simuladas nuevas que aparecen

# core/conditions.py
check(cond: dict, ctx: dict) -> bool
# ctx = {"astronaut", "environment", "severity", "vars", "answers", "latest": {indicator: value}}

# core/triggers.py
evaluate(measurement: dict, environment: str) -> list[dict]
# [{"problem", "severity", "indicator", "value", "z"}], uno por problema, ya con la gravedad máxima

# core/episodes.py
on_new_measurement(measurement: dict, environment: str) -> dict | None
# Punto de entrada único: lo llaman Check-in y mission.advance(). Aplica confirmar y "uno a la vez".
confirm(episode_id: str, measurement: dict) -> dict      # pasa a active o dismissed
get_pending(astronaut: str) -> list[dict]

# core/protocol_engine.py
current_step(episode: dict) -> dict       # el nodo, con los textos ya listos para mostrar
submit(episode: dict, user_input: dict | None) -> dict   # avanza, guarda medidas, cambia gravedad, cierra
```

Estado de sesión de Streamlit (lo crea `app.py`): `st.session_state.astronaut`, `st.session_state.environment`.

### 5.3 Reglas para que encaje

- Las pantallas **no** leen ni escriben archivos: solo llaman a `core/`.
- Nadie toca `core/` de otro. Si necesitas algo que aún no existe, pon un **stub** con la misma firma que devuelva datos falsos y avisa.
- `config.validate_all()` comprueba que cada `next` apunta a un nodo que existe, que hay al menos un `end` alcanzable y que no quedan `TODO_EDU` en los problemas que entran en la demo. Lo ejecuta un test.

---

## 6. Flujo de trabajo de cada rol

### Viernes por la noche (todos)
- Elegir **los 2 problemas** con el método de la guía. Tienen que salir de vosotros, no de la IA (la guía de entrega de 2026 lo exige). ⚠️ FALTA DETALLE · equipo.
- Repasar este documento y cambiar lo que no convenza **antes** de que Ansel lo pase al `AGENTS.md`.

### Ansel · Arquitectura e integración
- **9:00-10:00:** repo con el árbol de 5.1, `models.py`, `config.py` con validación, configs de ejemplo con marcadores, **un protocolo de prueba** que use los 8 tipos de nodo, `AGENTS.md` + `CLAUDE.md` con los contratos de 5.2, `README.md` con secciones (About, How it works, NASA resources, AI usage, Disclaimer, License).
- Después: revisar y fusionar PR, mantener `main` arrancando, tests de `validate_all`.
- **Mascota:** P0 = cara con sus expresiones, bocadillo y voz con botón de activar (versión provisional ya en el repo). P1 = boca que se mueve al hablar y más animaciones; P1 opcional = mascota fija en la esquina con CSS en lugar de la columna.
- **14:00:** integración 1. **19:00:** integración 2 y primer despliegue. **Domingo 13:00:** integración 3.

### Juan Carlos · Detectar (Funcionalidad A)
- Hasta las 14:00: `conditions.py`, `triggers.py` y `episodes.py` contra el problema de prueba y un stub de `data.py`; pantalla Check-in con el paso de confirmar y el botón «Simular espera».
- Por la tarde: los 2 problemas reales, pendientes y avisos.

### Javi · Actuar (Funcionalidad B)
- Hasta las 14:00: `protocol_engine.py` y la pantalla Protocol recorriendo el **protocolo de prueba** completo (los 8 tipos de nodo). Usa `conditions.check()`; hasta que Juan Carlos lo fusione, un stub.
- Por la tarde: los protocolos reales de Edu. Pantalla de `contact` con el retraso del entorno.

### Fran · Datos y tendencias (Funcionalidad C)
- Hasta las 14:00: `data.py`, `mission.py` y `charts.indicator_chart()` reales (Juan Carlos la usa en Check-in en versión compacta); `generate_data.py` con 3 astronautas, pre-espacio y misión, incluido **el escenario de la demo** (qué astronauta, qué día y qué anomalía; lo decide con Gonzalo).
- Por la tarde: pantalla Trends con bandas de color, línea base y marcas de los episodios.
- ⚠️ FALTA DETALLE · Fran (con Edu): cuántas medidas pre-espacio hacen falta, desviación típica mínima para que el z-score no explote con datos muy estables, y cómo tratar el ánimo (escala 1-5) y el sueño (diario).

### Edu · Ciencia y salud
- **Antes de las 12:00 del sábado:** problemas, triggers y gravedades en tabla, con fuente; entornos con sus valores.
- **Antes de las 16:00:** los 2 protocolos en tabla o dibujo y luego en JSON, revisados número a número.
- Revisa todo texto de salud que genere la IA. Prepara qué recursos de la NASA se citan (HRP Hazards, HRP Risks, HRP Research) y para qué se usó cada uno: es lo que pide el campo «NASA Data» y el criterio de Relevancia.

### Gonzalo · Producto, coordinación y pruebas
- **9:00:** historias de usuario y bocetos de las 4 pantallas, y **la historia de la demo** (el recorrido que se grabará). ⚠️ FALTA DETALLE · Gonzalo.
- Textos de la interfaz (con Edu para lo de salud), guía de estilo del semáforo (un color por gravedad).
- Tras cada fusión: probar contra las historias y abrir issues. Sábado por la tarde y domingo por la mañana: pruebas con gente de fuera.
- Decide P0/P1 de lo que queda abierto (sección 7).

---

## 7. Alcance

**P0 (sábado):**
1. Elegir astronauta y entorno.
2. Introducir medidas a mano y avanzar el reloj de misión.
3. Trigger con umbrales por entorno → confirmar repitiendo la medida → episodio.
4. Protocolo paso a paso con los 8 tipos de nodo, para 2 problemas.
5. Gráfica de evolución con línea base y bandas.
6. Mascota narrando Inicio, Check-in y Protocolo, con voz.
7. Reset demo y despliegue.

**P1 (domingo por la mañana, por orden a decidir por Gonzalo):**
- Historial de episodios y falsas alarmas (pantalla 4).
- Ver el protocolo como diagrama (`st.graphviz_chart` con texto DOT; comprobad que funciona sin instalar nada más).
- Cuerpo humano clicable con el estado de cada sistema (lo sugiere el enunciado).
- Recordatorios de rutina: «toca medirse la tensión».

**P2:** gamificación, vista para el médico de a bordo, más problemas.

---

## 8. Lista de huecos y su responsable

| # | Hueco | Responsable | Para cuándo |
|---|---|---|---|
| 1 | Qué 2 problemas | Equipo (propone Edu) | Viernes noche |
| 2 | Niveles de gravedad definitivos y su significado | Edu | Sábado 12:00 |
| 3 | Triggers: indicadores, umbrales absolutos, umbrales z, ajustes por entorno | Edu | Sábado 12:00 |
| 4 | `confirm_wait_min` de cada problema | Edu | Sábado 12:00 |
| 5 | Entornos: lista, gravedad y retraso con fuente | Edu | Sábado 12:00 |
| 6 | Contenido de los 2 protocolos con fuentes | Edu (+ Gonzalo redacción) | Sábado 16:00 |
| 7 | Recursos NASA que se citan y para qué | Edu | Domingo 13:00 |
| 8 | Línea base: n mínimo, desviación mínima, ánimo y sueño | Fran (+ Edu) | Sábado 14:00 |
| 9 | Escenario simulado de la demo | Fran + Gonzalo | Sábado 14:00 |
| 10 | Historia de la demo, bocetos y textos | Gonzalo | Sábado 10:00 / tarde |
| 11 | Qué ve el astronauta con un pendiente más grave | Gonzalo (+ Juan Carlos) | Sábado tarde |
| 12 | Si `contact` es solo un mensaje o simula una respuesta | Gonzalo | Sábado tarde |
| 13 | Orden del P1 | Gonzalo | Sábado 19:00 |
| 14 | Nombre y aspecto de la mascota (diseño vuestro, no de la IA) | Equipo | Sábado mañana |
| 15 | Lista de expresiones y en qué situación sale cada una (tono revisado por Edu) | Equipo (+ Edu) | Sábado mañana |
| 16 | Qué dice la mascota: solo los textos de las pantallas o también frases propias, y quién las escribe | Equipo | Sábado mañana |
