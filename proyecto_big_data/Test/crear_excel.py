import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os

# Configuración
path = "data/raw/"
if not os.path.exists(path):
    os.makedirs(path)

# Productos con diferentes categorías y precios
productos = {
    'Laptop': {'categoria': 'Electrónica', 'precio_base': 1200, 'rango': 200},
    'Mouse': {'categoria': 'Periféricos', 'precio_base': 25, 'rango': 15},
    'Teclado': {'categoria': 'Periféricos', 'precio_base': 45, 'rango': 20},
    'Monitor': {'categoria': 'Electrónica', 'precio_base': 300, 'rango': 100},
    'Auriculares': {'categoria': 'Audio', 'precio_base': 80, 'rango': 30},
    'Webcam': {'categoria': 'Periféricos', 'precio_base': 60, 'rango': 25},
    'Impresora': {'categoria': 'Oficina', 'precio_base': 200, 'rango': 80},
    'Tablet': {'categoria': 'Electrónica', 'precio_base': 350, 'rango': 150},
    'Disco Duro': {'categoria': 'Almacenamiento', 'precio_base': 90, 'rango': 40},
    'Memoria RAM': {'categoria': 'Componentes', 'precio_base': 70, 'rango': 30}
}

# Generar 1000 filas de datos
np.random.seed(42)
random.seed(42)

data = []
fecha_inicio = datetime(2026, 1, 1)

for i in range(1, 1001):
    # Seleccionar producto aleatorio
    producto_nombre = random.choice(list(productos.keys()))
    producto_info = productos[producto_nombre]
    
    # Generar fecha (con algunos valores nulos o inválidos)
    if i % 50 == 0:  # Cada 50 registros, fecha nula
        fecha = None
    elif i % 33 == 0:  # Cada 33 registros, fecha inválida
        fecha = "fecha_invalida"
    elif i % 25 == 0:  # Cada 25 registros, fecha futura
        fecha = (fecha_inicio + timedelta(days=i+1000)).strftime('%Y-%m-%d')
    else:
        fecha = (fecha_inicio + timedelta(days=random.randint(0, 365))).strftime('%Y-%m-%d')
    
    # Generar producto (con problemas de formato)
    if i % 20 == 0:
        producto = f"  {producto_nombre.upper()}  "  # Espacios y mayúsculas
    elif i % 15 == 0:
        producto = producto_nombre.lower()  # Minúsculas
    elif i % 12 == 0:
        producto = f"¡{producto_nombre}!"  # Caracteres especiales
    elif i % 10 == 0:
        producto = ""  # Vacío
    else:
        producto = producto_nombre
    
    # Generar precio (con problemas)
    if i % 18 == 0:
        precio = f"${producto_info['precio_base'] + random.randint(-50, 50)}"  # Con símbolo
    elif i % 14 == 0:
        precio = f"{producto_info['precio_base'] + random.randint(-30, 30)},50"  # Coma decimal
    elif i % 9 == 0:
        precio = None  # Nulo
    elif i % 7 == 0:
        precio = producto_info['precio_base'] + random.randint(-200, 200)  # Precio fuera de rango
    else:
        precio = producto_info['precio_base'] + random.randint(-20, 20)
        precio = round(precio, 2)
    
    # Generar cantidad (con problemas)
    if i % 22 == 0:
        cantidad = "dos"  # Texto
    elif i % 17 == 0:
        cantidad = -random.randint(1, 5)  # Negativo
    elif i % 13 == 0:
        cantidad = random.randint(100, 500)  # Cantidad irreal
    elif i % 8 == 0:
        cantidad = None  # Nulo
    else:
        cantidad = random.randint(1, 5)
    
    # Nuevos campos para enriquecer el análisis
    # Región (con problemas)
    regiones = ['Norte', 'Sur', 'Este', 'Oeste', 'Centro']
    if i % 11 == 0:
        region = "  "  # Vacío
    elif i % 6 == 0:
        region = random.choice(regiones).upper()  # Mayúsculas
    else:
        region = random.choice(regiones)
    
    # Vendedor (con problemas)
    vendedores = ['Ana', 'Carlos', 'María', 'Juan', 'Laura']
    if i % 16 == 0:
        vendedor = "DESCONOCIDO"
    elif i % 9 == 0:
        vendedor = f"  {random.choice(vendedores)}  "
    else:
        vendedor = random.choice(vendedores)
    
    # Método de pago (categoría)
    metodos_pago = ['Tarjeta', 'Efectivo', 'Transferencia', 'PayPal']
    if i % 19 == 0:
        metodo_pago = "otro"
    else:
        metodo_pago = random.choice(metodos_pago)
    
    # Descuento (con decimales extraños)
    if i % 23 == 0:
        descuento = "15%"  # Con porcentaje
    elif i % 12 == 0:
        descuento = random.uniform(0, 50)
    else:
        descuento = random.choice([0, 5, 10, 15, 20])
    
    data.append({
        'id': i,
        'fecha': fecha,
        'producto': producto,
        'precio': precio,
        'cantidad': cantidad,
        'region': region,
        'vendedor': vendedor,
        'metodo_pago': metodo_pago,
        'descuento': descuento,
        'comentarios': f"Venta #{i}" if i % 5 == 0 else None
    })

# Crear DataFrame
df = pd.DataFrame(data)

# Guardar el archivo
file_name = "data/raw/datos_ventas_complejos.xlsx"
df.to_excel(file_name, index=False)

print(f"✅ Archivo creado exitosamente con {len(df)} filas y {len(df.columns)} columnas")
print("\nEstadísticas de problemas generados:")
print(f"- Fechas nulas/inválidas: {df['fecha'].isna().sum() + sum(df['fecha'] == 'fecha_invalida')}")
print(f"- Precios con formato incorrecto: {sum(isinstance(x, str) for x in df['precio'])}")
print(f"- Cantidades no numéricas: {sum(isinstance(x, str) for x in df['cantidad'])}")
print(f"- Regiones con problemas: {sum(df['region'].str.strip() == '' if isinstance(x, str) else False for x in df['region'])}")