import logging
import pandas as pd
from typing import Dict, Optional
from pathlib import Path
import sqlite3
from ..database.connection import DatabaseManager

def load_to_database(data_dict: Dict[str, pd.DataFrame], 
                     db_path: str = None, 
                     schema: str = "main",
                     if_exists: str = 'replace'):
    """Carga múltiples tablas a SQLite asegurando integridad referencial"""
    try:
        db_manager = DatabaseManager(db_path)
        
        logging.info(f"✅ Conexión a SQLite exitosa: {db_manager.db_path}")
        
        # Orden de carga (dimensiones primero, luego hechos)
        tables_in_order = [
            'dim_ciudad',
            'dim_tiempo',
            'dim_cliente',
            'dim_sucursal',
            'dim_vehiculo',
            'dim_vendedor',
            'dim_tipoPago',
            'tipo_mantenimiento',
            'hecho_ventas',
            'hecho_mantenimiento'
        ]
        
        # Crear tablas y cargar datos
        with db_manager.get_connection() as conn:
            # Habilitar foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            
            for table_name in tables_in_order:
                if table_name in data_dict and not data_dict[table_name].empty:
                    df = data_dict[table_name]
                    
                    # Cargar datos a SQLite
                    df.to_sql(
                        name=table_name,
                        con=conn,
                        if_exists=if_exists,
                        index=False,
                        chunksize=1000
                    )
                    
                    logging.info(f"  → {table_name}: {len(df)} filas cargadas")
                elif table_name in data_dict and data_dict[table_name].empty:
                    logging.info(f"  → {table_name}: tabla vacía (no se carga)")
            
            conn.commit()
        
        logging.info("\n✅ Todas las tablas cargadas exitosamente")
        
        # Verificar conteos
        logging.info("\n Verificación de carga:")
        with db_manager.get_connection() as conn:
            for table_name in tables_in_order:
                if table_name in data_dict and not data_dict[table_name].empty:
                    try:
                        count = pd.read_sql(f'SELECT COUNT(*) FROM "{table_name}"', conn).iloc[0, 0]
                        logging.info(f"  • {table_name}: {count} registros")
                    except Exception as e:
                        logging.warning(f"  • {table_name}: no se pudo verificar ({e})")
        
        # Crear índices para mejorar rendimiento
        create_optimization_indexes(db_manager.db_path)
        
        return db_manager.db_path
        
    except Exception as e:
        logging.error(f"Error cargando datos: {e}")
        raise

def create_optimization_indexes(db_path: str):
    """Crea índices para optimizar consultas"""
    try:
        db_manager = DatabaseManager(db_path)
        
        indexes = [
            # Índices para hecho_ventas
            "CREATE INDEX IF NOT EXISTS idx_ventas_tiempo ON hecho_ventas(id_tiempo);",
            "CREATE INDEX IF NOT EXISTS idx_ventas_cliente ON hecho_ventas(id_cliente);",
            "CREATE INDEX IF NOT EXISTS idx_ventas_vehiculo ON hecho_ventas(id_vehiculo);",
            "CREATE INDEX IF NOT EXISTS idx_ventas_sucursal ON hecho_ventas(id_sucursal);",
            
            # Índices para hecho_mantenimiento
            "CREATE INDEX IF NOT EXISTS idx_mant_tiempo ON hecho_mantenimiento(id_tiempo);",
            "CREATE INDEX IF NOT EXISTS idx_mant_cliente ON hecho_mantenimiento(id_cliente);",
            "CREATE INDEX IF NOT EXISTS idx_mant_vehiculo ON hecho_mantenimiento(id_vehiculo);",
            "CREATE INDEX IF NOT EXISTS idx_mant_tipo ON hecho_mantenimiento(id_tipo_mantenimiento);",
            
            # Índices para búsquedas comunes
            "CREATE INDEX IF NOT EXISTS idx_ventas_financiado ON hecho_ventas(financiado);",
            "CREATE INDEX IF NOT EXISTS idx_ventas_precio ON hecho_ventas(precio_venta);",
            "CREATE INDEX IF NOT EXISTS idx_mant_fecha ON hecho_mantenimiento(id_tiempo);",
        ]
        
        with db_manager.get_connection() as conn:
            for idx in indexes:
                try:
                    conn.execute(idx)
                except Exception as e:
                    logging.warning(f"  No se pudo crear índice: {e}")
            conn.commit()
        
        logging.info("\n✅ Índices de optimización creados")
        
    except Exception as e:
        logging.warning(f"Error creando índices: {e}")

def save_to_csv_backup(data_dict: Dict[str, pd.DataFrame], output_dir: str = "data/processed"):
    """Guarda respaldo en CSV por si acaso"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
    
    for table_name, df in data_dict.items():
        if not df.empty:
            file_path = output_path / f"{table_name}_{timestamp}.csv"
            df.to_csv(file_path, index=False)
            logging.info(f"  → Backup CSV: {file_path}")