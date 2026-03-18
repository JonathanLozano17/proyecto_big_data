"""
transform_data.py
Transforma el Excel crudo del concesionario a un modelo estrella.
Genera IDs surrogados ya que el raw NO trae IDs.
Output: data/transformed/modelo_estrella.xlsx  (una hoja por tabla)
"""

import argparse
import logging
import os
import re
import unicodedata
from datetime import datetime
from typing import Any, Dict

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_CONFIG: Dict[str, Any] = {
    'validation': {
        'reject_future_dates': True,
        'min_date': '2019-01-01',
        'min_price': 0,
        'max_price': 500_000,
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# TRANSFORMER
# ──────────────────────────────────────────────────────────────────────────────

class DataTransformer:
    """Convierte datos desnormalizados del concesionario a modelo estrella.
    
    El raw NO contiene IDs — todos los IDs surrogados se generan aquí.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or DEFAULT_CONFIG
        # Asegurar que validation config exista aunque venga config de YAML
        if 'validation' not in self.config:
            self.config['validation'] = DEFAULT_CONFIG['validation']

    # ── Punto de entrada ──────────────────────────────────────────────────────

    def transform_all(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Recibe {'datos_concesionario': df_raw} y retorna todas las tablas."""
        df_raw = data_dict.get('datos_concesionario')
        if df_raw is None:
            log.error("No se encontró 'datos_concesionario' en el diccionario de entrada.")
            return {}

        log.info(f"DataFrame recibido: {len(df_raw):,} filas × {len(df_raw.columns)} columnas")

        df = self._normalize_all_text(df_raw.copy())

        # ── Dimensiones (orden importa: ciudad antes que cliente/sucursal) ────
        dim_ciudad            = self._create_dim_ciudad(df)
        dim_tiempo            = self._create_dim_tiempo(df)
        dim_cliente           = self._create_dim_cliente(df, dim_ciudad)
        dim_sucursal          = self._create_dim_sucursal(df, dim_ciudad)
        dim_vehiculo          = self._create_dim_vehiculo(df)
        dim_vendedor          = self._create_dim_vendedor(df, dim_sucursal)
        dim_tipo_pago         = self._create_dim_tipo_pago(df)
        dim_tipo_mantenimiento = self._create_dim_tipo_mantenimiento(df)

        # ── Hechos ────────────────────────────────────────────────────────────
        hecho_ventas        = self._create_hecho_ventas(
            df, dim_tiempo, dim_cliente, dim_vehiculo,
            dim_vendedor, dim_sucursal, dim_tipo_pago
        )
        hecho_mantenimiento = self._create_hecho_mantenimiento(
            df, dim_tiempo, dim_cliente, dim_vehiculo,
            dim_sucursal, dim_tipo_mantenimiento
        )

        result = {
            'dim_tiempo':             dim_tiempo,
            'dim_ciudad':             dim_ciudad,
            'dim_cliente':            dim_cliente,
            'dim_sucursal':           dim_sucursal,
            'dim_vehiculo':           dim_vehiculo,
            'dim_vendedor':           dim_vendedor,
            'dim_tipoPago':           dim_tipo_pago,
            'dim_tipoMantenimiento':  dim_tipo_mantenimiento,
            'hecho_ventas':           hecho_ventas,
            'hecho_mantenimiento':    hecho_mantenimiento,
        }

        log.info("─── Resultados ───────────────────────────────────────")
        for name, tbl in result.items():
            if tbl is not None and not tbl.empty:
                log.info(f"  {name:<30} {len(tbl):>6,} filas  ×  {len(tbl.columns)} cols")
            else:
                log.warning(f"  {name:<30} VACÍA")
        log.info("──────────────────────────────────────────────────────")

        return result

    # ── Normalización de texto ────────────────────────────────────────────────

    def _normalize_text_series(self, series: pd.Series,
                               default: str = 'no identificado',
                               replace_ñ: bool = False) -> pd.Series:
        """Limpia una columna de texto: strip, lower, sin tildes, sin chars raros."""

        def _clean(text):
            if pd.isna(text) or text is None:
                return default
            s = str(text).strip()
            if not s or s.lower() in ('nan', 'none', 'null', 'n/a', 'sin dato',
                                       '?', '', 'ciudad_invalida', 'no especificada'):
                return default
            s = s.lower()
            if replace_ñ:
                s = s.replace('ñ', 'ni').replace('Ñ', 'Ni')
            # Quitar tildes
            s = unicodedata.normalize('NFKD', s)
            s = ''.join(c for c in s if not unicodedata.combining(c))
            # Limpiar caracteres no alfanuméricos (salvo espacio y punto)
            s = re.sub(r'[^\w\s.]', ' ', s)
            s = re.sub(r'\s+', ' ', s).strip()
            return s or default

        return series.apply(_clean)

    def _normalize_all_text(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza todas las columnas object del DataFrame."""
        for col in df.select_dtypes(include='object').columns:
            sample = df[col].dropna().astype(str).head(200)
            has_ñ = (
                sample.str.contains('ñ', na=False).any() or
                sample.str.contains('Ñ', na=False).any() or
                'ñ' in col.lower()
            )
            df[col] = self._normalize_text_series(df[col], replace_ñ=has_ñ)
        return df

    # ── Limpieza de tipos básicos ─────────────────────────────────────────────

    def _clean_text(self, series: pd.Series) -> pd.Series:
        return self._normalize_text_series(series, replace_ñ=False)

    def _clean_date(self, series: pd.Series) -> pd.Series:
        FMTS = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d',
                '%d.%m.%Y', '%b %d, %Y', '%d-%b-%Y', '%Y%m%d']

        def _parse(val):
            if pd.isna(val) or str(val).strip() in ('no identificado', ''):
                return pd.NaT
            for fmt in FMTS:
                try:
                    return datetime.strptime(str(val).strip(), fmt)
                except ValueError:
                    pass
            return pd.NaT

        dates = series.apply(_parse)

        if self.config['validation'].get('reject_future_dates', True):
            dates = dates.where(dates <= pd.Timestamp.now(), pd.NaT)

        min_d = pd.Timestamp(self.config['validation'].get('min_date', '2019-01-01'))
        dates = dates.where(dates >= min_d, pd.NaT)
        return dates

    def _clean_price(self, series: pd.Series) -> pd.Series:
        lo = self.config['validation'].get('min_price', 0)
        hi = self.config['validation'].get('max_price', 500_000)

        def _parse(val):
            if pd.isna(val) or str(val).strip() in ('no identificado', ''):
                return None
            s = re.sub(r'[$€£\s]', '', str(val))
            s = re.sub(r'(?i)usd', '', s)
            if ',' in s and '.' in s:
                s = s.replace(',', '')
            elif ',' in s and s.count(',') == 1:
                parts = s.split(',')
                if len(parts[1]) <= 2:
                    s = s.replace(',', '.')
                else:
                    s = s.replace(',', '')
            s = re.sub(r'[^\d.]', '', s)
            try:
                return float(s)
            except ValueError:
                return None

        cleaned = series.apply(_parse)
        return pd.to_numeric(cleaned, errors='coerce').clip(lo, hi)

    def _clean_discount(self, series: pd.Series) -> pd.Series:
        def _parse(val):
            if pd.isna(val) or str(val).strip() in ('no identificado', ''):
                return 0.0
            s = re.sub(r'[^\d.]', '',
                       str(val).replace('%', '').replace('descuento', '').strip())
            try:
                v = float(s)
                return v * 100 if v <= 1 else v
            except ValueError:
                return 0.0
        return series.apply(_parse).clip(0, 100).fillna(0)

    def _clean_boolean(self, series: pd.Series) -> pd.Series:
        TRUE_SET  = {'1', 'si', 'sí', 'true', 'y', 'yes', 'verdadero', 't'}
        FALSE_SET = {'0', 'no', 'false', 'n', 'not', 'falso', 'f'}

        def _parse(val):
            if pd.isna(val):
                return 0
            s = str(val).lower().strip()
            if s in TRUE_SET:
                return 1
            if s in FALSE_SET:
                return 0
            try:
                return int(bool(float(s)))
            except Exception:
                return 0

        return series.apply(_parse).astype(int)

    def _clean_quantity(self, series: pd.Series) -> pd.Series:
        def _parse(val):
            if pd.isna(val):
                return 0.0
            s = re.sub(r'[^\d.]', '', str(val))
            try:
                return max(0.0, float(s))
            except Exception:
                return 0.0
        return series.apply(_parse).fillna(0)

    # ── Normalización de dominios ─────────────────────────────────────────────

    def _normalize_city(self, name: str) -> str:
        CITY_MAP = {
            'bogota':              'Bogotá',
            'bogota dc':           'Bogotá',
            'bogota d c':          'Bogotá',
            'santa fe de bogota':  'Bogotá',
            'medellin':            'Medellín',
            'medallo':             'Medellín',
            'cali':                'Cali',
            'santiago de cali':    'Cali',
            'barranquilla':        'Barranquilla',
            'b quilla':            'Barranquilla',
            'bquilla':             'Barranquilla',
            'cartagena':           'Cartagena',
            'cartagena de indias': 'Cartagena',
            'ctg':                 'Cartagena',
            'bucaramanga':         'Bucaramanga',
            'b manga':             'Bucaramanga',
            'buca':                'Bucaramanga',
            'pereira':             'Pereira',
            'cucuta':              'Cúcuta',
            'san jose de cucuta':  'Cúcuta',
            'santa marta':         'Santa Marta',
            'smarta':              'Santa Marta',
            's marta':             'Santa Marta',
            'ibague':              'Ibagué',
            'manizales':           'Manizales',
            'pasto':               'Pasto',
            'san juan de pasto':   'Pasto',
        }
        if pd.isna(name) or name == 'no identificado':
            return 'No Identificado'
        key = str(name).lower().strip()
        # Quitar tildes para comparación
        key_ascii = unicodedata.normalize('NFKD', key)
        key_ascii = ''.join(c for c in key_ascii if not unicodedata.combining(c))
        if key_ascii in CITY_MAP:
            return CITY_MAP[key_ascii]
        for k, v in CITY_MAP.items():
            if k in key_ascii:
                return v
        return name.title()

    def _validate_email(self, email: str) -> str:
        FIXES = {
            'gmial.com':  'gmail.com',
            'gmai.com':   'gmail.com',
            'hotmai.com': 'hotmail.com',
            'hotmil.com': 'hotmail.com',
            'yaho.com':   'yahoo.com',
            'yaho.es':    'yahoo.es',
            'outlok.com': 'outlook.com',
            'correo.c':   'correo.co',
        }
        PATTERN = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'

        if pd.isna(email) or email in ('no identificado', ''):
            return 'no_identificado'
        em = re.sub(r'\s+', '', str(email).lower())
        for wrong, right in FIXES.items():
            em = em.replace(wrong, right)
        return em if re.match(PATTERN, em) else 'email_invalido'

    # ── Helpers de lookup ─────────────────────────────────────────────────────

    def _build_ciudad_lookup(self, dim_ciudad: pd.DataFrame) -> dict:
        """Retorna {nombre_ciudad_lower: id_ciudad}"""
        if dim_ciudad.empty:
            return {}
        lookup = {}
        for _, row in dim_ciudad.iterrows():
            key = str(row['nombre_ciudad']).lower().strip()
            lookup[key] = row['id_ciudad']
        return lookup

    # ── Dimensiones ───────────────────────────────────────────────────────────

    def _create_dim_tiempo(self, df: pd.DataFrame) -> pd.DataFrame:
        ventas = self._clean_date(df['fecha_venta'])
        mantos = self._clean_date(df['fecha_mantenimiento'])
        all_dates = pd.concat([ventas, mantos]).dropna().unique()
        if len(all_dates) == 0:
            log.warning("dim_tiempo: no se encontraron fechas válidas")
            return pd.DataFrame()

        t = pd.DataFrame({'fecha_completa': sorted(all_dates)})
        t['id_tiempo']     = t['fecha_completa'].dt.strftime('%Y%m%d').astype(int)
        t['año']           = t['fecha_completa'].dt.year
        t['mes']           = t['fecha_completa'].dt.month
        t['nombre_mes']    = t['fecha_completa'].dt.strftime('%B').str.capitalize()
        t['trimestre']     = t['fecha_completa'].dt.quarter
        t['semana']        = t['fecha_completa'].dt.isocalendar().week.astype(int)
        t['dia']           = t['fecha_completa'].dt.day
        t['dia_semana']    = t['fecha_completa'].dt.strftime('%A').str.capitalize()
        t['es_fin_semana'] = (t['fecha_completa'].dt.weekday >= 5).astype(int)
        return t[['id_tiempo', 'fecha_completa', 'año', 'mes', 'nombre_mes',
                  'trimestre', 'semana', 'dia', 'dia_semana', 'es_fin_semana']]

    def _create_dim_ciudad(self, df: pd.DataFrame) -> pd.DataFrame:
        """Construye dim_ciudad a partir de las columnas de ciudad del raw."""
        frames = []

        # Ciudades de clientes
        cli = df[['ciudad_cliente', 'departamento_cliente', 'region_cliente']].copy()
        cli.columns = ['nombre_ciudad', 'departamento', 'region']
        frames.append(cli)

        # Ciudades de sucursales
        suc = df[['ciudad_sucursal', 'departamento_sucursal', 'region_sucursal']].copy()
        suc.columns = ['nombre_ciudad', 'departamento', 'region']
        frames.append(suc)

        combined = pd.concat(frames, ignore_index=True)
        combined['nombre_ciudad'] = combined['nombre_ciudad'].apply(self._normalize_city)
        combined['departamento']  = self._clean_text(combined['departamento'])
        combined['region']        = self._clean_text(combined['region'])

        # Descartar "No Identificado"
        combined = combined[combined['nombre_ciudad'] != 'No Identificado']
        combined = combined.drop_duplicates(subset=['nombre_ciudad']).reset_index(drop=True)

        combined.insert(0, 'id_ciudad', range(1, len(combined) + 1))
        log.info(f"dim_ciudad: {len(combined)} ciudades únicas")
        return combined

    def _create_dim_cliente(self, df: pd.DataFrame,
                             dim_ciudad: pd.DataFrame) -> pd.DataFrame:
        """Crea dim_cliente con IDs surrogados."""
        ciudad_lookup = self._build_ciudad_lookup(dim_ciudad)

        src = df[df['cliente_nombre'] != 'no identificado'][
            ['cliente_nombre', 'cliente_edad', 'cliente_genero',
             'cliente_tipo', 'cliente_email', 'ciudad_cliente']
        ].copy()

        src['cliente_nombre'] = self._clean_text(src['cliente_nombre'])
        src['cliente_email']  = src['cliente_email'].apply(self._validate_email)

        src['cliente_edad'] = (
            pd.to_numeric(src['cliente_edad'], errors='coerce')
            .clip(18, 100)
            .fillna(30)
            .astype(int)
        )

        TIPO_MAP = {
            'nuevo': 'nuevo', 'new': 'nuevo',
            'recurrente': 'recurrente', 'recurrent': 'recurrente',
            'vip': 'vip',
            'empresarial': 'empresarial', 'empresa': 'empresarial',
            'potencial': 'potencial',
        }
        src['cliente_tipo'] = (
            src['cliente_tipo']
            .apply(lambda x: next((v for k, v in TIPO_MAP.items()
                                   if k in str(x).lower()), 'nuevo'))
        )

        GEN_MAP = {
            'm': 'M', 'masculino': 'M', 'male': 'M',
            'f': 'F', 'femenino': 'F', 'female': 'F',
        }
        src['cliente_genero'] = (
            src['cliente_genero']
            .apply(lambda x: GEN_MAP.get(str(x).lower().strip(), 'M'))
        )

        # FK a ciudad
        src['id_ciudad'] = (
            src['ciudad_cliente']
            .apply(self._normalize_city)
            .apply(lambda c: ciudad_lookup.get(c.lower(), None))
        )

        src = src.drop_duplicates(subset=['cliente_nombre', 'cliente_email'])
        src = src.reset_index(drop=True)
        src.insert(0, 'id_cliente', range(1, len(src) + 1))

        return src.rename(columns={
            'cliente_nombre': 'nombre',
            'cliente_edad':   'edad',
            'cliente_genero': 'genero',
            'cliente_tipo':   'tipo_cliente',
            'cliente_email':  'email',
        })[['id_cliente', 'nombre', 'edad', 'genero',
            'tipo_cliente', 'email', 'id_ciudad']].reset_index(drop=True)

    def _create_dim_sucursal(self, df: pd.DataFrame,
                              dim_ciudad: pd.DataFrame) -> pd.DataFrame:
        """Crea dim_sucursal con IDs surrogados."""
        ciudad_lookup = self._build_ciudad_lookup(dim_ciudad)

        # Detectar columna tamaño (puede tener ñ o no dependiendo de normalización)
        col_tam = next((c for c in df.columns if 'tama' in c.lower()
                        or 'tamano' in c.lower() or 'tamañ' in c.lower()), None)

        cols = ['sucursal_nombre', 'ciudad_sucursal', 'sucursal_zona']
        if col_tam:
            cols.append(col_tam)

        src = df[[c for c in cols if c in df.columns]].copy()
        src.rename(columns={col_tam: 'tamano'} if col_tam else {}, inplace=True)

        src['sucursal_nombre'] = self._clean_text(src['sucursal_nombre'])
        src['sucursal_zona']   = self._clean_text(src['sucursal_zona'])
        if 'tamano' in src.columns:
            src['tamano'] = self._clean_text(src['tamano'])
        else:
            src['tamano'] = 'no identificado'

        src['id_ciudad'] = (
            src['ciudad_sucursal']
            .apply(self._normalize_city)
            .apply(lambda c: ciudad_lookup.get(c.lower(), None))
        )

        src = src[src['sucursal_nombre'] != 'no identificado']
        src = src.drop_duplicates(subset=['sucursal_nombre']).reset_index(drop=True)
        src.insert(0, 'id_sucursal', range(1, len(src) + 1))

        return src.rename(columns={
            'sucursal_nombre': 'nombre',
            'tamano':          'tamaño',
            'sucursal_zona':   'zona',
        })[['id_sucursal', 'nombre', 'id_ciudad',
            'tamaño', 'zona']].reset_index(drop=True)

    def _create_dim_vehiculo(self, df: pd.DataFrame) -> pd.DataFrame:
        """Crea dim_vehiculo con IDs surrogados."""
        # La columna año puede haberse normalizado quitando tilde
        col_año = next((c for c in df.columns
                        if re.search(r'vehiculo_a.?o', c, re.IGNORECASE)), 'vehiculo_año')

        cols_use = [c for c in [
            'vehiculo_marca', 'vehiculo_modelo', 'vehiculo_tipo',
            col_año, 'vehiculo_cilindraje', 'vehiculo_combustible', 'vehiculo_color'
        ] if c in df.columns]

        src = df[cols_use].copy()
        if col_año != 'vehiculo_año' and col_año in src.columns:
            src.rename(columns={col_año: 'vehiculo_año'}, inplace=True)

        for col in ['vehiculo_marca', 'vehiculo_modelo', 'vehiculo_tipo', 'vehiculo_color']:
            if col in src.columns:
                src[col] = self._clean_text(src[col])

        if 'vehiculo_año' in src.columns:
            src['vehiculo_año'] = (
                pd.to_numeric(src['vehiculo_año'], errors='coerce')
                .clip(2012, 2025)
                .fillna(2020)
                .astype(int)
            )
        if 'vehiculo_cilindraje' in src.columns:
            src['vehiculo_cilindraje'] = (
                pd.to_numeric(src['vehiculo_cilindraje'], errors='coerce')
                .clip(600, 6000)
                .fillna(1600)
                .astype(int)
            )

        COMB_MAP = {
            'gasolina':    'Gasolina',
            'diesel':      'Diesel',
            'hibrido':     'Híbrido',
            'electrico':   'Eléctrico',
            'gas natural': 'Gas Natural',
        }
        if 'vehiculo_combustible' in src.columns:
            src['vehiculo_combustible'] = src['vehiculo_combustible'].apply(
                lambda x: next(
                    (v for k, v in COMB_MAP.items() if k in str(x).lower()),
                    'Gasolina'
                )
            )

        # Deduplicar por marca+modelo+año
        subset_cols = [c for c in ['vehiculo_marca', 'vehiculo_modelo', 'vehiculo_año']
                       if c in src.columns]
        src = src.drop_duplicates(subset=subset_cols).reset_index(drop=True)
        src.insert(0, 'id_vehiculo', range(1, len(src) + 1))

        return src.rename(columns={
            'vehiculo_marca':       'marca',
            'vehiculo_modelo':      'modelo',
            'vehiculo_tipo':        'tipo',
            'vehiculo_año':         'año_modelo',
            'vehiculo_cilindraje':  'cilindraje',
            'vehiculo_combustible': 'tipo_combustible',
            'vehiculo_color':       'color',
        }).reset_index(drop=True)

    def _create_dim_vendedor(self, df: pd.DataFrame,
                              dim_sucursal: pd.DataFrame) -> pd.DataFrame:
        """Crea dim_vendedor con IDs surrogados."""
        sucursal_lookup = {}
        if not dim_sucursal.empty:
            sucursal_lookup = dict(
                zip(dim_sucursal['nombre'].str.lower(),
                    dim_sucursal['id_sucursal'])
            )

        src = df[df['tipo_registro'].str.lower() == 'venta'].copy()
        src = src[src['vendedor_nombre'] != 'no identificado'][
            ['vendedor_nombre', 'vendedor_experiencia', 'sucursal_nombre']
        ].copy()

        src['vendedor_nombre'] = self._clean_text(src['vendedor_nombre'])
        src['vendedor_experiencia'] = (
            pd.to_numeric(src['vendedor_experiencia'], errors='coerce')
            .clip(0, 40)
            .fillna(0)
            .astype(int)
        )
        src['id_sucursal'] = (
            src['sucursal_nombre']
            .apply(lambda x: sucursal_lookup.get(str(x).lower().strip()))
        )

        src = src.drop_duplicates(subset=['vendedor_nombre']).reset_index(drop=True)
        src.insert(0, 'id_vendedor', range(1, len(src) + 1))

        return src.rename(columns={
            'vendedor_nombre':      'nombre',
            'vendedor_experiencia': 'experiencia_años',
        })[['id_vendedor', 'nombre', 'experiencia_años',
            'id_sucursal']].reset_index(drop=True)

    def _create_dim_tipo_pago(self, df: pd.DataFrame) -> pd.DataFrame:
        """Crea dim_tipo_pago con IDs surrogados."""
        src = df[df['tipo_registro'].str.lower() == 'venta'].copy()
        src = src[src['tipo_pago'] != 'no identificado'][
            ['tipo_pago', 'entidad_financiera', 'plazo_meses',
             'tasa_interes', 'requiere_aprobacion']
        ].copy()

        PAGO_MAP = {
            'contado':  'contado',
            'credito':  'credito',
            'cr dito':  'credito',
            'leasing':  'leasing',
        }
        src['tipo_pago'] = src['tipo_pago'].apply(
            lambda x: next(
                (v for k, v in PAGO_MAP.items() if k in str(x).lower()),
                'contado'
            )
        )
        src['entidad_financiera'] = self._clean_text(src['entidad_financiera'])

        for col in ['plazo_meses', 'tasa_interes', 'requiere_aprobacion']:
            src[col] = pd.to_numeric(src[col], errors='coerce').fillna(0)

        src = src.drop_duplicates(subset=['tipo_pago']).reset_index(drop=True)
        src.insert(0, 'id_tipo_pago', range(1, len(src) + 1))
        return src.reset_index(drop=True)

    def _create_dim_tipo_mantenimiento(self, df: pd.DataFrame) -> pd.DataFrame:
        """Crea dim_tipo_mantenimiento con IDs surrogados."""
        src = df[df['tipo_registro'].str.lower() == 'mantenimiento'].copy()
        src = src[src['tipo_mantenimiento'] != 'no identificado'][
            ['tipo_mantenimiento', 'tipo_mantenimiento_descripcion',
             'incluye_garantia', 'meses_garantia', 'kilometros_garantia']
        ].copy()

        src['tipo_mantenimiento'] = self._clean_text(src['tipo_mantenimiento'])
        src['tipo_mantenimiento_descripcion'] = self._clean_text(
            src['tipo_mantenimiento_descripcion']
        )
        for col in ['incluye_garantia', 'meses_garantia', 'kilometros_garantia']:
            src[col] = pd.to_numeric(src[col], errors='coerce').fillna(0).astype(int)

        src = src.drop_duplicates(subset=['tipo_mantenimiento']).reset_index(drop=True)
        src.insert(0, 'id_tipo_mantenimiento', range(1, len(src) + 1))

        return src.rename(columns={
            'tipo_mantenimiento':             'nombre_tipo',
            'tipo_mantenimiento_descripcion': 'descripcion',
        }).reset_index(drop=True)

    # ── Hechos ────────────────────────────────────────────────────────────────

    def _lookup_id(self, series: pd.Series, dim: pd.DataFrame,
                   dim_key_col: str, dim_val_col: str) -> pd.Series:
        """Genera una serie de IDs haciendo lookup en una dimensión."""
        if dim.empty:
            return pd.Series([None] * len(series), index=series.index)
        lk = dict(zip(
            dim[dim_key_col].astype(str).str.lower().str.strip(),
            dim[dim_val_col]
        ))
        return series.astype(str).str.lower().str.strip().map(lk)

    def _create_hecho_ventas(self, df: pd.DataFrame,
                              dim_tiempo: pd.DataFrame,
                              dim_cliente: pd.DataFrame,
                              dim_vehiculo: pd.DataFrame,
                              dim_vendedor: pd.DataFrame,
                              dim_sucursal: pd.DataFrame,
                              dim_tipo_pago: pd.DataFrame) -> pd.DataFrame:
        src = df[df['tipo_registro'].str.lower() == 'venta'].copy()
        if src.empty:
            log.warning("hecho_ventas: no hay registros de VENTA")
            return pd.DataFrame()

        # Fechas → id_tiempo
        src['_fecha_clean'] = self._clean_date(src['fecha_venta'])
        if not dim_tiempo.empty:
            t_map = dict(zip(dim_tiempo['fecha_completa'], dim_tiempo['id_tiempo']))
            src['id_tiempo'] = src['_fecha_clean'].map(t_map)
        else:
            src['id_tiempo'] = None

        # FKs a dimensiones usando columnas descriptivas del raw
        src['id_cliente'] = self._lookup_id(
            src['cliente_nombre'], dim_cliente, 'nombre', 'id_cliente'
        )
        # Vehículo: lookup por marca+modelo (concatenado)
        if not dim_vehiculo.empty:
            veh_map = {
                (str(r['marca']).lower() + '|' + str(r['modelo']).lower()): r['id_vehiculo']
                for _, r in dim_vehiculo.iterrows()
            }
            src['id_vehiculo'] = (
                src['vehiculo_marca'].str.lower() + '|' + src['vehiculo_modelo'].str.lower()
            ).map(veh_map)
        else:
            src['id_vehiculo'] = None

        src['id_vendedor'] = self._lookup_id(
            src['vendedor_nombre'], dim_vendedor, 'nombre', 'id_vendedor'
        )
        src['id_sucursal'] = self._lookup_id(
            src['sucursal_nombre'], dim_sucursal, 'nombre', 'id_sucursal'
        )
        src['id_tipo_pago'] = self._lookup_id(
            src['tipo_pago'], dim_tipo_pago, 'tipo_pago', 'id_tipo_pago'
        )

        # Métricas
        src['precio_venta']      = self._clean_price(src['precio_venta'])
        src['costo_vehiculo']    = self._clean_price(src['costo_vehiculo'])
        src['descuento']         = self._clean_discount(src['descuento'])
        src['financiado']        = self._clean_boolean(src['financiado'])
        src['cantidad']          = self._clean_quantity(src['cantidad'])
        src['comision_vendedor'] = pd.to_numeric(src['comision_vendedor'], errors='coerce')

        src['margen_ganancia'] = src['precio_venta'] - src['costo_vehiculo']
        src['precio_neto']     = src['precio_venta'] * (1 - src['descuento'] / 100)

        # Filtrar filas sin cliente o vehículo identificable
        src = src.dropna(subset=['id_cliente', 'id_vehiculo'])

        hecho = src[[
            'id_tiempo', 'id_cliente', 'id_vehiculo', 'id_vendedor',
            'id_sucursal', 'id_tipo_pago', 'cantidad', 'precio_venta',
            'costo_vehiculo', 'descuento', 'precio_neto', 'margen_ganancia',
            'financiado', 'comision_vendedor'
        ]].copy().reset_index(drop=True)

        hecho.insert(0, 'id_venta', range(1, len(hecho) + 1))
        log.info(f"hecho_ventas: {len(hecho):,} registros")
        return hecho

    def _create_hecho_mantenimiento(self, df: pd.DataFrame,
                                     dim_tiempo: pd.DataFrame,
                                     dim_cliente: pd.DataFrame,
                                     dim_vehiculo: pd.DataFrame,
                                     dim_sucursal: pd.DataFrame,
                                     dim_tipo_mantenimiento: pd.DataFrame) -> pd.DataFrame:
        src = df[df['tipo_registro'].str.lower() == 'mantenimiento'].copy()
        if src.empty:
            log.warning("hecho_mantenimiento: no hay registros de MANTENIMIENTO")
            return pd.DataFrame()

        # Fechas → id_tiempo
        src['_fecha_clean'] = self._clean_date(src['fecha_mantenimiento'])
        if not dim_tiempo.empty:
            t_map = dict(zip(dim_tiempo['fecha_completa'], dim_tiempo['id_tiempo']))
            src['id_tiempo'] = src['_fecha_clean'].map(t_map)
        else:
            src['id_tiempo'] = None

        # FKs
        src['id_cliente'] = self._lookup_id(
            src['cliente_nombre'], dim_cliente, 'nombre', 'id_cliente'
        )
        if not dim_vehiculo.empty:
            veh_map = {
                (str(r['marca']).lower() + '|' + str(r['modelo']).lower()): r['id_vehiculo']
                for _, r in dim_vehiculo.iterrows()
            }
            src['id_vehiculo'] = (
                src['vehiculo_marca'].str.lower() + '|' + src['vehiculo_modelo'].str.lower()
            ).map(veh_map)
        else:
            src['id_vehiculo'] = None

        src['id_sucursal'] = self._lookup_id(
            src['sucursal_nombre'], dim_sucursal, 'nombre', 'id_sucursal'
        )
        src['id_tipo_mantenimiento'] = self._lookup_id(
            src['tipo_mantenimiento'],
            dim_tipo_mantenimiento,
            'nombre_tipo',
            'id_tipo_mantenimiento'
        )

        # Métricas
        src['costo_servicio']       = self._clean_price(src['costo_servicio'])
        src['costo_repuestos']      = self._clean_price(src['costo_repuestos'])
        src['repuestos_usados']     = self._clean_quantity(src['repuestos_usados'])
        src['horas_taller']         = pd.to_numeric(src['horas_taller'], errors='coerce')
        src['kilometraje_vehiculo'] = pd.to_numeric(src['kilometraje_vehiculo'], errors='coerce')
        src['costo_total'] = (
            src['costo_servicio'].fillna(0) + src['costo_repuestos'].fillna(0)
        )

        src = src.dropna(subset=['id_cliente', 'id_vehiculo'])

        hecho = src[[
            'id_tiempo', 'id_cliente', 'id_vehiculo', 'id_sucursal',
            'id_tipo_mantenimiento', 'costo_servicio', 'costo_repuestos',
            'costo_total', 'repuestos_usados', 'horas_taller', 'kilometraje_vehiculo'
        ]].copy().reset_index(drop=True)

        hecho.insert(0, 'id_mantenimiento', range(1, len(hecho) + 1))
        log.info(f"hecho_mantenimiento: {len(hecho):,} registros")
        return hecho

    # ── Validación integridad referencial ─────────────────────────────────────

    def validate_referential_integrity(self,
                                        tables: Dict[str, pd.DataFrame]) -> Dict[str, int]:
        results = {}

        def _orphans(fact_df, fact_col, dim_df, dim_col, label):
            if fact_df is None or fact_df.empty:
                return
            if dim_df is None or dim_df.empty:
                return
            if fact_col not in fact_df.columns or dim_col not in dim_df.columns:
                return
            valid = set(dim_df[dim_col].dropna())
            mask  = fact_df[fact_col].notna() & ~fact_df[fact_col].isin(valid)
            results[label] = int(mask.sum())

        ventas = tables.get('hecho_ventas', pd.DataFrame())
        mant   = tables.get('hecho_mantenimiento', pd.DataFrame())

        _orphans(ventas, 'id_cliente',   tables.get('dim_cliente',  pd.DataFrame()), 'id_cliente',  'ventas→clientes_huerfanos')
        _orphans(ventas, 'id_vehiculo',  tables.get('dim_vehiculo', pd.DataFrame()), 'id_vehiculo', 'ventas→vehiculos_huerfanos')
        _orphans(ventas, 'id_vendedor',  tables.get('dim_vendedor', pd.DataFrame()), 'id_vendedor', 'ventas→vendedores_huerfanos')
        _orphans(ventas, 'id_tipo_pago', tables.get('dim_tipoPago', pd.DataFrame()), 'id_tipo_pago','ventas→tipoPago_huerfanos')
        _orphans(mant,   'id_cliente',   tables.get('dim_cliente',  pd.DataFrame()), 'id_cliente',  'mant→clientes_huerfanos')
        _orphans(mant,   'id_tipo_mantenimiento',
                 tables.get('dim_tipoMantenimiento', pd.DataFrame()),
                 'id_tipo_mantenimiento', 'mant→tipoMant_huerfanos')

        return results


# ──────────────────────────────────────────────────────────────────────────────
# MAIN  (ejecución directa)
# ──────────────────────────────────────────────────────────────────────────────

def main(input_path: str, output_path: str):
    log.info(f"Leyendo: {input_path}")
    df_raw = pd.read_excel(input_path, sheet_name='datos_concesionario', dtype=str)
    log.info(f"Leídos {len(df_raw):,} registros")

    transformer = DataTransformer(DEFAULT_CONFIG)
    tables = transformer.transform_all({'datos_concesionario': df_raw})

    integrity = transformer.validate_referential_integrity(tables)
    if integrity:
        log.info("─── Integridad referencial ───────────────────────────")
        for k, v in integrity.items():
            status = "⚠️ " if v > 0 else "✅"
            log.info(f"  {status} {k}: {v} huérfanos")
        log.info("──────────────────────────────────────────────────────")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for name, tbl in tables.items():
            if tbl is not None and not tbl.empty:
                tbl.to_excel(writer, sheet_name=name, index=False)
                log.info(f"  Hoja '{name}' guardada ({len(tbl):,} filas)")

    log.info(f"\n✅ Modelo estrella guardado en: {output_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input',  default='data/raw/datos_concesionario_raw.xlsx')
    parser.add_argument('--output', default='data/transformed/modelo_estrella.xlsx')
    args = parser.parse_args()
    main(args.input, args.output)