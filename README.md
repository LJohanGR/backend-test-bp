# CSV Profiling API — Backend

API REST desarrollada en Python para el análisis, perfilado y exploración interactiva de datasets CSV, con soporte para filtrado dinámico, decodificación mediante catálogos, generación de métricas, KPIs y visualizaciones.

---

## Cómo correr el proyecto localmente

### Requisitos previos

- Python 3.10+
- `pip` o `pip3`

### Instalación

```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio>
cd back

# 2. Crear y activar el entorno virtual
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt
```

### Ejecución

```bash
uvicorn main:app --reload
```

La API quedará disponible en `http://localhost:8000`.  
La documentación interactiva (Swagger UI) en `http://localhost:8000/docs`.

### Variables de entorno (opcional)

Crear un archivo `.env` en la raíz del proyecto:

```env
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
MAX_FILE_SIZE_MB=50
SESSION_TTL_MINUTES=60
CATALOGOS_PATH=Catalogos
```

---

## Stack tecnológico utilizado

| Capa | Tecnología | Versión |
|---|---|---|
| Lenguaje | Python | 3.10+ |
| Framework web | FastAPI | 0.136 |
| Servidor ASGI | Uvicorn | 0.48 |
| Validación de datos | Pydantic v2 + pydantic-settings | 2.13 / 2.14 |
| Procesamiento de datos | Pandas | 3.0 |
| Operaciones numéricas | NumPy | 2.4 |
| Geocodificación | pgeocode | 0.5 |
| Gestión de configuración | python-dotenv | 1.2 |
| Carga de archivos | python-multipart | 0.0.29 |

---

## Principales decisiones de producto

El análisis de la información se realizó de forma **aislada e iterativa utilizando Pandas**, inspeccionando manualmente el dataset para identificar columnas con potencial informativo relevante: distribuciones atípicas, campos con alta cardinalidad, datos faltantes y variables categóricas codificadas.

Se integró **perfilado estadístico automático** (`profiling_service`) sobre los datos cargados en sesión, con el objetivo de exponer posibles nuevos filtros de forma dinámica. Este enfoque permite adaptar la API a nuevos catálogos o esquemas de datos sin modificaciones estructurales al código, anticipando la incorporación de futuros catálogos cuando estén disponibles.

La arquitectura de rutas fue segmentada por dominio funcional (`/upload`, `/profile`, `/metrics`, `/filter`, `/charts`, `/kpis`, `/map`, `/decode`, `/catalogs`) para mantener la separación de responsabilidades y facilitar la extensibilidad.

---

## Enfoque de procesamiento de datos

El pipeline de procesamiento consideró los siguientes criterios:

- **Catálogos como fuente de verdad:** Se utilizaron los catálogos provistos (archivos `.txt` en `Catalogos/`) para decodificar claves numéricas a etiquetas semánticas, habilitando una capa de interpretación legible sobre los datos crudos.
- **Volumen y consistencia:** Se evaluó la proporción de valores nulos, duplicados e inconsistencias por columna para determinar qué campos eran aptos para filtrado, agregación y visualización.
- **Separación de variables categóricas:** Las columnas con naturaleza categórica fueron identificadas y expuestas como dimensiones de filtrado, diferenciándolas de variables numéricas continuas utilizadas para métricas y KPIs.
- **Procesamiento en memoria por sesión:** Los DataFrames procesados se almacenan en un `SessionManager` en memoria, evitando reprocesamiento en cada request y manteniendo el estado de filtros aplicados durante la sesión del usuario.

---

## Uso de herramientas de IA

El desarrollo del proyecto se apoyó en **GitHub Copilot** utilizando el modelo **Claude Sonnet** (vía VS Code) para:

- Generación y refactorización de endpoints FastAPI.
- Asistencia en la escritura de lógica de transformación con Pandas.
- Revisión de estructuras de datos con Pydantic.
- Apoyo en decisiones de arquitectura de servicios y separación de capas.

El uso de IA permitió acelerar iteraciones de desarrollo manteniendo control explícito sobre la lógica de negocio y las decisiones de diseño.

---

## Limitaciones conocidas

- **Análisis geográfico incompleto:** La información geográfica disponible en el dataset se basa en claves numéricas de municipios y entidades federativas (`CVE_MUN`, `CVE_ENT`). Para construir visualizaciones de mapa funcionales se requiere una capa de interpretación externa (e.g., GeoJSON con geometrías por clave INEGI) que no fue provista en los datos originales.
- **Contaminación en catálogos:** Parte de los catálogos combinan valores numéricos categóricos con etiquetas textuales en un mismo campo, lo que dificulta la normalización automática y puede producir decodificaciones incorrectas o incompletas. Estos casos fueron tratados de forma defensiva pero no eliminados en su totalidad.
- **Sesiones en memoria:** El manejo de sesiones está implementado mediante un diccionario en memoria del proceso, lo que implica pérdida de estado ante reinicios del servidor y ausencia de soporte para entornos multi-worker o multi-instancia.
- **Sin persistencia de datos:** No existe una capa de base de datos; todos los datos procesados son volátiles y ligados al ciclo de vida del proceso.

---

## Qué mejoraría con más tiempo

- **Refactorización de la arquitectura de sesiones:** Migrar el `SessionManager` en memoria a una solución persistente y escalable, como **Redis** (para estado de sesión) o **PostgreSQL/PostGIS** (para persistencia de datos y consultas geoespaciales), habilitando soporte multi-worker con Uvicorn y despliegues en contenedores.
- **Integración de información geográfica:** Incorporar un servicio de resolución de claves INEGI a geometrías (GeoJSON), permitiendo análisis espacial real sobre municipios y entidades mediante librerías como `geopandas` o una integración con servicios de tiles.
- **Conexión a base de datos:** Reemplazar la carga de archivos CSV por una conexión directa a la fuente de datos mediante **SQLAlchemy** con soporte async (`asyncpg`), eliminando la dependencia de archivos temporales y mejorando el rendimiento en datasets grandes.
- **Mejora del pipeline de calidad de datos:** Implementar validaciones más robustas sobre los catálogos para detectar y normalizar automáticamente entradas híbridas (numérico + etiqueta), aumentando la confiabilidad de la decodificación.
- **Autenticación y autorización:** Agregar una capa de seguridad mediante JWT o sesiones firmadas para proteger los endpoints y asociar correctamente las sesiones a usuarios autenticados.
- **Testing automatizado:** Incorporar una suite de pruebas con `pytest` y `httpx` para cubrir los servicios críticos de procesamiento y los endpoints principales.
