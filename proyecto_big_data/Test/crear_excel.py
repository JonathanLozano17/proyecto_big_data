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

print("=" * 60)
print("🚗 GENERANDO DATOS DESNORMALIZADOS PARA CONCESIONARIO")
print("=" * 60)

# ============================================
# 1. GENERAR DATOS MAESTROS (DIMENSIONES)
# ============================================
print("\n📊 Generando datos maestros...")

# Ciudades
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

# Tipos de mantenimiento
tipos_mantenimiento = [
    {'id_tipo_mantenimiento': 1, 'nombre_tipo': 'Aceite y Filtros', 'descripcion': 'Cambio de aceite y filtros', 'incluye_garantia': 1, 'meses_garantia': 3, 'kilometros_garantia': 5000},
    {'id_tipo_mantenimiento': 2, 'nombre_tipo': 'Frenos', 'descripcion': 'Revisión y cambio de pastillas', 'incluye_garantia': 1, 'meses_garantia': 6, 'kilometros_garantia': 10000},
    {'id_tipo_mantenimiento': 3, 'nombre_tipo': 'Suspensión', 'descripcion': 'Revisión de amortiguadores', 'incluye_garantia': 1, 'meses_garantia': 12, 'kilometros_garantia': 20000},
    {'id_tipo_mantenimiento': 4, 'nombre_tipo': 'Motor', 'descripcion': 'Ajuste y calibración', 'incluye_garantia': 1, 'meses_garantia': 12, 'kilometros_garantia': 15000},
    {'id_tipo_mantenimiento': 5, 'nombre_tipo': 'Sistema Eléctrico', 'descripcion': 'Revisión eléctrica', 'incluye_garantia': 0, 'meses_garantia': 0, 'kilometros_garantia': 0},
    {'id_tipo_mantenimiento': 6, 'nombre_tipo': 'Aire Acondicionado', 'descripcion': 'Recarga y revisión', 'incluye_garantia': 0, 'meses_garantia': 0, 'kilometros_garantia': 0},
    {'id_tipo_mantenimiento': 7, 'nombre_tipo': 'Transmisión', 'descripcion': 'Cambio de aceite transmisión', 'incluye_garantia': 1, 'meses_garantia': 6, 'kilometros_garantia': 15000},
    {'id_tipo_mantenimiento': 8, 'nombre_tipo': 'Alineación y Balanceo', 'descripcion': 'Alineación y balanceo', 'incluye_garantia': 0, 'meses_garantia': 0, 'kilometros_garantia': 0}
]

# Tipos de pago
tipos_pago = []
entidades = ['Bancolombia', 'Davivienda', 'BBVA', 'Banco de Bogotá', 'Banco Popular', 'Colpatria', 'Citibank']
for i in range(1, 16):
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

# ============================================
# 2. GENERAR REGISTROS DESNORMALIZADOS (VENTAS + MANTENIMIENTO)
# ============================================
print("\n📈 Generando registros desnormalizados...")

# Generar datos de ventas (2000 registros)
ventas_data = []
nombres = ['Carlos', 'Ana', 'Juan', 'María', 'Luis', 'Laura', 'Pedro', 'Sofía', 'Andrés', 'Valentina']
apellidos = ['García', 'Rodríguez', 'Martínez', 'López', 'González', 'Pérez', 'Sánchez', 'Ramírez']
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
nombres_sucursal = ['Principal', 'Norte', 'Sur', 'Centro', 'Occidente', 'Oriente', 'Autopista', 'Calle 80']
nombres_vendedor = ['Carlos', 'Ana', 'Juan', 'María', 'Luis', 'Laura', 'Pedro', 'Sofía', 'Diego', 'Camila']

for i in range(1, 2001):
    # === DATOS DE CLIENTE (con problemas controlados) ===
    id_cliente = random.randint(1, 500)
    if i % 50 == 0:  # Clientes sin ciudad
        id_ciudad_cliente = None
        ciudad_cliente = None
        departamento_cliente = None
        region_cliente = None
    elif i % 33 == 0:  # Ciudad inválida
        id_ciudad_cliente = 999
        ciudad_cliente = "CIUDAD_INVALIDA"
        departamento_cliente = "DEPTO_INVALIDO"
        region_cliente = "REGION_INVALIDA"
    else:
        ciudad = random.choice(ciudades)
        id_ciudad_cliente = ciudad['id_ciudad']
        ciudad_cliente = ciudad['nombre_ciudad']
        departamento_cliente = ciudad['departamento']
        region_cliente = ciudad['region']
    
    if i % 25 == 0:
        tipo_cliente = "RECURRENTE"  # Mayúsculas
    elif i % 20 == 0:
        tipo_cliente = "nuevo  "  # Espacios
    else:
        tipo_cliente = random.choice(['nuevo', 'recurrente'])
    
    cliente_nombre = f"{random.choice(nombres)} {random.choice(apellidos)}"
    cliente_edad = random.randint(18, 70)
    cliente_genero = random.choice(['M', 'F', 'M', 'F', 'M'])
    cliente_email = f"cliente{id_cliente}@{random.choice(['gmail.com', 'hotmail.com', 'yahoo.es'])}" if i % 15 != 0 else None
    
    # === DATOS DE VEHÍCULO (con problemas) ===
    id_vehiculo = random.randint(1, 300)
    marca = random.choice(marcas)
    modelo = random.choice(modelos_por_marca[marca])
    
    if i % 40 == 0:
        tipo_combustible = "GASOLINA  "  # Espacios
    elif i % 30 == 0:
        tipo_combustible = "Diesel"  # Formato incorrecto
    else:
        tipo_combustible = random.choice(['Gasolina', 'Diesel', 'Híbrido', 'Eléctrico'])
    
    tipo_vehiculo = random.choice(['carro', 'carro', 'carro', 'moto'])
    año_modelo = random.randint(2018, 2025)
    cilindraje = random.choice([1000, 1200, 1400, 1600, 1800, 2000, 2400, 3000, 3500])
    color = random.choice(['Blanco', 'Negro', 'Plata', 'Rojo', 'Azul', 'Gris'])
    precio_compra = random.randint(30000, 80000)
    precio_venta_sugerido = random.randint(35000, 100000)
    
    # === DATOS DE SUCURSAL ===
    id_sucursal = random.randint(1, 20)
    ciudad_sucursal = random.choice(ciudades)
    nombre_sucursal = f"Sucursal {random.choice(nombres_sucursal)}"
    tamaño_sucursal = random.choice(['Pequeña', 'Mediana', 'Grande'])
    zona_sucursal = ciudad_sucursal['region']
    
    # === DATOS DE VENDEDOR ===
    id_vendedor = random.randint(1, 50) if i % 60 != 0 else 999  # Algunos inválidos
    vendedor_nombre = f"{random.choice(nombres_vendedor)} {random.choice(apellidos)}"
    vendedor_experiencia = random.randint(0, 15)
    
    # === DATOS DE FECHA (con problemas) ===
    if i % 70 == 0:
        fecha_venta = None
    elif i % 45 == 0:
        fecha_venta = "2024-13-45"  # Fecha inválida
    elif i % 30 == 0:
        fecha_venta = (fecha_fin + timedelta(days=30)).strftime('%Y-%m-%d')  # Fecha futura
    else:
        dias = random.randint(0, (fecha_fin - fecha_inicio).days)
        fecha_venta = (fecha_inicio + timedelta(days=dias)).strftime('%Y-%m-%d')
    
    # Calcular atributos de fecha
    if fecha_venta and isinstance(fecha_venta, str) and '-' in fecha_venta:
        try:
            fecha_obj = datetime.strptime(fecha_venta, '%Y-%m-%d')
            mes_venta = fecha_obj.month
            trimestre_venta = (fecha_obj.month - 1) // 3 + 1
            año_venta = fecha_obj.year
            dia_semana_venta = fecha_obj.strftime('%A')
            es_fin_semana_venta = 1 if fecha_obj.weekday() >= 5 else 0
        except:
            mes_venta = None
            trimestre_venta = None
            año_venta = None
            dia_semana_venta = None
            es_fin_semana_venta = None
    else:
        mes_venta = None
        trimestre_venta = None
        año_venta = None
        dia_semana_venta = None
        es_fin_semana_venta = None
    
    # === DATOS DE PAGO ===
    id_tipo_pago = random.randint(1, 15)
    tipo_pago_info = next((tp for tp in tipos_pago if tp['id_tipo_pago'] == id_tipo_pago), tipos_pago[0])
    
    # === MÉTRICAS DE VENTA (con problemas) ===
    if i % 55 == 0:
        descuento = "15%"  # Con porcentaje
    else:
        descuento = random.choice([0, 5, 10, 15, 20])
    
    if i % 25 == 0:
        financiado = "SI"  # Texto
    elif i % 15 == 0:
        financiado = random.choice(['Y', 'N'])
    else:
        financiado = 1 if random.random() < 0.4 else 0
    
    precio_venta_final = precio_venta_sugerido
    try:
        if isinstance(descuento, (int, float)) or (isinstance(descuento, str) and descuento.replace('%', '').isdigit()):
            desc_val = float(str(descuento).replace('%', ''))
            precio_venta_final = precio_venta_sugerido * (1 - desc_val/100)
    except:
        pass
    
    ventas_data.append({
        # Claves del hecho
        'id_venta': i,
        'tipo_registro': 'VENTA',
        'fecha_venta': fecha_venta,
        'id_cliente': id_cliente if i % 80 != 0 else None,  # Algunos nulos
        'id_vehiculo': id_vehiculo,
        'id_vendedor': id_vendedor,
        'id_sucursal': id_sucursal,
        'id_tipo_pago': id_tipo_pago,
        
        # Métricas de venta
        'cantidad': 1,
        'precio_venta': precio_venta_final,
        'costo_vehiculo': precio_compra,
        'descuento': descuento,
        'financiado': financiado,
        'comision_vendedor': round(precio_venta_final * random.uniform(0.01, 0.03), 2),
        
        # Atributos de tiempo (dim_Tiempo)
        'mes_venta': mes_venta,
        'trimestre_venta': trimestre_venta,
        'año_venta': año_venta,
        'dia_semana_venta': dia_semana_venta,
        'es_fin_semana_venta': es_fin_semana_venta,
        
        # Atributos de cliente (dim_Cliente)
        'cliente_nombre': cliente_nombre,
        'cliente_edad': cliente_edad,
        'cliente_genero': cliente_genero,
        'cliente_tipo': tipo_cliente,
        'cliente_email': cliente_email,
        'id_ciudad_cliente': id_ciudad_cliente,
        'ciudad_cliente': ciudad_cliente,
        'departamento_cliente': departamento_cliente,
        'region_cliente': region_cliente,
        
        # Atributos de vehículo (dim_Vehiculo)
        'vehiculo_marca': marca,
        'vehiculo_modelo': modelo,
        'vehiculo_tipo': tipo_vehiculo,
        'vehiculo_año': año_modelo,
        'vehiculo_cilindraje': cilindraje,
        'vehiculo_combustible': tipo_combustible,
        'vehiculo_color': color,
        
        # Atributos de sucursal (dim_Sucursal)
        'sucursal_nombre': nombre_sucursal,
        'id_ciudad_sucursal': ciudad_sucursal['id_ciudad'],
        'ciudad_sucursal': ciudad_sucursal['nombre_ciudad'],
        'departamento_sucursal': ciudad_sucursal['departamento'],
        'region_sucursal': ciudad_sucursal['region'],
        'sucursal_tamaño': tamaño_sucursal,
        'sucursal_zona': zona_sucursal,
        
        # Atributos de vendedor (dim_Vendedor)
        'vendedor_nombre': vendedor_nombre,
        'vendedor_experiencia': vendedor_experiencia,
        
        # Atributos de tipo de pago (dim_TipoPago)
        'tipo_pago_nombre': tipo_pago_info['tipo_pago'],
        'entidad_financiera': tipo_pago_info['entidad_financiera'],
        'plazo_meses': tipo_pago_info['plazo_meses'],
        'tasa_interes': tipo_pago_info['tasa_interes'],
        'requiere_aprobacion': tipo_pago_info['requiere_aprobacion'],
        
        # Campos de mantenimiento (vacíos para ventas)
        'id_mantenimiento': None,
        'fecha_mantenimiento': None,
        'id_tipo_mantenimiento': None,
        'tipo_mantenimiento_nombre': None,
        'tipo_mantenimiento_descripcion': None,
        'incluye_garantia': None,
        'meses_garantia': None,
        'kilometros_garantia': None,
        'costo_servicio': None,
        'costo_repuestos': None,
        'repuestos_usados': None,
        'horas_taller': None,
        'kilometraje_vehiculo': None,
    })

# Generar datos de mantenimiento (800 registros)
for i in range(2001, 2801):
    # Similar a ventas pero con datos de mantenimiento
    id_cliente = random.randint(1, 500)
    id_vehiculo = random.randint(1, 300)
    id_tipo_mantenimiento = random.randint(1, len(tipos_mantenimiento))
    tipo_mant = tipos_mantenimiento[id_tipo_mantenimiento - 1]
    
    # Fecha de mantenimiento (con problemas)
    if i % 50 == 0:
        fecha_mantenimiento = "error_fecha"
    else:
        dias = random.randint(30, 800)
        fecha_mantenimiento = (fecha_inicio + timedelta(days=dias)).strftime('%Y-%m-%d')
    
    # Calcular atributos de fecha
    if fecha_mantenimiento and isinstance(fecha_mantenimiento, str) and '-' in fecha_mantenimiento:
        try:
            fecha_obj = datetime.strptime(fecha_mantenimiento, '%Y-%m-%d')
            mes_mant = fecha_obj.month
            trimestre_mant = (fecha_obj.month - 1) // 3 + 1
            año_mant = fecha_obj.year
            dia_semana_mant = fecha_obj.strftime('%A')
            es_fin_semana_mant = 1 if fecha_obj.weekday() >= 5 else 0
        except:
            mes_mant = None
            trimestre_mant = None
            año_mant = None
            dia_semana_mant = None
            es_fin_semana_mant = None
    else:
        mes_mant = None
        trimestre_mant = None
        año_mant = None
        dia_semana_mant = None
        es_fin_semana_mant = None
    
    # Costos de mantenimiento
    costo_base = random.randint(100, 1500)
    repuestos = random.randint(0, 5)
    costo_repuestos = random.randint(0, 800) if repuestos > 0 else 0
    
    if i % 40 == 0:
        repuestos_usados = "muchos"
    elif i % 25 == 0:
        repuestos_usados = -repuestos
    else:
        repuestos_usados = repuestos
    
    # Ciudad para el cliente (aleatoria)
    ciudad = random.choice(ciudades)
    
    ventas_data.append({
        # Claves del hecho (vacías para mantenimiento)
        'id_venta': None,
        'tipo_registro': 'MANTENIMIENTO',
        'fecha_venta': None,
        'id_cliente': id_cliente,
        'id_vehiculo': id_vehiculo,
        'id_vendedor': None,
        'id_sucursal': random.randint(1, 20),
        'id_tipo_pago': None,
        
        # Métricas de venta (vacías)
        'cantidad': None,
        'precio_venta': None,
        'costo_vehiculo': None,
        'descuento': None,
        'financiado': None,
        'comision_vendedor': None,
        
        # Atributos de tiempo (para mantenimiento)
        'mes_venta': mes_mant,
        'trimestre_venta': trimestre_mant,
        'año_venta': año_mant,
        'dia_semana_venta': dia_semana_mant,
        'es_fin_semana_venta': es_fin_semana_mant,
        
        # Atributos de cliente
        'cliente_nombre': f"{random.choice(nombres)} {random.choice(apellidos)}",
        'cliente_edad': random.randint(18, 70),
        'cliente_genero': random.choice(['M', 'F', 'M', 'F', 'M']),
        'cliente_tipo': random.choice(['nuevo', 'recurrente']),
        'cliente_email': f"cliente{id_cliente}@gmail.com",
        'id_ciudad_cliente': ciudad['id_ciudad'],
        'ciudad_cliente': ciudad['nombre_ciudad'],
        'departamento_cliente': ciudad['departamento'],
        'region_cliente': ciudad['region'],
        
        # Atributos de vehículo (simplificados)
        'vehiculo_marca': random.choice(marcas),
        'vehiculo_modelo': random.choice(['Corolla', 'Duster', 'Onix', 'Mazda3']),
        'vehiculo_tipo': random.choice(['carro', 'moto']),
        'vehiculo_año': random.randint(2018, 2025),
        'vehiculo_cilindraje': random.choice([1000, 1400, 1600, 2000]),
        'vehiculo_combustible': random.choice(['Gasolina', 'Diesel']),
        'vehiculo_color': random.choice(['Blanco', 'Negro', 'Rojo']),
        
        # Atributos de sucursal
        'sucursal_nombre': f"Sucursal {random.choice(nombres_sucursal)}",
        'id_ciudad_sucursal': ciudad['id_ciudad'],
        'ciudad_sucursal': ciudad['nombre_ciudad'],
        'departamento_sucursal': ciudad['departamento'],
        'region_sucursal': ciudad['region'],
        'sucursal_tamaño': random.choice(['Pequeña', 'Mediana', 'Grande']),
        'sucursal_zona': ciudad['region'],
        
        # Atributos de vendedor (vacíos)
        'vendedor_nombre': None,
        'vendedor_experiencia': None,
        
        # Atributos de tipo de pago (vacíos)
        'tipo_pago_nombre': None,
        'entidad_financiera': None,
        'plazo_meses': None,
        'tasa_interes': None,
        'requiere_aprobacion': None,
        
        # Campos de mantenimiento
        'id_mantenimiento': i,
        'fecha_mantenimiento': fecha_mantenimiento,
        'id_tipo_mantenimiento': id_tipo_mantenimiento,
        'tipo_mantenimiento_nombre': tipo_mant['nombre_tipo'],
        'tipo_mantenimiento_descripcion': tipo_mant['descripcion'],
        'incluye_garantia': tipo_mant['incluye_garantia'],
        'meses_garantia': tipo_mant['meses_garantia'],
        'kilometros_garantia': tipo_mant['kilometros_garantia'],
        'costo_servicio': costo_base,
        'costo_repuestos': costo_repuestos,
        'repuestos_usados': repuestos_usados,
        'horas_taller': random.randint(1, 8) if i % 30 != 0 else None,
        'kilometraje_vehiculo': random.randint(5000, 60000),
    })

# Crear DataFrame único
df_unico = pd.DataFrame(ventas_data)

# ============================================
# 3. GUARDAR ARCHIVO ÚNICO
# ============================================
print("\n" + "=" * 60)
print("💾 GUARDANDO ARCHIVO ÚNICO DESNORMALIZADO")
print("=" * 60)

archivo_unico = f"{path}datos_concesionario_raw.xlsx"
df_unico.to_excel(archivo_unico, index=False, sheet_name='datos_concesionario')

print(f"\n✅ Archivo único guardado: {archivo_unico}")
print(f"   Total de registros: {len(df_unico)}")
print(f"   Total de columnas: {len(df_unico.columns)}")

# ============================================
# 4. REPORTE DE GENERACIÓN
# ============================================
print("\n" + "=" * 60)
print("📊 REPORTE DE GENERACIÓN")
print("=" * 60)

print("\n📁 Estructura del archivo único:")
print(f"  • Una sola hoja: 'datos_concesionario'")
print(f"  • {len(df_unico)} registros combinados:")
print(f"    - Ventas: {len(df_unico[df_unico['tipo_registro'] == 'VENTA'])} registros")
print(f"    - Mantenimiento: {len(df_unico[df_unico['tipo_registro'] == 'MANTENIMIENTO'])} registros")

print("\n📊 PROBLEMAS CONTROLADOS EN LOS DATOS:")
print("  • Fechas nulas, inválidas y futuras")
print("  • IDs de clientes/vendedores inexistentes")
print("  • Precios y descuentos con formato de texto y símbolos")
print("  • Campos categóricos con mayúsculas/minúsculas inconsistentes")
print("  • Valores nulos en campos críticos")
print("  • Relaciones referenciales rotas")
print("  • Datos combinados de ventas y mantenimiento en un mismo archivo")

print("\n🎯 AHORA PUEDES EJECUTAR TU ETL:")
print("   python main.py")
print("\n   El ETL procesará el archivo 'datos_concesionario_raw.xlsx'")
print("   y cargará los datos limpios en PostgreSQL en formato estrella")
print("=" * 60)