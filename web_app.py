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

st.title("Buscador de Consumo de Contratos")

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

    # 👉 Se toma la PRIMERA hoja del archivo
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

# ================= FILTROS =================
st.subheader("Filtros")

c1, c2, c3, c4 = st.columns([2, 2, 2, 1])

with c1:
    st.session_state.contrato = st.text_input(
        "N° CONTRATO", st.session_state.contrato
    )

with c2:
    st.session_state.proyecto = st.text_input(
        "DESC PROYECTO", st.session_state.proyecto
    )

with c3:
    st.session_state.empresa = st.text_input(
        "EMPRESA", st.session_state.empresa
    )

with c4:
    if st.button("Limpiar búsquedas"):
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

if st.session_state.proyecto:
    resultado = resultado[
        resultado["DESC PROYECTO"]
        .astype(str)
        .str.contains(st.session_state.proyecto, case=False, na=False)
    ]

if st.session_state.empresa:
    resultado = resultado[
        resultado["EMPRESA"]
        .astype(str)
        .str.contains(st.session_state.empresa, case=False, na=False)
    ]

# ================= CONSUMO =================
st.subheader("Consumo")

total_contrato = (
    resultado["Importe total (LC)"]
    .apply(pd.to_numeric, errors="coerce")
    .sum()
)

total_ejercido = (
    resultado["EJERCIDO"]
    .apply(pd.to_numeric, errors="coerce")
    .sum()
)

total_pendiente = (
    resultado["Abrir importe (LC)"]
    .apply(pd.to_numeric, errors="coerce")
    .sum()
)

a, b, c = st.columns(3)
a.metric("Importe total del contrato", formato_pesos(total_contrato))
b.metric("Importe ejercido", formato_pesos(total_ejercido))
c.metric("Importe pendiente", formato_pesos(total_pendiente))

# ================= TABLA =================
st.subheader("Tabla de resultados")

tabla = resultado[[
    "N° CONTRATO",
    "DESCRIPCION",
    "Importe total (LC)",
    "% PAGADO",
    "% PENDIENTE POR EJERCER"
]].copy()

st.dataframe(tabla, use_container_width=True, height=420)

# ================= EXPORTAR =================
st.divider()
st.download_button(
    "Descargar resultados en Excel",
    convertir_excel(tabla),
    file_name="resultados_contratos.xlsx"
)






