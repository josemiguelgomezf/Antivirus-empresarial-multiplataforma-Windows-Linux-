# Antivirus Empresarial Multiplataforma (Windows/Linux)

Proyecto de demostración para un sistema de seguridad orientado a laboratorio, investigación y TFM. El programa principal es [antivirus_enterprise.py](antivirus_enterprise.py) y combina una interfaz gráfica en Tkinter con una API REST local desarrollada con FastAPI.

## 1. Descripción técnica

Este proyecto implementa un prototipo de antivirus empresarial local con las siguientes capacidades:

- Escaneo de archivos por hash SHA-256 contra una base de firmas local
- Detección heurística básica de extensiones peligrosas y procesos sospechosos
- Monitorización de procesos mediante psutil
- Análisis multimedia para detectar patrones sospechosos en archivos de imagen, audio, video y documentos
- Análisis de código fuente para identificar vulnerabilidades comunes (CWE) en Python, JavaScript, Java, PHP, SQL y otros lenguajes
- Persistencia de alertas, historial de escaneos, cuarentena y análisis en base de datos SQLite
- Interfaz gráfica Tkinter con panel de dashboard y pestañas de análisis
- API REST local para integrar el motor de análisis desde otros clientes o pruebas automatizadas

## 2. Requisitos

- Python 3.9 o superior
- pip actualizado
- Sistema operativo Windows o Linux
- Acceso local a la red para probar la API en localhost

## 3. Dependencias

El programa requiere las siguientes dependencias de Python:

```bash
pip install fastapi uvicorn psutil watchdog
```

Notas importantes:
- Tkinter suele venir incluido con Python en Windows y muchas distribuciones de Linux.
- La base de datos se gestiona con SQLite, por lo que no requiere un servidor MySQL ni XAMPP.
- El proyecto crea automáticamente la carpeta data/ y logs/ al arrancar.

## 4. Instalación

Desde la raíz del proyecto:

```bash
cd "c:\Users\jose.gomez\Documents\Antivirus-empresarial-multiplataforma-Windows-Linux-"
python -m venv .venv
```

Activación del entorno virtual:

### Windows (PowerShell)
```powershell
.\.venv\Scripts\Activate.ps1
```

### Linux / macOS
```bash
source .venv/bin/activate
```

Instalación de dependencias:

```bash
pip install --upgrade pip
pip install fastapi uvicorn psutil watchdog
```

## 5. Inicio del programa

El arranque principal se realiza con:

```bash
python antivirus_enterprise.py
```

### Qué ocurre al iniciar

- Se abre la interfaz gráfica Tkinter
- Se inicia la API FastAPI en localhost
- Se crea o inicializa la base de datos SQLite en data/antivirus.db
- Se genera el archivo de log en logs/antivirus.log

### URL de la API

La API queda disponible en:

```text
http://127.0.0.1:8000
```

## 6. Funcionalidades principales

### 6.1 Interfaz gráfica Tkinter

La interfaz incluye:

- Dashboard con métricas del sistema
- Escaneo de archivos y carpetas
- Escaneo del sistema completo
- Monitorización de procesos sospechosos
- Análisis multimedia
- Análisis de código fuente
- Visualización de alertas, cuarentena e historial de escaneos

### 6.2 API REST FastAPI

Endpoints disponibles:

- GET / → estado del servicio
- GET /alerts → listar alertas
- GET /alerts/stats → estadísticas de alertas
- POST /scan/file?path=... → escaneo de un archivo concreto
- POST /scan/multimedia?path=... → análisis de un archivo multimedia
- POST /scan/code?code=... → análisis de código fuente
- GET /quarantine → listar elementos en cuarentena
- GET /scan/history → historial de escaneos
- GET /signatures/count → número de firmas cargadas
- GET /monitor/status → estado del monitor
- POST /monitor/start → iniciar monitorización
- POST /monitor/stop → detener monitorización
- GET /system/stats → métricas del sistema

Ejemplo de prueba rápida:

```bash
curl http://127.0.0.1:8000/
```

## 7. Estructura del proyecto

```text
antivirus_enterprise.py   # Aplicación principal
package.json              # Configuración de Node auxiliar del proyecto
README.md                 # Documentación del proyecto
data/                    # Base de datos SQLite y archivos persistentes
logs/                    # Registros de ejecución
```

## 8. Notas de seguridad y limitaciones

Este prototipo está orientado a demostración y análisis técnico, no a reemplazar un antivirus empresarial real. Sus limitaciones incluyen:

- Detección heurística básica y no completa
- Uso de firmas locales de ejemplo para demostración
- Monitorización de procesos limitada a señales de comportamiento sospechoso
- Sin sandboxing ni análisis dinámico en tiempo real
- Sin cifrado avanzado de logs o protección de datos en producción

## 9. Recomendaciones para TFM / desarrollo posterior

Posibles mejoras para convertir el prototipo en una solución más robusta:

- Integración con reglas heurísticas más sofisticadas
- Soporte real para detección de cambios de archivos con watchdog avanzado
- Clasificación de amenazas por severidad (low/medium/high/critical)
- Panel web más completo para visualización operativa
- Separación modular del proyecto en capas: core, ui, api, db
- Integración con motores de análisis externos o bases IOC

## 10. Resumen rápido

Comandos mínimos para arrancar:

```bash
pip install fastapi uvicorn psutil watchdog
python antivirus_enterprise.py
```

Si la interfaz se abre correctamente y la API responde en localhost, el entorno está listo para uso local y demostración técnica.
