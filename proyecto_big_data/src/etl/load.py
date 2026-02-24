import logging
from sqlalchemy import create_engine
import pandas as pd

def load_to_database(df, table_name, connection_string):
    """Carga datos a PostgreSQL"""
    try:
        engine = create_engine(connection_string)
        
        # Cargar datos (reemplazar o append según necesidad)
        df.to_sql(
            name=table_name,
            con=engine,
            if_exists='replace',  # o 'append' para datos nuevos
            index=False,
            chunksize=1000  # Para lotes grandes
        )
        
        logging.info(f"Datos cargados en {table_name}: {len(df)} filas")
        
    except Exception as e:
        logging.error(f"Error cargando datos: {e}")
        raise