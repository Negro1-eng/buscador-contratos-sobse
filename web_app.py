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

# ================= CONVERTIR NUMÉRICOS =================
for col in ["Importe total (LC)", "EJERCIDO", "Abrir importe (LC)"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# ================= FILTROS =================
st.subheader("🔎 Filtros")

c1, c2, c3, c4 = st.columns([2, 3, 3, 1])

with c1:
    st.session_state.contrato = st.text_input(
        "N° CONTRATO", st.session_state.contrato
    )

with c2:
    proyectos = ["Todos"] + sorted(
        df["DESC PROYECTO"].dropna().unique().tolist()
    )
    st.session_state.proyecto = st.selectbox(
        "DESC PROYECTO", proyectos
    )

with c3:
    empresas = ["Todas"] + sorted(
        df["EMPRESA"].dropna().unique().tolist()
    )
    st.session_state.empresa = st.selectbox(
        "EMPRESA", empresas
    )

with c4:
    if st.button("Limpiar"):
        for k in ["contrato", "proyecto", "empresa"]:
            st.session_state[k] = ""
        st.rerun()

# ================= FILTRADO =================
resultado = df.copy()

if st.session_state.contrato:
    resultado = resultado[
        resultado["N° CONTRATO"]
        .astype(str)
        .str.contains(st.session_state.contrato, case=False, na=False)
    ]

if st.session_state.proyecto and st.session_state.proyecto != "Todos":
    resultado = resultado[
        resultado["DESC PROYECTO"] == st.session_state.proyecto
    ]

if st.session_state.empresa and st.session_state.empresa != "Todas":
    resultado = resultado[
        resultado["EMPRESA"] == st.session_state.empresa
    ]

# ================= AGRUPAR POR CONTRATO =================
agrupado = resultado.groupby(
    ["N° CONTRATO", "DESCRIPCION"],
    as_index=False
).agg({
    "Importe total (LC)": "first",
    "EJERCIDO": "sum",
    "Abrir importe (LC)": "sum",
    "% PAGADO": "first",
    "% PENDIENTE POR EJERCER": "first"
})

# ================= CONSUMO =================
st.subheader("💰 Consumo del contrato")

total_contrato = agrupado["Importe total (LC)"].sum()
total_ejercido = agrupado["EJERCIDO"].sum()
total_pendiente = agrupado["Abrir importe (LC)"].sum()

a, b, c = st.columns(3)
a.metric("Importe total del contrato", formato_pesos(total_contrato))
b.metric("Importe ejercido", formato_pesos(total_ejercido))
c.metric("Importe pendiente", formato_pesos(total_pendiente))

# ================= TABLA =================
st.subheader("📄 Tabla de resultados")

tabla = agrupado[[
    "N° CONTRATO",
    "DESCRIPCION",
    "Importe total (LC)",
    "% PAGADO",
    "% PENDIENTE POR EJERCER"
]].copy()

tabla["Importe total (LC)"] = tabla["Importe total (LC)"].apply(formato_pesos)

st.dataframe(tabla, use_container_width=True, height=420)

# ================= EXPORTAR =================
st.divider()
st.download_button(
    "📥 Descargar resultados en Excel",
    convertir_excel(tabla),
    file_name="resultados_contratos.xlsx"
)

