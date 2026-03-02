import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os

# Configuración
path = "data/raw/"
if not os.path.exists(path):
    os.makedirs(path)

# Semillas para reproducibilidad
np.random.seed(42)
random.seed(42)

# Configuración de fechas
fecha_inicio = datetime(2020, 1, 1)
fecha_fin = datetime(2024, 12, 31)

# ============================================
# 1. DIMENSIONES AUXILIARES
# ============================================

# Ciudades para normalización geográfica
ciudades = [
    {'id_ciudad': 1, 'nombre_ciudad': 'Bogotá', 'departamento': 'Cundinamarca', 'region': 'Centro'},
    {'id_ciudad': 2, 'nombre_ciudad': 'Medellín', 'departamento': 'Antioquia', 'region': 'Norte'},
    {'id_ciudad': 3, 'nombre_ciudad': 'Cali', 'departamento': 'Valle del Cauca', 'region': 'Sur'},
    {'id_ciudad': 4, 'nombre_ciudad': 'Barranquilla', 'departamento': 'Atlántico', 'region': 'Norte'},
    {'id_ciudad': 5, 'nombre_ciudad': 'Cartagena', 'departamento': 'Bolívar', 'region': 'Norte'},
    {'id_ciudad': 6, 'nombre_ciudad': 'Bucaramanga', 'departamento': 'Santander', 'region': 'Este'},
    {'id_ciudad': 7, 'nombre_ciudad': 'Pereira', 'departamento': 'Risaralda', 'region': 'Oeste'},
    {'id_ciudad': 8, 'nombre_ciudad': 'Cúcuta', 'departamento': 'Norte de Santander', 'region': 'Este'},
]

# ============================================
# 2. DIMENSIONES PRINCIPALES
# ============================================

# dim_Tiempo - Generamos todos los días del período
print("Generando dim_Tiempo...")
fechas = []
fecha_actual = fecha_inicio
while fecha_actual <= fecha_fin:
    fechas.append({
        'id_tiempo': fecha_actual.strftime('%Y%m%d'),
        'fecha_completa': fecha_actual,
        'año': fecha_actual.year,
        'mes': fecha_actual.month,
        'nombre_mes': fecha_actual.strftime('%B'),
        'trimestre': (fecha_actual.month - 1) // 3 + 1,
        'dia': fecha_actual.day,
        'dia_semana': fecha_actual.strftime('%A'),
        'es_fin_semana': 1 if fecha_actual.weekday() >= 5 else 0
    })
    fecha_actual += timedelta(days=1)

df_tiempo = pd.DataFrame(fechas)
df_tiempo.to_excel(f"{path}dim_tiempo.xlsx", index=False)

# dim_Cliente
print("Generando dim_Cliente...")
nombres = ['Carlos', 'Ana', 'Juan', 'María', 'Luis', 'Laura', 'Pedro', 'Sofía', 'Andrés', 'Valentina']
apellidos = ['García', 'Rodríguez', 'Martínez', 'López', 'González', 'Pérez', 'Sánchez', 'Ramírez']

clientes = []
for i in range(1, 501):  # 500 clientes
    # Introducir problemas controlados
    if i % 50 == 0:  # Clientes sin ciudad
        id_ciudad = None
    elif i % 33 == 0:  # Ciudad inválida
        id_ciudad = 999
    else:
        id_ciudad = random.choice([c['id_ciudad'] for c in ciudades])
    
    # Tipo de cliente con problemas
    if i % 25 == 0:
        tipo_cliente = "RECURRENTE"  # Mayúsculas
    elif i % 20 == 0:
        tipo_cliente = "nuevo  "  # Espacios
    else:
        tipo_cliente = random.choice(['nuevo', 'recurrente'])
    
    clientes.append({
        'id_cliente': i,
        'nombre': f"{random.choice(nombres)} {random.choice(apellidos)}",
        'edad': random.randint(18, 70),
        'genero': random.choice(['M', 'F', 'M', 'F', 'M']),  # Más M que F para variar
        'id_ciudad': id_ciudad,
        'tipo_cliente': tipo_cliente,
        'fecha_registro': (fecha_inicio + timedelta(days=random.randint(0, 1000))).strftime('%Y-%m-%d'),
        'email': f"cliente{i}@{random.choice(['gmail.com', 'hotmail.com', 'yahoo.es'])}" if i % 15 != 0 else None
    })

df_cliente = pd.DataFrame(clientes)
df_cliente.to_excel(f"{path}dim_cliente.xlsx", index=False)

# dim_Sucursal
print("Generando dim_Sucursal...")
sucursales = []
nombres_sucursal = ['Principal', 'Norte', 'Sur', 'Centro', 'Occidente', 'Oriente', 'Autopista', 'Calle 80']
for i in range(1, 21):  # 20 sucursales
    ciudad = random.choice(ciudades)
    sucursales.append({
        'id_sucursal': i,
        'nombre': f"Sucursal {random.choice(nombres_sucursal)}",
        'id_ciudad': ciudad['id_ciudad'],
        'tamaño': random.choice(['Pequeña', 'Mediana', 'Grande']),
        'zona': ciudad['region'],
        'direccion': f"Carrera {random.randint(1, 100)} #{random.randint(1, 50)}-{random.randint(1, 50)}",
        'telefono': f"{random.randint(300, 320)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}" if i % 10 != 0 else None
    })

df_sucursal = pd.DataFrame(sucursales)
df_sucursal.to_excel(f"{path}dim_sucursal.xlsx", index=False)

# dim_Vehiculo
print("Generando dim_Vehiculo...")
marcas = ['Toyota', 'Renault', 'Chevrolet', 'Mazda', 'Kia', 'Hyundai', 'Nissan', 'Ford', 'Volkswagen', 'Suzuki']
modelos_por_marca = {
    'Toyota': ['Corolla', 'Hilux', 'Prado', 'Yaris', 'Rav4'],
    'Renault': ['Duster', 'Sandero', 'Logan', 'Kwid', 'Stepway'],
    'Chevrolet': ['Onix', 'Joy', 'Tracker', 'S10', 'Spin'],
    'Mazda': ['Mazda2', 'Mazda3', 'Mazda6', 'CX-30', 'CX-5'],
    'Kia': ['Rio', 'Sportage', 'Seltos', 'Picanto', 'Cerato'],
    'Hyundai': ['i10', 'i20', 'Tucson', 'Santa Fe', 'Creta'],
    'Nissan': ['Versa', 'Sentra', 'X-Trail', 'Frontier', 'Kicks'],
    'Ford': ['Fiesta', 'Focus', 'Escape', 'Ranger', 'Explorer'],
    'Volkswagen': ['Gol', 'Virtus', 'T-Cross', 'Amarok', 'Jetta'],
    'Suzuki': ['Swift', 'Vitara', 'Jimny', 'S-Cross', 'Ignis']
}

vehiculos = []
for i in range(1, 301):  # 300 vehículos en inventario
    marca = random.choice(marcas)
    modelo = random.choice(modelos_por_marca[marca])
    
    # Problemas controlados en campos
    if i % 40 == 0:
        tipo_combustible = "GASOLINA  "  # Espacios
    elif i % 30 == 0:
        tipo_combustible = "Diesel"  # Formato incorrecto
    else:
        tipo_combustible = random.choice(['Gasolina', 'Diesel', 'Híbrido', 'Eléctrico'])
    
    vehiculos.append({
        'id_vehiculo': i,
        'marca': marca,
        'modelo': modelo,
        'tipo': random.choice(['carro', 'carro', 'carro', 'moto']),  # 75% carros
        'año_modelo': random.randint(2018, 2025),
        'cilindraje': random.choice([1000, 1200, 1400, 1600, 1800, 2000, 2400, 3000, 3500]),
        'tipo_combustible': tipo_combustible,
        'color': random.choice(['Blanco', 'Negro', 'Plata', 'Rojo', 'Azul', 'Gris']),
        'id_sucursal': random.randint(1, 20),
        'precio_compra': random.randint(30000, 80000),
        'precio_venta_sugerido': random.randint(35000, 100000),
        'estado': random.choice(['disponible', 'vendido', 'reservado']) if i % 25 != 0 else None
    })

df_vehiculo = pd.DataFrame(vehiculos)
df_vehiculo.to_excel(f"{path}dim_vehiculo.xlsx", index=False)

# dim_vendedor
print("Generando dim_vendedor...")
nombres_vendedor = ['Carlos', 'Ana', 'Juan', 'María', 'Luis', 'Laura', 'Pedro', 'Sofía', 'Diego', 'Camila']
vendedores = []
for i in range(1, 51):  # 50 vendedores
    vendedores.append({
        'id_vendedor': i,
        'nombre': f"{random.choice(nombres_vendedor)} {random.choice(apellidos)}",
        'experiencia_anios': random.randint(0, 15),
        'id_sucursal': random.randint(1, 20),
        'telefono': f"3{random.randint(10, 99)}-{random.randint(100, 999)}-{random.randint(10, 99)}",
        'email': f"vendedor{i}@concesionario.com" if i % 20 != 0 else None,
        'fecha_contratacion': (fecha_inicio + timedelta(days=random.randint(0, 1500))).strftime('%Y-%m-%d')
    })

df_vendedor = pd.DataFrame(vendedores)
df_vendedor.to_excel(f"{path}dim_vendedor.xlsx", index=False)

# dim_tipoPago
print("Generando dim_tipoPago...")
tipos_pago = []
entidades = ['Bancolombia', 'Davivienda', 'BBVA', 'Banco de Bogotá', 'Banco Popular', 'Colpatria', 'Citibank']
for i in range(1, 16):  # 15 opciones de pago
    tipo = random.choice(['contado', 'credito', 'leasing'])
    if tipo == 'contado':
        entidad = None
        plazo = 0
        tasa = 0
    else:
        entidad = random.choice(entidades)
        plazo = random.choice([12, 24, 36, 48, 60])
        tasa = round(random.uniform(0.8, 2.5), 2)
    
    # Problemas controlados
    if i == 5:
        tipo_pago = "CREDITO"  # Mayúsculas
    else:
        tipo_pago = tipo
    
    tipos_pago.append({
        'id_tipo_pago': i,
        'tipo_pago': tipo_pago,
        'entidad_financiera': entidad,
        'plazo_meses': plazo,
        'tasa_interes': tasa,
        'requiere_aprobacion': 1 if tipo != 'contado' else 0
    })

df_tipoPago = pd.DataFrame(tipos_pago)
df_tipoPago.to_excel(f"{path}dim_tipoPago.xlsx", index=False)

# tipo_mantenimiento
print("Generando tipo_mantenimiento...")
tipos_mant = [
    {'nombre': 'Aceite y Filtros', 'desc': 'Cambio de aceite y filtros', 'garantia': 1, 'meses': 3, 'km': 5000},
    {'nombre': 'Frenos', 'desc': 'Revisión y cambio de pastillas', 'garantia': 1, 'meses': 6, 'km': 10000},
    {'nombre': 'Suspensión', 'desc': 'Revisión de amortiguadores', 'garantia': 1, 'meses': 12, 'km': 20000},
    {'nombre': 'Motor', 'desc': 'Ajuste y calibración', 'garantia': 1, 'meses': 12, 'km': 15000},
    {'nombre': 'Sistema Eléctrico', 'desc': 'Revisión eléctrica', 'garantia': 0, 'meses': 0, 'km': 0},
    {'nombre': 'Aire Acondicionado', 'desc': 'Recarga y revisión', 'garantia': 0, 'meses': 0, 'km': 0},
    {'nombre': 'Transmisión', 'desc': 'Cambio de aceite transmisión', 'garantia': 1, 'meses': 6, 'km': 15000},
    {'nombre': 'Alineación y Balanceo', 'desc': 'Alineación y balanceo', 'garantia': 0, 'meses': 0, 'km': 0}
]

mantenimientos_tipo = []
for i, mt in enumerate(tipos_mant, 1):
    mantenimientos_tipo.append({
        'id_tipo_mantenimiento': i,
        'nombre_tipo': mt['nombre'],
        'descripcion': mt['desc'],
        'incluye_garantia': mt['garantia'],
        'meses_garantia': mt['meses'],
        'kilometros_garantia': mt['km']
    })

df_tipo_mantenimiento = pd.DataFrame(mantenimientos_tipo)
df_tipo_mantenimiento.to_excel(f"{path}tipo_mantenimiento.xlsx", index=False)

# ============================================
# 3. TABLAS DE HECHOS
# ============================================

# hecho_Ventas (Tabla central)
print("Generando hecho_Ventas...")
ventas = []
num_ventas = 2000

for i in range(1, num_ventas + 1):
    # Seleccionar vehículo (asegurar que exista)
    id_vehiculo = random.randint(1, 300)
    vehiculo = df_vehiculo[df_vehiculo['id_vehiculo'] == id_vehiculo].iloc[0]
    
    # Fecha (con problemas controlados)
    if i % 70 == 0:
        fecha = None
    elif i % 45 == 0:
        fecha = "2024-13-45"  # Fecha inválida
    elif i % 30 == 0:
        fecha = (fecha_fin + timedelta(days=30)).strftime('%Y-%m-%d')  # Fecha futura
    else:
        dias = random.randint(0, (fecha_fin - fecha_inicio).days)
        fecha = (fecha_inicio + timedelta(days=dias)).strftime('%Y-%m-%d')
    
    # Precios y descuentos
    precio_base = vehiculo['precio_venta_sugerido']
    
    # Descuento (con problemas)
    if i % 55 == 0:
        descuento = "15%"  # Con porcentaje
    elif i % 35 == 0:
        descuento = random.uniform(0, 30)
    else:
        descuento = random.choice([0, 5, 10, 15, 20])
    
    # ID Cliente (algunos nulos)
    id_cliente = random.randint(1, 500) if i % 80 != 0 else None
    
    # ID Vendedor (algunos inválidos)
    if i % 60 == 0:
        id_vendedor = 999  # Inválido
    else:
        id_vendedor = random.randint(1, 50)
    
    # Financiado
    if i % 25 == 0:
        financiado = "SI"  # Texto
    elif i % 15 == 0:
        financiado = random.choice(['Y', 'N'])
    else:
        financiado = 1 if random.random() < 0.4 else 0
    
    ventas.append({
        'id_venta': i,
        'id_tiempo': fecha,
        'id_cliente': id_cliente,
        'id_vehiculo': id_vehiculo,
        'id_vendedor': id_vendedor,
        'id_sucursal': random.randint(1, 20),
        'id_tipo_pago': random.randint(1, 15),
        'cantidad': 1,  # Siempre 1 vehículo por venta
        'precio_venta': precio_base,
        'costo_vehiculo': vehiculo['precio_compra'],
        'descuento': descuento,
        'financiado': financiado,
        'comision_vendedor': round(precio_base * random.uniform(0.01, 0.03), 2),
        'fecha_registro': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

df_ventas = pd.DataFrame(ventas)
df_ventas.to_excel(f"{path}hecho_ventas.xlsx", index=False)

# hecho_mantenimiento (Postventa)
print("Generando hecho_mantenimiento...")
mantenimientos = []
num_mantenimientos = 800  # Menos que ventas (no todos los clientes hacen mantenimiento)

for i in range(1, num_mantenimientos + 1):
    # Seleccionar cliente (puede ser de los que compraron o no)
    id_cliente = random.randint(1, 500)
    
    # Seleccionar vehículo (relacionado con ventas anteriores o no)
    id_vehiculo = random.randint(1, 300)
    
    # Tipo de mantenimiento
    id_tipo = random.randint(1, len(tipos_mant))
    
    # Fecha (posterior a venta típicamente)
    if i % 50 == 0:
        fecha = "error_fecha"
    else:
        dias = random.randint(30, 800)  # Mantenimientos después de la venta
        fecha = (fecha_inicio + timedelta(days=dias)).strftime('%Y-%m-%d')
    
    # Costos
    costo_base = random.randint(100, 1500)
    repuestos = random.randint(0, 5)
    costo_repuestos = random.randint(0, 800) if repuestos > 0 else 0
    
    # Problemas en repuestos
    if i % 40 == 0:
        repuestos_usados = "muchos"
    elif i % 25 == 0:
        repuestos_usados = -repuestos  # Negativo
    else:
        repuestos_usados = repuestos
    
    mantenimientos.append({
        'id_mantenimiento': i,
        'id_tiempo': fecha,
        'id_cliente': id_cliente,
        'id_vehiculo': id_vehiculo,
        'id_sucursal': random.randint(1, 20),
        'id_tipo_mantenimiento': id_tipo,
        'costo_servicio': costo_base,
        'costo_repuestos': costo_repuestos,
        'repuestos_usados': repuestos_usados,
        'horas_taller': random.randint(1, 8) if i % 30 != 0 else None,
        'kilometraje_vehiculo': random.randint(5000, 60000),
        'fecha_proximo_mantenimiento': (datetime.strptime(fecha, '%Y-%m-%d') + timedelta(days=180)).strftime('%Y-%m-%d') if isinstance(fecha, str) and fecha != 'error_fecha' else None
    })

df_mantenimiento = pd.DataFrame(mantenimientos)
df_mantenimiento.to_excel(f"{path}hecho_mantenimiento.xlsx", index=False)

# ============================================
# 4. CIUDAD (Tabla de normalización geográfica)
# ============================================
print("Generando dim_ciudad...")
df_ciudad = pd.DataFrame(ciudades)
df_ciudad.to_excel(f"{path}dim_ciudad.xlsx", index=False)

# ============================================
# 5. CREAR ARCHIVO COMBINADO (RAW) CON PROBLEMAS
# ============================================
print("\n" + "="*50)
print("CREANDO ARCHIVO COMBINADO CON PROBLEMAS")
print("="*50)

# Tomamos muestra de ventas y lo combinamos con datos de dimensiones
ventas_sample = df_ventas.head(500).copy()

# 1. CONVERTIR A TIPO OBJETO ANTES DE INTRODUCIR TEXTO
ventas_sample['precio_venta'] = ventas_sample['precio_venta'].astype(object)
ventas_sample['descuento'] = ventas_sample['descuento'].astype(object)

# 2. AÑADIR COLUMNAS DESNORMALIZADAS (Aquí corregimos el uso de los puntos suspensivos)
ventas_sample['nombre_cliente'] = ventas_sample['id_cliente'].apply(
    lambda x: df_cliente[df_cliente['id_cliente'] == x]['nombre'].values[0] if pd.notna(x) and x in df_cliente['id_cliente'].values else 'DESCONOCIDO'
)

ventas_sample['marca_vehiculo'] = ventas_sample['id_vehiculo'].apply(
    lambda x: df_vehiculo[df_vehiculo['id_vehiculo'] == x]['marca'].values[0] if x in df_vehiculo['id_vehiculo'].values else 'SIN MARCA'
)

ventas_sample['nombre_vendedor'] = ventas_sample['id_vendedor'].apply(
    lambda x: df_vendedor[df_vendedor['id_vendedor'] == x]['nombre'].values[0] if x in df_vendedor['id_vendedor'].values else 'VENDEDOR INVÁLIDO'
)

# 3. INTRODUCIR LOS PROBLEMAS
for idx in ventas_sample.sample(frac=0.2).index:
    if random.random() < 0.5:
        val = ventas_sample.loc[idx, 'precio_venta']
        ventas_sample.loc[idx, 'precio_venta'] = f"${val}" 
    if random.random() < 0.3:
        val = ventas_sample.loc[idx, 'descuento']
        ventas_sample.loc[idx, 'descuento'] = f"{val}%"

# Guardar archivo combinado
ventas_sample.to_excel(f"{path}datos_ventas_complejos.xlsx", index=False)

# ============================================
# 6. REPORTE DE GENERACIÓN
# ============================================
print("\n✅ ARCHIVOS GENERADOS EXITOSAMENTE")
print("="*50)
print("\n📁 Archivos creados en 'data/raw/':")
archivos = [
    "dim_tiempo.xlsx",
    "dim_cliente.xlsx",
    "dim_sucursal.xlsx",
    "dim_vehiculo.xlsx",
    "dim_vendedor.xlsx",
    "dim_tipoPago.xlsx",
    "tipo_mantenimiento.xlsx",
    "dim_ciudad.xlsx",
    "hecho_ventas.xlsx",
    "hecho_mantenimiento.xlsx",
    "datos_ventas_complejos.xlsx"
]

for archivo in archivos:
    ruta = f"{path}{archivo}"
    if os.path.exists(ruta):
        df_temp = pd.read_excel(ruta)
        print(f"  • {archivo:30} → {len(df_temp):5} filas, {len(df_temp.columns)} columnas")

print("\n📊 PROBLEMAS CONTROLADOS EN LOS DATOS:")
print("  • Fechas nulas, inválidas y futuras")
print("  • IDs de clientes/vendedores inexistentes")
print("  • Precios con formato de texto y símbolos")
print("  • Descuentos con porcentajes y formatos mixtos")
print("  • Campos categóricos con mayúsculas/minúsculas inconsistentes")
print("  • Valores nulos en campos críticos")
print("  • Relaciones referenciales rotas")
print("\n🎯 Ahora puedes ejecutar tu ETL para limpiar estos datos")
print("   y cargarlos a PostgreSQL con el modelo estrella que diseñaste")