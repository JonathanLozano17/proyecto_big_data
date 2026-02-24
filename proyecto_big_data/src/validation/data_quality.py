def validate_data(df, config):
    """Revisa si el Excel tiene las columnas que prometimos"""
    required = config.get('required_columns', [])
    missing = [col for col in required if col not in df.columns]
    
    if missing:
        return {'passed': False, 'issues': f"Faltan columnas: {missing}"}
    return {'passed': True, 'issues': None}