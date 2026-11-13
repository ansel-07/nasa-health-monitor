# Cómo trabajamos con Git · NASA Space Apps 2026

Documento interno del equipo, en español: **traducir o borrar antes de entregar** (el repo será público y lo que vea el jurado va en inglés).

Programamos cuatro: **Ansel, Fran, Juan Carlos y Javi**. Ansel revisa y fusiona todo. Edu y Gonzalo no programan, pero también pueden proponer cambios (sección 9).

---

## 1. Chuleta: una tarea de principio a fin

```bash
# 1. Empezar, siempre desde main actualizado
git switch main
git pull
git switch -c tunombre/que-hace

# 2. Trabajar y guardar cada vez que algo funcione
git add ruta/archivo1.py ruta/archivo2.py
git commit -m "Add measurement form to Check-in"
git push -u origin tunombre/que-hace        # la primera vez; después basta git push

# 3. Antes de pedir revisión: traerte lo último de main y probar
git fetch origin
git merge origin/main
pytest
streamlit run app.py

# 4. Pedir revisión
git push
gh pr create --base main --fill
# ...y avisar en el chat del equipo

# 5. Cuando Ansel lo fusione
git switch main
git pull
```

Mientras esperas la revisión, **no te quedes parado**: vuelve al paso 1 con la siguiente tarea.

---

## 2. Reglas de oro

1. **Nunca se hace commit directamente en `main`.** Nadie, tampoco Ansel.
2. **`main` siempre arranca.** Lo que entra en `main` ha pasado `pytest` y se ha probado con `streamlit run app.py`.
3. **Una rama = una tarea pequeña** (1-2 horas como mucho). Si mezcla dos cosas, se separa en dos.
4. **Solo tocas tus archivos** (tabla de dueños en `AGENTS.md`, sección 4). Si necesitas un cambio en un archivo de otro, se lo pides a su dueño.
5. **Nunca `git push --force`** ni `git reset --hard` sobre algo que ya has subido.
6. **Quien fusiona es Ansel**, después de revisar. Tú abres el pull request; no lo fusionas.
7. **Ante la duda, para y pregunta.** Un comando que no entiendes puede costar más que esperar 5 minutos.

---

## 3. Nombres

**Ramas:** `tunombre/que-hace`, en minúsculas, con guiones y en inglés.

| Bien | Mal |
|---|---|
| `juancarlos/confirmation-step` | `rama1`, `cambios`, `Juan Carlos/Confirmación` |
| `fran/baseline` | `fran` (sin descripción) |
| `javi/protocol-question-node` | `javi/todo-el-protocolo` (demasiado grande) |

**Commits:** una frase en inglés que diga **qué cambia**, empezando por un verbo.

| Bien | Mal |
|---|---|
| `Add repeat-measurement step to Check-in` | `cambios` |
| `Fix z-score when std is zero` | `arreglado` |
| `Show contact delay on Mars` | `wip`, `asdf` |

---

## 4. Paso a paso, con explicación

### 4.1 Empezar una tarea

```bash
git switch main          # vuelve a la rama principal
git pull                 # baja lo último que se ha fusionado
git switch -c fran/baseline   # crea tu rama nueva y te cambia a ella
```

Comprueba en qué rama estás con `git branch` (la tuya lleva un `*`) o mirando abajo a la izquierda en VS Code.

> Si ya habías empezado a escribir código en `main` sin hacer commit, no pasa nada: `git switch -c fran/baseline` se lleva tus cambios a la rama nueva.

### 4.2 Trabajar

- Haz **commits pequeños y frecuentes**, cada vez que algo funcione. Es tu red de seguridad: si la IA estropea algo, puedes volver atrás.
- Añade los archivos **por nombre**. Antes de cada commit, mira qué vas a subir:

```bash
git status               # qué archivos han cambiado
git diff                 # qué líneas han cambiado
git add core/data.py tests/test_data.py
git commit -m "Compute baseline from preflight measurements"
```

- Sube tu rama de vez en cuando (`git push`), aunque no hayas terminado. Así no se pierde nada si se te cuelga el portátil.

> **Los datos de ejecución no se suben.** Al usar la app se modifican `data/measurements.csv` y `data/episodes.json`. Antes de cada commit, deshaz esos cambios:
> ```bash
> git restore data/measurements.csv data/episodes.json
> ```
> La excepción es Fran cuando cambie a propósito los datos iniciales (`data/seed/`).

### 4.3 Antes de pedir revisión

Tráete lo que otros han fusionado mientras trabajabas y comprueba que todo sigue funcionando junto:

```bash
git fetch origin         # baja las novedades de GitHub sin tocar tus archivos
git merge origin/main    # las mezcla en tu rama
pytest                   # todos los tests en verde
python -m core.config    # debe decir OK
streamlit run app.py     # prueba tu funcionalidad Y que las otras pantallas siguen abriendo
```

Si `git merge` dice `CONFLICT`, ve a la sección 6.

### 4.4 Pedir revisión (pull request)

```bash
git push
gh pr create --base main --fill
```

`gh` te abre un editor con el título y la descripción. Escribe en la descripción:

```
What: Check-in form saves the measurement and shows the alert.
How to test: Home -> pick Astronaut A -> Check-in -> enter heart_rate 150.
Files: pages/1_Check_in.py, core/episodes.py, tests/test_episodes.py
```

Y avisa en el chat del equipo: «PR #12 listo para revisar».

> Sin terminal: en VS Code, panel de Git (icono de ramas a la izquierda) → «Publish Branch», y luego en GitHub aparece un botón amarillo «Compare & pull request».

### 4.5 Mientras esperas

Empieza la siguiente tarea **en una rama nueva sacada de `main`** (paso 4.1). No la saques de la rama que está pendiente de revisión.

Si tu siguiente tarea necesita algo de tu PR pendiente, tienes dos opciones:
- Trabajar contra un **stub** (una función de mentira con la misma firma) hasta que se fusione.
- Pedirle a Ansel que priorice tu PR.

### 4.6 Si te piden cambios

Ansel dejará comentarios en el PR. Corrige **en la misma rama** y vuelve a subir:

```bash
git switch fran/baseline
# ...corriges...
git add core/data.py
git commit -m "Handle astronauts without preflight data"
git push
```

El PR se actualiza solo. Avisa de que ya está.

### 4.7 Después de que se fusione

```bash
git switch main
git pull
git branch -d fran/baseline     # borra tu rama local, ya no hace falta
```

---

## 5. Cada vez que alguien fusiona algo

Cuando Ansel avise de que ha fusionado un PR, **todos** hacen esto en cuanto puedan (no hace falta parar lo que estés haciendo; basta antes de pedir tu siguiente revisión):

```bash
git fetch origin
git merge origin/main          # dentro de tu rama de trabajo
```

Cuanto antes te traigas lo de los demás, más pequeños serán los conflictos.

---

## 6. Conflictos

Un conflicto ocurre cuando tú y otra persona habéis cambiado las mismas líneas. Como cada uno tiene sus archivos, debería pasar poco.

Si `git merge origin/main` dice `CONFLICT`:

1. `git status` te dice qué archivos tienen conflicto (`both modified`).
2. Ábrelos en VS Code. Verás bloques marcados con dos versiones y unos botones encima:
   - **Accept Current Change**: te quedas con lo tuyo.
   - **Accept Incoming Change**: te quedas con lo de `main`.
   - **Accept Both Changes**: las dos cosas, una detrás de otra.
3. Cuando no quede ningún bloque marcado, guarda y termina:
   ```bash
   git add archivo-con-conflicto.py
   git commit                   # el mensaje ya viene escrito; guarda y cierra
   ```
4. Vuelve a probar (`pytest` y la app).

**Si no lo ves claro:**
```bash
git merge --abort               # deja todo exactamente como estaba antes del merge
```
y llama a Ansel. Nunca resuelvas un conflicto en un archivo que no es tuyo sin hablar con su dueño.

---

## 7. «La he liado»: soluciones rápidas

| Qué ha pasado | Qué hacer |
|---|---|
| He hecho commit en `main` sin querer (**sin** push) | `git switch -c tunombre/rescate` (tus commits pasan a esa rama), luego `git switch main` y `git reset --hard origin/main` |
| He hecho push a `main` sin querer | No hagas nada más y avisa a Ansel |
| He empezado a trabajar en la rama equivocada (sin commit) | `git stash`, `git switch rama-buena`, `git stash pop` |
| Quiero deshacer los cambios de un archivo que no he guardado en commit | `git restore ruta/archivo.py` |
| Quiero deshacer mi último commit (sin push), conservando los cambios | `git reset --soft HEAD~1` |
| He subido `data/measurements.csv` o `data/episodes.json` | Avisa a Ansel; en tu siguiente commit: `git checkout origin/main -- data/measurements.csv data/episodes.json` |
| `git pull` dice que tienes cambios locales | Haz commit de tus cambios (si es tu rama) o `git stash` antes del `pull` |
| `git push` dice `rejected` / `fetch first` | Otro ha subido a tu rama, o el PR se actualizó: `git pull` y vuelve a hacer `git push` |
| `git push` pide usuario y contraseña | `gh auth setup-git` y vuelve a probar |
| No sé en qué estado estoy | `git status` y pégalo en el chat del equipo |

---

## 8. Calendario

| Cuándo | Qué |
|---|---|
| Sábado 14:00 | **Integración 1**: todo lo que funcione, en PR antes de las 13:30 |
| Sábado 19:00 | **Integración 2** y primer despliegue: PR antes de las 18:30 |
| Domingo 13:00 | **Integración 3**: PR antes de las 12:30 |
| Domingo 16:00 | **Congelación**: a partir de aquí solo se arreglan errores, nada nuevo |

---

## 9. Edu y Gonzalo (sin terminal)

Para cambiar un archivo de `config/` (Edu) o un texto (Gonzalo) desde la web:

1. En GitHub, entra en el archivo (por ejemplo `config/problems.json`).
2. Pulsa el lápiz (**Edit this file**).
3. Haz el cambio.
4. Pulsa **Commit changes…**, elige **Create a new branch for this commit and start a pull request**, ponle nombre (`edu/problem-1-thresholds`) y confirma.
5. Avisa a Ansel.

Si es mucho texto o no te aclaras, pásale el contenido a Ansel y lo sube él.

---

## 10. Para Ansel: cómo revisar un pull request

### 10.1 Cuándo

- Revisa en **menos de 15-20 minutos** desde que te avisan. Si los PR se acumulan, se bloquea todo el equipo.
- Orden de prioridad: lo que desbloquea a otros (contratos, `data.py`, `conditions.py`) → lo que entra en la próxima integración → el resto.
- Antes de cada integración, revisa todo lo pendiente.

### 10.2 Ver qué hay pendiente

```bash
gh pr list                      # PR abiertos
gh pr view 12                   # descripción y estado
gh pr diff 12 --name-only       # qué archivos toca
gh pr diff 12                   # el cambio completo
```

### 10.3 Probarlo en tu portátil

```bash
git status                      # asegúrate de no tener cambios sin guardar
gh pr checkout 12               # te pone en la rama del PR
git merge origin/main           # opcional: comprueba que se integra con lo último
pytest
python -m core.config
streamlit run app.py            # sigue el "How to test" de la descripción
```

Cuando acabes, vuelve a tu trabajo con `git switch tu-rama` (o `git switch main`). Si hiciste el merge opcional, no lo subas: solo era para probar.

### 10.4 Lista de comprobación

**Arranca e integra**
- [ ] `pytest` en verde y `python -m core.config` dice OK.
- [ ] La app arranca y **las demás pantallas siguen abriendo**, no solo la del PR.
- [ ] La funcionalidad hace lo que dice la descripción.
- [ ] La rama está al día con `main` o no tiene conflictos (GitHub lo indica en el PR).

**Respeta el `AGENTS.md`**
- [ ] Solo toca archivos de su dueño (`gh pr diff 12 --name-only`).
- [ ] No cambia firmas de funciones, claves de JSON ni columnas de CSV de los contratos.
- [ ] Las pantallas no leen ni escriben archivos directamente; solo llaman a `core/`.
- [ ] No añade librerías (`requirements.txt` sin cambios) ni carpetas nuevas en la raíz.
- [ ] Los archivos nuevos llevan la cabecera `# AI-assisted: ...`.
- [ ] Todo en inglés: textos de la interfaz, frases de la mascota, código y comentarios.

**Salud y datos**
- [ ] Ningún número médico inventado: umbrales, rangos y consejos vienen de `config/`. Si el PR toca `config/`, Edu lo ha revisado.
- [ ] No incluye `data/measurements.csv` ni `data/episodes.json` modificados por usar la app.

**Calidad mínima**
- [ ] Si añade lógica en `core/`, añade algún test.
- [ ] El PR hace una sola cosa. Si mezcla varias, pide separarlo.
- [ ] No hay restos evidentes: código comentado a montones, `print` de depuración, archivos de prueba sueltos.

No hace falta que el código sea perfecto: hace falta que funcione, que encaje y que no rompa lo de los demás.

### 10.5 Qué hacer con el PR

**Está bien → fusionar**
```bash
gh pr merge 12 --squash --delete-branch
```
`--squash` junta todos sus commits en uno solo en `main`. Después:
```bash
git switch main
git pull
```
Avisa en el chat: «PR #12 fusionado, haced `git fetch` + `git merge origin/main`».

**Tiene detalles menores → aprobar y fusionar, y apuntar lo pendiente**
Si no rompe nada y el arreglo es pequeño, fusiona y pide el arreglo en el siguiente PR (o abre un issue). No bloquees por cosas menores.
```bash
gh pr review 12 --comment -b "Merged. Next PR: rename the button to 'Done'."
```

**Hay que cambiar algo → pedir cambios**
```bash
gh pr review 12 --request-changes -b "The page reads data/measurements.csv directly; use data.load_measurements() instead."
```
Di **qué** hay que cambiar y **por qué**, en una o dos frases. El compañero corrige en la misma rama, hace `git push`, y vuelves a revisar.

**Tiene conflictos con `main`**
Pide al autor que haga `git fetch origin` + `git merge origin/main` en su rama, resuelva y suba (sección 6). Si el conflicto está en archivos de otro, resolvedlo juntos.

**No tiene sentido (duplicado, enfoque equivocado, se ha abandonado)**
```bash
gh pr close 12 -c "Closing: replaced by #15."
```

### 10.6 Tus propios cambios

Tú también trabajas en ramas (`ansel/...`) y abres PR. Puedes fusionarlos tú mismo, pero pásales la misma lista de comprobación. Si tocan contratos o algo que usan otros, avisa antes de fusionar.

### 10.7 En cada integración (14:00, 19:00, 13:00)

1. Revisa y fusiona todo lo que esté listo.
2. En `main` actualizado: `pytest`, `python -m core.config` y un recorrido completo por la app (Home → Check-in → Protocol → Trends).
3. Si algo se ha roto, identifica qué PR lo rompió (`git log --oneline`) y pide el arreglo al dueño, o revierte ese PR:
   ```bash
   gh pr view 12 --json mergeCommit --jq .mergeCommit.oid    # commit del merge
   git switch -c ansel/revert-12
   git revert <ese-commit>
   git push -u origin ansel/revert-12
   gh pr create --base main --fill
   ```
4. Desde la integración de las 19:00: comprueba que la app desplegada se actualiza y abre en una ventana privada.
5. Avisa al equipo de que `main` está al día.
