import pandas as pd
import numpy as np
import logging
from typing import Dict, Any

class DataTransformer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.transformations_log = []
        
    def transform_all(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Aplica transformaciones a todas las tablas"""
        transformed_data = {}
        
        for table_name, df in data_dict.items():
            logging.info(f"\nTransformando tabla: {table_name}")
            
            # Aplicar transformaciones específicas por tabla
            if table_name.startswith('dim_'):
                df_clean = self._transform_dimension(df, table_name)
            elif table_name.startswith('hecho_'):
                df_clean = self._transform_fact(df, table_name)
            else:
                df_clean = self._transform_generic(df)
            
            transformed_data[table_name] = df_clean
            logging.info(f"  → {table_name} transformada: {len(df_clean)} filas")
        
        return transformed_data
    
    def _transform_dimension(self, df: pd.DataFrame, table_name: str) -> pd.DataFrame:
        """Transformaciones específicas para dimensiones"""
        df = df.copy()
        
        # Limpiar IDs
        id_cols = [col for col in df.columns if 'id_' in col or col == 'id_cliente' or col == 'id_vehiculo']
        for col in id_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                # IDs negativos o nulos se marcan como NULL (luego se manejarán en base de datos)
                df.loc[df[col] < 0, col] = None
        
        # Limpiar campos de texto
        text_cols = df.select_dtypes(include=['object']).columns
        for col in text_cols:
            if col not in id_cols and col not in ['email', 'telefono', 'direccion']:
                # Limpiar texto
                df[col] = df[col].astype(str).str.strip()
                df[col] = df[col].str.lower()
                df[col] = df[col].replace(['', 'nan', 'none', 'null', 'na'], pd.NA)
                
                # Mapeos específicos por tabla
                if table_name == 'dim_cliente' and col == 'tipo_cliente':
                    df[col] = df[col].map({'nuevo': 'nuevo', 'recurrente': 'recurrente'}).fillna('nuevo')
                elif table_name == 'dim_vehiculo' and col == 'tipo_combustible':
                    df[col] = df[col].str.replace('gasolina', 'Gasolina')
                    df[col] = df[col].str.replace('diesel', 'Diesel')
                    df[col] = df[col].str.replace('hibrido', 'Híbrido')
                    df[col] = df[col].str.replace('electrico', 'Eléctrico')
        
        # Fechas en dimensiones
        date_cols = [col for col in df.columns if 'fecha' in col.lower() or 'date' in col.lower()]
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Manejar valores nulos en campos críticos
        if table_name == 'dim_cliente' and 'nombre' in df.columns:
            df['nombre'] = df['nombre'].fillna('Cliente Desconocido')
        elif table_name == 'dim_vehiculo' and 'marca' in df.columns:
            df['marca'] = df['marca'].fillna('Marca Desconocida')
            df['modelo'] = df['modelo'].fillna('Modelo Desconocido')
        
        return df
    
    def _transform_fact(self, df: pd.DataFrame, table_name: str) -> pd.DataFrame:
        """Transformaciones específicas para tablas de hechos"""
        df = df.copy()
        
        # Limpiar fechas
        date_cols = [col for col in df.columns if 'fecha' in col.lower() or 'tiempo' in col.lower()]
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                
                # Validar fechas según configuración
                if self.config.get('validation', {}).get('reject_future_dates', True):
                    today = pd.Timestamp.now()
                    df.loc[df[col] > today, col] = pd.NaT
                
                min_date = pd.Timestamp(self.config.get('validation', {}).get('min_date', '2020-01-01'))
                df.loc[df[col] < min_date, col] = pd.NaT
        
        # Limpiar IDs (claves foráneas)
        id_cols = [col for col in df.columns if 'id_' in col]
        for col in id_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                # IDs negativos o cero se convierten a NULL
                df.loc[df[col] <= 0, col] = None
        
        # Limpiar precios y costos
        price_cols = [col for col in df.columns if 'precio' in col.lower() or 'costo' in col.lower()]
        for col in price_cols:
            if col in df.columns:
                # Convertir a string y limpiar
                df[col] = df[col].astype(str)
                df[col] = df[col].str.replace(r'[$€£]', '', regex=True)
                df[col] = df[col].str.replace(',', '.')
                df[col] = df[col].str.replace(r'[^\d.-]', '', regex=True)
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Validar rangos
                min_price = self.config.get('validation', {}).get('min_price', 0)
                max_price = self.config.get('validation', {}).get('max_price', 200000)
                
                df.loc[df[col] < min_price, col] = min_price
                
                # Precios extremadamente altos (posibles errores)
                high_mask = (df[col] > max_price) & (df[col].notna())
                if high_mask.any():
                    median_price = df.loc[~high_mask, col].median()
                    df.loc[high_mask, col] = median_price
        
        # Limpiar descuentos
        if 'descuento' in df.columns:
            df['descuento'] = df['descuento'].astype(str)
            df['descuento'] = df['descuento'].str.replace('%', '')
            df['descuento'] = pd.to_numeric(df['descuento'], errors='coerce')
            df['descuento'] = df['descuento'].clip(0, 100)
            df['descuento'] = df['descuento'].fillna(0)
        
        # Manejar campo financiado
        if 'financiado' in df.columns:
            # Convertir varios formatos a booleano
            df['financiado'] = df['financiado'].astype(str).str.lower().str.strip()
            df['financiado'] = df['financiado'].map({
                '1': 1, 'si': 1, 'sí': 1, 'true': 1, 'y': 1,
                '0': 0, 'no': 0, 'false': 0, 'n': 0
            }).fillna(0).astype(int)
        
        # Crear columna calculada: margen_ganancia
        if 'precio_venta' in df.columns and 'costo_vehiculo' in df.columns:
            df['margen_ganancia'] = df['precio_venta'] - df['costo_vehiculo']
        
        return df
    
    def _transform_generic(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transformaciones genéricas para otras tablas"""
        df = df.copy()
        
        # Limpiar todas las columnas de texto
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace(['', 'nan', 'none', 'null'], pd.NA)
        
        return df
    
    def validate_referential_integrity(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Valida integridad referencial entre tablas"""
        validation_results = {}
        
        # Validar hecho_ventas vs dimensiones
        if 'hecho_ventas' in data_dict and 'dim_cliente' in data_dict:
            ventas = data_dict['hecho_ventas']
            clientes_validos = set(data_dict['dim_cliente']['id_cliente'].dropna())
            
            clientes_invalidos = ventas[~ventas['id_cliente'].isin(clientes_validos) & ventas['id_cliente'].notna()]
            validation_results['clientes_invalidos_en_ventas'] = len(clientes_invalidos)
            
            # Limpiar (opcional - marcar como NULL)
            if len(clientes_invalidos) > 0:
                data_dict['hecho_ventas'].loc[~data_dict['hecho_ventas']['id_cliente'].isin(clientes_validos), 'id_cliente'] = None
        
        # Validar hecho_ventas vs dim_vehiculo
        if 'hecho_ventas' in data_dict and 'dim_vehiculo' in data_dict:
            ventas = data_dict['hecho_ventas']
            vehiculos_validos = set(data_dict['dim_vehiculo']['id_vehiculo'].dropna())
            
            vehiculos_invalidos = ventas[~ventas['id_vehiculo'].isin(vehiculos_validos) & ventas['id_vehiculo'].notna()]
            validation_results['vehiculos_invalidos_en_ventas'] = len(vehiculos_invalidos)
        
        # Validar hecho_mantenimiento
        if 'hecho_mantenimiento' in data_dict and 'tipo_mantenimiento' in data_dict:
            mant = data_dict['hecho_mantenimiento']
            tipos_validos = set(data_dict['tipo_mantenimiento']['id_tipo_mantenimiento'].dropna())
            
            tipos_invalidos = mant[~mant['id_tipo_mantenimiento'].isin(tipos_validos) & mant['id_tipo_mantenimiento'].notna()]
            validation_results['tipos_mantenimiento_invalidos'] = len(tipos_invalidos)
        
        return validation_results