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
    sh = client.open_by_key(ID_SHEET)

    df_contratos = pd.DataFrame(sh.get_worksheet(0).get_all_records())
    df_evolucion = pd.DataFrame(sh.worksheet("Evolucion").get_all_records())
    df_clc = pd.DataFrame(sh.worksheet("CLC_CONTRATOS").get_all_records())

    df_contratos.columns = df_contratos.columns.str.strip()
    df_evolucion.columns = df_evolucion.columns.str.strip()
    df_clc.columns = df_clc.columns.str.strip()

    return df_contratos, df_evolucion, df_clc

df, df_evolucion, df_clc = cargar_datos()

# ================= NORMALIZAR NUMÉRICOS =================
for col in ["Importe total (LC)", "EJERCIDO", "Abrir importe (LC)"]:
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

df_clc["CONTRATO"] = df_clc["CONTRATO"].astype(str).str.strip()
df_clc["MONTO"] = (
    df_clc["MONTO"].astype(str)
    .str.replace("$", "", regex=False)
    .str.replace(",", "", regex=False)
)
df_clc["MONTO"] = pd.to_numeric(df_clc["MONTO"], errors="coerce").fillna(0)

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
    proyectos = ["Todos"] + sorted(df["DESC PROYECTO"].dropna().unique())
    st.selectbox("DESC PROGRAMA", proyectos, key="proyecto")

with c2:
    empresas = ["Todas"] + sorted(df["EMPRESA"].dropna().unique())
    st.selectbox("EMPRESA", empresas, key="empresa")

# ================= FILTRADO BASE =================
resultado = df.copy()

if st.session_state.proyecto != "Todos":
    resultado = resultado[resultado["DESC PROYECTO"] == st.session_state.proyecto]

if st.session_state.empresa != "Todas":
    resultado = resultado[resultado["EMPRESA"] == st.session_state.empresa]

# ================= AGRUPAR =================
agrupado = resultado.groupby(
    ["N° CONTRATO", "DESCRIPCION"],
    as_index=False
).agg({
    "Importe total (LC)": "max",
    "EJERCIDO": "sum",
    "Abrir importe (LC)": "sum",
    "% PAGADO": "first",
    "% PENDIENTE POR EJERCER": "first"
})

# ================= TABLA DE RESULTADOS =================
st.subheader("Resultados")

tabla = agrupado[[
    "N° CONTRATO",
    "DESCRIPCION",
    "Importe total (LC)",
    "% PAGADO",
    "% PENDIENTE POR EJERCER"
]].copy()

tabla["Importe total (LC)"] = tabla["Importe total (LC)"].apply(formato_pesos)

st.dataframe(tabla, use_container_width=True, height=420)

# ================= SELECCIÓN DE CONTRATO =================
st.markdown("### 🔎 Selecciona un contrato para ver sus CLC")

contrato_sel = st.selectbox(
    "Contrato",
    options=tabla["N° CONTRATO"].astype(str).unique()
)

# ================= CLC DEL CONTRATO =================
clc_contrato = df_clc[df_clc["CONTRATO"] == contrato_sel]

if not clc_contrato.empty:
    st.subheader(f"CLC asociadas al contrato {contrato_sel}")

    tabla_clc = clc_contrato[[
        "CLC",
        "Fondo",
        "Posición presupuestaria",
        "Programa de financiación",
        "MONTO"
    ]].copy()

    tabla_clc["MONTO"] = tabla_clc["MONTO"].apply(formato_pesos)

    st.dataframe(tabla_clc, use_container_width=True, height=300)

    st.metric(
        "Total ejercido por CLC",
        formato_pesos(clc_contrato["MONTO"].sum())
    )
else:
    st.info("Este contrato no tiene CLC registradas")

# ================= DESCARGA =================
st.divider()
st.download_button(
    "Descargar resultados en Excel",
    convertir_excel(tabla),
    file_name="resultados_contratos.xlsx"
)
