import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
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
        st.success("Datos actualizados desde Google Sheets y Drive")
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

# ================= IDs =================
ID_SHEET = "1q2cvx9FD1CW8XP_kZpsFvfKtu4QdrJPqKAZuueHRIW4"
FOLDER_ID = "1MQtSIS1l-nL0KLLgL46tmo83FJtq4XZJ"

# ================= CARGAR GOOGLE SHEETS =================
@st.cache_data
def cargar_datos():

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly"
    ]

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


# ================= CARGAR PDFs DRIVE =================
@st.cache_data
def cargar_pdfs_drive():

    scopes = ["https://www.googleapis.com/auth/drive.readonly"]

    creds = Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=scopes
    )

    service = build("drive", "v3", credentials=creds)

    results = service.files().list(
        q=f"'{FOLDER_ID}' in parents and mimeType='application/pdf'",
        fields="files(id, name)",
        pageSize=1000
    ).execute()

    files = results.get("files", [])

    pdf_dict = {}

    for file in files:
        nombre = file["name"]

        # 🔥 NORMALIZACIÓN FUERTE
        nombre_limpio = (
            nombre.lower()
            .replace(".pdf", "")
            .strip()
            .replace(" ", "")
        )

        link = f"https://drive.google.com/file/d/{file['id']}/view"
        pdf_dict[nombre_limpio] = link

    return pdf_dict


# ================= CARGA INICIAL =================
df, df_evolucion, df_clc = cargar_datos()
pdf_drive = cargar_pdfs_drive()

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

def limpiar_filtros():
    st.session_state.proyecto = "Todos"
    st.session_state.empresa = "Todas"
    st.session_state.contrato = ""

# ================= FILTROS =================
st.subheader("Filtros")
c1, c2, c3, c4 = st.columns([3, 3, 3, 1])

with c1:
    proyectos = ["Todos"] + sorted(df["DESC PROYECTO"].dropna().unique())
    st.selectbox("DESC PROGRAMA", proyectos, key="proyecto")

with c2:
    empresas = ["Todas"] + sorted(df["EMPRESA"].dropna().unique())
    st.selectbox("EMPRESA", empresas, key="empresa")

resultado = df.copy()

if st.session_state.proyecto != "Todos":
    resultado = resultado[resultado["DESC PROYECTO"] == st.session_state.proyecto]

if st.session_state.empresa != "Todas":
    resultado = resultado[resultado["EMPRESA"] == st.session_state.empresa]

contratos = [""] + sorted(resultado["N° CONTRATO"].dropna().astype(str).unique())

with c3:
    st.selectbox("N° CONTRATO", contratos, key="contrato")

with c4:
    st.button("Limpiar Filtros", on_click=limpiar_filtros)

# ================= TABLA DE CONTRATOS =================
if not st.session_state.contrato:

    tabla = resultado.groupby(
        ["N° CONTRATO", "DESCRIPCION"],
        as_index=False
    ).agg({
        "Importe total (LC)": "max",
        "% PAGADO": "first",
        "% PENDIENTE POR EJERCER": "first"
    })

    tabla["Importe total (LC)"] = tabla["Importe total (LC)"].apply(formato_pesos)

    st.subheader("Resultados")
    st.dataframe(tabla, use_container_width=True, height=420)

# ================= CONSUMO + CLC =================
if st.session_state.contrato:

    st.subheader("Consumo del contrato")

    df_contrato = resultado[
        resultado["N° CONTRATO"].astype(str) == st.session_state.contrato
    ]

    monto_contrato = df_contrato["Importe total (LC)"].max()
    monto_ejercido = df_contrato["EJERCIDO"].sum()
    monto_pendiente = df_contrato["Abrir importe (LC)"].sum()

    a, b, c = st.columns(3)
    a.metric("Importe del contrato", formato_pesos(monto_contrato))
    b.metric("Importe ejercido", formato_pesos(monto_ejercido))
    c.metric("Importe pendiente", formato_pesos(monto_pendiente))

    # ================= CLC =================
    st.subheader("CLC del contrato seleccionado")

    clc_contrato = df_clc[
        df_clc["CONTRATO"].astype(str) == st.session_state.contrato
    ][["CLC", "MONTO"]].copy()

    if clc_contrato.empty:
        st.info("Este contrato no tiene CLC registrados")
    else:
        total_clc = clc_contrato["MONTO"].sum()
        clc_contrato["MONTO"] = clc_contrato["MONTO"].apply(formato_pesos)

        def buscar_pdf(clc):
            clave = str(clc).strip().replace(" ", "").lower()
            return pdf_drive.get(clave, None)

        clc_contrato["PDF"] = clc_contrato["CLC"].apply(buscar_pdf)

        st.dataframe(
            clc_contrato,
            use_container_width=True,
            column_config={
                "PDF": st.column_config.LinkColumn(
                    "PDF",
                    display_text="Ver PDF"
                )
            }
        )

        st.markdown(f"### **Total CLC:** {formato_pesos(total_clc)}")
