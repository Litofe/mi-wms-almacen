import streamlit as st
import pandas as pd
from datetime import datetime

# Configuración del Sistema WMS
st.set_page_config(page_title="WMS - Control Automatizado de Inventario", layout="wide", page_icon="📦")

# 1. INICIALIZACIÓN DE LA BASE DE DATOS DE LA INFRAESTRUCTURA (RACKS)
@st.cache_data
def inicializar_estructura_almacen():
    filas_almacen = []
    # Bloque 01: 26 filas de 24 pallets c/u
    for f in range(1, 27):
        filas_almacen.append({"Bloque": "BLOQUE 01", "Fila": f, "Capacidad Maxima": 24})
    # Bloque 02: 54 filas de 15 pallets c/u
    for f in range(1, 55):
        filas_almacen.append({"Bloque": "BLOQUE 02", "Fila": f, "Capacidad Maxima": 15})
    # Bloque 03: Mixto (1-27: 15 pallets, 28-54: 33 pallets)
    for f in range(1, 55):
        cap = 15 if f <= 27 else 33
        filas_almacen.append({"Bloque": "BLOQUE 03", "Fila": f, "Capacidad Maxima": cap})
    # Bloque 04: Mixto (1-27: 15 pallets, 28-54: 18 pallets)
    for f in range(1, 55):
        cap = 15 if f <= 27 else 18
        filas_almacen.append({"Bloque": "BLOQUE 04", "Fila": f, "Capacidad Maxima": cap})
    # Bloque 05: 24 filas de 21 pallets c/u
    for f in range(1, 25):
        filas_almacen.append({"Bloque": "BLOQUE 05", "Fila": f, "Capacidad Maxima": 21})
    return pd.DataFrame(filas_almacen)

if 'config_racks' not in st.session_state:
    st.session_state.config_racks = inicializar_estructura_almacen()

if 'historial_ingresos' not in st.session_state:
    st.session_state.historial_ingresos = pd.DataFrame([
        {"Fecha Ingreso": "2026-10-01", "Hora": "08:30:00", "SKU": "LOA MANZANA 6", "Fecha Produccion": "2026-09-28", "Bloque": "BLOQUE 01", "Fila": 6, "Pallets": 19, "Cajas": 760},
        {"Fecha Ingreso": "2026-10-01", "Hora": "09:15:00", "SKU": "CIELO 2500", "Fecha Produccion": "2026-09-27", "Bloque": "BLOQUE 01", "Fila": 24, "Pallets": 11, "Cajas": 440}
    ])

if 'historial_salidas' not in st.session_state:
    st.session_state.historial_salidas = pd.DataFrame(columns=[
        "Fecha Salida", "Hora Salida", "SKU", "Fecha Produccion", "Bloque Origen", "Fila Origen", "Pallets", "Cajas"
    ])

def calcular_inventario_maestro():
    df_maestro = st.session_state.config_racks.copy()
    if not st.session_state.historial_ingresos.empty:
        ingresos_g = st.session_state.historial_ingresos.groupby(['Bloque', 'Fila'])['Pallets'].sum().reset_index()
        ingresos_g.rename(columns={'Pallets': 'Total_Ingresos'}, inplace=True)
        df_maestro = pd.merge(df_maestro, ingresos_g, on=['Bloque', 'Fila'], how='left').fillna(0)
    else:
        df_maestro['Total_Ingresos'] = 0.0
    if not st.session_state.historial_salidas.empty:
        salidas_g = st.session_state.historial_salidas.groupby(['Bloque Origen', 'Fila Origen'])['Pallets'].sum().reset_index()
        salidas_g.rename(columns={'Bloque Origen': 'Bloque', 'Fila Origen': 'Fila', 'Pallets': 'Total_Salidas'}, inplace=True)
        df_maestro = pd.merge(df_maestro, salidas_g, on=['Bloque', 'Fila'], how='left').fillna(0)
    else:
        df_maestro['Total_Salidas'] = 0.0
    df_maestro['Stock Actual (Pallets)'] = df_maestro['Total_Ingresos'] - df_maestro['Total_Salidas']
    df_maestro['Pallets Disponibles'] = df_maestro['Capacidad Maxima'] - df_maestro['Stock Actual (Pallets)']
    
    def asignar_estado(row):
        if row['Stock Actual (Pallets)'] < 0: return "⚠️ STOCK NEGATIVO"
        elif row['Stock Actual (Pallets)'] > row['Capacidad Maxima']: return "⚠️ SOBRECAPACIDAD"
        return "VACÍO" if row['Stock Actual (Pallets)'] == 0 else ("LLENO" if row['Stock Actual (Pallets)'] == row['Capacidad Maxima'] else "CON STOCK")
            
    df_maestro['Estado Fila'] = df_maestro.apply(asignar_estado, axis=1)
    return df_maestro

inventario_maestro = calcular_inventario_maestro()

st.title("📦 Sistema WMS Automatizado de Almacenes")
cap_total = int(inventario_maestro['Capacidad Maxima'].sum())
pallets_ocupados = int(inventario_maestro['Stock Actual (Pallets)'].sum())
dispo_total = cap_total - pallets_ocupados

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("Capacidad Almacén", f"{cap_total} Pallets")
kpi2.metric("Pallets Ocupados", f"{pallets_ocupados} Pallets")
kpi3.metric("Espacio Disponible", f"{dispo_total} Pallets")

menu = st.sidebar.radio("Menú", ["📋 Stock Actual", "📥 Ingresos", "📤 Salidas"])

if menu == "📋 Stock Actual":
    st.header("📋 Inventario en Tiempo Real")
    b_sel = st.selectbox("Filtrar por Bloque:", ["TODOS", "BLOQUE 01", "BLOQUE 02", "BLOQUE 03", "BLOQUE 04", "BLOQUE 05"])
    vista = inventario_maestro if b_sel == "TODOS" else inventario_maestro[inventario_maestro['Bloque'] == b_sel]
    st.dataframe(vista[['Bloque', 'Fila', 'Capacidad Maxima', 'Stock Actual (Pallets)', 'Pallets Disponibles', 'Estado Fila']], use_container_width=True, hide_index=True)

elif menu == "📥 Ingresos":
    st.header("📥 Módulo de Ingresos a Racks")
    with st.form("f_ing"):
        c1, c2, c3 = st.columns(3)
        sku = c1.text_input("SKU:")
        f_prod = c2.date_input("Fecha Producción:")
        bloque = c3.selectbox("Bloque:", ["BLOQUE 01", "BLOQUE 02", "BLOQUE 03", "BLOQUE 04", "BLOQUE 05"])
        c4, c5, c6 = st.columns(3)
        fila = c4.number_input("Fila:", min_value=1, max_value=54, step=1)
        pals = c5.number_input("Pallets:", min_value=1, step=1)
        cajs = c6.number_input("Cajas:", min_value=1, step=1)
        if st.form_submit_button("Registrar Ingreso"):
            f_info = inventario_maestro[(inventario_maestro['Bloque'] == bloque) & (inventario_maestro['Fila'] == fila)].iloc[0]
            if pals > f_info['Pallets Disponibles']:
                st.error(f"❌ Error: Capacidad excedida. Solo quedan {int(f_info['Pallets Disponibles'])} espacios.")
            else:
                st.session_state.historial_ingresos = pd.concat([st.session_state.historial_ingresos, pd.DataFrame([{
                    "Fecha Ingreso": datetime.now().strftime("%Y-%m-%d"), "Hora": datetime.now().strftime("%H:%M:%S"),
                    "SKU": sku.upper(), "Fecha Produccion": str(f_prod), "Bloque": bloque, "Fila": int(fila), "Pallets": int(pals), "Cajas": int(cajs)
                }])], ignore_index=True)
                st.success("✔️ Ingreso registrado con éxito.")
                st.rerun()
    st.dataframe(st.session_state.historial_ingresos, use_container_width=True)

elif menu == "📤 Salidas":
    st.header("📤 Módulo de Salidas y Despachos")
    with st.form("f_sal"):
        c1, c2, c3 = st.columns(3)
        sku = c1.text_input("SKU:")
        f_prod = c2.date_input("Fecha Producción:")
        bloque = c3.selectbox("Bloque Origen:", ["BLOQUE 01", "BLOQUE 02", "BLOQUE 03", "BLOQUE 04", "BLOQUE 05"])
        c4, c5, c6 = st.columns(3)
        fila = c4.number_input("Fila Origen:", min_value=1, max_value=54, step=1)
        pals = c5.number_input("Pallets a Retirar:", min_value=1, step=1)
        cajs = c6.number_input("Cajas a Retirar:", min_value=1, step=1)
        if st.form_submit_button("Despachar e Indexar"):
            f_info = inventario_maestro[(inventario_maestro['Bloque'] == bloque) & (inventario_maestro['Fila'] == fila)].iloc[0]
            if pals > f_info['Stock Actual (Pallets)']:
                st.error(f"❌ Error: Stock insuficiente. Solo hay {int(f_info['Stock Actual (Pallets)'])} pallets.")
            else:
                st.session_state.historial_salidas = pd.concat([st.session_state.historial_salidas, pd.DataFrame([{
                    "Fecha Salida": datetime.now().strftime("%Y-%m-%d"), "Hora Salida": datetime.now().strftime("%H:%M:%S"),
                    "SKU": sku.upper(), "Fecha Produccion": str(f_prod), "Bloque Origen": bloque, "Fila Origen": int(fila), "Pallets": int(pals), "Cajas": int(cajs)
                }])], ignore_index=True)
                st.success("✔️ Despacho procesado y restado del inventario.")
                st.rerun()
    st.dataframe(st.session_state.historial_salidas, use_container_width=True)
