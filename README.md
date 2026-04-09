# Antivirus-empresarial-multiplataforma-Windows-Linux
⚙️ ✅ Cómo ejecutarlo en Windows
1. Instalar dependencias

En CMD o PowerShell:

pip install fastapi uvicorn psutil mysql-connector-python watchdog

Tkinter normalmente ya viene con Python en Windows.

2. Tener MySQL (XAMPP)
Inicia MySQL desde XAMPP
Crea la base de datos:
CREATE DATABASE antivirus;

El código ya crea la tabla automáticamente.

3. Ejecutar el programa
python antivirus_app.py

Se abrirá:

🖥️ Interfaz gráfica (Tkinter)
🌐 API FastAPI en: http://127.0.0.1:8000
🧠 Qué hace este prototipo

Incluye:

✅ Motor de firmas
Hash SHA-256
Comparación con base de datos MySQL
✅ Monitor de procesos
Uso de psutil
Detección heurística básica
✅ API FastAPI

Endpoints:

/ → estado
/scan → escaneo manual
/alerts → alertas generadas
✅ GUI en Tkinter
Botón para escanear archivos
Visualización de alertas en tiempo real
⚠️ Limitaciones (importante para tu TFM)

Esto es clave que luego expliques en memoria:

Heurística muy básica (puedes ampliarla)
No hay sandboxing real
Monitor de archivos aún no usa watchdog completo
MySQL depende de XAMPP (no portable total)

👉 Esto no es malo, al contrario: te da “trabajo futuro”.

🚀 Siguientes mejoras (te suben la nota muchísimo)

Si quieres llevarlo a nivel sobresaliente:

Integrar watchdog real (detección de cambios en archivos)
Añadir reglas heurísticas más complejas
Clasificación de amenazas (low/medium/high)
Cifrado de logs
Panel web en FastAPI (dashboard)
Separar arquitectura en módulos (core, ui, api)
💬 Siguiente paso recomendado

Ahora que ya tienes código base funcional, lo ideal es:

👉 Integrarlo en la memoria del TFM en:

4.2.2 → descripción técnica
Diagramas de arquitectura
Explicación de módulos basada en este código
