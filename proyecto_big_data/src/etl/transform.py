import pandas as pd

def transform_data(df, config):
    """Limpieza y transformación de datos"""
    
    # 1. Eliminar duplicados
    df = df.drop_duplicates().copy() # Usamos .copy() para evitar advertencias
    
    # 2. Manejar valores nulos (Forma moderna sin inplace=True)
    for col in df.columns:
        if df[col].dtype in ['int64', 'float64']:
            df[col] = df[col].fillna(0)
        else:
            df[col] = df[col].fillna('Desconocido')
    
    # 3. Estandarizar formatos
    for col in df.select_dtypes(include=['object']):
        df[col] = df[col].str.strip().str.lower()
    
    # 4. Validar tipos de datos
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    
    # 5. Crear columnas derivadas
    if 'precio' in df.columns and 'cantidad' in df.columns:
        df['total'] = df['precio'] * df['cantidad']
    
    return df