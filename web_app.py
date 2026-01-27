@st.cache_data
def cargar_datos():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    creds = Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=scopes
    )

    client = gspread.authorize(creds)
    book = client.open_by_key(ID_SHEET)

    # Hoja principal
    ws_contratos = book.get_worksheet(0)
    df_contratos = pd.DataFrame(ws_contratos.get_all_records())
    df_contratos.columns = df_contratos.columns.str.strip()

    # Hoja Evolucion
    ws_evolucion = book.worksheet("Evolucion")
    df_evolucion = pd.DataFrame(ws_evolucion.get_all_records())
    df_evolucion.columns = df_evolucion.columns.str.strip()

    # Hoja CLC (manejo seguro)
    try:
        ws_clc = book.worksheet("CLC_CONTRATOS")
        df_clc = pd.DataFrame(ws_clc.get_all_records())
        df_clc.columns = df_clc.columns.str.strip()
    except Exception:
        df_clc = pd.DataFrame(columns=["CONTRATO", "CLC", "MONTO"])

    return df_contratos, df_evolucion, df_clc
