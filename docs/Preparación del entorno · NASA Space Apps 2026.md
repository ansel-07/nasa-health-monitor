# Preparación del entorno · NASA Space Apps 2026

Nov 13, 2026 · @Ansel

Haz esto antes del sábado a las 9:00: son unos 30-45 minutos. Sigue solo el apartado de tu sistema y luego los apartados comunes. Al final, la app del equipo tiene que arrancar en tu portátil.

## Qué vas a instalar

| Herramienta | Para qué | Versión |
| --- | --- | --- |
| Python | Ejecutar la app | 3.11 o 3.12 |
| Git | Trabajar con el repo del equipo | La que instale tu sistema |
| VS Code | Editar el código | La última |
| GitHub CLI (`gh`) | Iniciar sesión en GitHub y clonar sin configurar claves | La que instale tu sistema |
| Claude Code o Codex | La IA con la que programas, según tu rol | La última |
| Librerías de Python | Streamlit, pandas, Plotly, numpy, pytest | Las de `requirements.txt` |

Necesitas además una cuenta de GitHub. Si no tienes, créala en [github.com](https://github.com/signup) y pásale tu usuario al Rol 3 para que te dé acceso al repo.

## Windows 10 y 11

Todo se instala con `winget` desde **PowerShell**. Ábrelo con clic derecho en Inicio → «Terminal» (o «Windows PowerShell»).

1. Instala las herramientas:

```powershell
winget install -e --id Git.Git
winget install -e --id Python.Python.3.12
winget install -e --id Microsoft.VisualStudioCode
winget install -e --id GitHub.cli
```

2. **Cierra PowerShell y ábrelo de nuevo**, para que reconozca los programas nuevos. Comprueba:

```powershell
py -3.12 --version
git --version
code --version
gh --version
```

3. Permite activar entornos de Python (solo una vez):

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Responde `S` (o `Y`) si pregunta.

4. Evita problemas de saltos de línea con los compañeros de Linux:

```powershell
git config --global core.autocrlf true
```

Si `python` abre la Microsoft Store en lugar de Python, usa siempre `py -3.12`, o desactiva en Configuración → Aplicaciones → Configuración avanzada de aplicaciones → «Alias de ejecución de aplicaciones» los dos alias de Python.

Sigue en «Comunes a todos».

## Ubuntu y Linux Mint

Los mismos comandos valen para los dos. Linux Mint 22 está basado en Ubuntu 24.04 y trae Python 3.12; Linux Mint 21 está basado en Ubuntu 22.04 y trae Python 3.10, que necesita el paso extra del final.

1. Mira qué versión tienes:

```bash
lsb_release -a
```

2. Instala Python, Git y GitHub CLI:

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git curl wget gh
python3 --version
```

3. Instala VS Code con el paquete `.deb` oficial. Funciona igual en Ubuntu y en Mint (Mint bloquea `snap` por defecto, así que no uses `snap install code`):

```bash
wget -O /tmp/code.deb "https://code.visualstudio.com/sha/download?build=stable&os=linux-deb-x64"
sudo apt install -y /tmp/code.deb
code --version
```

Si pregunta si quieres añadir el repositorio de Microsoft, di que sí: así se actualiza solo.

4. Evita problemas de saltos de línea con los compañeros de Windows:

```bash
git config --global core.autocrlf input
```

**Solo si `python3 --version` da 3.10** (Ubuntu 22.04 o Mint 21):

```bash
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12 python3.12-venv
```

En ese caso, en los comandos de abajo usa `python3.12` donde pone `python3`.

Sigue en «Comunes a todos».

## Comunes a todos

En Windows, escribe estos comandos en PowerShell; en Linux, en la terminal. Donde difieren, van los dos.

1. Di a Git quién eres. Usa el email de tu cuenta de GitHub, para que tus commits salgan a tu nombre:

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu-email-de-github@ejemplo.com"
git config --global init.defaultBranch main
git config --global push.autoSetupRemote true
```

2. Inicia sesión en GitHub. Elige «GitHub.com», «HTTPS», «Yes» para usarlo con Git y «Login with a web browser»:

```bash
gh auth login
```

3. Clona el repo del equipo y entra en la carpeta:

```bash
gh repo clone ansel-07/nasa-health-monitor
cd nasa-health-monitor
```

4. Crea el entorno de Python dentro de la carpeta del repo y actívalo:

```powershell
# Windows (PowerShell)
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

```bash
# Ubuntu / Mint
python3 -m venv .venv
source .venv/bin/activate
```

Sabrás que está activo porque la línea de comandos empieza por `(.venv)`. **Cada vez que abras una terminal nueva, actívalo de nuevo** con el segundo comando.

5. Instala las librerías:

```bash
pip install -r requirements.txt
```

6. Comprueba que todo funciona:

```bash
pytest
python -m core.config
streamlit run app.py
```

`pytest` debe decir `passed`, `core.config` debe decir `OK`, y la app se abre en el navegador en `http://localhost:8501`. Para pararla, `Ctrl+C` en la terminal.

7. Abre el proyecto en VS Code con `code .` dentro de la carpeta. Instala la extensión **Python** (de Microsoft) y elige el intérprete del entorno: `Ctrl+Shift+P` → «Python: Select Interpreter» → el que pone `.venv`.

## La IA: Claude Code o Codex

Instala solo la que te toca según el reparto de cuentas de la guía del equipo. Las dos leen las mismas instrucciones del proyecto (`AGENTS.md`).

**Claude Code** (cuenta de Claude Pro o superior):

```powershell
# Windows (PowerShell). Necesita Git instalado antes.
irm https://claude.ai/install.ps1 | iex
```

```bash
# Ubuntu / Mint
curl -fsSL https://claude.ai/install.sh | bash
```

Cierra y abre la terminal, entra en la carpeta del repo y escribe `claude`. La primera vez te pide iniciar sesión en el navegador. Si prefieres usarlo dentro de VS Code, instala también la extensión **Claude Code** desde la pestaña de extensiones.

**Codex** (cuenta de ChatGPT Plus): en VS Code, pestaña de extensiones, busca **Codex** (de OpenAI), instálala y entra con tu cuenta de ChatGPT.

**Comprueba que la IA lee las instrucciones.** Abre el repo, inicia la IA y pregúntale: «¿Qué instrucciones del proyecto conoces?». Tiene que mencionar, entre otras cosas, que todo va en inglés, que no se inventan valores médicos y que solo toca los archivos de su dueño. Si no lo hace, avísale al Rol 3.

## Checklist antes del sábado

- [ ] `git`, `gh`, `code` y Python 3.11 o 3.12 responden con su versión
- [ ] Git tiene tu nombre y tu email de GitHub
- [ ] El repo está clonado y `.venv` activado
- [ ] `pytest` pasa y `python -m core.config` dice `OK`
- [ ] `streamlit run app.py` abre la app en el navegador
- [ ] Tu IA responde y conoce las instrucciones del proyecto

## Problemas frecuentes

| Síntoma | Solución |
| --- | --- |
| `streamlit`, `pytest` o `pip` «no se reconoce» o «command not found» | El entorno no está activo: entra en la carpeta del repo y actívalo (paso 4 de «Comunes»). |
| Windows: «la ejecución de scripts está deshabilitada» al activar | Ejecuta `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y vuelve a probar. |
| Windows: `python` abre la Microsoft Store | Usa `py -3.12`, o desactiva los alias de Python (apartado de Windows). |
| Windows: un programa recién instalado «no se reconoce» | Cierra y abre PowerShell. Si sigue, reinicia el portátil. |
| Linux: `error: externally-managed-environment` | Has usado `pip` fuera del entorno. Actívalo y repite. |
| Linux: `No module named venv` | `sudo apt install -y python3-venv` (o `python3.12-venv`). |
| `ModuleNotFoundError: No module named 'core'` | Ejecuta los comandos desde la carpeta raíz del repo, no desde una subcarpeta. |
| La app dice que el puerto 8501 está ocupado | Ya hay otra copia abierta: ciérrala con `Ctrl+C` o usa `streamlit run app.py --server.port 8502`. |
| `gh repo clone` da error de permisos | Aún no tienes acceso al repo: pásale tu usuario de GitHub al Rol 3. |

Si algo no sale en 15 minutos, escríbelo en el chat del equipo con el mensaje de error copiado.
