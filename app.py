import streamlit as st
import pandas as pd
import datetime
import urllib.parse
import time
import io
from PIL import Image
from supabase import create_client, Client
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Desactivar límite de píxeles para imágenes grandes
Image.MAX_IMAGE_PIXELS = None

# ==========================================
# CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="Z&A Taller Creativo - Cotizador",
    page_icon="✂️",
    layout="wide"
)

# ==========================================
# INICIALIZACIÓN DE SUPABASE
# ==========================================
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["supabase"]["SUPABASE_URL"]
    key = st.secrets["supabase"]["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# ==========================================
# FUNCIONES DE BASE DE DATOS OPTIMIZADAS
# ==========================================
@st.cache_data(ttl=600)
def cargar_materiales():
    res = supabase.table("materiales").select("*").execute()
    return {item["nombre"]: float(item["costo_cm2"]) for item in res.data}

@st.cache_data(ttl=600)
def cargar_catalogo():
    res = supabase.table("catalogo").select("*").execute()
    cat_dict = {}
    for item in res.data:
        cat_dict[item["nombre"]] = {
            "largo": float(item["largo"]),
            "ancho": float(item["ancho"]),
            "tiempo": float(item["tiempo"]),
            "material": item["material"],
            "foto": item["foto_url"]
        }
    return cat_dict

def cargar_historial():
    res = supabase.table("historial_cotizaciones").select("*").order("fecha", desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df["fecha"] = pd.to_datetime(df["fecha"]).dt.strftime("%Y-%m-%d %H:%M")
        
        # Mapear URL de foto desde el catálogo actual por nombre de producto
        cat_dict = cargar_catalogo()
        df["foto_url"] = df["producto"].map(lambda p: cat_dict.get(p, {}).get("foto"))
        
        df.rename(columns={
            "fecha": "Fecha", "cliente": "Cliente", "telefono": "Teléfono",
            "producto": "Producto", "material": "Material", "cantidad": "Cantidad",
            "precio_unitario": "Precio Unitario", "total_cobrado": "Total Cobrado",
            "foto_url": "Foto"
        }, inplace=True)
        return df[["id", "Foto", "Fecha", "Cliente", "Teléfono", "Producto", "Material", "Cantidad", "Precio Unitario", "Total Cobrado"]]
    return pd.DataFrame()

# Carga inicial
precios_materiales = cargar_materiales()
CATALOGO = cargar_catalogo()

# ==========================================
# GENERADOR DE PDF PROFESIONAL
# ==========================================
def generar_pdf_cotizacion(datos_pdf):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=20, textColor=colors.HexColor('#1E88E5'))
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#666666'))
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#333333'))
    bold_style = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#333333'))

    header_data = [
        [
            Paragraph("<b>Z&A TALLER CREATIVO</b><br/>Corte & Grabado Láser CNC<br/>Contacto: taller@zataller.com", title_style),
            Paragraph(f"<b>COTIZACIÓN DE VENTA</b><br/>Fecha: {datetime.datetime.now().strftime('%d/%m/%Y')}<br/>Vigencia: 15 días", subtitle_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[330, 210])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    elements.append(header_table)
    elements.append(Spacer(1, 15))

    cliente_info = [
        [Paragraph(f"<b>Cliente:</b> {datos_pdf['cliente']}", body_style), Paragraph(f"<b>Teléfono:</b> {datos_pdf['telefono']}", body_style)]
    ]
    info_table = Table(cliente_info, colWidths=[300, 240])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0F2F6')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 15))

    table_data = [
        ["Producto", "Material", "Dimensiones", "Cantidad", "Precio Unitario", "Total"],
        [
            datos_pdf['producto'],
            datos_pdf['material'],
            f"{datos_pdf['largo']:.1f} x {datos_pdf['ancho']:.1f} cm",
            str(datos_pdf['cantidad']),
            f"${datos_pdf['precio_unitario']:,.2f} MXN",
            f"${datos_pdf['total']:,.2f} MXN"
        ]
    ]

    prod_table = Table(table_data, colWidths=[140, 100, 100, 50, 80, 70])
    prod_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E88E5')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#DDDDDD')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(prod_table)
    elements.append(Spacer(1, 20))

    total_data = [
        ["", Paragraph(f"<b>TOTAL A PAGAR:</b> <font color='#1E88E5' size='12'><b>${datos_pdf['total']:,.2f} MXN</b></font>", bold_style)]
    ]
    total_table = Table(total_data, colWidths=[300, 240])
    total_table.setStyle(TableStyle([('ALIGN', (1,0), (1,0), 'RIGHT')]))
    elements.append(total_table)
    elements.append(Spacer(1, 30))

    elements.append(Paragraph("<i>¡Gracias por su preferencia! Quedamos a sus órdenes para cualquier ajuste en su proyecto.</i>", subtitle_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==========================================
# ESTILOS VISUALES CSS
# ==========================================
st.markdown("""
    <style>
    .main-title { font-size: 32px; font-weight: bold; color: #1E88E5; }
    div[data-testid="stImage"] img {
        max-height: 380px; width: 100%; object-fit: contain; border-radius: 10px;
    }
    table { width: 100%; border-collapse: collapse; margin: 10px 0; }
    th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #ddd; }
    th { background-color: #f0f2f6; color: #333; }
    
    .card-tech {
        background-color: #F8F9FA;
        border-left: 5px solid #1E88E5;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 12px;
        color: #212529;
    }
    .card-tech h4 { margin: 0 0 10px 0; color: #1E88E5; font-size: 16px; }
    .tech-row { display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# AUTENTICACIÓN
# ==========================================
def verificar_password():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        _, col2, _ = st.columns([1, 2, 1])
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.subheader("🔒 Acceso Restringido - Z&A Taller Creativo")
            pwd_input = st.text_input("Ingresa la contraseña del taller:", type="password")
            
            if st.button("Ingresar", type="primary", use_container_width=True, key="btn_login"):
                pwd_correcta = st.secrets.get("passwords", {}).get("admin", "ZA2026*")
                if pwd_input == pwd_correcta:
                    st.session_state["autenticado"] = True
                    st.rerun()
                else:
                    st.error("❌ Contraseña incorrecta")
        return False
    return True

if not verificar_password():
    st.stop()

# ==========================================
# BARRA LATERAL
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #4A90E2;'>Z&A TALLER CREATIVO</h2>", unsafe_allow_html=True)
    if st.button("🔒 Cerrar Sesión", use_container_width=True, key="btn_logout_sidebar"):
        st.session_state["autenticado"] = False
        st.rerun()

    st.markdown("---")
    st.header("⚙️ Configuración de Costos")

tarifa_minuto = st.sidebar.number_input("Tarifa Láser ($/min):", value=8.0, step=0.5)
utilidad_porcentaje = st.sidebar.slider("% Utilidad deseada:", min_value=10, max_value=200, value=30, step=5) / 100
desperdicio_factor = 1.10

# ==========================================
# PESTAÑAS DE NAVEGACIÓN
# ==========================================
tab_cotizador, tab_historial, tab_admin = st.tabs([
    "🧮 Cotizador Interactivo", 
    "📋 Historial de Cotizaciones", 
    "⚙️ Administración"
])

# ------------------------------------------
# TAB 1: COTIZADOR INTERACTIVO
# ------------------------------------------
with tab_cotizador:
    st.markdown("<h1 style='color: #1E88E5;'>Z&A Taller Creativo</h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 18px; color: #888;'>Cotizador Interactivo - Corte & Grabado Láser CNC</p>", unsafe_allow_html=True)
    st.markdown("---")

    col_cat, col_inputs = st.columns([1, 1.2])

    with col_cat:
        st.subheader("🖼️ Producto & Datos Cliente")
        nombre_cliente = st.text_input("Nombre del Cliente:", placeholder="Ej. Juan Pérez")
        telefono_cliente = st.text_input("Teléfono WhatsApp (opcional):", placeholder="Ej. 4421234567")
        
        lista_productos = list(CATALOGO.keys())
        if "Personalizado (Medida Libre)" in lista_productos:
            lista_productos.remove("Personalizado (Medida Libre)")
            lista_productos.insert(0, "Personalizado (Medida Libre)")

        producto_sel = st.selectbox("Elige un producto del catálogo:", lista_productos)        
        datos_prod = CATALOGO[producto_sel]
        
        if datos_prod.get("foto"):
            st.image(datos_prod["foto"], caption=producto_sel, use_container_width=True)
        else:
            st.info("💡 Producto personalizado sin foto asignada.")

    with col_inputs:
        st.subheader("📏 Dimensiones y Tiempos")
        mat_keys = list(precios_materiales.keys())
        mat_index = mat_keys.index(datos_prod["material"]) if datos_prod["material"] in mat_keys else 0
        material = st.selectbox("Material:", mat_keys, index=mat_index)
        
        col_l, col_a = st.columns(2)
        largo = col_l.number_input("Largo (cm):", value=float(datos_prod["largo"]), min_value=1.0, step=1.0)
        ancho = col_a.number_input("Ancho (cm):", value=float(datos_prod["ancho"]), min_value=1.0, step=1.0)
            
        col_t, col_c = st.columns(2)
        tiempo = col_t.number_input("Tiempo Láser por Pieza (min):", value=float(datos_prod["tiempo"]), min_value=0.1, step=0.5)
        cantidad = col_c.number_input("Cantidad Pedida (piezas):", value=1, min_value=1, step=1)

    area_bruta = largo * ancho
    area_con_merma = area_bruta * desperdicio_factor
    costo_cm2 = precios_materiales.get(material, 0.0)
    
    costo_mat_unitario = area_con_merma * costo_cm2
    costo_maq_unitario = tiempo * tarifa_minuto
    costo_prod_unitario = costo_mat_unitario + costo_maq_unitario
    
    precio_unitario_base = costo_prod_unitario / (1 - utilidad_porcentaje)
    descuento_pct = 0.20 if cantidad >= 50 else (0.10 if cantidad >= 12 else 0.00)
    precio_unitario_final = precio_unitario_base * (1 - descuento_pct)
    
    costo_total_lote = costo_prod_unitario * cantidad
    precio_total_neto = precio_unitario_final * cantidad
    utilidad_total_lote = precio_total_neto - costo_total_lote

    st.markdown("---")
    
    res_col1, res_col2, res_col3, res_col4 = st.columns(4)
    res_col1.metric("Costo Producción (1 pz)", f"${costo_prod_unitario:,.2f} MXN")
    res_col2.metric("Precio Base (1 pz)", f"${precio_unitario_base:,.2f} MXN")
    res_col3.metric("Descuento Mayoreo", f"{int(descuento_pct * 100)}%")
    res_col4.metric("PRECIO TOTAL", f"${precio_total_neto:,.2f} MXN", delta=f"{cantidad} pieza(s)")

    with st.expander("🔍 **Ver Desglose Técnico & Estructura de Costos Interfaz**", expanded=False):
        st.markdown("### 📊 Análisis Detallado de Cotización")
        d_col1, d_col2, d_col3 = st.columns(3)
        with d_col1:
            st.markdown(f"""
            <div class='card-tech'>
                <h4>🪵 Materia Prima</h4>
                <div class='tech-row'><span>Área Real:</span> <b>{area_bruta:,.1f} cm²</b></div>
                <div class='tech-row'><span>Área (+10% Merma):</span> <b>{area_con_merma:,.1f} cm²</b></div>
                <div class='tech-row'><span>Costo cm²:</span> <b>${costo_cm2:,.4f} MXN</b></div>
                <hr style='margin: 8px 0;'>
                <div class='tech-row'><span>Subtotal Material (1 pz):</span> <b style='color:#2E7D32;'>${costo_mat_unitario:,.2f} MXN</b></div>
            </div>
            """, unsafe_allow_html=True)

        with d_col2:
            st.markdown(f"""
            <div class='card-tech'>
                <h4>⚡ Operación & Maquinado CNC</h4>
                <div class='tech-row'><span>Tiempo Estimado:</span> <b>{tiempo:,.1f} min</b></div>
                <div class='tech-row'><span>Tarifa Láser:</span> <b>${tarifa_minuto:,.2f} / min</b></div>
                <div class='tech-row'><span>Tiempo Total Lote:</span> <b>{(tiempo * cantidad):,.1f} min</b></div>
                <hr style='margin: 8px 0;'>
                <div class='tech-row'><span>Subtotal Máquina (1 pz):</span> <b style='color:#2E7D32;'>${costo_maq_unitario:,.2f} MXN</b></div>
            </div>
            """, unsafe_allow_html=True)

        with d_col3:
            st.markdown(f"""
            <div class='card-tech'>
                <h4>📈 Márgenes y Rendimiento Lote</h4>
                <div class='tech-row'><span>Margen Utilidad:</span> <b>{int(utilidad_porcentaje * 100)}%</b></div>
                <div class='tech-row'><span>Costo Total Lote:</span> <b>${costo_total_lote:,.2f} MXN</b></div>
                <div class='tech-row'><span>Descuento Aplicado:</span> <b>{int(descuento_pct * 100)}%</b></div>
                <hr style='margin: 8px 0;'>
                <div class='tech-row'><span>Ganancia Neta Estimada:</span> <b style='color:#1565C0;'>${utilidad_total_lote:,.2f} MXN</b></div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_act1, col_act2, col_act3 = st.columns(3)
    with col_act1:
        cliente_txt = nombre_cliente.strip() if nombre_cliente.strip() else "Cliente"
        
        desc_msg = f"🎉 *¡Incluye {int(descuento_pct * 100)}% de descuento por mayoreo!*\n" if descuento_pct > 0 else ""
        foto_msg = f"🖼️ *Vista previa:* {datos_prod['foto']}\n" if datos_prod.get("foto") else ""

        msg_wa = (
            f"Hola *{cliente_txt}* 👋\n\n"
            f"Te comparto la cotización de tu pedido de *Z&A Taller Creativo*:\n"
            f"📌 *Producto:* {producto_sel}\n"
            f"{foto_msg}"
            f"📐 *Medidas:* {largo:,.1f} x {ancho:,.1f} cm\n"
            f"🪵 *Material:* {material}\n"
            f"📦 *Cantidad:* {cantidad} pieza(s)\n"
            f"{desc_msg}"
            f"💵 *Precio Unitario:* ${precio_unitario_final:,.2f} MXN\n"
            f"💰 *TOTAL A COBRAR:* *${precio_total_neto:,.2f} MXN*\n\n"
            f"_Cotización válida por 15 días. ¡Quedo atento a tus comentarios!_"
        )
        tel_clean = "".join(filter(str.isdigit, telefono_cliente))
        wa_url = f"https://wa.me/{tel_clean}?text={urllib.parse.quote(msg_wa)}" if tel_clean else f"https://wa.me/?text={urllib.parse.quote(msg_wa)}"
        st.link_button("📲 Enviar por WhatsApp", wa_url, type="primary", use_container_width=True)

    with col_act2:
        pdf_bytes = generar_pdf_cotizacion({
            "cliente": cliente_txt,
            "telefono": telefono_cliente.strip() if telefono_cliente.strip() else "N/A",
            "producto": producto_sel,
            "material": material,
            "largo": largo,
            "ancho": ancho,
            "cantidad": cantidad,
            "precio_unitario": precio_unitario_final,
            "total": precio_total_neto
        })
        st.download_button(
            label="📄 Descargar PDF Formal",
            data=pdf_bytes,
            file_name=f"Cotizacion_{cliente_txt.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    with col_act3:
        if st.button("💾 Guardar en Historial", use_container_width=True, key="btn_save_cot"):
            data_cot = {
                "cliente": nombre_cliente.strip() if nombre_cliente.strip() else "General",
                "telefono": telefono_cliente.strip(),
                "producto": producto_sel,
                "material": material,
                "cantidad": cantidad,
                "precio_unitario": round(precio_unitario_final, 2),
                "total_cobrado": round(precio_total_neto, 2)
            }
            supabase.table("historial_cotizaciones").insert(data_cot).execute()
            st.toast("¡Cotización guardada exitosamente!", icon="✅")
            st.success("✅ Cotización registrada.")

# ------------------------------------------
# TAB 2: HISTORIAL DE COTIZACIONES
# ------------------------------------------
with tab_historial:
    st.header("📋 Historial de Cotizaciones Guardadas")
    df_historial = cargar_historial()
    
    if not df_historial.empty:
        h_col1, h_col2, h_col3 = st.columns(3)
        h_col1.metric("Total Cotizaciones", len(df_historial))
        h_col2.metric("Monto Total Cotizado", f"${df_historial['Total Cobrado'].sum():,.2f} MXN")
        h_col3.metric("Promedio por Venta", f"${df_historial['Total Cobrado'].mean():,.2f} MXN")
        st.markdown("---")

        df_editado = st.data_editor(
            df_historial,
            use_container_width=True,
            num_rows="dynamic",
            key="editor_historial",
            column_config={
                "id": None,
                "Foto": st.column_config.ImageColumn("Foto", help="Vista previa del producto en catálogo", width="small"),
                "Fecha": st.column_config.TextColumn("Fecha", disabled=True),
                "Precio Unitario": st.column_config.NumberColumn("Precio Unitario", format="$%.2f"),
                "Total Cobrado": st.column_config.NumberColumn("Total Cobrado", format="$%.2f")
            }
        )

        if st.button("💾 Guardar Cambios en Historial", type="primary", key="btn_save_hist"):
            for _, row in df_editado.iterrows():
                if pd.notnull(row["id"]):
                    supabase.table("historial_cotizaciones").update({
                        "cliente": row["Cliente"],
                        "telefono": row["Teléfono"],
                        "cantidad": int(row["Cantidad"]),
                        "precio_unitario": float(row["Precio Unitario"]),
                        "total_cobrado": float(row["Total Cobrado"])
                    }).eq("id", row["id"]).execute()
            st.toast("Historial actualizado correctamente", icon="📝")
            st.success("✅ Historial actualizado.")
            time.sleep(1)
            st.rerun()
    else:
        st.info("💡 Aún no hay cotizaciones guardadas.")

# ------------------------------------------
# TAB 3: PANEL DE ADMINISTRACIÓN
# ------------------------------------------
with tab_admin:
    st.header("⚙️ Panel de Gestión del Taller")
    
    main_admin_tab1, main_admin_tab2 = st.tabs([
        "📦 Gestión de Catálogo de Productos", 
        "🪵 Gestión de Materiales e Insumos"
    ])
    
    # PRODUCTOS
    with main_admin_tab1:
        prod_add_tab, prod_edit_tab, prod_del_tab = st.tabs([
            "➕ Agregar Producto", "✏️ Modificar Producto", "🗑️ Eliminar Producto"
        ])
        
        with prod_add_tab:
            st.markdown("### ➕ Registrar Nuevo Producto en Catálogo")
            with st.form("form_add_prod"):
                n_p = st.text_input("Nombre del Producto:", placeholder="Ej. Llavero Personalizado")
                col_p1, col_p2 = st.columns(2)
                l_p = col_p1.number_input("Largo (cm):", value=10.0, min_value=0.1, step=0.5)
                a_p = col_p2.number_input("Ancho (cm):", value=10.0, min_value=0.1, step=0.5)
                t_p = col_p1.number_input("Tiempo Láser Estimado (min):", value=2.0, min_value=0.1, step=0.5)
                m_p = col_p2.selectbox("Material Predeterminado:", list(precios_materiales.keys()))
                foto_up = st.file_uploader("Imagen del Producto (JPG/PNG):", type=["jpg", "png", "jpeg"])
                
                btn_add = st.form_submit_button("✨ Guardar Producto Nuevo", type="primary", use_container_width=True)
                
                if btn_add:
                    if not n_p.strip():
                        st.error("❌ El nombre del producto no puede estar vacío.")
                    else:
                        foto_url = None
                        if foto_up:
                            file_ext = foto_up.name.split(".")[-1]
                            file_path = f"{n_p.strip().lower().replace(' ', '_')}.{file_ext}"
                            file_bytes = foto_up.getvalue()
                            
                            try:
                                supabase.storage.from_("productos_img").upload(
                                    path=file_path, file=file_bytes, file_options={"content-type": foto_up.type}
                                )
                            except Exception:
                                supabase.storage.from_("productos_img").update(
                                    path=file_path, file=file_bytes, file_options={"content-type": foto_up.type}
                                )
                                
                            foto_url = supabase.storage.from_("productos_img").get_public_url(file_path)

                        supabase.table("catalogo").insert({
                            "nombre": n_p.strip(), "largo": l_p, "ancho": a_p, 
                            "tiempo": t_p, "material": m_p, "foto_url": foto_url
                        }).execute()
                        st.cache_data.clear()
                        st.toast(f"Producto '{n_p}' registrado con éxito", icon="📦")
                        st.success(f"✅ Producto '{n_p}' registrado correctamente.")
                        time.sleep(1.2)
                        st.rerun()

        with prod_edit_tab:
            st.markdown("### ✏️ Editar Parámetros de Producto Existente")
            lista_prods_edit = [p for p in CATALOGO.keys() if p != "Personalizado (Medida Libre)"]
            
            if lista_prods_edit:
                p_edit_sel = st.selectbox("Selecciona el producto a editar:", lista_prods_edit, key="sel_edit_prod")
                dados_edit = CATALOGO[p_edit_sel]
                
                with st.form("form_edit_prod"):
                    col_pe1, col_pe2 = st.columns(2)
                    l_edit = col_pe1.number_input("Nuevo Largo (cm):", value=float(dados_edit["largo"]), min_value=0.1, step=0.5)
                    a_edit = col_pe2.number_input("Nuevo Ancho (cm):", value=float(dados_edit["ancho"]), min_value=0.1, step=0.5)
                    t_edit = col_pe1.number_input("Nuevo Tiempo (min):", value=float(dados_edit["tiempo"]), min_value=0.1, step=0.5)
                    
                    mat_keys = list(precios_materiales.keys())
                    m_idx = mat_keys.index(dados_edit["material"]) if dados_edit["material"] in mat_keys else 0
                    m_edit = col_pe2.selectbox("Nuevo Material Default:", mat_keys, index=m_idx)
                    
                    foto_up_edit = st.file_uploader("Reemplazar Imagen (Opcional):", type=["jpg", "png", "jpeg"], key="up_edit_img")
                    
                    btn_save_edit = st.form_submit_button("💾 Actualizar Producto", type="primary", use_container_width=True)
                    
                    if btn_save_edit:
                        foto_url_final = dados_edit.get("foto")
                        if foto_up_edit:
                            file_ext = foto_up_edit.name.split(".")[-1]
                            file_path = f"{p_edit_sel.strip().lower().replace(' ', '_')}.{file_ext}"
                            file_bytes = foto_up_edit.getvalue()
                            
                            try:
                                supabase.storage.from_("productos_img").upload(
                                    path=file_path, file=file_bytes, file_options={"content-type": foto_up_edit.type}
                                )
                            except Exception:
                                supabase.storage.from_("productos_img").update(
                                    path=file_path, file=file_bytes, file_options={"content-type": foto_up_edit.type}
                                )
                            foto_url_final = supabase.storage.from_("productos_img").get_public_url(file_path)

                        supabase.table("catalogo").update({
                            "largo": l_edit, "ancho": a_edit, 
                            "tiempo": t_edit, "material": m_edit, "foto_url": foto_url_final
                        }).eq("nombre", p_edit_sel).execute()
                        
                        st.cache_data.clear()
                        st.toast(f"Producto '{p_edit_sel}' actualizado correctamente", icon="✏️")
                        st.success(f"✅ Producto '{p_edit_sel}' actualizado.")
                        time.sleep(1.2)
                        st.rerun()
            else:
                st.info("💡 No hay productos en el catálogo para editar.")

        with prod_del_tab:
            st.markdown("### 🗑️ Dar de Baja Producto")
            prods_del = [p for p in CATALOGO.keys() if p != "Personalizado (Medida Libre)"]
            
            if prods_del:
                p_del = st.selectbox("Selecciona producto a eliminar permanentemente:", prods_del, key="sel_del_prod")
                st.warning(f"⚠️ ¿Estás seguro de que deseas eliminar '{p_del}'? Esta acción no se puede deshacer.")
                
                if st.button("❌ Confirmar y Eliminar Producto", type="primary", key="btn_del_prod_confirm"):
                    foto_url = CATALOGO[p_del].get("foto")
                    
                    supabase.table("catalogo").delete().eq("nombre", p_del).execute()
                    
                    if foto_url:
                        try:
                            nombre_archivo = foto_url.split("/")[-1]
                            supabase.storage.from_("productos_img").remove([nombre_archivo])
                        except Exception:
                            pass
                            
                    st.cache_data.clear()
                    st.toast(f"Producto '{p_del}' eliminado del catálogo", icon="🗑️")
                    st.success(f"✅ Producto '{p_del}' e imagen eliminados correctamente.")
                    time.sleep(1.2)
                    st.rerun()
            else:
                st.info("💡 No hay productos en el catálogo para eliminar.")

    # MATERIALES
    with main_admin_tab2:
        mat_add_tab, mat_edit_tab, mat_del_tab = st.tabs([
            "➕ Agregar Material", "✏️ Modificar Material", "🗑️ Eliminar Material"
        ])
        
        with mat_add_tab:
            st.markdown("### ➕ Registrar Nuevo Material / Placa")
            with st.form("form_add_mat"):
                nom_m = st.text_input("Nombre del Material:", placeholder="Ej. MDF 3mm Premium")
                col_m1, col_m2, col_m3 = st.columns(3)
                p_m = col_m1.number_input("Precio Placa Completa ($):", value=120.0, min_value=1.0, step=5.0)
                l_m = col_m2.number_input("Largo Placa (cm):", value=122.0, min_value=1.0, step=1.0)
                a_m = col_m3.number_input("Ancho Placa (cm):", value=244.0, min_value=1.0, step=1.0)
                
                btn_add_m = st.form_submit_button("✨ Guardar Material", type="primary", use_container_width=True)
                
                if btn_add_m:
                    if not nom_m.strip():
                        st.error("❌ El nombre del material no puede estar vacío.")
                    else:
                        c_cm2 = p_m / (l_m * a_m)
                        supabase.table("materiales").insert({"nombre": nom_m.strip(), "costo_cm2": c_cm2}).execute()
                        st.cache_data.clear()
                        st.toast(f"Material '{nom_m}' agregado con costo de ${c_cm2:,.4f}/cm²", icon="🪵")
                        st.success(f"✅ Material '{nom_m}' registrado.")
                        time.sleep(1.2)
                        st.rerun()

        with mat_edit_tab:
            st.markdown("### ✏️ Actualizar Precios de Placa")
            mat_list = list(precios_materiales.keys())
            
            if mat_list:
                mat_edit_sel = st.selectbox("Selecciona material a actualizar:", mat_list, key="sel_edit_mat")
                c_cm2_actual = precios_materiales[mat_edit_sel]
                st.caption(f"Costo por cm² actual: **${c_cm2_actual:,.4f} MXN**")
                
                with st.form("form_edit_mat"):
                    col_me1, col_me2, col_me3 = st.columns(3)
                    p_m_edit = col_me1.number_input("Nuevo Precio Placa ($):", value=150.0, min_value=1.0, step=5.0)
                    l_m_edit = col_me2.number_input("Largo Placa (cm):", value=122.0, min_value=1.0, step=1.0)
                    a_m_edit = col_me3.number_input("Ancho Placa (cm):", value=244.0, min_value=1.0, step=1.0)
                    
                    btn_save_mat_edit = st.form_submit_button("💾 Recalcular y Actualizar Costo", type="primary", use_container_width=True)
                    
                    if btn_save_mat_edit:
                        nuevo_c_cm2 = p_m_edit / (l_m_edit * a_m_edit)
                        supabase.table("materiales").update({"costo_cm2": nuevo_c_cm2}).eq("nombre", mat_edit_sel).execute()
                        st.cache_data.clear()
                        st.toast(f"Material '{mat_edit_sel}' actualizado a ${nuevo_c_cm2:,.4f}/cm²", icon="✏️")
                        st.success(f"✅ Material '{mat_edit_sel}' actualizado.")
                        time.sleep(1.2)
                        st.rerun()
            else:
                st.info("💡 No hay materiales registrados.")

        with mat_del_tab:
            st.markdown("### 🗑️ Eliminar Material del Sistema")
            mat_list_del = list(precios_materiales.keys())
            
            if mat_list_del:
                mat_del = st.selectbox("Selecciona material a eliminar:", mat_list_del, key="sel_del_mat")
                st.warning(f"⚠️ ¿Eliminar '{mat_del}'? Los productos que usen este material deberán ser reasignados.")
                
                if st.button("❌ Confirmar y Eliminar Material", type="primary", key="btn_del_mat_confirm"):
                    supabase.table("materiales").delete().eq("nombre", mat_del).execute()
                    st.cache_data.clear()
                    st.toast(f"Material '{mat_del}' eliminado del sistema", icon="🗑️")
                    st.success(f"✅ Material '{mat_del}' eliminado.")
                    time.sleep(1.2)
                    st.rerun()
            else:
                st.info("💡 No hay materiales registrados para eliminar.")
