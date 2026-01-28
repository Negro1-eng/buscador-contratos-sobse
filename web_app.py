import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ================= CONFIGURACIÓN =================
st.set_page_config(page_title="Consumo de Contratos", layout="wide")
st.title("Consumo de Contratos")

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

    df = pd.DataFrame(client.open_by_key(ID_SHEET).get_worksheet(0).get_all_records())
    df_clc = pd.DataFrame(client.open_by_key(ID_SHEET).worksheet("CLC_CONTRATOS").get_all_records())

    df.columns = df.columns.str.strip()
    df_clc.columns = df_clc.columns.str.strip()

    return df, df_clc

df, df_clc = cargar_datos()

# ================= NORMALIZAR =================
for col in ["Importe total (LC)", "EJERCIDO", "Abrir importe (LC)"]:
    df[col] = (
        df[col].astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
    )
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

df_clc["MONTO"] = (
    df_clc["MONTO"].astype(str)
    .str.replace("$", "", regex=False)
    .str.replace(",", "", regex=False)
)
df_clc["MONTO"] = pd.to_numeric(df_clc["MONTO"], errors="coerce").fillna(0)

# ================= FORMATO =================
def pesos(v):
    return f"$ {v:,.2f}"

# ================= AGRUPAR CONTRATOS =================
agrupado = df.groupby(
    ["N° CONTRATO", "DESCRIPCION"],
    as_index=False
).agg({
    "Importe total (LC)": "max",
    "EJERCIDO": "sum",
    "Abrir importe (LC)": "sum"
})

# ================= RESULTADOS =================
st.subheader("Resultados de contratos")

for _, row in agrupado.iterrows():
    contrato = str(row["N° CONTRATO"])

    with st.expander(f"📄 Contrato {contrato} | {row['DESCRIPCION']}"):
        c1, c2, c3 = st.columns(3)

        c1.metric("Importe contrato", pesos(row["Importe total (LC)"]))
        c2.metric("Ejercido", pesos(row["EJERCIDO"]))
        c3.metric("Pendiente", pesos(row["Abrir importe (LC)"]))

        # ===== CLC DEL CONTRATO =====
        clc_contrato = df_clc[
            df_clc["CONTRATO"].astype(str) == contrato
        ][["CLC", "MONTO"]].copy()

        if clc_contrato.empty:
            st.info("Este contrato no tiene CLC registrados")
        else:
            total_clc = clc_contrato["MONTO"].sum()

            clc_contrato["MONTO"] = clc_contrato["MONTO"].apply(pesos)

            st.markdown("####  CLC del contrato")
            st.dataframe(clc_contrato, use_container_width=True)

            st.markdown(
                f"###  **Total CLC:** {pesos(total_clc)}"
            )
