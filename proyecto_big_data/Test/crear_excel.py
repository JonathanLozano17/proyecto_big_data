import pandas as pd
import os

# Asegurar que la carpeta existe
path = "data/raw/"
if not os.path.exists(path):
    os.makedirs(path)

# Crear datos de prueba coherentes con tu config.yaml
data = {
    'id': [1, 2, 3, 4, 5],
    'fecha': ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04', '2026-01-05'],
    'producto': ['Laptop ', ' Mouse', 'Teclado', 'Monitor', ' Mouse'], # Con espacios para probar limpieza
    'precio': [1200.50, 25.00, 45.99, 300.00, 25.00],
    'cantidad': [1, 2, 1, 3, 1]
}

df = pd.DataFrame(data)

# Guardar el archivo
file_name = "data/raw/datos_ventas.xlsx"
df.to_excel(file_name, index=False)

print(f"✅ Archivo creado exitosamente en: {file_name}")