import pandas as pd
import logging
from typing import Dict, Any, List, Tuple

def validate_data(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
    """Validación exhaustiva de calidad de datos"""
    
    validation_results = {
        'passed': True,
        'issues': [],
        'warnings': [],
        'statistics': {}
    }
    
    # 1. Validar columnas requeridas
    required_cols = config.get('required_columns', [])
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        validation_results['passed'] = False
        validation_results['issues'].append(f"Columnas faltantes: {missing_cols}")
    
    # 2. Validar tipos de datos
    dtypes_config = config.get('column_dtypes', {})
    for col, expected_type in dtypes_config.items():
        if col in df.columns:
            actual_type = str(df[col].dtype)
            if expected_type not in actual_type:
                validation_results['warnings'].append(
                    f"Columna {col}: esperado {expected_type}, actual {actual_type}"
                )
    
    # 3. Validar valores nulos
    null_threshold = config.get('max_null_percentage', 20)
    for col in df.columns:
        null_pct = (df[col].isna().sum() / len(df)) * 100
        if null_pct > null_threshold:
            validation_results['warnings'].append(
                f"Columna {col}: {null_pct:.1f}% valores nulos (umbral: {null_threshold}%)"
            )
    
    # 4. Validar rangos numéricos
    ranges = config.get('value_ranges', {})
    for col, range_config in ranges.items():
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            min_val, max_val = range_config.get('min', -float('inf')), range_config.get('max', float('inf'))
            
            out_of_range = df[(df[col] < min_val) | (df[col] > max_val)][col].count()
            if out_of_range > 0:
                validation_results['warnings'].append(
                    f"Columna {col}: {out_of_range} valores fuera de rango [{min_val}, {max_val}]"
                )
    
    # 5. Validar valores únicos (para IDs)
    if 'id' in df.columns:
        if df['id'].nunique() != len(df):
            validation_results['warnings'].append(
                f"ID: {len(df) - df['id'].nunique()} valores duplicados"
            )
    
    # 6. Validar formatos de fecha
    date_cols = [col for col in df.columns if 'fecha' in col.lower()]
    for col in date_cols:
        if col in df.columns:
            try:
                pd.to_datetime(df[col], errors='raise')
            except:
                validation_results['warnings'].append(
                    f"Columna {col}: contiene fechas inválidas"
                )
    
    # 7. Estadísticas básicas
    validation_results['statistics'] = {
        'total_rows': len(df),
        'total_columns': len(df.columns),
        'memory_usage': df.memory_usage(deep=True).sum() / 1024 / 1024,  # MB
        'duplicated_rows': df.duplicated().sum(),
        'columns_with_nulls': [col for col in df.columns if df[col].isna().any()]
    }
    
    return validation_results


def generate_quality_report(df: pd.DataFrame, validation_result: Dict[str, Any]) -> str:
    """Genera un reporte legible de calidad de datos"""
    
    report = []
    report.append("=" * 50)
    report.append("INFORME DE CALIDAD DE DATOS")
    report.append("=" * 50)
    
    report.append(f"\n Estadísticas Generales:")
    report.append(f"  • Filas: {validation_result['statistics']['total_rows']:,}")
    report.append(f"  • Columnas: {validation_result['statistics']['total_columns']}")
    report.append(f"  • Memoria: {validation_result['statistics']['memory_usage']:.2f} MB")
    report.append(f"  • Filas duplicadas: {validation_result['statistics']['duplicated_rows']}")
    
    if validation_result['issues']:
        report.append(f"\n Problemas Críticos:")
        for issue in validation_result['issues']:
            report.append(f"  • {issue}")
    
    if validation_result['warnings']:
        report.append(f"\n Advertencias:")
        for warning in validation_result['warnings']:
            report.append(f"  • {warning}")
    
    if not validation_result['issues'] and not validation_result['warnings']:
        report.append(f"\n Datos limpios - No se detectaron problemas")
    
    report.append("\n" + "=" * 50)
    
    return "\n".join(report)