"""
generate_data.py
Genera datos crudos del concesionario con suciedad intencional.
Output: data/raw/datos_concesionario_raw.xlsx  (hoja: datos_concesionario)
"""

import pandas as pd
import numpy as np
import random
import unicodedata
import os
from datetime import datetime, timedelta

random.seed(None)
np.random.seed(None)

OUT_PATH = "data/raw/"
os.makedirs(OUT_PATH, exist_ok=True)

# ──────────────────────────────────────────────
# CATÁLOGOS BASE
# ──────────────────────────────────────────────

NOMBRES = [
    ('José','Jose','JOSÉ','jose'),('María','Maria','MARÍA','maria'),
    ('Jesús','Jesus','JESÚS','jesus'),('Álvaro','Alvaro','ÁLVARO','alvaro'),
    ('Sofía','Sofia','SOFÍA','sofia'),('Andrés','Andres','ANDRÉS','andres'),
    ('Mónica','Monica','MÓNICA','monica'),('Ángela','Angela','ÁNGELA','angela'),
    ('Benjamín','Benjamin','BENJAMÍN','benjamin'),('Julián','Julian','JULIÁN','julian'),
    ('Raúl','Raul','RAÚL','raul'),('Verónica','Veronica','VERÓNICA','veronica'),
    ('Sebastián','Sebastian','SEBASTIÁN','sebastian'),('Natalia','natalia','NATALIA','Natalia'),
    ('Camilo','CAMILO','camilo','Camilo'),('Valentina','valentina','VALENTINA','Valentina'),
    ('Felipe','FELIPE','felipe','Felipe'),('Daniela','daniela','DANIELA','Daniela'),
    ('Alejandro','ALEJANDRO','alejandro','Alejandro'),('Carolina','carolina','CAROLINA','Carolina'),
    ('Diego','DIEGO','diego','Diego'),('Paola','PAOLA','paola','Paola'),
    ('Ricardo','RICARDO','ricardo','Ricardo'),('Laura','LAURA','laura','Laura'),
    ('Hernán','Hernan','HERNÁN','hernan'),('Claudia','CLAUDIA','claudia','Claudia'),
    ('Mauricio','MAURICIO','mauricio','Mauricio'),('Patricia','PATRICIA','patricia','Patricia'),
]

APELLIDOS = [
    ('García','Garcia','GARCÍA','garcia'),('Rodríguez','Rodriguez','RODRÍGUEZ','rodriguez'),
    ('González','Gonzalez','GONZÁLEZ','gonzalez'),('López','Lopez','LÓPEZ','lopez'),
    ('Martínez','Martinez','MARTÍNEZ','martinez'),('Sánchez','Sanchez','SÁNCHEZ','sanchez'),
    ('Pérez','Perez','PÉREZ','perez'),('Muñoz','Munoz','MUÑOZ','munoz'),
    ('Peña','Pena','PEÑA','pena'),('Castaño','Castano','CASTAÑO','castano'),
    ('Niñez','Ninez','NIÑEZ','ninez'),('Álvarez','Alvarez','ÁLVAREZ','alvarez'),
    ('Fernández','Fernandez','FERNÁNDEZ','fernandez'),('Domínguez','Dominguez','DOMÍNGUEZ','dominguez'),
    ('España','Espana','ESPAÑA','espana'),('Cifuentes','CIFUENTES','cifuentes','Cifuentes'),
    ('Ospina','OSPINA','ospina','Ospina'),('Ríos','Rios','RÍOS','rios'),
    ('Vargas','VARGAS','vargas','Vargas'),('Cárdenas','Cardenas','CÁRDENAS','cardenas'),
    ('Ramírez','Ramirez','RAMÍREZ','ramirez'),('Gutiérrez','Gutierrez','GUTIÉRREZ','gutierrez'),
    ('Cruz','CRUZ','cruz','Cruz'),('Moreno','MORENO','moreno','Moreno'),
    ('Herrera','HERRERA','herrera','Herrera'),('Toro','TORO','toro','Toro'),
]

CIUDADES = [
    {'id':1,'base':'Bogotá','vars':['Bogotá','Bogota','BOGOTÁ','Bogotá D.C.','Bogota DC','bogotá','BOGOTA','Santa Fe de Bogotá'],'depto':'Cundinamarca','region':'Centro'},
    {'id':2,'base':'Medellín','vars':['Medellín','Medellin','MEDELLÍN','Medallo','medellín','MEDELLIN','Medellín, Antioquia'],'depto':'Antioquia','region':'Norte'},
    {'id':3,'base':'Cali','vars':['Cali','CALI','cali','Santiago de Cali','Cali, Valle','SANTIAGO DE CALI'],'depto':'Valle del Cauca','region':'Sur'},
    {'id':4,'base':'Barranquilla','vars':['Barranquilla','BARRANQUILLA','B/quilla','barranquilla','Bquilla'],'depto':'Atlántico','region':'Norte'},
    {'id':5,'base':'Cartagena','vars':['Cartagena','CARTAGENA','Cartagena de Indias','cartagena','CTG'],'depto':'Bolívar','region':'Norte'},
    {'id':6,'base':'Bucaramanga','vars':['Bucaramanga','BUCARAMANGA','B/manga','bucaramanga','Buca'],'depto':'Santander','region':'Este'},
    {'id':7,'base':'Pereira','vars':['Pereira','PEREIRA','pereira','Pereira Risaralda'],'depto':'Risaralda','region':'Oeste'},
    {'id':8,'base':'Cúcuta','vars':['Cúcuta','Cucuta','CÚCUTA','cucuta','San José de Cúcuta'],'depto':'Norte de Santander','region':'Este'},
    {'id':9,'base':'Santa Marta','vars':['Santa Marta','SANTA MARTA','S. Marta','santa marta','SMarta'],'depto':'Magdalena','region':'Norte'},
    {'id':10,'base':'Ibagué','vars':['Ibagué','Ibague','IBAGUÉ','ibagué','IBAGUE'],'depto':'Tolima','region':'Centro'},
    {'id':11,'base':'Manizales','vars':['Manizales','MANIZALES','manizales'],'depto':'Caldas','region':'Oeste'},
    {'id':12,'base':'Pasto','vars':['Pasto','PASTO','pasto','San Juan de Pasto'],'depto':'Nariño','region':'Sur'},
]

MARCAS_MODELOS = {
    'Toyota':['Corolla','Hilux','Prado','Yaris','Rav4','Fortuner','Land Cruiser'],
    'Renault':['Duster','Sandero','Logan','Kwid','Stepway','Koleos','Oroch'],
    'Chevrolet':['Onix','Joy','Tracker','S10','Spin','Blazer','Montana'],
    'Mazda':['Mazda2','Mazda3','Mazda6','CX-30','CX-5','BT-50'],
    'Kia':['Rio','Sportage','Seltos','Picanto','Cerato','Sonet','Carnival'],
    'Hyundai':['i10','i20','Tucson','Santa Fe','Creta','Ioniq','Accent'],
    'Nissan':['Versa','Sentra','X-Trail','Frontier','Kicks','Pathfinder'],
    'Ford':['Fiesta','Focus','Escape','Ranger','Explorer','Maverick','Bronco'],
    'Volkswagen':['Gol','Virtus','T-Cross','Amarok','Jetta','Tiguan','Polo'],
    'Suzuki':['Swift','Vitara','Jimny','S-Cross','Ignis','Grand Vitara'],
    'Honda':['Civic','CR-V','HR-V','Fit','Accord','WR-V'],
    'Mitsubishi':['Lancer','Outlander','ASX','L200','Eclipse Cross'],
}

COMBUSTIBLES_POOL = (
    ['Gasolina']*5 + ['GASOLINA','gasolina','Gasolina  '] +
    ['Diesel']*4  + ['DIESEL','diesel','Diesel  '] +
    ['Híbrido','HIBRIDO','hibrido'] +
    ['Eléctrico','ELECTRICO','electrico'] +
    ['Gas Natural','GAS NATURAL','gas natural']
)

COLORES_POOL = (
    ['Blanco','Negro','Plata','Rojo','Azul','Gris','Verde','Amarillo','Naranja','Marrón','Beige','Vino'] +
    ['BLANCO','blanco','NEGRO','negro','PLATA','plata','ROJO','rojo','AZUL','azul','GRIS','gris']
)

TIPOS_MANTENIMIENTO = [
    {'id':1,'nombre':'Aceite y Filtros','desc':'Cambio de aceite y filtros','garantia':1,'meses':3,'km':5000},
    {'id':2,'nombre':'Frenos','desc':'Revisión y cambio de pastillas','garantia':1,'meses':6,'km':10000},
    {'id':3,'nombre':'Suspensión','desc':'Revisión de amortiguadores','garantia':1,'meses':12,'km':20000},
    {'id':4,'nombre':'Motor','desc':'Ajuste y calibración del motor','garantia':1,'meses':12,'km':15000},
    {'id':5,'nombre':'Sistema Eléctrico','desc':'Revisión eléctrica completa','garantia':0,'meses':0,'km':0},
    {'id':6,'nombre':'Aire Acondicionado','desc':'Recarga y revisión A/C','garantia':0,'meses':0,'km':0},
    {'id':7,'nombre':'Transmisión','desc':'Cambio de aceite transmisión','garantia':1,'meses':6,'km':15000},
    {'id':8,'nombre':'Alineación y Balanceo','desc':'Alineación y balanceo de llantas','garantia':0,'meses':0,'km':0},
    {'id':9,'nombre':'Llantas y Neumáticos','desc':'Cambio y rotación de llantas','garantia':1,'meses':12,'km':15000},
    {'id':10,'nombre':'Revisión General','desc':'Revisión completa del vehículo','garantia':0,'meses':0,'km':0},
    {'id':11,'nombre':'Latonería y Pintura','desc':'Reparación de carrocería','garantia':1,'meses':6,'km':0},
    {'id':12,'nombre':'Vidrios y Lunas','desc':'Cambio o reparación de vidrios','garantia':0,'meses':0,'km':0},
]

ENTIDADES_POOL = (
    ['Bancolombia','Davivienda','BBVA','Banco de Bogotá','Banco Popular','Colpatria','Citibank','Scotiabank','GNB Sudameris','Finandina'] +
    ['bancolombia','DAVIVIENDA','Bbva','banco de bogota','BANCO POPULAR','colpatria','CITIBANK','scotiabank']
)

TIPOS_PAGO_POOL = (
    ['contado']*4 + ['CONTADO','Contado','contado  '] +
    ['credito']*4 + ['CREDITO','Crédito','credito  ','crédito'] +
    ['leasing']*3 + ['LEASING','Leasing','leasing  ']
)

SUCURSALES = ['Principal','Norte','Sur','Centro','Occidente','Oriente','Autopista','Calle 80','Carrera 7','El Poblado','Aeropuerto','Industrial']
TAMAÑOS   = ['Pequeña','Mediana','Grande','Pequeño','Mediano','GRANDE','PEQUEÑA','MEDIANA','grande','pequeña']
FINANCIADO_VALS = [1,0,'SI','NO','Y','N','true','false','verdadero','falso','Si','No','1','0']

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def strip_accents(s):
    return unicodedata.normalize('NFKD', s).encode('ASCII','ignore').decode()

def maybe(val, pct=0.88):
    """Retorna val con probabilidad pct, sino None"""
    return val if random.random() < pct else None

def dirty(val, pct=0.25):
    """Aleatoriamente altera mayúsculas/minúsculas o añade espacios"""
    if val is None or random.random() > pct:
        return val
    val = str(val)
    r = random.random()
    if r < 0.33: return val.upper()
    elif r < 0.66: return val.lower()
    else: return (" " + val + " ") if random.random() < 0.5 else val + "  "

def rand_date():
    base = datetime(2019, 1, 1) + timedelta(days=random.randint(0, 2190))
    fmts = [
        base.strftime('%Y-%m-%d'),
        base.strftime('%d/%m/%Y'),
        base.strftime('%d-%m-%Y'),
        base.strftime('%Y/%m/%d'),
        base.strftime('%d.%m.%Y'),
        base.strftime('%b %d, %Y'),
        base.strftime('%d-%b-%Y'),
    ]
    # ~5% fechas inválidas
    if random.random() < 0.05:
        return random.choice(['2024-13-45','31/02/2023','fecha_invalida','99/99/9999',''])
    return random.choice(fmts)

def gen_email(nombre, apellido, id_c):
    dominios_ok  = ['gmail.com','hotmail.com','yahoo.es','outlook.com','correo.co','icloud.com']
    dominios_err = ['gmial.com','hotmai.com','yaho.es','outlok.com','correo.c']
    n = strip_accents(nombre).lower()
    a = strip_accents(apellido).lower()
    opciones = [
        f"{n}.{a}@{random.choice(dominios_ok)}",
        f"{n}{a}@{random.choice(dominios_ok)}",
        f"{n[0]}{a}@{random.choice(dominios_ok)}",
        f"{n}{random.randint(1,999)}@{random.choice(dominios_ok)}",
        f"cliente{id_c}@{random.choice(dominios_ok)}",
        f"{a}.{n}@{random.choice(dominios_ok)}",
        f"{n}_{a}@{random.choice(dominios_ok)}",
    ]
    # ~12% emails rotos
    if random.random() < 0.12:
        return random.choice([
            f"{n}.{a}@{random.choice(dominios_err)}",
            f"{n}{a}sinpunto",
            f"{n}.{a}",
            "correo@incompleto.",
            "@sinusuario.com",
            f"{n}..{a}@gmail.com",
        ])
    # ~8% nulos
    if random.random() < 0.08:
        return None
    return random.choice(opciones)

def gen_precio(base):
    r = random.random()
    if r < 0.25:  return f"${base:,.0f}".replace(',','.')
    elif r < 0.35: return f"${base:,}"
    elif r < 0.42: return str(base) + " USD"
    elif r < 0.48: return f"{base:.2f}"
    elif r < 0.50: return None          # ~2% nulos
    return base

def gen_descuento():
    val = random.randint(0, 35)
    r = random.random()
    if r < 0.30:  return f"{val}%"
    elif r < 0.40: return f"{val/100:.2f}"
    elif r < 0.45: return f"descuento {val}%"
    return val

# ──────────────────────────────────────────────
# GENERACIÓN PRINCIPAL
# ──────────────────────────────────────────────

N_VENTAS = 2000
N_MANT   = 1000
records  = []

for i in range(1, N_VENTAS + N_MANT + 1):
    tipo_reg = 'VENTA' if i <= N_VENTAS else 'MANTENIMIENTO'

    # ── Cliente ──────────────────────────────
    id_cli  = random.randint(1, 900)
    nombre  = random.choice(random.choice(NOMBRES))
    ap1     = random.choice(random.choice(APELLIDOS))
    ap2     = random.choice(random.choice(APELLIDOS))
    cli_nombre = f"{nombre} {ap1} {ap2}"

    # Ciudad cliente: 75% válida, 25% sucia/nula
    if random.random() < 0.75:
        ciu     = random.choice(CIUDADES)
        ciudad_cli  = dirty(random.choice(ciu['vars']), 0.25)
        depto_cli   = dirty(ciu['depto'], 0.15)
        region_cli  = dirty(ciu['region'], 0.15)
        id_ciu_cli  = ciu['id']
    else:
        ciudad_cli  = random.choice(['','CIUDAD_INVALIDA','No especificada',' ',None,'N/A','sin dato','?'])
        depto_cli   = random.choice(['',None,'N/A','sin dato'])
        region_cli  = random.choice(['',None,'N/A'])
        id_ciu_cli  = random.choice([999,-1,None,0])

    tipo_cli = dirty(random.choice(['nuevo','recurrente','vip','empresarial','potencial']), 0.35)
    cli_email = gen_email(nombre, ap1, id_cli)
    cli_edad  = random.randint(18,80) if random.random() > 0.03 else random.randint(5,120)
    cli_edad  = maybe(cli_edad, 0.92)
    cli_gen   = dirty(random.choice(['M','F','Masculino','Femenino','M','F','M','F']), 0.2)

    # ── Vehículo ─────────────────────────────
    id_veh    = random.randint(1, 600)
    marca     = random.choice(list(MARCAS_MODELOS.keys()))
    modelo    = random.choice(MARCAS_MODELOS[marca])
    tipo_veh  = dirty(random.choice(['carro','moto','camioneta','bus','furgón','pickup']), 0.2)
    año_mod   = random.randint(2012, 2025)
    cilindraje = random.choice([1000,1200,1400,1500,1600,1800,2000,2400,3000,3500,4000])
    combustible = dirty(random.choice(COMBUSTIBLES_POOL), 0.1)
    color     = random.choice(COLORES_POOL)
    p_compra  = random.randint(15000, 120000)
    p_venta_s = int(p_compra * random.uniform(1.05, 1.40))

    # ── Sucursal ─────────────────────────────
    id_suc    = random.randint(1, 35)
    ciu_suc   = random.choice(CIUDADES)
    nom_suc   = f"Sucursal {random.choice(SUCURSALES)}"
    tam_suc   = random.choice(TAMAÑOS)

    # ── Vendedor ─────────────────────────────
    id_vend   = random.randint(1, 100)
    vend_nom  = f"{random.choice(random.choice(NOMBRES))} {random.choice(random.choice(APELLIDOS))}"
    vend_exp  = maybe(random.randint(0, 25), 0.92)

    fecha = rand_date()

    # ── Campos específicos por tipo ──────────
    if tipo_reg == 'VENTA':
        fecha_venta    = fecha
        fecha_mant     = None
        id_tipo_mant   = None
        nom_mant       = None
        desc_mant      = None
        garantia_mant  = None
        meses_gar      = None
        km_gar         = None
        costo_serv     = None
        costo_rep      = None
        rep_usados     = None
        horas_taller   = None
        km_vehiculo    = None

        precio_venta   = gen_precio(p_venta_s)
        costo_vehiculo = p_compra
        descuento      = gen_descuento()
        financiado     = random.choice(FINANCIADO_VALS)
        comision       = maybe(round(p_venta_s * random.uniform(0.008, 0.035), 2), 0.90)
        id_tipo_pago   = random.randint(1, 20)
        tipo_pago_nom  = dirty(random.choice(TIPOS_PAGO_POOL), 0.15)
        entidad_fin    = maybe(dirty(random.choice(ENTIDADES_POOL), 0.10), 0.55)
        plazo          = maybe(random.choice([12,24,36,48,60,72]), 0.55)
        tasa           = maybe(round(random.uniform(0.5, 2.8), 2), 0.55)
        req_aprobacion = random.choice([1,0])
        cantidad       = maybe(1, 0.97)
    else:
        fecha_venta    = None
        fecha_mant     = fecha
        tm             = random.choice(TIPOS_MANTENIMIENTO)
        id_tipo_mant   = tm['id']
        nom_mant       = dirty(tm['nombre'], 0.10)
        desc_mant      = tm['desc']
        garantia_mant  = tm['garantia']
        meses_gar      = tm['meses']
        km_gar         = tm['km']
        costo_serv     = maybe(random.randint(30, 3000), 0.95)
        costo_rep      = maybe(random.randint(0, 800), 0.70)
        rep_usados     = maybe(random.randint(0, 15))
        horas_taller   = maybe(random.randint(1, 16))
        km_vehiculo    = maybe(random.randint(500, 150000))

        precio_venta   = None
        costo_vehiculo = None
        descuento      = None
        financiado     = None
        comision       = None
        id_tipo_pago   = None
        tipo_pago_nom  = None
        entidad_fin    = None
        plazo          = None
        tasa           = None
        req_aprobacion = None
        cantidad       = None

    records.append({
        # ── Identificadores ──────────────────
        'id_venta':               i if tipo_reg == 'VENTA' else None,
        'tipo_registro':          tipo_reg,
        'fecha_venta':            fecha_venta,
        'fecha_mantenimiento':    fecha_mant,
        'id_cliente':             id_cli,
        'id_vehiculo':            id_veh,
        'id_vendedor':            id_vend if tipo_reg == 'VENTA' else None,
        'id_sucursal':            id_suc,
        'id_tipo_pago':           id_tipo_pago,
        'id_tipo_mantenimiento':  id_tipo_mant,
        # ── Métricas venta ───────────────────
        'cantidad':               cantidad,
        'precio_venta':           precio_venta,
        'costo_vehiculo':         costo_vehiculo,
        'descuento':              descuento,
        'financiado':             financiado,
        'comision_vendedor':      comision,
        # ── Cliente ──────────────────────────
        'cliente_nombre':         cli_nombre,
        'cliente_edad':           cli_edad,
        'cliente_genero':         cli_gen,
        'cliente_tipo':           tipo_cli,
        'cliente_email':          cli_email,
        'id_ciudad_cliente':      id_ciu_cli,
        'ciudad_cliente':         ciudad_cli,
        'departamento_cliente':   depto_cli,
        'region_cliente':         region_cli,
        # ── Vehículo ─────────────────────────
        'vehiculo_marca':         marca,
        'vehiculo_modelo':        modelo,
        'vehiculo_tipo':          tipo_veh,
        'vehiculo_año':           año_mod,
        'vehiculo_cilindraje':    cilindraje,
        'vehiculo_combustible':   combustible,
        'vehiculo_color':         color,
        # ── Sucursal ─────────────────────────
        'sucursal_nombre':        nom_suc,
        'id_ciudad_sucursal':     ciu_suc['id'],
        'ciudad_sucursal':        ciu_suc['base'],
        'departamento_sucursal':  ciu_suc['depto'],
        'region_sucursal':        ciu_suc['region'],
        'sucursal_tamaño':        tam_suc,
        'sucursal_zona':          ciu_suc['region'],
        # ── Vendedor ─────────────────────────
        'vendedor_nombre':        vend_nom if tipo_reg == 'VENTA' else None,
        'vendedor_experiencia':   vend_exp if tipo_reg == 'VENTA' else None,
        # ── Pago ─────────────────────────────
        'tipo_pago_nombre':       tipo_pago_nom,
        'entidad_financiera':     entidad_fin,
        'plazo_meses':            plazo,
        'tasa_interes':           tasa,
        'requiere_aprobacion':    req_aprobacion,
        # ── Mantenimiento ────────────────────
        'tipo_mantenimiento_nombre':       nom_mant,
        'tipo_mantenimiento_descripcion':  desc_mant,
        'incluye_garantia':        garantia_mant,
        'meses_garantia':          meses_gar,
        'kilometros_garantia':     km_gar,
        'costo_servicio':          costo_serv,
        'costo_repuestos':         costo_rep,
        'repuestos_usados':        rep_usados,
        'horas_taller':            horas_taller,
        'kilometraje_vehiculo':    km_vehiculo,
    })

# Mezclar filas
df = pd.DataFrame(records).sample(frac=1).reset_index(drop=True)

out_file = f"{OUT_PATH}datos_concesionario_raw.xlsx"
df.to_excel(out_file, index=False, sheet_name='datos_concesionario')

print(f"✅ Archivo generado: {out_file}")
print(f"   Total filas  : {len(df)}")
print(f"   Ventas       : {(df['tipo_registro']=='VENTA').sum()}")
print(f"   Mantenimiento: {(df['tipo_registro']=='MANTENIMIENTO').sum()}")
print(f"   Columnas     : {len(df.columns)}")