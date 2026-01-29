# ================= TABLA =================
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

    # ===== TABLA RESULTADOS =====
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
        ][["CLC", "MONTO"]].copy()

        if clc_contrato.empty:
            st.info("Este contrato no tiene CLC registrados")
        else:
            total_clc = clc_contrato["MONTO"].sum()
            clc_contrato["MONTO"] = clc_contrato["MONTO"].apply(formato_pesos)

            # altura dinámica
            filas = len(clc_contrato)
            altura = min(45 + filas * 35, 500)

            st.dataframe(
                clc_contrato,
                use_container_width=True,
                height=altura
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
