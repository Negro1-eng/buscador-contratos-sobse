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

# ================= CONTRATOS =================
contratos = [""] + sorted(
    resultado["N° CONTRATO"].dropna().astype(str).unique()
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

        e1.metric("Original", formato_pesos(evo["ORIGINAL"]))
        e2.metric("Modificado", formato_pesos(evo["MODIFICADO"]))
        e3.metric("Comprometido", formato_pesos(evo["COMPROMETIDO"]))
        e4.metric("Ejercido", formato_pesos(evo["EJERCIDO"]))

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

# ================= RESULTADOS + CLC =================
hay_filtros = (
    st.session_state.proyecto != "Todos"
    or st.session_state.empresa != "Todas"
    or st.session_state.contrato != ""
)

if hay_filtros:
    tabla = agrupado[[
        "N° CONTRATO",
        "DESCRIPCION",
        "Importe total (LC)",
        "% PAGADO",
        "% PENDIENTE POR EJERCER"
    ]].copy()

    tabla["Importe total (LC)"] = tabla["Importe total (LC)"].apply(formato_pesos)

    if st.session_state.contrato:
        with st.expander("Resultados del proyecto / empresa", expanded=False):
            st.dataframe(tabla, use_container_width=True, height=300)
    else:
        st.subheader("Resultados")
        st.dataframe(tabla, use_container_width=True, height=420)

    # ===== CLC =====
    if st.session_state.contrato:
        st.subheader("CLC del contrato seleccionado")

        clc_contrato = df_clc[
            df_clc["CONTRATO"].astype(str) == st.session_state.contrato
        ][["CLC", "MONTO", "LINK_PDF"]].copy()

        if clc_contrato.empty:
            st.info("Este contrato no tiene CLC registrados")
        else:
            total_clc = clc_contrato["MONTO"].sum()
            clc_contrato["MONTO"] = clc_contrato["MONTO"].apply(formato_pesos)

            clc_contrato["PDF"] = clc_contrato["LINK_PDF"].apply(
                lambda x: f"[📄 Ver PDF]({x})" if x else ""
            )

            clc_contrato = clc_contrato[["CLC", "MONTO", "PDF"]]

            filas = len(clc_contrato)
            altura = min(45 + filas * 35, 500)

            st.dataframe(
                clc_contrato,
                use_container_width=True,
                height=altura,
                column_config={
                    "PDF": st.column_config.MarkdownColumn(
                        "PDF",
                        help="Abrir CLC en PDF"
                    )
                }
            )

            st.markdown(f"### **Total CLC:** {formato_pesos(total_clc)}")

    st.divider()
    st.download_button(
        "Descargar resultados en Excel",
        convertir_excel(tabla),
        file_name="resultados_contratos.xlsx"
    )
else:
    st.info("Aplica un filtro para ver resultados")
