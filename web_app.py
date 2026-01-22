import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ================= CONFIGURACIÓN =================
st.set_page_config(
    page_title="Buscador de Pagos y Consumo de Contratos",
    layout="wide"
)

st.title("🔍 Buscador de Pagos y Consumo de Contratos")

# ================= ESTADO INICIAL =================
for key in ["beneficiario", "clc", "contrato", "factura"]:
    if key not in st.session_state:
        st.session_state[key] = ""

if "mostrar_resultados" not in st.session_state:
    st.session_state.mostrar_resultados = False

# ================= GOOGLE SHEETS =================
ID_SHEET = "TU_ID_DE_GOOGLE_SHEETS_AQUI"

@st.cache_data
def cargar_datos():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(
        "credenciales.json",
        scopes=scopes
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(ID_SHEET)

    pagos = sheet.worksheet("PAGOS").get_all_records()
    compromisos = sheet.worksheet("COMPROMISOS").get_all_records()

    df_pagos = pd.DataFrame(pagos)
    df_compromisos = pd.DataFrame(compromisos)

    df = pd.merge(
        df_pagos,
        df_compromisos,
        on="CONTRATO",
        how="left"
    )

    return df

df = cargar_datos()

# ================= FILTROS =================
st.subheader("Filtros de búsqueda")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.text_input(
        "Beneficiario",
        key="beneficiario"
    )

with col2:
    st.text_input(
        "CLC",
        key="clc"
    )

with col3:
    st.text_input(
        "Contrato",
        key="contrato"
    )

with col4:
    st.text_input(
        "Factura",
        key="factura"
    )

# ================= BOTONES =================
col_buscar, col_limpiar = st.columns([1, 1])

with col_buscar:
    if st.button("🔎 Buscar"):
        st.session_state.mostrar_resultados = True

with col_limpiar:
    if st.button("🧹 Limpiar búsqueda"):
        st.session_state.beneficiario = ""
        st.session_state.clc = ""
        st.session_state.contrato = ""
        st.session_state.factura = ""
        st.session_state.mostrar_resultados = False

# ================= FILTRADO =================
if st.session_state.mostrar_resultados:

    resultado = df.copy()

    if st.session_state.beneficiario:
        resultado = resultado[
            resultado["BENEFICIARIO"]
            .str.contains(st.session_state.beneficiario, case=False, na=False)
        ]

    if st.session_state.clc:
        resultado = resultado[
            resultado["CLC"]
            .astype(str)
            .str.contains(st.session_state.clc, case=False, na=False)
        ]

    if st.session_state.contrato:
        resultado = resultado[
            resultado["CONTRATO"]
            .astype(str)
            .str.contains(st.session_state.contrato, case=False, na=False)
        ]

    if st.session_state.factura:
        resultado = resultado[
            resultado["FACTURA"]
            .astype(str)
            .str.contains(st.session_state.factura, case=False, na=False)
        ]

    st.subheader("Resultados")

    if resultado.empty:
        st.warning("No se encontraron resultados con los filtros aplicados.")
    else:
        tabla = resultado[[
            "BENEFICIARIO",
            "CLC",
            "CONTRATO",
            "FACTURA",
            "MONTO",
            "Fecha de pago"
        ]].copy()

        st.dataframe(tabla, use_container_width=True)
