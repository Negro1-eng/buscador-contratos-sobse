import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ================= CONFIGURACIÓN =================
st.set_page_config(
    page_title="Buscador de Consumo de Contratos",
    layout="wide"
)

st.title("📊 Buscador de Consumo de Contratos")

# ================= GOOGLE SHEETS =================
ID_SHEET = "TU_ID_DE_GOOGLE_SHEET_AQUI"
HOJA_DATOS = "CONTRATOS"  # ← nombre exacto de la hoja

# ================= CARGA DE DATOS =================
@st.cache_data
def cargar_datos():

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=scopes
    )

    client = gspread.authorize(creds)
    sh = client.open_by_key(ID_SHEET)
    ws = sh.worksheet(HOJA_DATOS)

    data = ws.get_all_records()
    df = pd.DataFrame(data)

    return df


# ================= CARGAR DATA =================
df = cargar_datos()

# ================= VALIDACIÓN =================
columnas_necesarias = [
    "NUM CONTRATO",
    "DESC PROYECTO",
    "EMPRESA",
    "MONTO CONTRATO",
    "CONSUMO CONTRATO"
]

for col in columnas_necesarias:
    if col not in df.columns:
        st.error(f"❌ Falta la columna: {col}")
        st.stop()

# ================= CONVERSIÓN NUMÉRICA =================
df["MONTO CONTRATO"] = pd.to_numeric(df["MONTO CONTRATO"], errors="coerce").fillna(0)
df["CONSUMO CONTRATO"] = pd.to_numeric(df["CONSUMO CONTRATO"], errors="coerce").fillna(0)

# ================= FILTROS =================
st.subheader("🔎 Filtros de búsqueda")

lista_proyectos = ["Todos"] + sorted(
    df["DESC PROYECTO"].dropna().unique().tolist()
)

lista_empresas = ["Todas"] + sorted(
    df["EMPRESA"].dropna().unique().tolist()
)

col1, col2 = st.columns(2)

with col1:
    proyecto_sel = st.selectbox(
        "DESC PROYECTO",
        lista_proyectos
    )

with col2:
    empresa_sel = st.selectbox(
        "EMPRESA",
        lista_empresas
    )

# ================= APLICAR FILTROS =================
resultado = df.copy()

if proyecto_sel != "Todos":
    resultado = resultado[
        resultado["DESC PROYECTO"] == proyecto_sel
    ]

if empresa_sel != "Todas":
    resultado = resultado[
        resultado["EMPRESA"] == empresa_sel
    ]

# ================= AGRUPAR Y CALCULAR =================
resultado = resultado.groupby(
    ["NUM CONTRATO", "DESC PROYECTO", "EMPRESA"],
    as_index=False
).agg({
    "MONTO CONTRATO": "first",
    "CONSUMO CONTRATO": "sum"
})

resultado["SALDO"] = (
    resultado["MONTO CONTRATO"] - resultado["CONSUMO CONTRATO"]
)

# ================= FORMATO =================
resultado["MONTO CONTRATO"] = resultado["MONTO CONTRATO"].map("${:,.2f}".format)
resultado["CONSUMO CONTRATO"] = resultado["CONSUMO CONTRATO"].map("${:,.2f}".format)
resultado["SALDO"] = resultado["SALDO"].map("${:,.2f}".format)

# ================= MOSTRAR RESULTADOS =================
st.subheader("📄 Resultados")

st.dataframe(
    resultado,
    use_container_width=True
)

# ================= TOTALES =================
st.subheader("📌 Totales")

total_contrato = df["MONTO CONTRATO"].sum()
total_consumo = df["CONSUMO CONTRATO"].sum()
total_saldo = total_contrato - total_consumo

col1, col2, col3 = st.columns(3)

col1.metric("Monto Contratos", f"${total_contrato:,.2f}")
col2.metric("Consumo Total", f"${total_consumo:,.2f}")
col3.metric("Saldo Total", f"${total_saldo:,.2f}")
