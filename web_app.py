import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

# ================= CONFIGURACIÓN =================
st.set_page_config(
    page_title="Buscador de Consumo de Contratos",
    layout="wide"
)
st.title("Consumo de Contratos")

# ================= ACTUALIZAR DATOS =================
col1, col2 = st.columns([1, 6])

with col1:
    if st.button("Actualizar datos"):
        st.cache_data.clear()
        st.success("Datos actualizados desde Google Sheets")
        st.rerun()

# ================= ESTADO =================
defaults = {
    "proyecto": "Todos",
    "empresa": "Todas",
    "contrato": ""
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ================= GOOGLE SHEETS =================
ID_SHEET = "1q2cvx9FD1CW8XP_kZpsFvfKtu4QdrJPqKAZuueHRIW4"

@st.cache_data
def cargar_datos():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=scopes
    )
    client = gspread.authorize(creds)

    ws_contratos = client.open_by_key(ID_SHEET).get_worksheet(0)
    ws_evolucion = client.open_by_key(ID_SHEET).worksheet("Evolucion")
    ws_clc = client.open_by_key(ID_SHEET).worksheet("CLC_CONTRATOS")

    df_contratos = pd.DataFrame(ws_contratos.get_all_records())
    df_evolucion = pd.DataFrame(ws_evolucion.get_all_records())
    df_clc = pd.DataFrame(ws_clc.get_all_records())

    # limpiar encabezados
    for df_tmp in [df_contratos, df_evolucion, df_clc]:
        df_tmp.columns = (
            df_tmp.columns
            .str.strip()
            .str.replace(r"\s+", "_", regex=True)
        )

    return df_contratos, df_evolucion, df_clc


df, df_evolucion, df_clc = cargar_datos()

# ================= NORMALIZAR NUMÉRICOS =================
for col in ["Importe_total_(LC)", "EJERCIDO", "Abrir_importe_(LC)"]:
    df[col] = (
        df[col].astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
    )
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

for col in ["ORIGINAL", "MODIFICADO", "COMPROMETIDO", "EJERCIDO"]:
    df_evolucion[col] = (
        df_evolucion[col].astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
    )
    df_evolucion[col] = pd.to_numeric(df_evolucion[col], errors="coerce").fillna(0)

df_clc["MONTO"] = (
    df_clc["MONTO"].astype(str)
    .str.replace("$", "", regex=False)
    .str.replace(",", "", regex=False)
)
df_clc["MONTO"] = pd.to_numeric(df_clc["MONTO"], errors="coerce").fillna(0)

# asegurar columna LINK_PDF
if "LINK_PDF" not in df_clc.columns:
    df_clc["LINK_PDF"] = ""

# ================= FUNCIONES =================
def formato_pesos(valor):
    return f"$ {valor:,.2f}"

def convertir_excel(dataframe):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False)
    return output.getvalue()

# ================= FILTROS =================
def limpiar_filtros():
    st.session_state.proyecto = "Todos"
    st.session_state.empresa = "Todas"
    st.session_state.contrato = ""

st.subheader("Filtros")
c1, c2, c3, c4 = st.columns([3, 3, 3, 1])

with c1:
    proyectos = ["Todos"] + sorted(df["DESC_PROYECTO"].dropna().unique())
    st.selectbox("DESC PROGRAMA", proyectos, key="proyecto")

with c2:
    empresas = ["Todas"] + sorted(df["EMPRESA"].dropna().unique())
    st.selectbox("EMPRESA", empresas, key="empresa")

# ================= FILTRADO BASE =================
resultado = df.copy()

if st.session_state.proyecto != "Todos":
    resultado = resultado[resultado["DESC_PROYECTO"] == st.session_state.proyecto]

if st.session_state.empresa != "Todas":
    resultado = resultado[resultado["EMPRESA"] == st.session_state.empresa]

# ================= CONTRATOS =================
contratos = [""] + sorted(
    resultado["N°_CONTRATO"].dropna().astype(str).unique()
)

if st.session_state.contrato not in contratos:
    st.session_state.contrato = ""

with c3:
    st.selectbox("N° CONTRATO", contratos, key="contrato")

st.button("Limpiar Filtros", on_click=limpiar_filtros)

# ================= EVOLUCIÓN =================
if st.session_state.proyecto != "Todos":
    evo = df_evolucion[df_evolucion["PROYECTO"] == st.session_state.proyecto]

    if not evo.empty:
        evo = evo.iloc[0]
        st.subheader("Evolución presupuestal del proyecto")
        e1, e2, e3, e4 = st.columns(4)

        e1.metric("Original"


