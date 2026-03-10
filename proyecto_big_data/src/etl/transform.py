import pandas as pd
import numpy as np
import logging
from typing import Dict, Any

class DataTransformer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.transformations_log = []
        
    def transform_all(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Transforma datos desnormalizados a modelo estrella"""
        logging.info("Iniciando transformación a modelo estrella...")
        
        # Obtener el DataFrame único (viene como 'datos_concesionario')
        df_raw = data_dict.get('datos_concesionario')
        if df_raw is None:
            logging.error("No se encontró el DataFrame 'datos_concesionario'")
            return {}
        
        logging.info(f"DataFrame recibido: {len(df_raw)} filas, {len(df_raw.columns)} columnas")
        
        # Crear dimensiones y hechos
        dim_tiempo = self._create_dim_tiempo(df_raw)
        dim_ciudad = self._create_dim_ciudad(df_raw)
        dim_cliente = self._create_dim_cliente(df_raw, dim_ciudad)
        dim_sucursal = self._create_dim_sucursal(df_raw, dim_ciudad)
        dim_vehiculo = self._create_dim_vehiculo(df_raw)
        dim_vendedor = self._create_dim_vendedor(df_raw)
        dim_tipo_pago = self._create_dim_tipo_pago(df_raw)
        dim_tipo_mantenimiento = self._create_dim_tipo_mantenimiento(df_raw)
        
        # Crear tablas de hechos
        hecho_ventas = self._create_hecho_ventas(
            df_raw, dim_tiempo, dim_cliente, dim_vehiculo, 
            dim_vendedor, dim_sucursal, dim_tipo_pago
        )
        
        hecho_mantenimiento = self._create_hecho_mantenimiento(
            df_raw, dim_tiempo, dim_cliente, dim_vehiculo, 
            dim_sucursal, dim_tipo_mantenimiento
        )
        
        # Diccionario con todas las tablas
        transformed_data = {
            'dim_tiempo': dim_tiempo,
            'dim_ciudad': dim_ciudad,
            'dim_cliente': dim_cliente,
            'dim_sucursal': dim_sucursal,
            'dim_vehiculo': dim_vehiculo,
            'dim_vendedor': dim_vendedor,
            'dim_tipoPago': dim_tipo_pago,
            'tipo_mantenimiento': dim_tipo_mantenimiento,
            'hecho_ventas': hecho_ventas,
            'hecho_mantenimiento': hecho_mantenimiento
        }
        
        # Logging de resultados
        logging.info("\n📊 Resultados de la transformación:")
        for name, df in transformed_data.items():
            if df is not None and not df.empty:
                logging.info(f"  → {name}: {len(df)} filas, {len(df.columns)} columnas")
        
        return transformed_data
    
    def _clean_id(self, series: pd.Series) -> pd.Series:
        """Limpia y convierte IDs a numérico"""
        if series is None:
            return pd.Series(dtype='float64')
        
        cleaned = pd.to_numeric(series, errors='coerce')
        cleaned = cleaned.where(cleaned > 0, None)
        return cleaned
    
    def _clean_text(self, series: pd.Series) -> pd.Series:
        """Limpia campos de texto"""
        if series is None:
            return pd.Series(dtype='object')
        
        if series.dtype == 'object':
            cleaned = series.astype(str).str.strip()
            cleaned = cleaned.replace(['', 'nan', 'none', 'null', 'None', 'NaN', 'nat'], pd.NA)
            cleaned = cleaned.where(pd.notna(cleaned), None)
            return cleaned
        return series
    
    def _clean_date(self, series: pd.Series) -> pd.Series:
        """Limpia y convierte fechas"""
        if series is None:
            return pd.Series(dtype='datetime64[ns]')
        
        dates = pd.to_datetime(series, errors='coerce')
        
        # Validar fechas según configuración
        if self.config.get('validation', {}).get('reject_future_dates', True):
            today = pd.Timestamp.now()
            dates = dates.where(dates <= today, pd.NaT)
        
        min_date = pd.Timestamp(self.config.get('validation', {}).get('min_date', '2020-01-01'))
        dates = dates.where(dates >= min_date, pd.NaT)
        
        return dates
    
    def _create_dim_tiempo(self, df: pd.DataFrame) -> pd.DataFrame:
        """Crea dimensión tiempo a partir de fechas únicas"""
        # Extraer todas las fechas de ventas y mantenimiento
        fechas_ventas = pd.to_datetime(df['fecha_venta'], errors='coerce')
        fechas_mantenimiento = pd.to_datetime(df['fecha_mantenimiento'], errors='coerce')
        
        # Combinar fechas únicas
        todas_fechas = pd.concat([fechas_ventas, fechas_mantenimiento]).dropna().unique()
        
        if len(todas_fechas) == 0:
            return pd.DataFrame()
        
        # Crear DataFrame de fechas
        fechas_df = pd.DataFrame({'fecha_completa': sorted(todas_fechas)})
        fechas_df['id_tiempo'] = fechas_df['fecha_completa'].dt.strftime('%Y%m%d')
        fechas_df['año'] = fechas_df['fecha_completa'].dt.year
        fechas_df['mes'] = fechas_df['fecha_completa'].dt.month
        fechas_df['nombre_mes'] = fechas_df['fecha_completa'].dt.strftime('%B')
        fechas_df['trimestre'] = fechas_df['fecha_completa'].dt.quarter
        fechas_df['dia'] = fechas_df['fecha_completa'].dt.day
        fechas_df['dia_semana'] = fechas_df['fecha_completa'].dt.strftime('%A')
        fechas_df['es_fin_semana'] = (fechas_df['fecha_completa'].dt.weekday >= 5).astype(int)
        
        return fechas_df[['id_tiempo', 'fecha_completa', 'año', 'mes', 'nombre_mes', 
                         'trimestre', 'dia', 'dia_semana', 'es_fin_semana']]
    
    def _create_dim_ciudad(self, df: pd.DataFrame) -> pd.DataFrame:
        """Crea dimensión ciudad a partir de datos únicos de ciudades"""
        ciudades = []
        
        # Extraer ciudades de clientes
        if 'id_ciudad_cliente' in df.columns and 'ciudad_cliente' in df.columns:
            clientes_ciudades = df[['id_ciudad_cliente', 'ciudad_cliente', 'departamento_cliente', 'region_cliente']].drop_duplicates()
            clientes_ciudades.columns = ['id_ciudad', 'nombre_ciudad', 'departamento', 'region']
            ciudades.append(clientes_ciudades)
        
        # Extraer ciudades de sucursales
        if 'id_ciudad_sucursal' in df.columns and 'ciudad_sucursal' in df.columns:
            sucursales_ciudades = df[['id_ciudad_sucursal', 'ciudad_sucursal', 'departamento_sucursal', 'region_sucursal']].drop_duplicates()
            sucursales_ciudades.columns = ['id_ciudad', 'nombre_ciudad', 'departamento', 'region']
            ciudades.append(sucursales_ciudades)
        
        if not ciudades:
            return pd.DataFrame()
        
        # Combinar y limpiar
        df_ciudades = pd.concat(ciudades).drop_duplicates(subset=['id_ciudad'])
        df_ciudades = df_ciudades[df_ciudades['id_ciudad'].notna()]
        df_ciudades['id_ciudad'] = self._clean_id(df_ciudades['id_ciudad'])
        
        for col in ['nombre_ciudad', 'departamento', 'region']:
            if col in df_ciudades.columns:
                df_ciudades[col] = self._clean_text(df_ciudades[col])
        
        # IDs válidos
        df_ciudades = df_ciudades[df_ciudades['id_ciudad'].notna()]
        
        return df_ciudades
    
    def _create_dim_cliente(self, df: pd.DataFrame, dim_ciudad: pd.DataFrame) -> pd.DataFrame:
        """Crea dimensión cliente a partir de datos desnormalizados"""
        # Seleccionar columnas de cliente
        cols_cliente = ['id_cliente', 'cliente_nombre', 'cliente_edad', 'cliente_genero', 
                       'cliente_tipo', 'cliente_email', 'id_ciudad_cliente']
        
        # Filtrar solo donde hay id_cliente
        mask = df['id_cliente'].notna()
        if not mask.any():
            return pd.DataFrame()
        
        clientes = df[mask][cols_cliente].copy()
        clientes = clientes.drop_duplicates(subset=['id_cliente'])
        
        # Limpiar datos
        clientes['id_cliente'] = self._clean_id(clientes['id_cliente'])
        clientes['id_ciudad_cliente'] = self._clean_id(clientes['id_ciudad_cliente'])
        
        for col in ['cliente_nombre', 'cliente_genero', 'cliente_tipo', 'cliente_email']:
            if col in clientes.columns:
                clientes[col] = self._clean_text(clientes[col])
        
        # Limpiar edad
        if 'cliente_edad' in clientes.columns:
            clientes['cliente_edad'] = pd.to_numeric(clientes['cliente_edad'], errors='coerce')
            clientes['cliente_edad'] = clientes['cliente_edad'].clip(18, 100)
        
        # Normalizar tipo_cliente
        if 'cliente_tipo' in clientes.columns:
            clientes['cliente_tipo'] = clientes['cliente_tipo'].str.lower().str.strip()
            tipo_map = {
                'nuevo': 'nuevo', 'nuevo  ': 'nuevo', 'new': 'nuevo',
                'recurrente': 'recurrente', 'recurrente  ': 'recurrente', 'rec': 'recurrente'
            }
            clientes['cliente_tipo'] = clientes['cliente_tipo'].map(tipo_map).fillna('nuevo')
        
        # Renombrar columnas
        clientes = clientes.rename(columns={
            'cliente_nombre': 'nombre',
            'cliente_edad': 'edad',
            'cliente_genero': 'genero',
            'cliente_tipo': 'tipo_cliente',
            'cliente_email': 'email',
            'id_ciudad_cliente': 'id_ciudad'
        })
        
        return clientes
    
    def _create_dim_sucursal(self, df: pd.DataFrame, dim_ciudad: pd.DataFrame) -> pd.DataFrame:
        """Crea dimensión sucursal"""
        cols_sucursal = ['id_sucursal', 'sucursal_nombre', 'id_ciudad_sucursal', 
                        'sucursal_tamaño', 'sucursal_zona']
        
        mask = df['id_sucursal'].notna()
        if not mask.any():
            return pd.DataFrame()
        
        sucursales = df[mask][cols_sucursal].copy()
        sucursales = sucursales.drop_duplicates(subset=['id_sucursal'])
        
        # Limpiar
        sucursales['id_sucursal'] = self._clean_id(sucursales['id_sucursal'])
        sucursales['id_ciudad_sucursal'] = self._clean_id(sucursales['id_ciudad_sucursal'])
        
        for col in ['sucursal_nombre', 'sucursal_tamaño', 'sucursal_zona']:
            if col in sucursales.columns:
                sucursales[col] = self._clean_text(sucursales[col])
        
        # Renombrar
        sucursales = sucursales.rename(columns={
            'sucursal_nombre': 'nombre',
            'id_ciudad_sucursal': 'id_ciudad',
            'sucursal_tamaño': 'tamaño',
            'sucursal_zona': 'zona'
        })
        
        return sucursales
    
    def _create_dim_vehiculo(self, df: pd.DataFrame) -> pd.DataFrame:
        """Crea dimensión vehículo"""
        cols_vehiculo = ['id_vehiculo', 'vehiculo_marca', 'vehiculo_modelo', 'vehiculo_tipo',
                        'vehiculo_año', 'vehiculo_cilindraje', 'vehiculo_combustible', 'vehiculo_color']
        
        mask = df['id_vehiculo'].notna()
        if not mask.any():
            return pd.DataFrame()
        
        vehiculos = df[mask][cols_vehiculo].copy()
        vehiculos = vehiculos.drop_duplicates(subset=['id_vehiculo'])
        
        # Limpiar
        vehiculos['id_vehiculo'] = self._clean_id(vehiculos['id_vehiculo'])
        
        for col in ['vehiculo_marca', 'vehiculo_modelo', 'vehiculo_tipo', 
                   'vehiculo_combustible', 'vehiculo_color']:
            if col in vehiculos.columns:
                vehiculos[col] = self._clean_text(vehiculos[col])
        
        # Limpiar año y cilindraje
        if 'vehiculo_año' in vehiculos.columns:
            vehiculos['vehiculo_año'] = pd.to_numeric(vehiculos['vehiculo_año'], errors='coerce')
            vehiculos['vehiculo_año'] = vehiculos['vehiculo_año'].clip(2015, 2025)
        
        if 'vehiculo_cilindraje' in vehiculos.columns:
            vehiculos['vehiculo_cilindraje'] = pd.to_numeric(vehiculos['vehiculo_cilindraje'], errors='coerce')
            vehiculos['vehiculo_cilindraje'] = vehiculos['vehiculo_cilindraje'].clip(600, 6000)
        
        # Normalizar tipo_combustible
        if 'vehiculo_combustible' in vehiculos.columns:
            vehiculos['vehiculo_combustible'] = vehiculos['vehiculo_combustible'].str.lower().str.strip()
            combustible_map = {
                'gasolina': 'Gasolina', 'gasolina  ': 'Gasolina',
                'diesel': 'Diesel', 'diesel': 'Diesel',
                'hibrido': 'Híbrido', 'híbrido': 'Híbrido',
                'electrico': 'Eléctrico', 'eléctrico': 'Eléctrico'
            }
            vehiculos['vehiculo_combustible'] = vehiculos['vehiculo_combustible'].map(combustible_map).fillna('Gasolina')
        
        # Renombrar
        vehiculos = vehiculos.rename(columns={
            'vehiculo_marca': 'marca',
            'vehiculo_modelo': 'modelo',
            'vehiculo_tipo': 'tipo',
            'vehiculo_año': 'año_modelo',
            'vehiculo_cilindraje': 'cilindraje',
            'vehiculo_combustible': 'tipo_combustible',
            'vehiculo_color': 'color'
        })
        
        return vehiculos
    
    def _create_dim_vendedor(self, df: pd.DataFrame) -> pd.DataFrame:
        """Crea dimensión vendedor"""
        # Solo ventas tienen vendedor
        df_ventas = df[df['tipo_registro'] == 'VENTA']
        
        cols_vendedor = ['id_vendedor', 'vendedor_nombre', 'vendedor_experiencia', 'id_sucursal']
        
        mask = df_ventas['id_vendedor'].notna()
        if not mask.any():
            return pd.DataFrame()
        
        vendedores = df_ventas[mask][cols_vendedor].copy()
        vendedores = vendedores.drop_duplicates(subset=['id_vendedor'])
        
        # Limpiar
        vendedores['id_vendedor'] = self._clean_id(vendedores['id_vendedor'])
        vendedores['id_sucursal'] = self._clean_id(vendedores['id_sucursal'])
        vendedores['vendedor_nombre'] = self._clean_text(vendedores['vendedor_nombre'])
        
        # Limpiar experiencia
        if 'vendedor_experiencia' in vendedores.columns:
            vendedores['vendedor_experiencia'] = pd.to_numeric(vendedores['vendedor_experiencia'], errors='coerce')
            vendedores['vendedor_experiencia'] = vendedores['vendedor_experiencia'].clip(0, 40).fillna(0)
        
        # Renombrar
        vendedores = vendedores.rename(columns={
            'vendedor_nombre': 'nombre',
            'vendedor_experiencia': 'experiencia_anios'
        })
        
        return vendedores
    
    def _create_dim_tipo_pago(self, df: pd.DataFrame) -> pd.DataFrame:
        """Crea dimensión tipo de pago"""
        # Solo ventas tienen tipo de pago
        df_ventas = df[df['tipo_registro'] == 'VENTA']
        
        cols_pago = ['id_tipo_pago', 'tipo_pago_nombre', 'entidad_financiera', 
                    'plazo_meses', 'tasa_interes', 'requiere_aprobacion']
        
        mask = df_ventas['id_tipo_pago'].notna()
        if not mask.any():
            return pd.DataFrame()
        
        tipos_pago = df_ventas[mask][cols_pago].copy()
        tipos_pago = tipos_pago.drop_duplicates(subset=['id_tipo_pago'])
        
        # Limpiar
        tipos_pago['id_tipo_pago'] = self._clean_id(tipos_pago['id_tipo_pago'])
        
        for col in ['tipo_pago_nombre', 'entidad_financiera']:
            if col in tipos_pago.columns:
                tipos_pago[col] = self._clean_text(tipos_pago[col])
        
        # Normalizar tipo_pago
        if 'tipo_pago_nombre' in tipos_pago.columns:
            tipos_pago['tipo_pago_nombre'] = tipos_pago['tipo_pago_nombre'].str.lower().str.strip()
            pago_map = {
                'contado': 'contado', 'credito': 'credito', 'crédito': 'credito',
                'leasing': 'leasing', 'leassing': 'leasing'
            }
            tipos_pago['tipo_pago_nombre'] = tipos_pago['tipo_pago_nombre'].map(pago_map).fillna('contado')
        
        # Limpiar numéricos
        if 'plazo_meses' in tipos_pago.columns:
            tipos_pago['plazo_meses'] = pd.to_numeric(tipos_pago['plazo_meses'], errors='coerce').fillna(0)
        if 'tasa_interes' in tipos_pago.columns:
            tipos_pago['tasa_interes'] = pd.to_numeric(tipos_pago['tasa_interes'], errors='coerce').fillna(0)
        if 'requiere_aprobacion' in tipos_pago.columns:
            tipos_pago['requiere_aprobacion'] = pd.to_numeric(tipos_pago['requiere_aprobacion'], errors='coerce').fillna(0)
        
        # Renombrar
        tipos_pago = tipos_pago.rename(columns={
            'tipo_pago_nombre': 'tipo_pago'
        })
        
        return tipos_pago
    
    def _create_dim_tipo_mantenimiento(self, df: pd.DataFrame) -> pd.DataFrame:
        """Crea dimensión tipo de mantenimiento"""
        # Solo mantenimientos tienen tipo
        df_mant = df[df['tipo_registro'] == 'MANTENIMIENTO']
        
        cols_mant = ['id_tipo_mantenimiento', 'tipo_mantenimiento_nombre', 'tipo_mantenimiento_descripcion',
                    'incluye_garantia', 'meses_garantia', 'kilometros_garantia']
        
        mask = df_mant['id_tipo_mantenimiento'].notna()
        if not mask.any():
            return pd.DataFrame()
        
        tipos_mant = df_mant[mask][cols_mant].copy()
        tipos_mant = tipos_mant.drop_duplicates(subset=['id_tipo_mantenimiento'])
        
        # Limpiar
        tipos_mant['id_tipo_mantenimiento'] = self._clean_id(tipos_mant['id_tipo_mantenimiento'])
        
        for col in ['tipo_mantenimiento_nombre', 'tipo_mantenimiento_descripcion']:
            if col in tipos_mant.columns:
                tipos_mant[col] = self._clean_text(tipos_mant[col])
        
        # Limpiar numéricos
        if 'incluye_garantia' in tipos_mant.columns:
            tipos_mant['incluye_garantia'] = pd.to_numeric(tipos_mant['incluye_garantia'], errors='coerce').fillna(0)
        if 'meses_garantia' in tipos_mant.columns:
            tipos_mant['meses_garantia'] = pd.to_numeric(tipos_mant['meses_garantia'], errors='coerce').fillna(0)
        if 'kilometros_garantia' in tipos_mant.columns:
            tipos_mant['kilometros_garantia'] = pd.to_numeric(tipos_mant['kilometros_garantia'], errors='coerce').fillna(0)
        
        # Renombrar
        tipos_mant = tipos_mant.rename(columns={
            'tipo_mantenimiento_nombre': 'nombre_tipo',
            'tipo_mantenimiento_descripcion': 'descripcion'
        })
        
        return tipos_mant
    
    def _create_hecho_ventas(self, df, dim_tiempo, dim_cliente, dim_vehiculo, 
                            dim_vendedor, dim_sucursal, dim_tipo_pago):
        """Crea tabla de hechos de ventas"""
        # Filtrar solo ventas
        df_ventas = df[df['tipo_registro'] == 'VENTA'].copy()
        
        if df_ventas.empty:
            return pd.DataFrame()
        
        # Limpiar fechas y obtener IDs de tiempo
        df_ventas['fecha_venta_clean'] = self._clean_date(df_ventas['fecha_venta'])
        
        # Merge con dim_tiempo para obtener id_tiempo
        if not dim_tiempo.empty:
            fecha_to_id = dict(zip(dim_tiempo['fecha_completa'], dim_tiempo['id_tiempo']))
            df_ventas['id_tiempo'] = df_ventas['fecha_venta_clean'].map(fecha_to_id)
        
        # Limpiar IDs
        for id_col in ['id_cliente', 'id_vehiculo', 'id_vendedor', 'id_sucursal', 'id_tipo_pago']:
            if id_col in df_ventas.columns:
                df_ventas[id_col] = self._clean_id(df_ventas[id_col])
        
        # Limpiar precio y costo
        if 'precio_venta' in df_ventas.columns:
            df_ventas['precio_venta'] = self._clean_price(df_ventas['precio_venta'])
        if 'costo_vehiculo' in df_ventas.columns:
            df_ventas['costo_vehiculo'] = self._clean_price(df_ventas['costo_vehiculo'])
        
        # Limpiar descuento
        if 'descuento' in df_ventas.columns:
            df_ventas['descuento'] = self._clean_discount(df_ventas['descuento'])
        
        # Limpiar financiado
        if 'financiado' in df_ventas.columns:
            df_ventas['financiado'] = self._clean_boolean(df_ventas['financiado'])
        
        # Columnas a incluir
        cols_to_include = ['id_venta', 'id_cliente', 'id_vehiculo', 'id_vendedor', 
                          'id_sucursal', 'id_tipo_pago', 'cantidad',
                          'precio_venta', 'costo_vehiculo', 'descuento', 'financiado']
        
        if 'id_tiempo' in df_ventas.columns:
            cols_to_include.insert(1, 'id_tiempo')
        
        # Crear DataFrame de hechos
        hecho = df_ventas[[col for col in cols_to_include if col in df_ventas.columns]].copy()
        
        # Calcular margen_ganancia
        if 'precio_venta' in hecho.columns and 'costo_vehiculo' in hecho.columns:
            hecho['margen_ganancia'] = hecho['precio_venta'] - hecho['costo_vehiculo']
        
        return hecho
    
    def _create_hecho_mantenimiento(self, df, dim_tiempo, dim_cliente, dim_vehiculo,
                                   dim_sucursal, dim_tipo_mantenimiento):
        """Crea tabla de hechos de mantenimiento"""
        # Filtrar solo mantenimientos
        df_mant = df[df['tipo_registro'] == 'MANTENIMIENTO'].copy()
        
        if df_mant.empty:
            return pd.DataFrame()
        
        # Limpiar fechas y obtener IDs de tiempo
        df_mant['fecha_mantenimiento_clean'] = self._clean_date(df_mant['fecha_mantenimiento'])
        
        # Merge con dim_tiempo
        if not dim_tiempo.empty:
            fecha_to_id = dict(zip(dim_tiempo['fecha_completa'], dim_tiempo['id_tiempo']))
            df_mant['id_tiempo'] = df_mant['fecha_mantenimiento_clean'].map(fecha_to_id)
        
        # Limpiar IDs
        for id_col in ['id_cliente', 'id_vehiculo', 'id_sucursal', 'id_tipo_mantenimiento']:
            if id_col in df_mant.columns:
                df_mant[id_col] = self._clean_id(df_mant[id_col])
        
        # Limpiar costos
        if 'costo_servicio' in df_mant.columns:
            df_mant['costo_servicio'] = self._clean_price(df_mant['costo_servicio'])
        if 'costo_repuestos' in df_mant.columns:
            df_mant['costo_repuestos'] = self._clean_price(df_mant['costo_repuestos'])
        
        # Limpiar repuestos_usados
        if 'repuestos_usados' in df_mant.columns:
            df_mant['repuestos_usados'] = self._clean_quantity(df_mant['repuestos_usados'])
        
        # Columnas a incluir
        cols_to_include = ['id_mantenimiento', 'id_cliente', 'id_vehiculo', 'id_sucursal', 
                          'id_tipo_mantenimiento', 'costo_servicio', 'costo_repuestos', 
                          'repuestos_usados', 'horas_taller', 'kilometraje_vehiculo']
        
        if 'id_tiempo' in df_mant.columns:
            cols_to_include.insert(1, 'id_tiempo')
        
        # Crear DataFrame de hechos
        hecho = df_mant[[col for col in cols_to_include if col in df_mant.columns]].copy()
        
        return hecho
    
    def _clean_price(self, series: pd.Series) -> pd.Series:
        """Limpia precios y costos"""
        if series is None:
            return pd.Series(dtype='float64')
        
        if series.dtype == 'object':
            cleaned = series.astype(str)
            cleaned = cleaned.str.replace(r'[$€£]', '', regex=True)
            cleaned = cleaned.str.replace(',', '.')
            cleaned = cleaned.str.replace(r'[^\d.-]', '', regex=True)
            cleaned = pd.to_numeric(cleaned, errors='coerce')
        else:
            cleaned = pd.to_numeric(series, errors='coerce')
        
        # Validar rangos
        min_price = self.config.get('validation', {}).get('min_price', 0)
        max_price = self.config.get('validation', {}).get('max_price', 200000)
        
        cleaned = cleaned.clip(min_price, max_price)
        
        return cleaned
    
    def _clean_discount(self, series: pd.Series) -> pd.Series:
        """Limpia descuentos"""
        if series is None:
            return pd.Series(dtype='float64')
        
        if series.dtype == 'object':
            cleaned = series.astype(str)
            cleaned = cleaned.str.replace('%', '')
            cleaned = cleaned.str.replace(',', '.')
            cleaned = cleaned.str.replace(r'[^\d.-]', '', regex=True)
            cleaned = pd.to_numeric(cleaned, errors='coerce')
        else:
            cleaned = pd.to_numeric(series, errors='coerce')
        
        cleaned = cleaned.clip(0, 100).fillna(0)
        
        return cleaned
    
    def _clean_boolean(self, series: pd.Series) -> pd.Series:
        """Limpia campos booleanos"""
        if series is None:
            return pd.Series(dtype='int64')
        
        if series.dtype == 'object':
            cleaned = series.astype(str).str.lower().str.strip()
            bool_map = {
                '1': 1, 'si': 1, 'sí': 1, 'true': 1, 'y': 1, 'yes': 1,
                '0': 0, 'no': 0, 'false': 0, 'n': 0, 'not': 0
            }
            cleaned = cleaned.map(bool_map).fillna(0)
        else:
            cleaned = pd.to_numeric(series, errors='coerce').fillna(0)
        
        return cleaned.astype(int)
    
    def _clean_quantity(self, series: pd.Series) -> pd.Series:
        """Limpia cantidades"""
        if series is None:
            return pd.Series(dtype='float64')
        
        if series.dtype == 'object':
            cleaned = series.astype(str)
            cleaned = cleaned.str.replace(r'[^\d-]', '', regex=True)
            cleaned = pd.to_numeric(cleaned, errors='coerce')
        else:
            cleaned = pd.to_numeric(series, errors='coerce')
        
        cleaned = cleaned.clip(0, None).fillna(0)
        
        return cleaned
    
    def validate_referential_integrity(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Valida integridad referencial entre tablas"""
        validation_results = {}
        
        # Validar hecho_ventas
        if 'hecho_ventas' in data_dict and not data_dict['hecho_ventas'].empty:
            ventas = data_dict['hecho_ventas']
            
            # Clientes
            if 'dim_cliente' in data_dict and not data_dict['dim_cliente'].empty:
                clientes_validos = set(data_dict['dim_cliente']['id_cliente'].dropna())
                clientes_invalidos = ventas[~ventas['id_cliente'].isin(clientes_validos) & ventas['id_cliente'].notna()]
                validation_results['clientes_invalidos_en_ventas'] = len(clientes_invalidos)
            
            # Vehículos
            if 'dim_vehiculo' in data_dict and not data_dict['dim_vehiculo'].empty:
                vehiculos_validos = set(data_dict['dim_vehiculo']['id_vehiculo'].dropna())
                vehiculos_invalidos = ventas[~ventas['id_vehiculo'].isin(vehiculos_validos) & ventas['id_vehiculo'].notna()]
                validation_results['vehiculos_invalidos_en_ventas'] = len(vehiculos_invalidos)
        
        # Validar hecho_mantenimiento
        if 'hecho_mantenimiento' in data_dict and not data_dict['hecho_mantenimiento'].empty:
            mant = data_dict['hecho_mantenimiento']
            
            if 'tipo_mantenimiento' in data_dict and not data_dict['tipo_mantenimiento'].empty:
                tipos_validos = set(data_dict['tipo_mantenimiento']['id_tipo_mantenimiento'].dropna())
                tipos_invalidos = mant[~mant['id_tipo_mantenimiento'].isin(tipos_validos) & mant['id_tipo_mantenimiento'].notna()]
                validation_results['tipos_mantenimiento_invalidos'] = len(tipos_invalidos)
        
        return validation_results