# 🚗 Sistema de Gestión e Inteligencia de Datos — Concesionario

> **Pipeline completo de Big Data** para un concesionario automotriz: desde la extracción de datos crudos en Excel hasta reportes analíticos, predicciones de precios con Machine Learning y un dashboard HTML interactivo.

---

## 📋 Tabla de Contenidos

1. [Descripción General](#descripción-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Estructura del Proyecto](#estructura-del-proyecto)
4. [Modelo Estrella (Data Warehouse)](#modelo-estrella-data-warehouse)
5. [KPIs del Proyecto](#-kpis-del-proyecto)
6. [Módulo de Predicciones (ML)](#-módulo-de-predicciones-ml)
7. [Reportes Generados](#-reportes-generados)
8. [Tecnologías y Dependencias](#tecnologías-y-dependencias)
9. [Instalación y Configuración](#instalación-y-configuración)
10. [Uso del Sistema](#uso-del-sistema)
11. [Calidad de Datos](#-calidad-de-datos)
12. [Configuración Avanzada](#configuración-avanzada)

---

## Descripción General

Este proyecto implementa un **sistema end-to-end de Business Intelligence** para un concesionario automotriz. Cubre las tres etapas clásicas de un pipeline de datos:

| Etapa                 | Descripción                                                                        |
| --------------------- | ---------------------------------------------------------------------------------- |
| **ETL**               | Extracción desde Excel, transformación a modelo estrella y carga en SQLite         |
| **Reportes & KPIs**   | Generación automática de gráficas, dashboards HTML y métricas clave                |
| **Predicciones (ML)** | Predicción de precios, proyección de ventas futuras y segmentación RFM de clientes |

El sistema está diseñado siguiendo los principios **SOLID**, con módulos desacoplados, logging integrado y validación automática de integridad referencial.

---

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SISTEMA COMPLETO                             │
│                   run_complete_system.py                            │
└────────┬──────────────────┬───────────────────┬────────────────────┘
         │                  │                   │
    FASE 1: ETL        FASE 2: REPORTES    FASE 3: PREDICCIONES
         │                  │                   │
    ┌────▼────┐        ┌────▼────┐         ┌────▼────────┐
    │extract  │        │generate │         │VehiclePrice │
    │transform│        │reports  │         │Predictor    │
    │load     │        │kpis     │         │CustomerSeg  │
    └────┬────┘        └────┬────┘         └────┬────────┘
         │                  │                   │
    ┌────▼────────────────────────────────────────────┐
    │           SQLite - concesionario.db              │
    │  (Modelo Estrella: dim_* + hecho_*)              │
    └──────────────────────────────────────────────────┘
```

### Flujo de Datos

```
datos_concesionario_raw.xlsx
           │
           ▼
   [EXTRACCIÓN] extract.py
           │ DataFrame crudo
           ▼
   [TRANSFORMACIÓN] transform.py
    ├── Normalización de texto
    ├── Limpieza de fechas, precios, IDs
    ├── Mapeo de ciudades / estados
    └── Construcción del modelo estrella
           │ 10 tablas normalizadas
           ▼
   [CARGA] load.py → concesionario.db (SQLite)
           │
           ├──▶ [KPIs] kpi_calculator.py
           ├──▶ [REPORTES] generate_reports.py → reports/
           └──▶ [PREDICCIONES] vehicle_price_predictor.py → models/
```

---

## Estructura del Proyecto

```
proyecto_big_data/
│
├── proyecto_big_data/              # Paquete principal
│   ├── run_complete_system.py      # 🚀 Punto de entrada único del sistema
│   │
│   ├── config/
│   │   └── config.yaml             # Configuración de rutas, validación y logging
│   │
│   ├── data/
│   │   ├── raw/                    # Datos originales (Excel crudo)
│   │   └── processed/              # Base de datos SQLite generada
│   │       └── concesionario.db
│   │
│   ├── models/                     # Modelos ML serializados (.pkl) + gráficas
│   │   ├── vehicle_price_model_current.pkl
│   │   ├── preprocessors_current.pkl
│   │   ├── model_results_*.json
│   │   ├── customer_segments.csv
│   │   ├── customer_segments.png
│   │   ├── feature_importance.png
│   │   └── sales_prediction.png
│   │
│   ├── reports/                    # Reportes generados automáticamente
│   │   └── report_YYYYMMDD_HHMMSS/
│   │       ├── dashboard.html      # Dashboard interactivo HTML
│   │       ├── resumen.json        # Métricas y KPIs en JSON
│   │       ├── ventas_por_tiempo.png
│   │       ├── analisis_financiero.png
│   │       ├── top_clientes.png
│   │       ├── rendimiento_vendedores.png
│   │       ├── mantenimiento_por_tipo.png
│   │       ├── kpi_rotacion_quarterly.png
│   │       ├── kpi_retencion_quarterly.png
│   │       ├── kpi_margen_promedio_quarterly.png
│   │       └── kpi_dias_inventario_quarterly.png
│   │
│   ├── logs/                       # Archivos de log del sistema
│   │
│   └── src/                        # Código fuente principal
│       ├── run_etl.py              # Orquestador del proceso ETL
│       │
│       ├── etl/
│       │   ├── extract.py          # Lectura del archivo Excel crudo
│       │   ├── transform.py        # DataTransformer → modelo estrella
│       │   └── load.py             # Carga en SQLite con validación
│       │
│       ├── kpis/
│       │   └── kpi_calculator.py   # KPICalculator: cálculo de métricas clave
│       │
│       ├── predictions/
│       │   └── vehicle_price_predictor.py  # ML: precios, ventas y segmentación RFM
│       │
│       ├── reports/
│       │   └── generate_reports.py # ReportGenerator: gráficas y dashboard HTML
│       │
│       ├── validation/
│       │   └── data_quality.py     # Validación de calidad de datos
│       │
│       └── database/
│           └── connection.py       # Gestor de conexión SQLite
│
├── requirements.txt                # Dependencias Python
└── README.md                       # Este archivo
```

---

## Modelo Estrella (Data Warehouse)

El sistema implementa un **esquema en estrella** clásico optimizado para consultas analíticas (OLAP). A continuación se detalla cada tabla con sus atributos, tipos de datos y restricciones.

---

### 📅 `dim_tiempo` — Dimensión de Tiempo

| Columna          | Tipo      | Restricción  | Descripción                                              |
| ---------------- | --------- | ------------ | -------------------------------------------------------- |
| `id_tiempo`      | `INTEGER` | PK, NOT NULL | Clave en formato `YYYYMMDD` (ej. `20231215`)             |
| `fecha_completa` | `DATE`    | NOT NULL     | Fecha completa en formato `YYYY-MM-DD`                   |
| `año`            | `INTEGER` | NOT NULL     | Año de la fecha (ej. `2023`)                             |
| `mes`            | `INTEGER` | NOT NULL     | Mes numérico del 1 al 12                                 |
| `nombre_mes`     | `TEXT`    | NOT NULL     | Nombre del mes en español (ej. `Enero`)                  |
| `trimestre`      | `INTEGER` | NOT NULL     | Trimestre del 1 al 4                                     |
| `semana`         | `INTEGER` | NOT NULL     | Número de semana ISO del año (1–53)                      |
| `dia`            | `INTEGER` | NOT NULL     | Día del mes del 1 al 31                                  |
| `dia_semana`     | `TEXT`    | NOT NULL     | Nombre del día en español (ej. `Lunes`)                  |
| `es_fin_semana`  | `INTEGER` | NOT NULL     | Indicador binario: `1` = sábado/domingo, `0` = día hábil |

---

### 👤 `dim_cliente` — Dimensión de Clientes

| Columna        | Tipo      | Restricción            | Descripción                                                          |
| -------------- | --------- | ---------------------- | -------------------------------------------------------------------- |
| `id_cliente`   | `FLOAT`   | PK, NOT NULL, > 0      | Identificador único del cliente                                      |
| `nombre`       | `TEXT`    | NOT NULL               | Nombre completo normalizado (lowercase, sin tildes)                  |
| `edad`         | `INTEGER` | NOT NULL, entre 18–100 | Edad del cliente; default `30` si no se especifica                   |
| `genero`       | `TEXT`    | NOT NULL               | Género del cliente: `'M'` (Masculino) o `'F'` (Femenino)             |
| `tipo_cliente` | `TEXT`    | NOT NULL               | Categoría: `nuevo`, `recurrente`, `vip`, `empresarial`, `potencial`  |
| `email`        | `TEXT`    | NOT NULL               | Correo electrónico validado; `email_invalido` si no cumple el patrón |
| `id_ciudad`    | `FLOAT`   | FK → `dim_ciudad`      | ID de la ciudad de residencia del cliente                            |

---

### 🚗 `dim_vehiculo` — Dimensión de Vehículos

| Columna            | Tipo      | Restricción               | Descripción                                                                      |
| ------------------ | --------- | ------------------------- | -------------------------------------------------------------------------------- |
| `id_vehiculo`      | `FLOAT`   | PK, NOT NULL, > 0         | Identificador único del vehículo                                                 |
| `marca`            | `TEXT`    | NOT NULL                  | Marca del vehículo (ej. `toyota`, `chevrolet`)                                   |
| `modelo`           | `TEXT`    | NOT NULL                  | Modelo del vehículo (ej. `corolla`)                                              |
| `tipo`             | `TEXT`    | NOT NULL                  | Tipo de carrocería (ej. `sedan`, `suv`, `camioneta`)                             |
| `año_modelo`       | `INTEGER` | NOT NULL, entre 2012–2025 | Año de fabricación del vehículo; default `2020`                                  |
| `cilindraje`       | `INTEGER` | NOT NULL, entre 600–6000  | Cilindraje del motor en cc; default `1600`                                       |
| `tipo_combustible` | `TEXT`    | NOT NULL                  | Tipo de combustible: `Gasolina`, `Diesel`, `Híbrido`, `Eléctrico`, `Gas Natural` |
| `color`            | `TEXT`    | NOT NULL                  | Color del vehículo (ej. `blanco`, `negro`)                                       |

---

### 🏢 `dim_sucursal` — Dimensión de Sucursales

| Columna       | Tipo    | Restricción       | Descripción                                                |
| ------------- | ------- | ----------------- | ---------------------------------------------------------- |
| `id_sucursal` | `FLOAT` | PK, NOT NULL, > 0 | Identificador único de la sucursal                         |
| `nombre`      | `TEXT`  | NOT NULL          | Nombre de la sucursal normalizado                          |
| `id_ciudad`   | `FLOAT` | FK → `dim_ciudad` | ID de la ciudad donde opera la sucursal                    |
| `tamaño`      | `TEXT`  | —                 | Tamaño de la sucursal (ej. `pequeña`, `mediana`, `grande`) |
| `zona`        | `TEXT`  | —                 | Zona geográfica (ej. `norte`, `sur`, `centro`)             |

---

### 🧑‍💼 `dim_vendedor` — Dimensión de Vendedores

| Columna            | Tipo      | Restricción          | Descripción                             |
| ------------------ | --------- | -------------------- | --------------------------------------- |
| `id_vendedor`      | `FLOAT`   | PK, NOT NULL, > 0    | Identificador único del vendedor        |
| `nombre`           | `TEXT`    | NOT NULL             | Nombre completo normalizado             |
| `experiencia_años` | `INTEGER` | NOT NULL, entre 0–40 | Años de experiencia; default `0`        |
| `id_sucursal`      | `FLOAT`   | FK → `dim_sucursal`  | Sucursal a la que pertenece el vendedor |

---

### 💳 `dim_tipoPago` — Dimensión de Tipos de Pago

| Columna               | Tipo    | Restricción           | Descripción                                               |
| --------------------- | ------- | --------------------- | --------------------------------------------------------- |
| `id_tipo_pago`        | `FLOAT` | PK, NOT NULL, > 0     | Identificador único del tipo de pago                      |
| `tipo_pago`           | `TEXT`  | NOT NULL              | Modalidad de pago: `contado`, `credito`, `leasing`        |
| `entidad_financiera`  | `TEXT`  | —                     | Nombre de la entidad financiera (si aplica)               |
| `plazo_meses`         | `FLOAT` | NOT NULL, default `0` | Plazo del crédito en meses                                |
| `tasa_interes`        | `FLOAT` | NOT NULL, default `0` | Tasa de interés anual en porcentaje                       |
| `requiere_aprobacion` | `FLOAT` | NOT NULL, default `0` | Indicador: `1` = requiere aprobación crediticia, `0` = no |

---

### 🔧 `dim_tipoMantenimiento` — Dimensión de Tipos de Mantenimiento

| Columna                 | Tipo      | Restricción           | Descripción                                          |
| ----------------------- | --------- | --------------------- | ---------------------------------------------------- |
| `id_tipo_mantenimiento` | `FLOAT`   | PK, NOT NULL, > 0     | Identificador único del tipo de mantenimiento        |
| `nombre_tipo`           | `TEXT`    | NOT NULL              | Nombre del servicio (ej. `preventivo`, `correctivo`) |
| `descripcion`           | `TEXT`    | —                     | Descripción detallada del servicio                   |
| `incluye_garantia`      | `INTEGER` | NOT NULL, default `0` | `1` = incluye garantía, `0` = no                     |
| `meses_garantia`        | `INTEGER` | NOT NULL, default `0` | Duración de la garantía en meses                     |
| `kilometros_garantia`   | `INTEGER` | NOT NULL, default `0` | Kilometraje máximo cubierto por la garantía          |

---

### 🌆 `dim_ciudad` — Dimensión de Ciudades

| Columna         | Tipo    | Restricción       | Descripción                                            |
| --------------- | ------- | ----------------- | ------------------------------------------------------ |
| `id_ciudad`     | `FLOAT` | PK, NOT NULL, > 0 | Identificador único de la ciudad                       |
| `nombre_ciudad` | `TEXT`  | NOT NULL          | Nombre oficial de la ciudad (ej. `Bogotá`, `Medellín`) |
| `departamento`  | `TEXT`  | NOT NULL          | Departamento o estado al que pertenece                 |
| `region`        | `TEXT`  | NOT NULL          | Región geográfica (ej. `andina`, `caribe`)             |

---

### 🛒 `hecho_ventas` — Tabla de Hechos de Ventas

| Columna             | Tipo      | Restricción                        | Descripción                                    |
| ------------------- | --------- | ---------------------------------- | ---------------------------------------------- |
| `id_venta`          | `TEXT`    | PK, NOT NULL                       | Identificador único de la transacción de venta |
| `id_tiempo`         | `INTEGER` | FK → `dim_tiempo`, NOT NULL        | Fecha de la venta en formato `YYYYMMDD`        |
| `id_cliente`        | `FLOAT`   | FK → `dim_cliente`, NOT NULL       | Cliente que realizó la compra                  |
| `id_vehiculo`       | `FLOAT`   | FK → `dim_vehiculo`, NOT NULL      | Vehículo vendido                               |
| `id_vendedor`       | `FLOAT`   | FK → `dim_vendedor`                | Vendedor que gestionó la venta                 |
| `id_sucursal`       | `FLOAT`   | FK → `dim_sucursal`                | Sucursal donde ocurrió la venta                |
| `id_tipo_pago`      | `FLOAT`   | FK → `dim_tipoPago`                | Modalidad de pago utilizada                    |
| `cantidad`          | `FLOAT`   | NOT NULL, ≥ 0, default `0`         | Número de unidades vendidas                    |
| `precio_venta`      | `FLOAT`   | NOT NULL, entre 0–500.000          | Precio de venta final en USD                   |
| `costo_vehiculo`    | `FLOAT`   | NOT NULL, entre 0–500.000          | Costo de adquisición del vehículo en USD       |
| `descuento`         | `FLOAT`   | NOT NULL, entre 0–100, default `0` | Descuento aplicado en porcentaje (%)           |
| `precio_neto`       | `FLOAT`   | Calculado                          | `precio_venta × (1 − descuento / 100)`         |
| `margen_ganancia`   | `FLOAT`   | Calculado                          | `precio_venta − costo_vehiculo`                |
| `financiado`        | `INTEGER` | NOT NULL, default `0`              | `1` = venta financiada, `0` = pago directo     |
| `comision_vendedor` | `FLOAT`   | —                                  | Comisión percibida por el vendedor en USD      |

---

### 🛠️ `hecho_mantenimiento` — Tabla de Hechos de Mantenimiento

| Columna                 | Tipo      | Restricción                   | Descripción                                      |
| ----------------------- | --------- | ----------------------------- | ------------------------------------------------ |
| `id_tiempo`             | `INTEGER` | FK → `dim_tiempo`, NOT NULL   | Fecha del servicio en formato `YYYYMMDD`         |
| `id_cliente`            | `FLOAT`   | FK → `dim_cliente`, NOT NULL  | Cliente que solicitó el servicio                 |
| `id_vehiculo`           | `FLOAT`   | FK → `dim_vehiculo`, NOT NULL | Vehículo al que se realizó el mantenimiento      |
| `id_sucursal`           | `FLOAT`   | FK → `dim_sucursal`           | Sucursal donde se realizó el servicio            |
| `id_tipo_mantenimiento` | `FLOAT`   | FK → `dim_tipoMantenimiento`  | Tipo de mantenimiento realizado                  |
| `costo_servicio`        | `FLOAT`   | entre 0–500.000               | Costo de la mano de obra en USD                  |
| `costo_repuestos`       | `FLOAT`   | entre 0–500.000               | Costo de los repuestos utilizados en USD         |
| `costo_total`           | `FLOAT`   | Calculado                     | `costo_servicio + costo_repuestos`               |
| `repuestos_usados`      | `FLOAT`   | NOT NULL, ≥ 0, default `0`    | Cantidad de repuestos utilizados                 |
| `horas_taller`          | `FLOAT`   | —                             | Horas de trabajo invertidas en el servicio       |
| `kilometraje_vehiculo`  | `FLOAT`   | —                             | Kilometraje del vehículo al momento del servicio |

---

## 📊 KPIs del Proyecto

El módulo `kpi_calculator.py` implementa **4 KPIs principales**, cada uno con su fórmula exacta, propósito estratégico y aplicación táctica.

---

### 1. 🔄 Rotación de Inventario

**Definición:** Mide qué porcentaje del catálogo total de vehículos ha sido efectivamente vendido.

**Fórmula:**

```
Rotación de Inventario (%) = (Total unidades vendidas / Total vehículos en catálogo) × 100
```

**Implementación SQL:**

```sql
-- Numerador: unidades vendidas
SELECT SUM(COALESCE(cantidad, 1)) AS total_unidades FROM hecho_ventas;

-- Denominador: total de vehículos registrados
SELECT COUNT(*) AS total FROM dim_vehiculo;
```

**¿Por qué es importante?**

- Un valor **alto** (> 70%) indica que el inventario se renueva con rapidez, reduciendo costos de almacenamiento y capital inmovilizado.
- Un valor **bajo** (< 30%) puede señalar sobrestock de modelos poco demandados o problemas de pricing.

**¿Cómo ayuda a tomar estrategias?**

| Escenario                          | Acción Estratégica                                                          |
| ---------------------------------- | --------------------------------------------------------------------------- |
| Rotación baja en sedanes de lujo   | Revisar precios, aplicar descuentos o mover stock entre sucursales          |
| Rotación alta en SUVs compactas    | Aumentar los pedidos de ese segmento al proveedor                           |
| Rotación desigual entre sucursales | Redistribuir inventario desde sucursales saturadas hacia las más vendedoras |

---

### 2. 👥 Índice de Retención de Clientes

**Definición:** Porcentaje de clientes que han realizado más de una compra sobre el total de clientes únicos registrados.

**Fórmula:**

```
Índice de Retención (%) = (Clientes con más de 1 compra / Total clientes únicos) × 100
```

**Implementación SQL:**

```sql
-- Clientes recurrentes
SELECT COUNT(*) FROM (
    SELECT id_cliente, COUNT(*) AS num_compras
    FROM hecho_ventas
    WHERE id_cliente IS NOT NULL
    GROUP BY id_cliente
    HAVING COUNT(*) > 1
);

-- Total de clientes únicos
SELECT COUNT(DISTINCT id_cliente)
FROM hecho_ventas
WHERE id_cliente IS NOT NULL;
```

**¿Por qué es importante?**

- Adquirir un nuevo cliente cuesta **5–7 veces más** que retener uno existente.
- Un índice de retención alto refleja satisfacción con el producto y el servicio posventa.
- Es un predictor confiable de **ingresos futuros estables**.

**¿Cómo ayuda a tomar estrategias?**

| Escenario                                          | Acción Estratégica                                                            |
| -------------------------------------------------- | ----------------------------------------------------------------------------- |
| Retención < 20%                                    | Implementar programa de fidelización, seguimiento post-venta y CRM activo     |
| Retención estancada                                | Analizar el tiempo entre compras y enviar ofertas de servicio o mantenimiento |
| Segmento VIP con alta retención                    | Crear referral programs para convertirlos en embajadores de marca             |
| Clientes que no regresan tras primer mantenimiento | Diseñar paquetes de mantenimiento preventivo con descuento                    |

---

### 3. 📅 Días Promedio en Inventario

**Definición:** Número promedio de días que transcurren entre eventos de venta consecutivos del mismo vehículo. Es una aproximación al tiempo que un vehículo permanece disponible antes de venderse.

**Fórmula:**

```
Días Promedio en Inventario = Promedio(diferencia en días entre ventas consecutivas por vehículo)
```

**Implementación (Python + SQL):**

```python
# Se extraen las fechas de ventas por vehículo, ordenadas cronológicamente
df_dates = query("""
    SELECT hv.id_vehiculo, t.fecha_completa
    FROM hecho_ventas hv
    JOIN dim_tiempo t ON hv.id_tiempo = t.id_tiempo
    ORDER BY hv.id_vehiculo, t.fecha_completa
""")

# Diferencia entre ventas consecutivas del mismo vehículo
df_dates['diff_days'] = df_dates.groupby('id_vehiculo')['fecha_completa'].diff().dt.days

resultado = df_dates['diff_days'].mean()
```

**¿Por qué es importante?**

- Permite estimar el **ciclo de rotación real** del inventario.
- Un promedio alto (> 90 días) puede indicar problemas de liquidez y costos financieros elevados.
- Facilita la planificación de **órdenes de reposición** con mayor precisión.

**¿Cómo ayuda a tomar estrategias?**

| Escenario                                    | Acción Estratégica                                              |
| -------------------------------------------- | --------------------------------------------------------------- |
| Vehículos con > 120 días sin venta           | Lanzar campañas específicas de precio o financiamiento especial |
| Días en inventario aumentan en ciertos meses | Ajustar compras estacionales anticipando caídas en la demanda   |
| Promedio inferior a 30 días en cierta marca  | Priorizar ese fabricante en las negociaciones de cuota          |
| Diferencias por sucursal                     | Reasignar stock hacia sucursales con menor tiempo de venta      |

---

### 4. 💰 Margen Promedio por Venta

**Definición:** Rentabilidad neta media por cada transacción de venta, calculada como la diferencia entre precio de venta y costo del vehículo.

**Fórmula:**

```
Margen Promedio por Venta = AVG(precio_venta − costo_vehiculo)
                         = AVG(margen_ganancia)
```

**Implementación SQL:**

```sql
SELECT AVG(COALESCE(margen_ganancia, 0))
FROM hecho_ventas;

-- margen_ganancia se calcula en la fase ETL como:
-- margen_ganancia = precio_venta - costo_vehiculo
```

**¿Por qué es importante?**

- Es el indicador directo de la **salud financiera** del negocio por operación.
- Permite comparar la rentabilidad entre marcas, modelos, vendedores y sucursales.
- Un margen negativo o muy bajo puede revelar problemas de pricing o descuentos excesivos.

**¿Cómo ayuda a tomar estrategias?**

| Escenario                                         | Acción Estratégica                                                            |
| ------------------------------------------------- | ----------------------------------------------------------------------------- |
| Margen promedio decreciente trimestre a trimestre | Revisar la política de descuentos y comisiones de vendedores                  |
| Alta varianza en el margen entre vendedores       | Implementar floor prices mínimos no negociables                               |
| Margen bajo en vehículos financiados              | Renegociar condiciones con la entidad financiera o agregar cargos por gestión |
| Modelos con margen consistentemente alto          | Asignarles mayor espacio en showroom y fuerza de ventas dedicada              |

---

### 5. 📈 KPIs Trimestrales (Vista Histórica)

Adicionalmente, el sistema genera una **vista trimestral** de todos los KPIs anteriores, permitiendo analizar tendencias en el tiempo.

**Período:** Agrupación por `año-trimestre` (ej. `2023-T1`, `2023-T2`).

**Métricas calculadas por trimestre:**

| KPI                        | Fórmula Trimestral                                                                            |
| -------------------------- | --------------------------------------------------------------------------------------------- |
| Rotación de inventario (%) | `(Unidades vendidas en trimestre / Total vehículos) × 100`                                    |
| Retención de clientes (%)  | `(Clientes del trimestre actual que ya compraron antes / Total clientes del trimestre) × 100` |
| Margen promedio            | `AVG(margen_ganancia)` por trimestre                                                          |
| Días en inventario         | `AVG(días entre ventas consecutivas)` por vehículo en el trimestre                            |

**Aplicación estratégica:** Permite identificar **estacionalidad**, evaluar el impacto de campañas comerciales y planificar recursos para períodos históricos de alta o baja demanda.

---

## 🤖 Módulo de Predicciones (ML)

### 1. Predicción de Precio de Vehículos

El sistema entrena y compara **3 modelos de regresión** para predecir el precio de venta óptimo:

| Modelo                | Descripción                                      |
| --------------------- | ------------------------------------------------ |
| **Regresión Lineal**  | Modelo base, interpretable                       |
| **Random Forest**     | Ensemble de árboles, captura no linealidades     |
| **Gradient Boosting** | Boosting secuencial, generalmente el más preciso |

**Features utilizadas:** marca, modelo, tipo, año, cilindraje, tipo de combustible, color, costo base, descuento, financiado, año/mes de venta, edad y género del cliente, tamaño y zona de la sucursal.

**Métricas de evaluación:** MAE, RMSE, R², Cross-Validation R² (5-fold).

**Aplicación estratégica:**

- Fijar precios de lista competitivos basados en datos históricos reales.
- Detectar vehículos subvalorados o sobrevalorados en el inventario actual.
- Apoyar negociaciones en tiempo real con clientes.

---

### 2. Predicción de Ventas Futuras

Proyección de ventas para los próximos **N meses** (default: 6) basada en el promedio de los últimos 3 meses con una tasa de crecimiento asumida del **2% mensual**.

**Output:** número de ventas predichas e ingresos estimados por mes, más gráfica de línea histórica + proyección.

---

### 3. Segmentación RFM de Clientes

Clasifica a cada cliente usando el modelo **RFM (Recencia, Frecuencia, Valor Monetario)**:

| Dimensión     | Definición                  |
| ------------- | --------------------------- |
| **Recency**   | Días desde la última compra |
| **Frequency** | Número total de compras     |
| **Monetary**  | Valor total gastado         |

**Segmentos generados:**

| Segmento            | Rango RFM Score | Estrategia Recomendada                                    |
| ------------------- | --------------- | --------------------------------------------------------- |
| 🏆 **Campeones**    | ≥ 13            | Retener con beneficios exclusivos VIP, referral programs  |
| ⭐ **Leales**       | 10–12           | Upselling de modelos premium, membresías de mantenimiento |
| 🌱 **Prometedores** | 7–9             | Incentivar segunda compra con ofertas personalizadas      |
| 🎯 **Potenciales**  | 4–6             | Campañas de nurturing, encuestas de satisfacción          |
| ⚠️ **En Riesgo**    | < 4             | Campañas de reactivación urgente, descuentos especiales   |

---

## 📈 Reportes Generados

Cada ejecución genera automáticamente una carpeta `reports/report_TIMESTAMP/` con:

| Archivo                             | Contenido                                                     |
| ----------------------------------- | ------------------------------------------------------------- |
| `dashboard.html`                    | Dashboard interactivo con KPIs dinámicos cargados desde JSON  |
| `resumen.json`                      | Todas las métricas y KPIs en formato estructurado             |
| `ventas_por_tiempo.png`             | Ingresos mensuales, trimestrales y anuales; ticket promedio   |
| `analisis_financiero.png`           | Ingresos vs costos, margen absoluto y %, tasa de financiación |
| `top_clientes.png`                  | Top 20 clientes por gasto total                               |
| `rendimiento_vendedores.png`        | Top 10 vendedores e impacto de la experiencia                 |
| `mantenimiento_por_tipo.png`        | Distribución y costo promedio por tipo de servicio            |
| `kpi_rotacion_quarterly.png`        | Tendencia trimestral de rotación de inventario                |
| `kpi_retencion_quarterly.png`       | Tendencia trimestral de retención de clientes                 |
| `kpi_margen_promedio_quarterly.png` | Tendencia trimestral del margen por venta                     |
| `kpi_dias_inventario_quarterly.png` | Tendencia trimestral de días en inventario                    |
| `calidad_datos.json`                | Reporte de nulos, duplicados y relaciones rotas               |

---

## Tecnologías y Dependencias

### Stack Principal

| Tecnología               | Uso                                      |
| ------------------------ | ---------------------------------------- |
| **Python 3.10+**         | Lenguaje principal                       |
| **pandas**               | Manipulación y transformación de datos   |
| **SQLite**               | Base de datos embebida (Data Warehouse)  |
| **scikit-learn**         | Modelos de Machine Learning              |
| **matplotlib / seaborn** | Generación de gráficas y visualizaciones |
| **joblib**               | Serialización de modelos ML              |
| **openpyxl**             | Lectura y escritura de archivos Excel    |
| **PyYAML**               | Lectura del archivo de configuración     |

### Instalación de Dependencias

```bash
pip install -r requirements.txt
```

Contenido de `requirements.txt`:

```
pandas
openpyxl
pyyaml
scikit-learn
matplotlib
seaborn
joblib
numpy
```

---

## Instalación y Configuración

### Prerrequisitos

- Python **3.10** o superior
- pip actualizado

### Pasos de Instalación

```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio>
cd proyecto_big_data

# 2. Crear entorno virtual (recomendado)
python -m venv .venv

# Activar en Windows
.venv\Scripts\activate

# Activar en Linux/macOS
source .venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Verificar estructura de datos
# Asegurarse de que el archivo fuente exista en:
# proyecto_big_data/data/raw/datos_concesionario_raw.xlsx
```

### Configuración (config.yaml)

```yaml
etl:
  source_files:
    datos_concesionario: "data/raw/datos_concesionario_raw.xlsx"

database:
  type: "sqlite"
  path: "data/processed/concesionario.db"

validation:
  min_date: "2020-01-01"
  max_date: "2024-12-31"
  min_price: 1000
  max_price: 200000
  reject_future_dates: true

logging:
  level: "INFO"
  format: "%(asctime)s - %(levelname)s - %(message)s"
  file: "logs/etl_concesionario.log"
```

---

## Uso del Sistema

### Ejecutar el Sistema Completo

```bash
# Desde la carpeta proyecto_big_data/
python run_complete_system.py
# Equivalente a --all: ejecuta ETL + Reportes + Predicciones
```

### Ejecutar Módulos de Forma Independiente

```bash
# Solo ETL (extracción, transformación y carga)
python run_complete_system.py --etl

# Solo generación de reportes y KPIs
python run_complete_system.py --reports

# Solo predicciones ML
python run_complete_system.py --predictions

# Dos módulos combinados
python run_complete_system.py --etl --reports
```

### Ver el Dashboard

Tras ejecutar el sistema, abrir en el navegador:

```
proyecto_big_data/reports/report_YYYYMMDD_HHMMSS/dashboard.html
```

---

## ✅ Calidad de Datos

El sistema implementa validaciones automáticas en múltiples capas:

### Capa ETL (transform.py)

| Validación                      | Detalle                                                                |
| ------------------------------- | ---------------------------------------------------------------------- |
| **IDs negativos o cero**        | Se convierten a `NaN`                                                  |
| **Fechas futuras**              | Se rechazan si `reject_future_dates: true`                             |
| **Fechas anteriores al mínimo** | Filtradas según `min_date`                                             |
| **Precios fuera de rango**      | Truncados a `[min_price, max_price]`                                   |
| **Emails inválidos**            | Marcados como `email_invalido`                                         |
| **Ciudades con alias**          | Normalizadas mediante mapa de equivalencias (ej. `medallo → Medellín`) |
| **Texto sucio**                 | Strip, lowercase, eliminación de tildes y caracteres especiales        |
| **Valores nulos en texto**      | Reemplazados por `'no identificado'`                                   |

### Capa de Validación (data_quality.py)

| Check                       | Qué verifica                                             |
| --------------------------- | -------------------------------------------------------- |
| **Nulos en columnas clave** | `id_cliente` en `hecho_ventas` y `hecho_mantenimiento`   |
| **Duplicados en ventas**    | `COUNT(*) - COUNT(DISTINCT id_venta)`                    |
| **Integridad referencial**  | Registros huérfanos entre tablas de hechos y dimensiones |

El reporte de calidad se guarda en `reports/report_*/calidad_datos.json`.

---

## Configuración Avanzada

### Variables de Validación (config.yaml)

| Parámetro             | Default      | Descripción                         |
| --------------------- | ------------ | ----------------------------------- |
| `min_date`            | `2020-01-01` | Fecha mínima aceptada en los datos  |
| `max_date`            | `2024-12-31` | Fecha máxima aceptada en los datos  |
| `min_price`           | `1000`       | Precio mínimo válido de un vehículo |
| `max_price`           | `200000`     | Precio máximo válido de un vehículo |
| `reject_future_dates` | `true`       | Rechazar fechas posteriores a hoy   |

### Logging

Los logs del sistema se almacenan en:

- `logs/system.log` — log del sistema completo
- `logs/etl_concesionario.log` — log detallado del ETL

El nivel de log se puede cambiar en `config.yaml` (`DEBUG`, `INFO`, `WARNING`, `ERROR`).

---

## 👨‍💻 Principios de Diseño

El proyecto fue construido siguiendo los principios **SOLID**:

| Principio                     | Aplicación                                                                                                                 |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **S** — Single Responsibility | Cada clase tiene una única responsabilidad: `DataTransformer`, `KPICalculator`, `VehiclePricePredictor`, `ReportGenerator` |
| **O** — Open/Closed           | Los módulos de KPI y reportes pueden extenderse sin modificar el código existente                                          |
| **L** — Liskov Substitution   | Los gestores de base de datos son intercambiables                                                                          |
| **I** — Interface Segregation | Las interfaces de cada módulo son mínimas y específicas                                                                    |
| **D** — Dependency Inversion  | Los módulos de alto nivel (reportes, predicciones) dependen de abstracciones, no de implementaciones concretas             |

---
