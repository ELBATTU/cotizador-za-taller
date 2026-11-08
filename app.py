# ------------------------------------------
# TAB 2: HISTORIAL DE COTIZACIONES CON FILTROS, DESCARGA Y EDICIÓN CONTROLADA
# ------------------------------------------
with tab_historial:
    st.header("📋 Historial de Cotizaciones Registradas")
    df_hist = cargar_historial()
    
    if not df_hist.empty:
        # CONTROLES DE FILTRADO POR FECHA
        st.markdown("### 🔍 Filtrar Métricas y Registros")
        f_col1, f_col2 = st.columns([2, 3])
        
        with f_col1:
            filtro_tipo = st.selectbox("Filtrar por período:", ["Histórico Completo", "Por Mes", "Por Año", "Rango Personalizado"])
            
        df_filtrado = df_hist.copy()
        
        if filtro_tipo == "Por Mes":
            meses_disp = sorted(df_hist["dt_cotizacion"].dt.to_period("M").astype(str).unique(), reverse=True)
            mes_sel = st.selectbox("Selecciona el mes:", meses_disp)
            df_filtrado = df_hist[df_hist["dt_cotizacion"].dt.to_period("M").astype(str) == mes_sel]
            
        elif filtro_tipo == "Por Año":
            anos_disp = sorted(df_hist["dt_cotizacion"].dt.year.unique(), reverse=True)
            ano_sel = st.selectbox("Selecciona el año:", anos_disp)
            df_filtrado = df_hist[df_hist["dt_cotizacion"].dt.year == ano_sel]
            
        elif filtro_tipo == "Rango Personalizado":
            r_col1, r_col2 = st.columns(2)
            f_inicio = r_col1.date_input("Fecha Inicio", value=datetime.date.today().replace(day=1))
            f_fin = r_col2.date_input("Fecha Fin", value=datetime.date.today())
            df_filtrado = df_hist[(df_hist["dt_cotizacion"].dt.date >= f_inicio) & (df_hist["dt_cotizacion"].dt.date <= f_fin)]

        st.markdown("---")

        # MÉTRICAS DINÁMICAS SEGÚN FILTRO
        h_col1, h_col2, h_col3 = st.columns(3)
        h_col1.metric("Cotizaciones en el Periodo", len(df_filtrado))
        h_col2.metric("Monto Total Cotizado", f"${df_filtrado['Total Cobrado'].sum():,.2f} MXN")
        promedio_venta = df_filtrado['Total Cobrado'].mean() if len(df_filtrado) > 0 else 0.0
        h_col3.metric("Promedio por Venta", f"${promedio_venta:,.2f} MXN")

        # BOTÓN PARA DESCARGAR REPORTE EN CSV RESPETANDO EL FILTRO
        df_exportar = df_filtrado[["Fecha Cotización", "Fecha Captura", "Cliente", "Teléfono", "Producto", "Material", "Cantidad", "Precio Unitario", "Total Cobrado"]].copy()
        csv_bytes = df_exportar.to_csv(index=False).encode('utf-8-sig')

        st.download_button(
            label=f"📥 Descargar Reporte Filtrado ({len(df_filtrado)} registros)",
            data=csv_bytes,
            file_name=f"Reporte_Cotizaciones_{filtro_tipo.replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        st.markdown("---")
        st.markdown("### ✏️ Edición Controlada (Cliente, Teléfono y Fecha de Trato)")
        st.info("💡 Puedes modificar directamente en la tabla el **Nombre del Cliente**, **Teléfono** o la **Fecha Cotización** (por si capturas algo desfasado). Los montos y productos se mantienen protegidos por seguridad.")

        df_editable = df_filtrado[["id", "Foto", "Fecha Cotización", "Fecha Captura", "Cliente", "Teléfono", "Producto", "Material", "Cantidad", "Precio Unitario", "Total Cobrado"]].copy()

        df_editado = st.data_editor(
            df_editable,
            use_container_width=True,
            hide_index=True,
            key="editor_historial_controlado",
            column_config={
                "id": None,
                "Foto": st.column_config.ImageColumn("Foto", help="Vista previa", width="small"),
                "Fecha Cotización": st.column_config.TextColumn("Fecha Cotización (Editable)"),
                "Fecha Captura": st.column_config.TextColumn("Fecha Captura (Sistema)", disabled=True),
                "Cliente": st.column_config.TextColumn("Cliente (Editable)"),
                "Teléfono": st.column_config.TextColumn("Teléfono (Editable)"),
                "Producto": st.column_config.TextColumn("Producto", disabled=True),
                "Material": st.column_config.TextColumn("Material", disabled=True),
                "Cantidad": st.column_config.NumberColumn("Cantidad", format="%d", disabled=True),
                "Precio Unitario": st.column_config.NumberColumn("Precio Unitario", format="$%.2f", disabled=True),
                "Total Cobrado": st.column_config.NumberColumn("Total Cobrado", format="$%.2f", disabled=True)
            }
        )

        if st.button("💾 Guardar Cambios en Historial", type="primary", key="btn_save_hist"):
            for _, row in df_editado.iterrows():
                if pd.notnull(row["id"]):
                    supabase.table("historial_cotizaciones").update({
                        "cliente": row["Cliente"],
                        "telefono": row["Teléfono"],
                        "fecha_cotizacion": str(row["Fecha Cotización"])
                    }).eq("id", int(row["id"])).execute()
            
            st.cache_data.clear()
            st.toast("Historial actualizado correctamente", icon="📝")
            st.success("✅ Historial actualizado.")
            time.sleep(1)
            st.rerun()
    else:
        st.info("💡 Aún no hay cotizaciones guardadas.")
