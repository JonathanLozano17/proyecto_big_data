import pandas as pd
import numpy as np
import re
import logging
from typing import Dict, Any, List, Callable

class DataTransformer:
    """Clase para manejar transformaciones de datos de manera modular"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.transformations_log = []
        
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica todas las transformaciones configuradas"""
        df = df.copy()
        
        # Registrar estado inicial
        self.transformations_log.append({
            'step': 'inicial',
            'rows': len(df),
            'columns': list(df.columns)
        })
        
        # Aplicar transformaciones en orden
        transformation_steps = [
            self.clean_ids,
            self.clean_dates,
            self.clean_text_fields,
            self.clean_prices,
            self.clean_quantities,
            self.clean_categorical,
            self.handle_outliers,
            self.create_derived_columns,
            self.remove_duplicates
        ]
        
        for step in transformation_steps:
            df = step(df)
            
        return df
    
    def clean_ids(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia campos de ID"""
        if 'id' in df.columns:
            # Asegurar que ID sea numérico
            df['id'] = pd.to_numeric(df['id'], errors='coerce')
            # IDs negativos o nulos se reasignan
            mask = (df['id'].isna()) | (df['id'] < 0)
            if mask.any():
                max_id = df['id'].max() if not df['id'].isna().all() else 0
                df.loc[mask, 'id'] = range(max_id + 1, max_id + 1 + mask.sum())
                logging.info(f"IDs corregidos: {mask.sum()} filas")
        
        self.transformations_log.append({
            'step': 'clean_ids',
            'modified_count': mask.sum() if 'mask' in locals() else 0
        })
        return df
    
    def clean_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia y estandariza fechas"""
        date_columns = [col for col in df.columns if 'fecha' in col.lower() or 'date' in col.lower()]
        
        for col in date_columns:
            if col in df.columns:
                # Registrar valores problemáticos antes
                invalid_before = df[col].isna().sum()
                
                # Intentar convertir a datetime
                df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=False)
                
                # Validar fechas futuras
                if self.config.get('validation', {}).get('reject_future_dates', True):
                    today = pd.Timestamp.now()
                    future_mask = df[col] > today
                    if future_mask.any():
                        df.loc[future_mask, col] = pd.NaT
                        logging.info(f"Fechas futuras eliminadas: {future_mask.sum()} en {col}")
                
                # Validar fechas muy antiguas
                min_date = pd.Timestamp(self.config.get('validation', {}).get('min_date', '2000-01-01'))
                old_mask = df[col] < min_date
                if old_mask.any():
                    df.loc[old_mask, col] = pd.NaT
                    logging.info(f"Fechas muy antiguas eliminadas: {old_mask.sum()} en {col}")
                
                invalid_after = df[col].isna().sum()
                if invalid_after > invalid_before:
                    logging.info(f"Columna {col}: {invalid_after - invalid_before} fechas inválidas convertidas a NaT")
        
        self.transformations_log.append({
            'step': 'clean_dates',
            'date_columns': date_columns
        })
        return df
    
    def clean_text_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia campos de texto"""
        text_columns = df.select_dtypes(include=['object']).columns
        
        for col in text_columns:
            if col in ['producto', 'region', 'vendedor', 'metodo_pago']:
                # 1. Eliminar espacios extras
                df[col] = df[col].astype(str).str.strip()
                
                # 2. Estandarizar a mayúsculas/minúsculas según configuración
                if self.config.get('transformations', {}).get('text_case') == 'upper':
                    df[col] = df[col].str.upper()
                else:
                    df[col] = df[col].str.lower()
                
                # 3. Eliminar caracteres especiales
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace(r'[^\w\s]', '', regex=True)
                )
                
                # 4. Manejar valores vacíos
                df[col] = df[col].replace(['', 'nan', 'none', 'null'], pd.NA)
                df[col] = df[col].fillna(self.config.get('transformations', {}).get('default_text', 'desconocido'))
                
                # 5. Mapear valores a categorías estándar (si existe mapping)
                if f'{col}_mapping' in self.config:
                    df[col] = df[col].map(self.config[f'{col}_mapping']).fillna(df[col])
        
        self.transformations_log.append({
            'step': 'clean_text_fields',
            'text_columns': list(text_columns)
        })
        return df
    
    def clean_prices(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia campos de precio"""
        price_columns = [col for col in df.columns if 'precio' in col.lower() or 'price' in col.lower()]
        
        for col in price_columns:
            if col in df.columns:
                # 1. Convertir a string para limpieza
                df[col] = df[col].astype(str)
                
                # 2. Eliminar símbolos de moneda y espacios
                df[col] = df[col].str.replace(r'[$€£]', '', regex=True)
                
                # 3. Estandarizar decimales (reemplazar coma por punto)
                df[col] = df[col].str.replace(',', '.')
                
                # 4. Eliminar caracteres no numéricos (excepto punto y signo)
                df[col] = df[col].str.replace(r'[^\d.-]', '', regex=True)
                
                # 5. Convertir a numérico
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # 6. Validar rangos
                min_price = self.config.get('validation', {}).get('min_price', 0)
                max_price = self.config.get('validation', {}).get('max_price', 10000)
                
                # Precios negativos o muy bajos
                low_mask = (df[col] < min_price) & (df[col].notna())
                if low_mask.any():
                    df.loc[low_mask, col] = min_price
                    logging.info(f"Precios mínimos ajustados: {low_mask.sum()} en {col}")
                
                # Precios muy altos (posibles errores)
                high_mask = (df[col] > max_price) & (df[col].notna())
                if high_mask.any():
                    # Podríamos imputar con la mediana en lugar de eliminar
                    median_price = df.loc[~high_mask, col].median()
                    df.loc[high_mask, col] = median_price
                    logging.info(f"Precios extremos imputados con mediana: {high_mask.sum()} en {col}")
        
        self.transformations_log.append({
            'step': 'clean_prices',
            'price_columns': price_columns
        })
        return df
    
    def clean_quantities(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia campos de cantidad"""
        qty_columns = [col for col in df.columns if 'cantidad' in col.lower() or 'qty' in col.lower()]
        
        for col in qty_columns:
            if col in df.columns:
                # 1. Convertir a numérico
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # 2. Manejar negativos
                negative_mask = df[col] < 0
                if negative_mask.any():
                    df.loc[negative_mask, col] = abs(df.loc[negative_mask, col])
                    logging.info(f"Cantidades negativas corregidas: {negative_mask.sum()}")
                
                # 3. Validar límites
                min_qty = self.config.get('validation', {}).get('min_quantity', 1)
                max_qty = self.config.get('validation', {}).get('max_quantity', 100)
                
                # Cantidades mínimas
                low_mask = (df[col] < min_qty) & (df[col].notna())
                if low_mask.any():
                    df.loc[low_mask, col] = min_qty
                
                # Cantidades máximas (posibles errores)
                high_mask = (df[col] > max_qty) & (df[col].notna())
                if high_mask.any():
                    df.loc[high_mask, col] = max_qty
                    logging.info(f"Cantidades extremas limitadas: {high_mask.sum()}")
                
                # 4. Imputar nulos con 1 (valor por defecto)
                null_mask = df[col].isna()
                if null_mask.any():
                    df.loc[null_mask, col] = 1
                    logging.info(f"Cantidades nulas imputadas a 1: {null_mask.sum()}")
        
        return df
    
    def clean_categorical(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia y estandariza campos categóricos"""
        categorical_cols = ['region', 'metodo_pago', 'vendedor']
        
        for col in categorical_cols:
            if col in df.columns:
                # 1. Limpiar texto
                df[col] = df[col].astype(str).str.strip().str.lower()
                
                # 2. Reemplazar variantes comunes
                if col == 'metodo_pago':
                    replacements = {
                        'tarjeta': 'tarjeta',
                        'credito': 'tarjeta',
                        'debito': 'tarjeta',
                        'efectivo': 'efectivo',
                        'cash': 'efectivo',
                        'transferencia': 'transferencia',
                        'paypal': 'paypal',
                        'pay pal': 'paypal'
                    }
                    df[col] = df[col].replace(replacements)
                
                elif col == 'region':
                    replacements = {
                        'norte': 'norte',
                        'n': 'norte',
                        'sur': 'sur',
                        's': 'sur',
                        'este': 'este',
                        'e': 'este',
                        'oeste': 'oeste',
                        'o': 'oeste',
                        'centro': 'centro',
                        'c': 'centro'
                    }
                    df[col] = df[col].replace(replacements)
                
                # 3. Valores válidos
                valid_values = self.config.get('validation', {}).get(f'valid_{col}', [])
                if valid_values:
                    df.loc[~df[col].isin(valid_values), col] = 'otro'
        
        return df
    
    def handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detecta y maneja outliers"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            if col not in ['id']:  # No tratar IDs como outliers
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bound = Q1 - 3 * IQR  # Usar 3*IQR para outliers extremos
                upper_bound = Q3 + 3 * IQR
                
                outlier_mask = (df[col] < lower_bound) | (df[col] > upper_bound)
                
                if outlier_mask.any():
                    logging.info(f"Outliers detectados en {col}: {outlier_mask.sum()} filas")
                    
                    if self.config.get('transformations', {}).get('outlier_strategy') == 'cap':
                        # Cap en lugar de eliminar
                        df.loc[df[col] < lower_bound, col] = lower_bound
                        df.loc[df[col] > upper_bound, col] = upper_bound
                    elif self.config.get('transformations', {}).get('outlier_strategy') == 'median':
                        # Imputar con mediana
                        median_val = df[col].median()
                        df.loc[outlier_mask, col] = median_val
        
        return df
    
    def create_derived_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Crea columnas derivadas para análisis"""
        
        # 1. Total de venta
        if 'precio' in df.columns and 'cantidad' in df.columns:
            df['total'] = df['precio'] * df['cantidad']
            
            # Aplicar descuento si existe
            if 'descuento' in df.columns:
                # Limpiar descuento
                df['descuento'] = pd.to_numeric(df['descuento'], errors='coerce').fillna(0)
                # Asegurar que sea porcentaje
                df['descuento'] = df['descuento'].clip(0, 100)
                df['total_con_descuento'] = df['total'] * (1 - df['descuento'] / 100)
        
        # 2. Métricas temporales
        if 'fecha' in df.columns:
            df['año'] = df['fecha'].dt.year
            df['mes'] = df['fecha'].dt.month
            df['dia'] = df['fecha'].dt.day
            df['dia_semana'] = df['fecha'].dt.day_name()
            df['trimestre'] = df['fecha'].dt.quarter
        
        # 3. Categorías de precio
        if 'precio' in df.columns:
            bins = [0, 50, 200, 500, 1000, float('inf')]
            labels = ['Económico', 'Medio', 'Premium', 'Alta gama', 'Lujo']
            df['categoria_precio'] = pd.cut(df['precio'], bins=bins, labels=labels)
        
        return df
    
    def remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Elimina duplicados basado en configuración"""
        subset = self.config.get('transformations', {}).get('deduplicate_subset')
        
        before = len(df)
        if subset:
            df = df.drop_duplicates(subset=subset, keep='first')
        else:
            df = df.drop_duplicates()
        
        after = len(df)
        if before > after:
            logging.info(f"Duplicados eliminados: {before - after} filas")
        
        return df
    
    def get_transformation_report(self) -> Dict[str, Any]:
        """Retorna reporte de transformaciones aplicadas"""
        return {
            'steps': self.transformations_log,
            'total_steps': len(self.transformations_log)
        }


# Mantener compatibilidad con código existente
def transform_data(df, config):
    """Wrapper para mantener compatibilidad"""
    transformer = DataTransformer(config)
    return transformer.transform(df)