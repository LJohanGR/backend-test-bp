# Backend Integration Guide — Dashboard de Avalúos

> Documento para el equipo backend. Describe los endpoints existentes y los **dos nuevos endpoints requeridos** para que la integración completa funcione.

---

## 1. Configuración general

| Variable | Valor default |
|---|---|
| `VITE_API_URL` | `http://localhost:8000` |

El frontend lee `VITE_API_URL` de `.env.local`. Todas las rutas son relativas a esa base.

### CORS

El backend debe aceptar requests desde el origen del frontend (e.g. `http://localhost:5173`).  
Headers requeridos:

```
Access-Control-Allow-Origin: http://localhost:5173
Access-Control-Allow-Methods: GET, POST, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

---

## 2. Sesión — flujo completo

```
1. POST /upload            → crea sesión, devuelve session_id
2. GET  /session/{id}      → confirma que la sesión sigue activa
3. [cualquier endpoint de sesión con session_id]
4. DELETE /session/{id}    → limpia recursos al cerrar / cargar nuevo archivo
```

---

## 3. Endpoints existentes (ya implementados)

### `GET /health`
Comprobación de disponibilidad del backend.  
**Response:** `{ "status": "ok" }` — HTTP 200

---

### `POST /upload`
Sube un archivo CSV y crea una nueva sesión.

**Request:** `multipart/form-data` con campo `file` (CSV).

**Response `200`:**
```json
{
  "session_id": "abc123",
  "total_rows": 18420,
  "total_columns": 42,
  "column_names": ["SIGLAS", "CLASE", "GRUPO", "VALOR CONCLUIDO", "LATITUD", "LONGITUD", "..."],
  "numeric_columns": ["VALOR CONCLUIDO", "SUP CONSTRUIDA", "$M2 SV", "LATITUD", "LONGITUD"],
  "categorical_columns": ["SIGLAS", "CLASE", "GRUPO", "ENTIDAD"],
  "datetime_columns": ["FECHA AVALUO"],
  "null_summary": { "LATITUD": 142, "LONGITUD": 142 },
  "catalogs": {
    "CLASE": { "1": "Habitacional", "2": "Comercial", "3": "Industrial" },
    "GRUPO": { "1": "Terreno", "2": "Construcción" }
  }
}
```

---

### `GET /session/{session_id}`
Devuelve el perfil de la sesión activa.  
**Response:** igual a `POST /upload`.

---

### `DELETE /session/{session_id}`
Elimina la sesión y libera recursos del servidor.  
**Response:** HTTP 204 sin cuerpo.

---

### `GET /session/{session_id}/metrics`
Estadísticas descriptivas del dataset (sin filtros).

**Response:**
```json
{
  "session_id": "abc123",
  "total_rows": 18420,
  "total_columns": 42,
  "null_summary": { "LATITUD": 142 },
  "numeric_columns": {
    "VALOR CONCLUIDO": { "min": 120000, "max": 85000000, "mean": 2400000, "std": 1800000 }
  },
  "categorical_columns": {
    "SIGLAS": { "unique": 18, "top": "Inst 1", "freq": 3200 }
  },
  "datetime_columns": {}
}
```

---

### `POST /session/{session_id}/filter`
Filtra el dataset y devuelve filas paginadas.

**Request body:**
```json
{
  "filters": {
    "SIGLAS": ["Inst. 1", "Inst. 2"],
    "CLASE": ["3"],
    "VALOR CONCLUIDO": { "min": 500000, "max": 5000000 },
    "$M2 SV": { "min": 10000 }
  },
  "search": "guadalajara",
  "limit": 100,
  "offset": 0
}
```

> **Formato de `filters`:**  
> - Columna categórica → `string[]` de valores permitidos  
> - Columna numérica  → `{ "min"?: number, "max"?: number }`  
> - `search` → texto libre aplicado contra todas las columnas de texto (opcional)

**Response `200`:**
```json
{
  "session_id": "abc123",
  "total_matching": 412,
  "returned": 100,
  "offset": 0,
  "data": [
    { "SIGLAS": "Inst. 1", "CLASE": "3", "VALOR CONCLUIDO": 1500000, "LATITUD": 20.65, "LONGITUD": -103.35, "..." : "..." }
  ]
}
```

---

### `GET /session/{session_id}/map-data`
Devuelve coordenadas para el mapa (sin filtros, snapshot completo de la sesión).

**Query params:**

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `lat_col` | string | `LATITUD` | Nombre de la columna de latitud |
| `lon_col` | string | `LONGITUD` | Nombre de la columna de longitud |
| `limit` | int | 5000 | Máximo de features a devolver |

**Response `200`:**
```json
{
  "session_id": "abc123",
  "lat_column": "LATITUD",
  "lon_column": "LONGITUD",
  "features": [
    { "SIGLAS": "Inst. 1", "CLASE": "3", "VALOR CONCLUIDO": 1500000, "LATITUD": 20.65, "LONGITUD": -103.35 }
  ]
}
```

> El frontend usa `lat_column` y `lon_column` del response para extraer las coordenadas de cada feature.

---

### `GET /catalogs`
Catálogos globales de código→etiqueta, independiente de sesión.

**Response:**
```json
{
  "CLASE": { "1": "Habitacional", "2": "Comercial", "3": "Industrial" },
  "GRUPO": { "1": "Terreno", "2": "Construcción" },
  "ENTIDAD": { "01": "Aguascalientes", "09": "Ciudad de México" }
}
```

---

## 4. Endpoints nuevos — requeridos para integración completa

### ⭐ `POST /session/{session_id}/charts`

**Propósito:** Devolver datos pre-agregados para las cuatro gráficas del dashboard.  
El frontend lo llama cada vez que cambian los filtros (debounce de 400 ms).

**Request body:** mismo formato que `/filter`:
```json
{
  "filters": {
    "SIGLAS": ["..."],
    "VALOR CONCLUIDO": { "min": 500000 }
  },
  "search": "",
  "limit": 5000,
  "offset": 0
}
```

**Response `200`:**
```json
{
  "session_id": "abc123",
  "total_matching": 412,
  "by_institution": [
    { "name": "Inst. 1 ",    "count": 3200, "avg_valor": 2100000 },
    { "name": "Inst. 2", "count": 2800, "avg_valor": 1850000 }
  ],
  "by_clase": [
    { "code": "1", "label": "Habitacional", "avg_valor": 1500000, "count": 8200 },
    { "code": "2", "label": "Comercial",    "avg_valor": 4200000, "count": 3100 },
    { "code": "3", "label": "Industrial",   "avg_valor": 8500000, "count": 1200 }
  ],
  "by_grupo": [
    { "code": "1", "label": "Terreno",       "avg_m2": 12000, "count": 9400 },
    { "code": "2", "label": "Construcción",  "avg_m2": 18500, "count": 9020 }
  ],
  "scatter": [
    { "x": 120.5, "y": 1500000, "clase": "1" },
    { "x": 85.0,  "y": 980000,  "clase": "2" }
  ]
}
```

> - `by_institution` — máx. 12 instituciones (ordenadas por `count` desc).  
> - `by_clase`, `by_grupo` — todas las categorías presentes en los datos filtrados.  
> - `scatter` — muestra aleatoria máx. **500 puntos** de SUP CONSTRUIDA vs VALOR CONCLUIDO, con `clase` para colorear.
> - `total_matching` — total de registros que cumplen los filtros (útil para los KPI cards).

---

### ⭐ `POST /session/{session_id}/map-data` _(variante con filtros)_

El endpoint `GET /map-data` existente devuelve toda la sesión sin filtrar.  
Se necesita una variante `POST` que acepte el mismo `FilterBody` y devuelva solo los puntos que coincidan.

**Request body:** mismo formato que `/filter`.

**Response `200`:** mismo formato que `GET /map-data`:
```json
{
  "session_id": "abc123",
  "lat_column": "LATITUD",
  "lon_column": "LONGITUD",
  "features": [
    { "SIGLAS": "Inst. 1", "CLASE": "3", "LATITUD": 20.65, "LONGITUD": -103.35, "VALOR CONCLUIDO": 1500000 }
  ]
}
```

> El frontend envía `limit: 5000` en el body. El backend puede aplicar su propio límite si lo considera necesario.

---

## 5. Contrato de tipos — resumen

### `FilterBody`
```typescript
interface FilterBody {
  filters: {
    [column: string]:
      | string[]                           // categórico: valores permitidos
      | { min?: number; max?: number };    // numérico: rango
  };
  search?: string;   // búsqueda libre (opcional)
  limit: number;     // default: 5000 para charts/map, 100 para tabla
  offset: number;    // paginación para /filter, siempre 0 para charts/map
}
```

### `ChartsResponse`
```typescript
interface ChartsResponse {
  session_id:     string;
  total_matching: number;
  by_institution: { name: string; count: number; avg_valor: number }[];
  by_clase:       { code: string; label: string; avg_valor: number; count: number }[];
  by_grupo:       { code: string; label: string; avg_m2: number;    count: number }[];
  scatter:        { x: number; y: number; clase: string }[];  // max 500
}
```

### `MapDataResponse`
```typescript
interface MapDataResponse {
  session_id:  string;
  lat_column:  string;   // nombre de la columna usada para latitud
  lon_column:  string;   // nombre de la columna usada para longitud
  features:    Record<string, unknown>[];  // filas con todas las columnas
}
```

---

## 6. Flujo de datos en el frontend

```
Usuario cambia filtro
       ↓ (debounce 400ms)
useBackendData
   ├── POST /session/{id}/charts   → chartData  → ChartPanel (byInstitution, byClase, byGrupo, scatter)
   └── GET  /session/{id}/map-data → mapData    → MapView   (features con lat/lon dinámico)

Sidebar → useCSVData (client-side)
   └── filteredRows → DataTable + SummaryCards  (feedback inmediato sin espera al backend)
```

- Los filtros del sidebar generan `filteredRows` en el cliente **y** disparan `useBackendData` al backend en paralelo.
- `DataTable` y `SummaryCards` usan `filteredRows` local (respuesta inmediata).
- `ChartPanel` y `MapView` usan los datos pre-calculados del backend (respetan la misma lógica de filtrado que aplique el servidor).

---

## 7. Prioridad de implementación

| # | Endpoint | Bloqueante para |
|---|---|---|
| 1 | `POST /session/{id}/charts` | Gráficas con datos reales |
| 2 | `POST /session/{id}/map-data` | Mapa filtrado |
| 3 | `GET /catalogs` | Ya implementado — verificar que responde |
| 4 | `POST /upload` respuesta con `catalogs` | Autocompletado de filtros |
