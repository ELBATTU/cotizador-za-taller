import streamlit as st
import pandas as pd
import datetime
import urllib.parse
import time
import io
import os
from zoneinfo import ZoneInfo
from PIL import Image as PILImage
from supabase import create_client, Client
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Desactivar límite de píxeles para imágenes grandes
PILImage.MAX_IMAGE_PIXELS = None

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
# FUNCIÓN DE COMPRESIÓN DE IMÁGENES
# ==========================================
def optimizar_imagen(uploaded_file, max_ancho=1200, calidad=85):
    img = PILImage.open(uploaded_file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")
        
    if img.width > max_ancho or img.height > max_ancho:
        img.thumbnail((max_ancho, max_ancho), PILImage.Resampling.LANCZOS)
        
    buffer = io.BytesIO()
    img.save(buffer, format="WEBP", quality=calidad, optimize=True)
    buffer.seek(0)
    return buffer.getvalue()

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
        
        dt_utc = pd.to_datetime(df["fecha"])
        if dt_utc.dt.tz is None:
            dt_mexico = dt_utc.dt.tz_localize("UTC").dt.tz_convert(ZoneInfo("America/Mexico_City"))
        else:
            dt_mexico = dt_utc.dt.tz_convert(ZoneInfo("America/Mexico_City"))
            
        df["fecha_captura"] = dt_mexico.dt.strftime("%Y-%m-%d %H:%M")
        
        if "fecha_cotizacion" in df.columns:
            df["fecha_cotizacion"] = df["fecha_cotizacion"].fillna(df["fecha"])
        else:
            df["fecha_cotizacion"] = df["fecha"]
            
        df["dt_cotizacion"] = pd.to_datetime(df["fecha_cotizacion"], errors="coerce")
        df["dt_cotizacion"] = df["dt_cotizacion"].fillna(pd.to_datetime(df["fecha"]))
        
        df["Fecha Cotización"] = df["dt_cotizacion"].dt.date
            
        cat_dict = cargar_catalogo()
        df["foto_url"] = df["producto"].map(lambda p: cat_dict.get(p, {}).get("foto"))
        
        # Soportar campos retrocompatibles si no existían en registros viejos
        if "precio_lista_total" not in df.columns:
            df["precio_lista_total"] = df["total_cobrado"]
        if "monto_descuento" not in df.columns:
            df["monto_descuento"] = 0.0
        if "pct_descuento" not in df.columns:
            df["pct_descuento"] = 0.0

        df.rename(columns={
            "fecha_captura": "Fecha Captura", "cliente": "Cliente", "telefono": "Teléfono",
            "producto": "Producto", "material": "Material", "cantidad": "Cantidad",
            "precio_unitario": "Precio Unitario", "total_cobrado": "Total Cobrado",
            "precio_lista_total": "Precio Lista Total", "monto_descuento": "Descuento ($)",
            "pct_descuento": "Descuento (%)", "foto_url": "Foto"
        }, inplace=True)
        
        return df[["id", "Foto", "Fecha Cotización", "Fecha Captura", "Cliente", "Teléfono", "Producto", "Material", "Cantidad", "Precio Unitario", "Precio Lista Total", "Descuento ($)", "Descuento (%)", "Total Cobrado", "dt_cotizacion"]]
    return pd.DataFrame()

precios_materiales = cargar_materiales()
CATALOGO = cargar_catalogo()

# ==========================================
# GENERADOR DE PDF PROFESIONAL MULTIPARTIDA
# ==========================================
def generar_pdf_cotizacion(datos_cliente, partidas):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()

    COLOR_PRINCIPAL = colors.HexColor('#5C3A21')  
    COLOR_SECUNDARIO = colors.HexColor('#8C5830') 
    COLOR_FONDO = colors.HexColor('#F4EAD5')      
    COLOR_TEXTO = colors.HexColor('#2B1A0E')      

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, textColor=COLOR_PRINCIPAL)
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=COLOR_SECUNDARIO)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=COLOR_TEXTO)
    bold_style = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=COLOR_TEXTO)

    logo_widget = None
    for filename in ["logo.png", "logo.jpg", "logo.jpeg"]:
        if os.path.exists(filename):
            try:
                with PILImage.open(filename) as im:
                    orig_w, orig_h = im.size
                target_w = 75  
                target_h = target_w * (orig_h / orig_w)  
                logo_widget = RLImage(filename, width=target_w, height=target_h)
                logo_widget.hAlign = 'LEFT'
            except Exception:
                pass
            break

    if logo_widget:
        header_col1 = [logo_widget, Spacer(1, 4), Paragraph("<b>Z&A TALLER CREATIVO</b><br/>Corte & Grabado Láser CNC<br/>MDF & CNC | Taller Creativo", subtitle_style)]
    else:
        header_col1 = [Paragraph("<b>Z&A TALLER CREATIVO</b><br/>Corte & Grabado Láser CNC", title_style)]

    header_data = [
        [
            header_col1,
            Paragraph(f"<b>COTIZACIÓN DE VENTA</b><br/><b>Fecha:</b> {datetime.datetime.now(ZoneInfo('America/Mexico_City')).strftime('%d/%m/%Y')}<br/><b>Vigencia:</b> 15 días", subtitle_style)
        ]
    ]
    
    header_table = Table(header_data, colWidths=[330, 210])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(header_table)
    elements.append(Spacer(1, 15))

    cliente_info = [
        [Paragraph(f"<b>Cliente:</b> {datos_cliente['cliente']}", body_style), Paragraph(f"<b>Teléfono:</b> {datos_cliente['telefono']}", body_style)]
    ]
    info_table = Table(cliente_info, colWidths=[300, 240])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_FONDO),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_SECUNDARIO)
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 15))

    table_data = [["Producto", "Material", "Dimensiones", "Cant.", "P. Unitario", "Subtotal"]]
    gran_total = 0.0

    for item in partidas:
        subtotal = item['total']
        gran_total += subtotal
        table_data.append([
            Paragraph(str(item['producto']), body_style),
            Paragraph(str(item['material']), body_style),
            f"{item['largo']:.1f}x{item['ancho']:.1f}cm",
            str(item['cantidad']),
            f"${item['precio_unitario']:,.2f}",
            f"${subtotal:,.2f}"
        ])

    prod_table = Table(table_data, colWidths=[130, 90, 90, 45, 90, 95])
    prod_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRINCIPAL),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_SECUNDARIO),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(prod_table)
    elements.append(Spacer(1, 15))

    total_data = [
        ["", Paragraph(f"<b>GRAN TOTAL:</b> <font color='#5C3A21' size='12'><b>${gran_total:,.2f} MXN</b></font>", bold_style)]
    ]
    total_table = Table(total_data, colWidths=[300, 240])
    total_table.setStyle(TableStyle([('ALIGN', (1,0), (1,0), 'RIGHT')]))
    elements.append(total_table)
    elements.append(Spacer(1, 25))

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
# TAB 1: COTIZADOR INTERACTIVO CON CARRITO
# ------------------------------------------
with tab_cotizador:
    if "carrito_cotizacion" not in st.session_state:
        st.session_state["carrito_cotizacion"] = []
    if "input_cliente" not in st.session_state:
        st.session_state["input_cliente"] = ""
    if "input_telefono" not in st.session_state:
        st.session_state["input_telefono"] = ""
    if "select_producto" not in st.session_state:
        st.session_state["select_producto"] = "Personalizado (Medida Libre)"

    title_col1, title_col2 = st.columns([3, 1])
    with title_col1:
        st.markdown("<h1 style='color: #1E88E5; margin-bottom: 0;'>Z&A Taller Creativo</h1>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 18px; color: #888;'>Cotizador Interactivo con Carrito - Corte & Grabado Láser CNC</p>", unsafe_allow_html=True)
    with title_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Nueva Cotización", use_container_width=True, type="secondary"):
            st.session_state["input_cliente"] = ""
            st.session_state["input_telefono"] = ""
            st.session_state["input_cantidad"] = 1
            st.session_state["select_producto"] = "Personalizado (Medida Libre)"
            st.session_state["carrito_cotizacion"] = []
            st.rerun()

    st.markdown("---")

    col_cat, col_inputs = st.columns([1, 1.2])

    with col_cat:
        st.subheader("🖼️ Producto & Datos Cliente")
        nombre_cliente = st.text_input("Nombre del Cliente:", placeholder="Ej. Juan Pérez", key="input_cliente")
        telefono_cliente = st.text_input("Teléfono WhatsApp (opcional):", placeholder="Ej. 4421234567", key="input_telefono")

        lista_productos = list(CATALOGO.keys())
        if "Personalizado (Medida Libre)" in lista_productos:
            lista_productos.remove("Personalizado (Medida Libre)")
            lista_productos.insert(0, "Personalizado (Medida Libre)")

        try:
            default_idx = lista_productos.index(st.session_state["select_producto"])
        except ValueError:
            default_idx = 0

        producto_sel = st.selectbox("Elige un producto del catálogo (puedes escribir para buscar):", lista_productos, index=default_idx, key="select_producto")        
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
        
        if "input_cantidad" not in st.session_state:
            st.session_state["input_cantidad"] = 1
            
        cantidad = col_c.number_input("Cantidad Pedida (piezas):", min_value=1, step=1, key="input_cantidad")

        st.markdown("<br>", unsafe_allow_html=True)

        # CÁLCULOS TÉCNICOS BASE
        area_bruta_tmp = largo * ancho
        area_con_merma_tmp = area_bruta_tmp * desperdicio_factor
        costo_cm2_tmp = precios_materiales.get(material, 0.0)
        costo_prod_unitario_tmp = (area_con_merma_tmp * costo_cm2_tmp) + (tiempo * tarifa_minuto)
        precio_unitario_base_tmp = costo_prod_unitario_tmp / (1 - utilidad_porcentaje)
        
        # Precio lista formal sin ningún descuento (total del lote)
        precio_lista_lote = precio_unitario_base_tmp * cantidad

        # SECCIÓN DE AJUSTE MANUAL DE PRECIO POR PATRONES
        usar_precio_manual = st.checkbox("🏷️ Aplicar precio especial / manual (Patrones)")
        
        descuento_pct_mayoreo = 0.20 if cantidad >= 50 else (0.10 if cantidad >= 12 else 0.00)
        precio_unitario_sugerido = precio_unitario_base_tmp * (1 - descuento_pct_mayoreo)
        precio_total_sugerido = precio_unitario_sugerido * cantidad

        if usar_precio_manual:
            precio_total_neto_tmp = st.number_input(
                "Total acordado ($ MXN):", 
                value=round(precio_total_sugerido, 2), 
                min_value=0.0, 
                step=10.0,
                help="Ingresa el precio final aleatorio o especial que dicten los patrones para este lote."
            )
            precio_unitario_final_tmp = precio_total_neto_tmp / cantidad if cantidad > 0 else 0.0
        else:
            precio_unitario_final_tmp = precio_unitario_sugerido
            precio_total_neto_tmp = precio_total_sugerido

        # Cálculo exacto de descuentos para auditoría interna
        monto_descuento_tmp = max(0.0, precio_lista_lote - precio_total_neto_tmp)
        pct_descuento_real_tmp = (monto_descuento_tmp / precio_lista_lote * 100) if precio_lista_lote > 0 else 0.0

        # BOTÓN PARA AGREGAR AL CARRITO
        if st.button("➕ Agregar este producto a la Cotización", type="primary", use_container_width=True):
            nueva_partida = {
                "producto": producto_sel,
                "material": material,
                "largo": largo,
                "ancho": ancho,
                "cantidad": cantidad,
                "precio_unitario": round(precio_unitario_final_tmp, 2),
                "precio_lista_total": round(precio_lista_lote, 2),
                "monto_descuento": round(monto_descuento_tmp, 2),
                "pct_descuento": round(pct_descuento_real_tmp, 1),
                "total": round(precio_total_neto_tmp, 2)
            }
            st.session_state["carrito_cotizacion"].append(nueva_partida)
            st.toast("¡Partida agregada con éxito!", icon="🛒")
            st.rerun()

    # Cálculos para la tarjeta métrica del producto actual seleccionado
    area_bruta = largo * ancho
    area_con_merma = area_bruta * desperdicio_factor
    costo_cm2 = precios_materiales.get(material, 0.0)
    costo_mat_unitario = area_con_merma * costo_cm2
    costo_maq_unitario = tiempo * tarifa_minuto
    costo_prod_unitario = costo_mat_unitario + costo_maq_unitario
    precio_unitario_base = costo_prod_unitario / (1 - utilidad_porcentaje)
    
    precio_lista_lote_vista = precio_unitario_base * cantidad
    precio_total_neto_vista = precio_total_neto_tmp
    utilidad_total_lote_vista = precio_total_neto_vista - (costo_prod_unitario * cantidad)

    st.markdown("---")
    
    res_col1, res_col2, res_col3, res_col4 = st.columns(4)
    res_col1.metric("Costo Producción (1 pz)", f"${costo_prod_unitario:,.2f} MXN")
    res_col2.metric("Precio Lista Lote (Sin Desc.)", f"${precio_lista_lote_vista:,.2f} MXN")
    res_col3.metric("Descuento Real Aplicado", f"{pct_descuento_real_tmp:.1f}%", delta=f"-${monto_descuento_tmp:,.2f}")
    res_col4.metric("SUBTOTAL A COBRAR", f"${precio_total_neto_vista:,.2f} MXN", delta=f"{cantidad} pieza(s)")

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
                <div class='tech-row'><span>Margen Utilidad Base:</span> <b>{int(utilidad_porcentaje * 100)}%</b></div>
                <div class='tech-row'><span>Costo Total Lote:</span> <b>${(costo_prod_unitario * cantidad):,.2f} MXN</b></div>
                <div class='tech-row'><span>Descuento Otorgado:</span> <b>${monto_descuento_tmp:,.2f} MXN</b></div>
                <hr style='margin: 8px 0;'>
                <div class='tech-row'><span>Ganancia Neta Estimada:</span> <b style='color:#1565C0;'>${utilidad_total_lote_vista:,.2f} MXN</b></div>
            </div>
            """, unsafe_allow_html=True)

    # MOSTRAR CARRITO Y GESTIÓN DE ELIMINACIÓN INDIVIDUAL
    if st.session_state["carrito_cotizacion"]:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 🛒 Partidas Agregadas en esta Cotización")
        
        df_carrito = pd.DataFrame(st.session_state["carrito_cotizacion"])
        df_carrito.index = df_carrito.index + 1
        
        # Mostrar desglose claro con Lista, Descuento y Total en el Carrito
        df_carrito_view = df_carrito[["producto", "material", "largo", "ancho", "cantidad", "precio_unitario", "precio_lista_total", "monto_descuento", "total"]].copy()
        df_carrito_view.rename(columns={
            "precio_lista_total": "Precio Lista Total",
            "monto_descuento": "Descuento ($)",
            "total": "Total Cobrado"
        }, inplace=True)
        
        st.dataframe(df_carrito_view, use_container_width=True)
        
        del_col1, del_col2 = st.columns([3, 1])
        with del_col1:
            opciones_del = [f"Item {idx}: {p['producto']} ({p['cantidad']} pz - ${p['total']:.2f})" for idx, p in enumerate(st.session_state["carrito_cotizacion"], 1)]
            item_a_eliminar = st.selectbox("Selecciona un producto específico para quitar del carrito:", opciones_del, key="sel_del_cart_item")
        with del_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("❌ Quitar de la Cotización", type="secondary", use_container_width=True):
                idx_del = opciones_del.index(item_a_eliminar)
                prod_removido = st.session_state["carrito_cotizacion"].pop(idx_del)
                st.toast(f"Producto '{prod_removido['producto']}' eliminado del carrito.", icon="🗑️")
                st.rerun()

        st.markdown("---")
        gran_total_carrito = df_carrito["total"].sum()
        gran_lista_carrito = df_carrito["precio_lista_total"].sum()
        gran_desc_carrito = df_carrito["monto_descuento"].sum()
        
st.markdown(f"### 💰 **GRAN TOTAL A COBRAR: ${gran_total_carrito:,.2f} MXN** *(Precio Lista original: ${gran_lista_carrito:,.2f} | Ahorro/Descuento: ${gran_desc_carrito:,.2f})*")
        c_btn1, c_btn2, c_btn3, c_btn4 = st.columns(4)
        
        with c_btn1:
            if st.button("🗑️ Vaciar Carrito Completo", use_container_width=True):
                st.session_state["carrito_cotizacion"] = []
                st.rerun()

        with c_btn2:
            cliente_txt = nombre_cliente.strip() if nombre_cliente.strip() else "Cliente"
            msg_wa = f"Hola *{cliente_txt}* 👋\n\nTe comparto el presupuesto de tu pedido en *Z&A Taller Creativo*:\n\n"
            for idx, p in enumerate(st.session_state["carrito_cotizacion"], 1):
                msg_wa += f"*{idx}. {p['producto']}*\n"
                msg_wa += f"   📐 Medidas: {p['largo']:.1f} x {p['ancho']:.1f} cm\n"
                msg_wa += f"   🪵 Material: {p['material']}\n"
                msg_wa += f"   📦 Cantidad: {p['cantidad']} pz(s)\n"
                msg_wa += f"   💵 Subtotal: ${p['total']:,.2f} MXN\n\n"
            
            msg_wa += f"💰 *GRAN TOTAL A PAGAR:* *${gran_total_carrito:,.2f} MXN*\n\n_Cotización válida por 15 días. ¡Quedo atento a tus comentarios!_"
            
            tel_clean = "".join(filter(str.isdigit, telefono_cliente))
            wa_url = f"https://wa.me/{tel_clean}?text={urllib.parse.quote(msg_wa)}" if tel_clean else f"https://wa.me/?text={urllib.parse.quote(msg_wa)}"
            st.link_button("📲 Enviar por WhatsApp", wa_url, type="primary", use_container_width=True)

        with c_btn3:
            pdf_bytes = generar_pdf_cotizacion(
                {"cliente": cliente_txt, "telefono": telefono_cliente.strip() if telefono_cliente.strip() else "N/A"},
                st.session_state["carrito_cotizacion"]
            )
            st.download_button(
                label="📄 Descargar PDF Formal",
                data=pdf_bytes,
                file_name=f"Cotizacion_{cliente_txt.replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        with c_btn4:
            if st.button("💾 Guardar en Historial", type="primary", use_container_width=True, key="btn_save_cart"):
                f_ahora = datetime.datetime.now(ZoneInfo("America/Mexico_City")).strftime("%Y-%m-%d")
                for p in st.session_state["carrito_cotizacion"]:
                    data_cot = {
                        "cliente": cliente_txt,
                        "telefono": telefono_cliente.strip(),
                        "producto": p["producto"],
                        "material": p["material"],
                        "cantidad": p["cantidad"],
                        "precio_unitario": p["precio_unitario"],
                        "precio_lista_total": p["precio_lista_total"],
                        "monto_descuento": p["monto_descuento"],
                        "pct_descuento": p["pct_descuento"],
                        "total_cobrado": p["total"],
                        "fecha_cotizacion": f_ahora
                    }
                    supabase.table("historial_cotizaciones").insert(data_cot).execute()
                
                st.cache_data.clear()
                st.toast("¡Cotización múltiple guardada en el historial con éxito!", icon="✅")
                st.success("✅ Cotizaciones registradas.")
                st.session_state["carrito_cotizacion"] = []
                time.sleep(1)
                st.rerun()

# ------------------------------------------
# TAB 2: HISTORIAL DE COTIZACIONES
# ------------------------------------------
with tab_historial:
    st.header("📋 Historial de Cotizaciones Registradas")
    df_hist = cargar_historial()
    
    if not df_hist.empty:
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

        h_col1, h_col2, h_col3, h_col4 = st.columns(4)
        h_col1.metric("Cotizaciones en Periodo", len(df_filtrado))
        h_col2.metric("Monto Total Cobrado", f"${df_filtrado['Total Cobrado'].sum():,.2f} MXN")
        h_col3.metric("Total Descontado / Rebajas", f"${df_filtrado['Descuento ($)'].sum():,.2f} MXN")
        promedio_venta = df_filtrado['Total Cobrado'].mean() if len(df_filtrado) > 0 else 0.0
        h_col4.metric("Promedio por Venta", f"${promedio_venta:,.2f} MXN")

        df_exportar = df_filtrado[["Fecha Cotización", "Fecha Captura", "Cliente", "Teléfono", "Producto", "Material", "Cantidad", "Precio Unitario", "Precio Lista Total", "Descuento ($)", "Descuento (%)", "Total Cobrado"]].copy()
        df_exportar["Fecha Cotización"] = df_exportar["Fecha Cotización"].astype(str)
        csv_bytes = df_exportar.to_csv(index=False).encode('utf-8-sig')

        st.download_button(
            label=f"📥 Descargar Reporte Filtrado ({len(df_filtrado)} registros)",
            data=csv_bytes,
            file_name=f"Reporte_Cotizaciones_{filtro_tipo.replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        st.markdown("---")
        st.markdown("### ✏️ Edición Controlada")
        st.info("💡 Campos editables permitidos: **Nombre del Cliente**, **Teléfono** y **Fecha Cotización** (haz doble clic en la fecha para abrir el calendario interactivo). No se permiten fechas futuras.")

        df_editable = df_filtrado[["id", "Foto", "Fecha Cotización", "Fecha Captura", "Cliente", "Teléfono", "Producto", "Material", "Cantidad", "Precio Unitario", "Precio Lista Total", "Descuento ($)", "Descuento (%)", "Total Cobrado"]].copy()

        df_editado = st.data_editor(
            df_editable,
            use_container_width=True,
            hide_index=True,
            key="editor_historial_controlado",
            column_config={
                "id": None,
                "Foto": st.column_config.ImageColumn("Foto", help="Vista previa", width="small"),
                "Fecha Cotización": st.column_config.DateColumn("Fecha Cotización", format="YYYY-MM-DD", help="Selecciona una fecha del calendario"),
                "Fecha Captura": st.column_config.TextColumn("Fecha Captura (Sistema)", disabled=True),
                "Cliente": st.column_config.TextColumn("Cliente (Editable)"),
                "Teléfono": st.column_config.TextColumn("Teléfono (Editable)"),
                "Producto": st.column_config.TextColumn("Producto", disabled=True),
                "Material": st.column_config.TextColumn("Material", disabled=True),
                "Cantidad": st.column_config.NumberColumn("Cantidad", format="%d", disabled=True),
                "Precio Unitario": st.column_config.NumberColumn("Precio Unitario", format="$%.2f", disabled=True),
                "Precio Lista Total": st.column_config.NumberColumn("Precio Lista", format="$%.2f", disabled=True),
                "Descuento ($)": st.column_config.NumberColumn("Desc. ($)", format="$%.2f", disabled=True),
                "Descuento (%)": st.column_config.NumberColumn("Desc. (%)", format="%.1f%%", disabled=True),
                "Total Cobrado": st.column_config.NumberColumn("Total Cobrado", format="$%.2f", disabled=True)
            }
        )

        cambios_detectados = False
        for idx, row in df_editado.iterrows():
            orig = df_editable.loc[df_editable["id"] == row["id"]].iloc[0]
            
            f_edit_str = str(row["Fecha Cotización"]) if pd.notnull(row["Fecha Cotización"]) else ""
            f_orig_str = str(orig["Fecha Cotización"]) if pd.notnull(orig["Fecha Cotización"]) else ""

            if (str(row["Cliente"]) != str(orig["Cliente"]) or
                str(row["Teléfono"]) != str(orig["Teléfono"]) or
                f_edit_str != f_orig_str):
                cambios_detectados = True
                break

        if cambios_detectados:
            btn_guardar = st.button("💾 Guardar Cambios en Historial", type="primary", key="btn_save_hist")
        else:
            st.button("💾 Guardar Cambios en Historial (Sin cambios)", disabled=True, key="btn_save_hist_disabled")
            btn_guardar = False

        if btn_guardar:
            error_fecha_futura = False
            hoy = datetime.date.today()
            
            for _, row in df_editado.iterrows():
                if pd.notnull(row["Fecha Cotización"]):
                    f_cot = row["Fecha Cotización"]
                    if isinstance(f_cot, str):
                        f_cot = datetime.datetime.strptime(f_cot, "%Y-%m-%d").date()
                        
                    if f_cot > hoy:
                        error_fecha_futura = True
                        st.error(f"❌ No puedes asignar una fecha futura ({f_cot}) en la cotización de '{row['Cliente']}'. La fecha máxima permitida es hoy ({hoy}).")
                        break

            if not error_fecha_futura:
                for _, row in df_editado.iterrows():
                    if pd.notnull(row["id"]):
                        f_val = str(row["Fecha Cotización"]) if pd.notnull(row["Fecha Cotización"]) else datetime.date.today().isoformat()
                        supabase.table("historial_cotizaciones").update({
                            "cliente": row["Cliente"],
                            "telefono": row["Teléfono"],
                            "fecha_cotizacion": f_val
                        }).eq("id", int(row["id"])).execute()
                
                st.cache_data.clear()
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
                        nombre_formateado = n_p.strip().upper()
                        nombres_existentes = [p.upper() for p in CATALOGO.keys()]
                        
                        if nombre_formateado in nombres_existentes:
                            st.error(f"❌ El producto '{nombre_formateado}' ya existe en el catálogo. No se permiten nombres duplicados.")
                        else:
                            foto_url = None
                            if foto_up:
                                file_bytes = optimizar_imagen(foto_up)
                                file_path = f"{nombre_formateado.lower().replace(' ', '_')}.webp"
                                
                                try:
                                    supabase.storage.from_("productos_img").upload(
                                        path=file_path, file=file_bytes, file_options={"content-type": "image/webp"}
                                    )
                                except Exception:
                                    supabase.storage.from_("productos_img").update(
                                        path=file_path, file=file_bytes, file_options={"content-type": "image/webp"}
                                    )
                                    
                                foto_url = supabase.storage.from_("productos_img").get_public_url(file_path)

                            supabase.table("catalogo").insert({
                                "nombre": nombre_formateado, "largo": l_p, "ancho": a_p, 
                                "tiempo": t_p, "material": m_p, "foto_url": foto_url
                            }).execute()
                            st.cache_data.clear()
                            st.toast(f"Producto '{nombre_formateado}' registrado con éxito", icon="📦")
                            st.success(f"✅ Producto '{nombre_formateado}' registrado correctamente.")
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
                            file_bytes = optimizar_imagen(foto_up_edit)
                            file_path = f"{p_edit_sel.strip().lower().replace(' ', '_')}.webp"
                            
                            try:
                                supabase.storage.from_("productos_img").upload(
                                    path=file_path, file=file_bytes, file_options={"content-type": "image/webp"}
                                )
                            except Exception:
                                supabase.storage.from_("productos_img").update(
                                    path=file_path, file=file_bytes, file_options={"content-type": "image/webp"}
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
                p_
