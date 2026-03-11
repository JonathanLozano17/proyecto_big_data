"""
transform_data.py
Transforma el Excel crudo del concesionario a un modelo estrella.
Output: data/transformed/modelo_estrella.xlsx  (una hoja por tabla)

Uso:
    python transform_data.py
    python transform_data.py --input data/raw/datos_concesionario_raw.xlsx
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
    """Convierte datos desnormalizados del concesionario a modelo estrella."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or DEFAULT_CONFIG

    # ── Punto de entrada ──────────────────────────────────────────────────────

    def transform_all(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Recibe {'datos_concesionario': df_raw} y retorna todas las tablas."""
        df_raw = data_dict.get('datos_concesionario')
        if df_raw is None:
            log.error("No se encontró 'datos_concesionario' en el diccionario de entrada.")
            return {}

        log.info(f"DataFrame recibido: {len(df_raw):,} filas × {len(df_raw.columns)} columnas")

        df = self._normalize_all_text(df_raw.copy())

        # Dimensiones
        dim_tiempo            = self._create_dim_tiempo(df)
        dim_ciudad            = self._create_dim_ciudad(df)
        dim_cliente           = self._create_dim_cliente(df)
        dim_sucursal          = self._create_dim_sucursal(df)
        dim_vehiculo          = self._create_dim_vehiculo(df)
        dim_vendedor          = self._create_dim_vendedor(df)
        dim_tipo_pago         = self._create_dim_tipo_pago(df)
        dim_tipo_mantenimiento = self._create_dim_tipo_mantenimiento(df)

        # Hechos
        hecho_ventas          = self._create_hecho_ventas(df, dim_tiempo)
        hecho_mantenimiento   = self._create_hecho_mantenimiento(df, dim_tiempo)

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

        log.info("─── Resultados ───────────────────────────────")
        for name, tbl in result.items():
            if tbl is not None and not tbl.empty:
                log.info(f"  {name:<28} {len(tbl):>6,} filas  ×  {len(tbl.columns)} cols")
        log.info("──────────────────────────────────────────────")

        return result

    # ── Normalización de texto ────────────────────────────────────────────────

    def _normalize_text_series(self, series: pd.Series,
                               default: str = 'no identificado',
                               replace_ñ: bool = False) -> pd.Series:
        """Limpia una columna de texto: strip, lower, sin tildes, sin caracteres raros."""

        def _clean(text):
            if pd.isna(text) or text is None:
                return default
            s = str(text).strip()
            if not s or s.lower() in ('nan', 'none', 'null', 'n/a', 'sin dato', '?', ''):
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

    def _clean_id(self, series: pd.Series) -> pd.Series:
        cleaned = pd.to_numeric(series, errors='coerce')
        return cleaned.where(cleaned > 0)   # IDs negativos o 0 → NaN

    def _clean_text(self, series: pd.Series) -> pd.Series:
        return self._normalize_text_series(series, replace_ñ=False)

    def _clean_date(self, series: pd.Series) -> pd.Series:
        FMTS = ['%Y-%m-%d','%d/%m/%Y','%d-%m-%Y','%Y/%m/%d',
                '%d.%m.%Y','%b %d, %Y','%d-%b-%Y','%Y%m%d']

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

        if self.config['validation']['reject_future_dates']:
            dates = dates.where(dates <= pd.Timestamp.now(), pd.NaT)

        min_d = pd.Timestamp(self.config['validation']['min_date'])
        dates = dates.where(dates >= min_d, pd.NaT)
        return dates

    def _clean_price(self, series: pd.Series) -> pd.Series:
        lo = self.config['validation']['min_price']
        hi = self.config['validation']['max_price']

        def _parse(val):
            if pd.isna(val):
                return None
            s = re.sub(r'[$€£\s]', '', str(val))   # quitar símbolo moneda
            s = re.sub(r'[usd|USD]', '', s)          # quitar "USD"
            # Detectar si coma es decimal o miles
            if ',' in s and '.' in s:
                s = s.replace(',', '')               # 1.234,56 → quitar comas
            elif ',' in s and s.count(',') == 1:
                parts = s.split(',')
                if len(parts[1]) <= 2:
                    s = s.replace(',', '.')          # 1234,56 → 1234.56
                else:
                    s = s.replace(',', '')           # 1,234 → 1234
            s = re.sub(r'[^\d.]', '', s)
            try:
                return float(s)
            except ValueError:
                return None

        cleaned = series.apply(_parse)
        return cleaned.clip(lo, hi)

    def _clean_discount(self, series: pd.Series) -> pd.Series:
        def _parse(val):
            if pd.isna(val):
                return 0.0
            s = re.sub(r'[^\d.]', '', str(val).replace('%', '').replace('descuento', '').strip())
            try:
                v = float(s)
                # Si viene como decimal (0.15) convertir a porcentaje
                return v * 100 if v <= 1 else v
            except ValueError:
                return 0.0
        return series.apply(_parse).clip(0, 100).fillna(0)

    def _clean_boolean(self, series: pd.Series) -> pd.Series:
        TRUE_SET  = {'1','si','sí','true','y','yes','verdadero','t'}
        FALSE_SET = {'0','no','false','n','not','falso','f'}

        def _parse(val):
            if pd.isna(val):
                return 0
            s = str(val).lower().strip()
            if s in TRUE_SET:  return 1
            if s in FALSE_SET: return 0
            try:   return int(bool(float(s)))
            except: return 0

        return series.apply(_parse).astype(int)

    def _clean_quantity(self, series: pd.Series) -> pd.Series:
        def _parse(val):
            if pd.isna(val): return 0.0
            s = re.sub(r'[^\d.]', '', str(val))
            try: return max(0.0, float(s))
            except: return 0.0
        return series.apply(_parse).fillna(0)

    # ── Normalización de dominios ─────────────────────────────────────────────

    def _normalize_city(self, name: str) -> str:
        CITY_MAP = {
            'bogota':'Bogotá','bogotá':'Bogotá','bogota dc':'Bogotá',
            'bogota d c':'Bogotá','santa fe de bogota':'Bogotá',
            'medellin':'Medellín','medellín':'Medellín','medallo':'Medellín',
            'cali':'Cali','santiago de cali':'Cali',
            'barranquilla':'Barranquilla','b quilla':'Barranquilla',
            'cartagena':'Cartagena','cartagena de indias':'Cartagena','ctg':'Cartagena',
            'bucaramanga':'Bucaramanga','b manga':'Bucaramanga','buca':'Bucaramanga',
            'pereira':'Pereira','cucuta':'Cúcuta','cúcuta':'Cúcuta',
            'san jose de cucuta':'Cúcuta','santa marta':'Santa Marta',
            'smarta':'Santa Marta','ibague':'Ibagué','ibagué':'Ibagué',
            'manizales':'Manizales','pasto':'Pasto','san juan de pasto':'Pasto',
        }
        if pd.isna(name) or name == 'no identificado':
            return 'no identificado'
        key = str(name).lower().strip()
        if key in CITY_MAP:
            return CITY_MAP[key]
        for k, v in CITY_MAP.items():
            if k in key:
                return v
        return name.title()

    def _validate_email(self, email: str) -> str:
        FIXES = {
            'gmial.com':'gmail.com','gmai.com':'gmail.com',
            'hotmai.com':'hotmail.com','hotmil.com':'hotmail.com',
            'yaho.com':'yahoo.com','yaho.es':'yahoo.es',
            'outlok.com':'outlook.com',
        }
        PATTERN = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'

        if pd.isna(email) or email in ('no identificado', ''):
            return 'no identificado'
        em = re.sub(r'\s+', '', str(email).lower())
        for wrong, right in FIXES.items():
            em = em.replace(wrong, right)
        return em if re.match(PATTERN, em) else 'email_invalido'

    # ── Dimensiones ───────────────────────────────────────────────────────────

    def _create_dim_tiempo(self, df: pd.DataFrame) -> pd.DataFrame:
        ventas = self._clean_date(df['fecha_venta'])
        mantos = self._clean_date(df['fecha_mantenimiento'])
        all_dates = pd.concat([ventas, mantos]).dropna().unique()
        if len(all_dates) == 0:
            return pd.DataFrame()

        t = pd.DataFrame({'fecha_completa': sorted(all_dates)})
        t['id_tiempo']   = t['fecha_completa'].dt.strftime('%Y%m%d').astype(int)
        t['año']         = t['fecha_completa'].dt.year
        t['mes']         = t['fecha_completa'].dt.month
        t['nombre_mes']  = t['fecha_completa'].dt.strftime('%B').str.capitalize()
        t['trimestre']   = t['fecha_completa'].dt.quarter
        t['semana']      = t['fecha_completa'].dt.isocalendar().week.astype(int)
        t['dia']         = t['fecha_completa'].dt.day
        t['dia_semana']  = t['fecha_completa'].dt.strftime('%A').str.capitalize()
        t['es_fin_semana'] = (t['fecha_completa'].dt.weekday >= 5).astype(int)
        return t[['id_tiempo','fecha_completa','año','mes','nombre_mes',
                  'trimestre','semana','dia','dia_semana','es_fin_semana']]

    def _create_dim_ciudad(self, df: pd.DataFrame) -> pd.DataFrame:
        cli_cols = ['id_ciudad_cliente','ciudad_cliente','departamento_cliente','region_cliente']
        suc_cols = ['id_ciudad_sucursal','ciudad_sucursal','departamento_sucursal','region_sucursal']

        frames = []
        for cols in [cli_cols, suc_cols]:
            if all(c in df.columns for c in cols):
                tmp = df[cols].copy()
                tmp.columns = ['id_ciudad','nombre_ciudad','departamento','region']
                frames.append(tmp)

        if not frames:
            return pd.DataFrame()

        out = pd.concat(frames).drop_duplicates()
        out['id_ciudad'] = self._clean_id(out['id_ciudad'])
        out = out[out['id_ciudad'].notna()]
        out['nombre_ciudad'] = out['nombre_ciudad'].apply(self._normalize_city)
        out['departamento']  = self._clean_text(out['departamento'])
        out['region']        = self._clean_text(out['region'])
        out = out.drop_duplicates(subset=['id_ciudad']).sort_values('id_ciudad')
        return out.reset_index(drop=True)

    def _create_dim_cliente(self, df: pd.DataFrame) -> pd.DataFrame:
        COLS = ['id_cliente','cliente_nombre','cliente_edad','cliente_genero',
                'cliente_tipo','cliente_email','id_ciudad_cliente']
        src = df[df['id_cliente'].notna()][COLS].drop_duplicates('id_cliente').copy()

        src['id_cliente']       = self._clean_id(src['id_cliente'])
        src['id_ciudad_cliente']= self._clean_id(src['id_ciudad_cliente'])
        src['cliente_nombre']   = self._clean_text(src['cliente_nombre'])
        src['cliente_email']    = src['cliente_email'].apply(self._validate_email)

        src['cliente_edad'] = pd.to_numeric(src['cliente_edad'], errors='coerce').clip(18, 100).fillna(30).astype(int)

        TIPO_MAP = {
            'nuevo':'nuevo','new':'nuevo',
            'recurrente':'recurrente','recurrent':'recurrente',
            'vip':'vip',
            'empresarial':'empresarial','empresa':'empresarial',
            'potencial':'potencial',
        }
        src['cliente_tipo'] = src['cliente_tipo'].map(TIPO_MAP).fillna('nuevo')

        GEN_MAP = {
            'm':'M','masculino':'M','male':'M',
            'f':'F','femenino':'F','female':'F',
        }
        src['cliente_genero'] = src['cliente_genero'].map(GEN_MAP).fillna('M')

        return src.rename(columns={
            'cliente_nombre':'nombre','cliente_edad':'edad',
            'cliente_genero':'genero','cliente_tipo':'tipo_cliente',
            'cliente_email':'email','id_ciudad_cliente':'id_ciudad',
        }).sort_values('id_cliente').reset_index(drop=True)

    def _create_dim_sucursal(self, df: pd.DataFrame) -> pd.DataFrame:
        COLS = ['id_sucursal','sucursal_nombre','id_ciudad_sucursal','sucursal_tamano','sucursal_zona']
        # nombre real de la columna puede tener ñ → buscar dinámicamente
        actual_tam = next((c for c in df.columns if 'tama' in c.lower()), None)
        col_map = {
            'id_sucursal':'id_sucursal',
            'sucursal_nombre':'sucursal_nombre',
            'id_ciudad_sucursal':'id_ciudad_sucursal',
            actual_tam: 'tamano',
            'sucursal_zona':'sucursal_zona',
        }
        cols_exist = {k:v for k,v in col_map.items() if k and k in df.columns}
        src = df[df['id_sucursal'].notna()][list(cols_exist.keys())].drop_duplicates('id_sucursal').copy()
        src.rename(columns=cols_exist, inplace=True)

        src['id_sucursal']       = self._clean_id(src['id_sucursal'])
        src['id_ciudad_sucursal']= self._clean_id(src['id_ciudad_sucursal'])
        for col in ['sucursal_nombre','tamano','sucursal_zona']:
            if col in src.columns:
                src[col] = self._clean_text(src[col])

        return src.rename(columns={
            'sucursal_nombre':'nombre','id_ciudad_sucursal':'id_ciudad',
            'tamano':'tamaño','sucursal_zona':'zona',
        }).sort_values('id_sucursal').reset_index(drop=True)

    def _create_dim_vehiculo(self, df: pd.DataFrame) -> pd.DataFrame:
        COLS = ['id_vehiculo','vehiculo_marca','vehiculo_modelo','vehiculo_tipo',
                'vehiculo_ano','vehiculo_cilindraje','vehiculo_combustible','vehiculo_color']
        # columna año puede haberse normalizado quitando la ñ → ño → no :(
        actual_año = next((c for c in df.columns if 'vehiculo_a' in c.lower()), 'vehiculo_año')
        cols_use = [c for c in [
            'id_vehiculo','vehiculo_marca','vehiculo_modelo','vehiculo_tipo',
            actual_año,'vehiculo_cilindraje','vehiculo_combustible','vehiculo_color'
        ] if c in df.columns]

        src = df[df['id_vehiculo'].notna()][cols_use].drop_duplicates('id_vehiculo').copy()
        src.rename(columns={actual_año: 'vehiculo_año'}, inplace=True)

        src['id_vehiculo'] = self._clean_id(src['id_vehiculo'])
        for col in ['vehiculo_marca','vehiculo_modelo','vehiculo_tipo','vehiculo_color']:
            if col in src.columns:
                src[col] = self._clean_text(src[col])

        if 'vehiculo_año' in src.columns:
            src['vehiculo_año'] = pd.to_numeric(src['vehiculo_año'], errors='coerce').clip(2012, 2025).fillna(2020).astype(int)
        if 'vehiculo_cilindraje' in src.columns:
            src['vehiculo_cilindraje'] = pd.to_numeric(src['vehiculo_cilindraje'], errors='coerce').clip(600, 6000).fillna(1600).astype(int)

        COMB_MAP = {
            'gasolina':'Gasolina','diesel':'Diesel',
            'hibrido':'Híbrido','electrico':'Eléctrico',
            'gas natural':'Gas Natural',
        }
        if 'vehiculo_combustible' in src.columns:
            src['vehiculo_combustible'] = (
                src['vehiculo_combustible']
                .apply(lambda x: next((v for k,v in COMB_MAP.items() if k in str(x).lower()), 'Gasolina'))
            )

        return src.rename(columns={
            'vehiculo_marca':'marca','vehiculo_modelo':'modelo',
            'vehiculo_tipo':'tipo','vehiculo_año':'año_modelo',
            'vehiculo_cilindraje':'cilindraje','vehiculo_combustible':'tipo_combustible',
            'vehiculo_color':'color',
        }).sort_values('id_vehiculo').reset_index(drop=True)

    def _create_dim_vendedor(self, df: pd.DataFrame) -> pd.DataFrame:
        src = df[df['tipo_registro'].str.lower() == 'venta'].copy()
        src = src[src['id_vendedor'].notna()][['id_vendedor','vendedor_nombre','vendedor_experiencia','id_sucursal']]
        src = src.drop_duplicates('id_vendedor').copy()

        src['id_vendedor']           = self._clean_id(src['id_vendedor'])
        src['id_sucursal']           = self._clean_id(src['id_sucursal'])
        src['vendedor_nombre']       = self._clean_text(src['vendedor_nombre'])
        src['vendedor_experiencia']  = pd.to_numeric(src['vendedor_experiencia'], errors='coerce').clip(0, 40).fillna(0).astype(int)

        return src.rename(columns={
            'vendedor_nombre':'nombre','vendedor_experiencia':'experiencia_años',
        }).sort_values('id_vendedor').reset_index(drop=True)

    def _create_dim_tipo_pago(self, df: pd.DataFrame) -> pd.DataFrame:
        COLS = ['id_tipo_pago','tipo_pago_nombre','entidad_financiera',
                'plazo_meses','tasa_interes','requiere_aprobacion']
        src = df[(df['tipo_registro'].str.lower()=='venta') & df['id_tipo_pago'].notna()][COLS]
        src = src.drop_duplicates('id_tipo_pago').copy()

        src['id_tipo_pago']  = self._clean_id(src['id_tipo_pago'])
        src['entidad_financiera'] = self._clean_text(src['entidad_financiera'])

        PAGO_MAP = {
            'contado':'contado',
            'credito':'credito','cr dito':'credito',
            'leasing':'leasing',
        }
        src['tipo_pago_nombre'] = (
            src['tipo_pago_nombre']
            .apply(lambda x: next((v for k,v in PAGO_MAP.items() if k in str(x).lower()), 'contado'))
        )

        for col in ['plazo_meses','tasa_interes','requiere_aprobacion']:
            src[col] = pd.to_numeric(src[col], errors='coerce').fillna(0)

        return src.rename(columns={'tipo_pago_nombre':'tipo_pago'}).sort_values('id_tipo_pago').reset_index(drop=True)

    def _create_dim_tipo_mantenimiento(self, df: pd.DataFrame) -> pd.DataFrame:
        COLS = ['id_tipo_mantenimiento','tipo_mantenimiento_nombre',
                'tipo_mantenimiento_descripcion','incluye_garantia',
                'meses_garantia','kilometros_garantia']
        src = df[(df['tipo_registro'].str.lower()=='mantenimiento') & df['id_tipo_mantenimiento'].notna()][COLS]
        src = src.drop_duplicates('id_tipo_mantenimiento').copy()

        src['id_tipo_mantenimiento'] = self._clean_id(src['id_tipo_mantenimiento'])
        src['tipo_mantenimiento_nombre']      = self._clean_text(src['tipo_mantenimiento_nombre'])
        src['tipo_mantenimiento_descripcion'] = self._clean_text(src['tipo_mantenimiento_descripcion'])
        for col in ['incluye_garantia','meses_garantia','kilometros_garantia']:
            src[col] = pd.to_numeric(src[col], errors='coerce').fillna(0).astype(int)

        return src.rename(columns={
            'tipo_mantenimiento_nombre':'nombre_tipo',
            'tipo_mantenimiento_descripcion':'descripcion',
        }).sort_values('id_tipo_mantenimiento').reset_index(drop=True)

    # ── Hechos ────────────────────────────────────────────────────────────────

    def _create_hecho_ventas(self, df: pd.DataFrame, dim_tiempo: pd.DataFrame) -> pd.DataFrame:
        src = df[df['tipo_registro'].str.lower() == 'venta'].copy()
        if src.empty:
            return pd.DataFrame()

        src['_fecha_clean'] = self._clean_date(src['fecha_venta'])

        if not dim_tiempo.empty:
            t_map = dict(zip(dim_tiempo['fecha_completa'], dim_tiempo['id_tiempo']))
            src['id_tiempo'] = src['_fecha_clean'].map(t_map)

        for col in ['id_cliente','id_vehiculo','id_vendedor','id_sucursal','id_tipo_pago']:
            src[col] = self._clean_id(src[col])

        src['precio_venta']   = self._clean_price(src['precio_venta'])
        src['costo_vehiculo'] = self._clean_price(src['costo_vehiculo'])
        src['descuento']      = self._clean_discount(src['descuento'])
        src['financiado']     = self._clean_boolean(src['financiado'])
        src['cantidad']       = self._clean_quantity(src['cantidad'])
        src['comision_vendedor'] = pd.to_numeric(src['comision_vendedor'], errors='coerce')

        src['margen_ganancia'] = src['precio_venta'] - src['costo_vehiculo']
        src['precio_neto']     = src['precio_venta'] * (1 - src['descuento'] / 100)

        BASE_COLS = ['id_venta','id_tiempo','id_cliente','id_vehiculo','id_vendedor',
                     'id_sucursal','id_tipo_pago','cantidad','precio_venta','costo_vehiculo',
                     'descuento','precio_neto','margen_ganancia','financiado','comision_vendedor']
        hecho = src[[c for c in BASE_COLS if c in src.columns]].copy()
        hecho = hecho.dropna(subset=['id_cliente','id_vehiculo'])
        return hecho.reset_index(drop=True)

    def _create_hecho_mantenimiento(self, df: pd.DataFrame, dim_tiempo: pd.DataFrame) -> pd.DataFrame:
        src = df[df['tipo_registro'].str.lower() == 'mantenimiento'].copy()
        if src.empty:
            return pd.DataFrame()

        src['_fecha_clean'] = self._clean_date(src['fecha_mantenimiento'])

        if not dim_tiempo.empty:
            t_map = dict(zip(dim_tiempo['fecha_completa'], dim_tiempo['id_tiempo']))
            src['id_tiempo'] = src['_fecha_clean'].map(t_map)

        for col in ['id_cliente','id_vehiculo','id_sucursal','id_tipo_mantenimiento']:
            src[col] = self._clean_id(src[col])

        src['costo_servicio']  = self._clean_price(src['costo_servicio'])
        src['costo_repuestos'] = self._clean_price(src['costo_repuestos'])
        src['repuestos_usados']= self._clean_quantity(src['repuestos_usados'])
        src['horas_taller']    = pd.to_numeric(src['horas_taller'], errors='coerce')
        src['kilometraje_vehiculo'] = pd.to_numeric(src['kilometraje_vehiculo'], errors='coerce')

        src['costo_total'] = src['costo_servicio'].fillna(0) + src['costo_repuestos'].fillna(0)

        BASE_COLS = ['id_tiempo','id_cliente','id_vehiculo','id_sucursal',
                     'id_tipo_mantenimiento','costo_servicio','costo_repuestos',
                     'costo_total','repuestos_usados','horas_taller','kilometraje_vehiculo']
        hecho = src[[c for c in BASE_COLS if c in src.columns]].copy()
        hecho = hecho.dropna(subset=['id_cliente','id_vehiculo'])
        return hecho.reset_index(drop=True)

    # ── Validación integridad referencial ─────────────────────────────────────

    def validate_referential_integrity(self, tables: Dict[str, pd.DataFrame]) -> Dict[str, int]:
        results = {}

        def _orphans(fact_df, fact_col, dim_df, dim_col, label):
            if fact_df is None or fact_df.empty: return
            if dim_df is None or dim_df.empty: return
            valid = set(dim_df[dim_col].dropna())
            mask  = fact_df[fact_col].notna() & ~fact_df[fact_col].isin(valid)
            results[label] = int(mask.sum())

        ventas = tables.get('hecho_ventas', pd.DataFrame())
        mant   = tables.get('hecho_mantenimiento', pd.DataFrame())

        _orphans(ventas, 'id_cliente',   tables.get('dim_cliente'),  'id_cliente',  'ventas_clientes_sin_dim')
        _orphans(ventas, 'id_vehiculo',  tables.get('dim_vehiculo'), 'id_vehiculo', 'ventas_vehiculos_sin_dim')
        _orphans(ventas, 'id_vendedor',  tables.get('dim_vendedor'), 'id_vendedor', 'ventas_vendedores_sin_dim')
        _orphans(ventas, 'id_tipo_pago', tables.get('dim_tipoPago'), 'id_tipo_pago','ventas_tipoPago_sin_dim')
        _orphans(mant,   'id_cliente',   tables.get('dim_cliente'),  'id_cliente',  'mant_clientes_sin_dim')
        _orphans(mant,   'id_tipo_mantenimiento', tables.get('dim_tipoMantenimiento'),
                 'id_tipo_mantenimiento', 'mant_tipo_sin_dim')

        return results


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main(input_path: str, output_path: str):
    # Leer datos crudos
    log.info(f"Leyendo: {input_path}")
    df_raw = pd.read_excel(input_path, sheet_name='datos_concesionario', dtype=str)
    log.info(f"Leídos {len(df_raw):,} registros")

    # Transformar
    transformer = DataTransformer(DEFAULT_CONFIG)
    tables = transformer.transform_all({'datos_concesionario': df_raw})

    # Validar integridad referencial
    integrity = transformer.validate_referential_integrity(tables)
    if integrity:
        log.info("─── Integridad referencial ───────────────────")
        for k, v in integrity.items():
            status = "⚠️ " if v > 0 else "✅ "
            log.info(f"  {status}{k}: {v} huérfanos")
        log.info("──────────────────────────────────────────────")

    # Guardar modelo estrella
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for name, tbl in tables.items():
            if tbl is not None and not tbl.empty:
                tbl.to_excel(writer, sheet_name=name, index=False)
                log.info(f"  Hoja '{name}' guardada ({len(tbl):,} filas)")

    log.info(f"\n✅ Modelo estrella guardado en: {output_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Transforma datos crudos del concesionario a modelo estrella')
    parser.add_argument('--input',  default='data/raw/datos_concesionario_raw.xlsx',
                        help='Ruta al Excel crudo')
    parser.add_argument('--output', default='data/transformed/modelo_estrella.xlsx',
                        help='Ruta de salida del modelo estrella')
    args = parser.parse_args()
    main(args.input, args.output)