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

st.title("📊 Buscador de Consumo de Contratos")

# ================= ESTADO =================
for key in ["contrato", "proyecto", "empresa"]:
    if key not in st.session_state:
        st.session_state[key] = ""

# ================= GOOGLE SHEETS =================
ID_SHEET = "1q2cvx9FD1CW8XP_kZpsFvfKtu4QdrJPqKAZuueHRIW4"

# ================= CARGA DE DATOS =================
@st.cache_data
def cargar_datos():

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    creds = Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=scopes
    )

    client = gspread.authorize(creds)
    sh = client.open_by_key(ID_SHEET)
    ws = sh.get_worksheet(0)

    df = pd.DataFrame(ws.get_all_records())
    df.columns = df.columns.str.strip()

    return df


df = cargar_datos()

# ================= LIMPIEZA NUMÉRICA =================
for col in ["Importe total (LC)", "EJERCIDO", "Abrir importe (LC)"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# ================= FUNCIONES =================
def formato_pesos(valor):
    try:
        return f"$ {float(valor):,.2f}"
    except:
        return "$ 0.00"


def convertir_excel(dataframe):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False)
    return output.getvalue()

# ================= FILTROS =================
st.subheader("🔎 Filtros")

c1, c2, c3, c4 = st.columns([2, 3, 3, 1])

# ---- PROYECTO ----
with c1:
    proyectos = ["Todos"] + sorted(df["DESC PROYECTO"].dropna().unique())
    st.session_state.proyecto = st.selectbox(
        "DESC PROYECTO",
        proyectos,
        index=0 if st.session_state.proyecto == "" else proyectos.index(st.session_state.proyecto)
    )

# ---- EMPRESA ----
with c2:
    empresas = ["Todas"] + sorted(df["EMPRESA"].dropna().unique())
    st.session_state.empresa = st.selectbox(
        "EMPRESA",
        empresas,
        index=0 if st.session_state.empresa == "" else empresas.index(st.session_state.empresa)
    )

# ================= FILTRADO BASE =================
resultado = df.copy()

if st.session_state.proyecto not in ["", "Todos"]:
    resultado = resultado[
        resultado["DESC PROYECTO"] == st.session_state.proyecto
    ]

if st.session_state.empresa not in ["", "Todas"]:
    resultado = resultado[
        resultado["EMPRESA"] == st.session_state.empresa
    ]

# ---- CONTRATOS DEPENDIENTES ----
contratos = [""] + sorted(
    resultado["N° CONTRATO"].dropna().astype(str).unique().tolist()
)

with c3:
    st.session_state.contrato = st.selectbox(
        "N° CONTRATO",
        contratos,
        index=0 if st.session_state.contrato == "" else contratos.index(st.session_state.contrato)
    )

# ---- LIMPIAR ----
with c4:
    if st.button("Limpiar"):
        for k in ["contrato", "proyecto", "empresa"]:
            st.session_state[k] = ""
        st.rerun()

# ================= CONSUMO (SOLO SI HAY CONTRATO) =================
st.subheader("💰 Consumo del contrato")

if st.session_state.contrato:

    df_contrato = resultado[
        resultado["N° CONTRATO"].astype(str) == st.session_state.contrato
    ]

    monto_contrato = df_contrato["Importe total (LC)"].iloc[0]
    monto_ejercido = df_contrato["EJERCIDO"].sum()
    monto_pendiente = df_contrato["Abrir importe (LC)"].sum()

    a, b, c = st.columns(3)
    a.metric("Importe del contrato", formato_pesos(monto_contrato))
    b.metric("Importe ejercido", formato_pesos(monto_ejercido))
    c.metric("Importe pendiente", formato_pesos(monto_pendiente)

else:
    st.info("ℹ️ Selecciona un contrato para visualizar el consumo")

# ================= TABLA =================
st.subheader("📄 Tabla de resultados")

tabla = resultado.groupby(
    ["N° CONTRATO", "DESCRIPCION"],
    as_index=False
).agg({
    "Importe total (LC)": "first",
    "% PAGADO": "first",
    "% PENDIENTE POR EJERCER": "first"
})

tabla["Importe total (LC)"] = tabla["Importe total (LC)"].apply(formato_pesos)

st.dataframe(tabla, use_container_width=True, height=420)

# ================= EXPORTAR =================
st.divider()
st.download_button(
    "📥 Descargar resultados en Excel",
    convertir_excel(tabla),
    file_name="resultados_contratos.xlsx"
)
