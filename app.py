Ese error ocurre porque se pegó la palabra `import streamlit as st` justo al lado de `st.rerun()` en la última línea del archivo, quedando `st.rerun()import streamlit as st`.

Aquí tienes el código completo de `app.py` corregido y limpio para reemplazar todo tu archivo:

```python
import streamlit as st
import pandas as pd
import datetime
import urllib.parse
from PIL import Image
from supabase import create_client, Client

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
# FUNCIONES DE BASE DE DATOS
# ==========================================
def cargar_materiales():
    res = supabase.table("materiales").select("*").execute()
    return {item["nombre"]: float(item["costo_cm2"]) for item in res.data}

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
        df.rename(columns={
            "fecha": "Fecha", "cliente": "Cliente", "telefono": "Teléfono",
            "producto": "Producto", "material": "Material", "cantidad": "Cantidad",
            "precio_unitario": "Precio Unitario", "total_cobrado": "Total Cobrado"
        }, inplace=True)
        return df[["id", "Fecha", "Cliente", "Teléfono", "Producto", "Material", "Cantidad", "Precio Unitario", "Total Cobrado"]]
    return pd.DataFrame()

# Carga inicial
precios_materiales = cargar_materiales()
CATALOGO = cargar_catalogo()

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
            
            if st.button("Ingresar", type="primary", use_container_width=True, key="btn_login_main"):
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

    # CÁLCULO DE COSTOS
    area_pieza = largo * ancho
    area_con_merma = area_pieza * desperdicio_factor
    costo_mat_unitario = area_con_merma * precios_materiales[material]
    costo_maq_unitario = tiempo * tarifa_minuto
    costo_prod_unitario = costo_mat_unitario + costo_maq_unitario
    precio_unitario_base = costo_prod_unitario / (1 - utilidad_porcentaje)

    descuento_pct = 0.20 if cantidad >= 50 else (0.10 if cantidad >= 12 else 0.00)
    precio_unitario_final = precio_unitario_base * (1 - descuento_pct)
    precio_total_neto = precio_unitario_final * cantidad

    st.markdown("---")
    res_col1, res_col2, res_col3, res_col4 = st.columns(4)
    res_col1.metric("Costo Producción (1 pz)", f"${costo_prod_unitario:.2f} MXN")
    res_col2.metric("Precio Base (1 pz)", f"${precio_unitario_base:.2f} MXN")
    res_col3.metric("Descuento Mayoreo", f"{int(descuento_pct * 100)}%")
    res_col4.metric("PRECIO TOTAL", f"${precio_total_neto:.2f} MXN", delta=f"{cantidad} pieza(s)")

    # DESGLOSE TÉCNICO INTERNO
    with st.expander("📊 Ver Desglose Técnico de Costos y Márgenes"):
        d_col1, d_col2 = st.columns(2)
        
        with d_col1:
            st.markdown("**Cálculo de Material y Áreas:**")
            st.write(f"• **Área nominal por pieza:** {area_pieza:.1f} cm²")
            st.write(f"• **Área con merma (10%):** {area_con_merma:.1f} cm²")
            st.write(f"• **Costo por cm² ({material}):** ${precios_materiales[material]:.4f} MXN")
            st.write(f"• **Costo total de material (1 pz):** ${costo_mat_unitario:.2f} MXN")
            
        with d_col2:
            st.markdown("**Cálculo de Maquinado y Márgenes:**")
            st.write(f"• **Costo de tiempo máquina (1 pz):** ${costo_maq_unitario:.2f} MXN ({tiempo} min @ ${tarifa_minuto}/min)")
            st.write(f"• **Utilidad estimada (1 pz):** ${precio_unitario_base - costo_prod_unitario:.2f} MXN ({int(utilidad_porcentaje * 100)}%)")
            st.write(f"• **Precio unitario final con descuento:** ${precio_unitario_final:.2f} MXN")
            st.write(f"• **Costo producción total del lote ({cantidad} pz):** ${costo_prod_unitario * cantidad:.2f} MXN")

    st.markdown("---")
    col_act1, col_act2 = st.columns(2)
    with col_act1:
        cliente_txt = nombre_cliente.strip() if nombre_cliente.strip() else "Cliente"
        msg_wa = (
            f"Hola *{cliente_txt}* 👋\n\n"
            f"Te comparto la cotización de tu pedido de *Z&A Taller Creativo*:\n"
            f"📌 *Producto:* {producto_sel}\n"
            f"📐 *Medidas:* {largo:.1f} x {ancho:.1f} cm\n"
            f"🪵 *Material:* {material}\n"
            f"📦 *Cantidad:* {cantidad} pieza(s)\n"
            f"💵 *Precio Unitario:* ${precio_unitario_final:.2f} MXN\n"
            f"💰 *TOTAL A COBRAR:* *${precio_total_neto:.2f} MXN*\n\n"
            f"_Cotización válida por 15 días. ¡Quedo atento a tus comentarios!_"
        )
        tel_clean = "".join(filter(str.isdigit, telefono_cliente))
        wa_url = f"https://wa.me/{tel_clean}?text={urllib.parse.quote(msg_wa)}" if tel_clean else f"https://wa.me/?text={urllib.parse.quote(msg_wa)}"
        st.link_button("📲 Enviar Cotización por WhatsApp", wa_url, type="primary")

    with col_act2:
        if st.button("💾 Guardar Cotización en Historial", key="btn_guardar_cotizacion"):
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
            st.success("✅ ¡Cotización guardada en Supabase!")

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
                "Fecha": st.column_config.TextColumn("Fecha", disabled=True)
            }
        )

        if st.button("💾 Guardar Cambios en Historial", type="primary", key="btn_guardar_historial"):
            for _, row in df_editado.iterrows():
                if pd.notnull(row["id"]):
                    supabase.table("historial_cotizaciones").update({
                        "cliente": row["Cliente"],
                        "telefono": row["Teléfono"],
                        "cantidad": int(row["Cantidad"]),
                        "precio_unitario": float(row["Precio Unitario"]),
                        "total_cobrado": float(row["Total Cobrado"])
                    }).eq("id", row["id"]).execute()
            st.success("✅ Historial actualizado.")
            st.rerun()
    else:
        st.info("💡 Aún no hay cotizaciones guardadas.")

# ------------------------------------------
# TAB 3: ADMINISTRACIÓN
# ------------------------------------------
with tab_admin:
    st.header("⚙️ Panel de Administración")
    subtab_mat, subtab_prod_add, subtab_prod_del = st.tabs([
        "🪵 Administrar Materiales", "➕ Agregar Producto", "🗑️ Eliminar Producto"
    ])
    
    # MATERIALES
    with subtab_mat:
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown("#### ➕ Agregar Material")
            nom_m = st.text_input("Nombre Material:")
            p_m = st.number_input("Precio Placa ($):", value=120.0)
            l_m = st.number_input("Largo (cm):", value=122.0)
            a_m = st.number_input("Ancho (cm):", value=244.0)
            if st.button("Guardar Material", key="btn_add_mat"):
                c_cm2 = p_m / (l_m * a_m)
                supabase.table("materiales").insert({"nombre": nom_m.strip(), "costo_cm2": c_cm2}).execute()
                st.success("Material agregado")
                st.rerun()

        with col_m2:
            st.markdown("#### 🗑️ Eliminar Material")
            mat_del = st.selectbox("Selecciona material:", list(precios_materiales.keys()))
            if st.button("Eliminar Material", key="btn_del_mat"):
                supabase.table("materiales").delete().eq("nombre", mat_del).execute()
                st.success("Material eliminado")
                st.rerun()

    # AGREGAR PRODUCTO
    with subtab_prod_add:
        st.subheader("➕ Agregar Nuevo Producto")
        n_p = st.text_input("Nombre Producto:")
        col_pa, col_pb = st.columns(2)
        l_p = col_pa.number_input("Largo (cm):", value=10.0)
        a_p = col_pb.number_input("Ancho (cm):", value=10.0)
        t_p = col_pa.number_input("Tiempo (min):", value=2.0)
        m_p = col_pb.selectbox("Material default:", list(precios_materiales.keys()))
        foto_up = st.file_uploader("Imagen:", type=["jpg", "png", "jpeg"])

        if st.button("Guardar Producto Nuevo", key="btn_add_prod"):
            foto_url = None
            if foto_up:
                file_ext = foto_up.name.split(".")[-1]
                file_path = f"{n_p.strip().lower().replace(' ', '_')}.{file_ext}"
                file_bytes = foto_up.getvalue()
                
                supabase.storage.from_("productos_img").upload(file_path, file_bytes, {"content-type": foto_up.type})
                foto_url = supabase.storage.from_("productos_img").get_public_url(file_path)

            supabase.table("catalogo").insert({
                "nombre": n_p.strip(), "largo": l_p, "ancho": a_p, 
                "tiempo": t_p, "material": m_p, "foto_url": foto_url
            }).execute()
            st.success("Producto agregado correctamente")
            st.rerun()

    # ELIMINAR PRODUCTO
    with subtab_prod_del:
        prods_del = [p for p in CATALOGO.keys() if p != "Personalizado (Medida Libre)"]
        if prods_del:
            p_del = st.selectbox("Producto a eliminar:", prods_del)
            if st.button("Eliminar Definitivamente", key="btn_del_prod"):
                supabase.table("catalogo").delete().eq("nombre", p_del).execute()
                st.success("Producto eliminado")
                st.rerun()

```import streamlit as st
import pandas as pd
import datetime
import urllib.parse
from PIL import Image
from supabase import create_client, Client

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
# FUNCIONES DE BASE DE DATOS
# ==========================================
def cargar_materiales():
    res = supabase.table("materiales").select("*").execute()
    return {item["nombre"]: float(item["costo_cm2"]) for item in res.data}

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
        df.rename(columns={
            "fecha": "Fecha", "cliente": "Cliente", "telefono": "Teléfono",
            "producto": "Producto", "material": "Material", "cantidad": "Cantidad",
            "precio_unitario": "Precio Unitario", "total_cobrado": "Total Cobrado"
        }, inplace=True)
        return df[["id", "Fecha", "Cliente", "Teléfono", "Producto", "Material", "Cantidad", "Precio Unitario", "Total Cobrado"]]
    return pd.DataFrame()

# Carga inicial
precios_materiales = cargar_materiales()
CATALOGO = cargar_catalogo()

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
            
            if st.button("Ingresar", type="primary", use_container_width=True, key="btn_login_main"):
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

    # CÁLCULO DE COSTOS
    area_pieza = largo * ancho
    area_con_merma = area_pieza * desperdicio_factor
    costo_mat_unitario = area_con_merma * precios_materiales[material]
    costo_maq_unitario = tiempo * tarifa_minuto
    costo_prod_unitario = costo_mat_unitario + costo_maq_unitario
    precio_unitario_base = costo_prod_unitario / (1 - utilidad_porcentaje)

    descuento_pct = 0.20 if cantidad >= 50 else (0.10 if cantidad >= 12 else 0.00)
    precio_unitario_final = precio_unitario_base * (1 - descuento_pct)
    precio_total_neto = precio_unitario_final * cantidad

    st.markdown("---")
    res_col1, res_col2, res_col3, res_col4 = st.columns(4)
    res_col1.metric("Costo Producción (1 pz)", f"${costo_prod_unitario:.2f} MXN")
    res_col2.metric("Precio Base (1 pz)", f"${precio_unitario_base:.2f} MXN")
    res_col3.metric("Descuento Mayoreo", f"{int(descuento_pct * 100)}%")
    res_col4.metric("PRECIO TOTAL", f"${precio_total_neto:.2f} MXN", delta=f"{cantidad} pieza(s)")

    # DESGLOSE TÉCNICO INTERNO
    with st.expander("📊 Ver Desglose Técnico de Costos y Márgenes"):
        d_col1, d_col2 = st.columns(2)
        
        with d_col1:
            st.markdown("**Cálculo de Material y Áreas:**")
            st.write(f"• **Área nominal por pieza:** {area_pieza:.1f} cm²")
            st.write(f"• **Área con merma (10%):** {area_con_merma:.1f} cm²")
            st.write(f"• **Costo por cm² ({material}):** ${precios_materiales[material]:.4f} MXN")
            st.write(f"• **Costo total de material (1 pz):** ${costo_mat_unitario:.2f} MXN")
            
        with d_col2:
            st.markdown("**Cálculo de Maquinado y Márgenes:**")
            st.write(f"• **Costo de tiempo máquina (1 pz):** ${costo_maq_unitario:.2f} MXN ({tiempo} min @ ${tarifa_minuto}/min)")
            st.write(f"• **Utilidad estimada (1 pz):** ${precio_unitario_base - costo_prod_unitario:.2f} MXN ({int(utilidad_porcentaje * 100)}%)")
            st.write(f"• **Precio unitario final con descuento:** ${precio_unitario_final:.2f} MXN")
            st.write(f"• **Costo producción total del lote ({cantidad} pz):** ${costo_prod_unitario * cantidad:.2f} MXN")

    st.markdown("---")
    col_act1, col_act2 = st.columns(2)
    with col_act1:
        cliente_txt = nombre_cliente.strip() if nombre_cliente.strip() else "Cliente"
        msg_wa = (
            f"Hola *{cliente_txt}* 👋\n\n"
            f"Te comparto la cotización de tu pedido de *Z&A Taller Creativo*:\n"
            f"📌 *Producto:* {producto_sel}\n"
            f"📐 *Medidas:* {largo:.1f} x {ancho:.1f} cm\n"
            f"🪵 *Material:* {material}\n"
            f"📦 *Cantidad:* {cantidad} pieza(s)\n"
            f"💵 *Precio Unitario:* ${precio_unitario_final:.2f} MXN\n"
            f"💰 *TOTAL A COBRAR:* *${precio_total_neto:.2f} MXN*\n\n"
            f"_Cotización válida por 15 días. ¡Quedo atento a tus comentarios!_"
        )
        tel_clean = "".join(filter(str.isdigit, telefono_cliente))
        wa_url = f"https://wa.me/{tel_clean}?text={urllib.parse.quote(msg_wa)}" if tel_clean else f"https://wa.me/?text={urllib.parse.quote(msg_wa)}"
        st.link_button("📲 Enviar Cotización por WhatsApp", wa_url, type="primary")

    with col_act2:
        if st.button("💾 Guardar Cotización en Historial", key="btn_guardar_cotizacion"):
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
            st.success("✅ ¡Cotización guardada en Supabase!")

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
                "Fecha": st.column_config.TextColumn("Fecha", disabled=True)
            }
        )

        if st.button("💾 Guardar Cambios en Historial", type="primary", key="btn_guardar_historial"):
            for _, row in df_editado.iterrows():
                if pd.notnull(row["id"]):
                    supabase.table("historial_cotizaciones").update({
                        "cliente": row["Cliente"],
                        "telefono": row["Teléfono"],
                        "cantidad": int(row["Cantidad"]),
                        "precio_unitario": float(row["Precio Unitario"]),
                        "total_cobrado": float(row["Total Cobrado"])
                    }).eq("id", row["id"]).execute()
            st.success("✅ Historial actualizado.")
            st.rerun()
    else:
        st.info("💡 Aún no hay cotizaciones guardadas.")

# ------------------------------------------
# TAB 3: ADMINISTRACIÓN
# ------------------------------------------
with tab_admin:
    st.header("⚙️ Panel de Administración")
    subtab_mat, subtab_prod_add, subtab_prod_del = st.tabs([
        "🪵 Administrar Materiales", "➕ Agregar Producto", "🗑️ Eliminar Producto"
    ])
    
    # MATERIALES
    with subtab_mat:
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown("#### ➕ Agregar Material")
            nom_m = st.text_input("Nombre Material:")
            p_m = st.number_input("Precio Placa ($):", value=120.0)
            l_m = st.number_input("Largo (cm):", value=122.0)
            a_m = st.number_input("Ancho (cm):", value=244.0)
            if st.button("Guardar Material", key="btn_add_mat"):
                c_cm2 = p_m / (l_m * a_m)
                supabase.table("materiales").insert({"nombre": nom_m.strip(), "costo_cm2": c_cm2}).execute()
                st.success("Material agregado")
                st.rerun()

        with col_m2:
            st.markdown("#### 🗑️ Eliminar Material")
            mat_del = st.selectbox("Selecciona material:", list(precios_materiales.keys()))
            if st.button("Eliminar Material", key="btn_del_mat"):
                supabase.table("materiales").delete().eq("nombre", mat_del).execute()
                st.success("Material eliminado")
                st.rerun()

    # AGREGAR PRODUCTO
    with subtab_prod_add:
        st.subheader("➕ Agregar Nuevo Producto")
        n_p = st.text_input("Nombre Producto:")
        col_pa, col_pb = st.columns(2)
        l_p = col_pa.number_input("Largo (cm):", value=10.0)
        a_p = col_pb.number_input("Ancho (cm):", value=10.0)
        t_p = col_pa.number_input("Tiempo (min):", value=2.0)
        m_p = col_pb.selectbox("Material default:", list(precios_materiales.keys()))
        foto_up = st.file_uploader("Imagen:", type=["jpg", "png", "jpeg"])

        if st.button("Guardar Producto Nuevo", key="btn_add_prod"):
            foto_url = None
            if foto_up:
                file_ext = foto_up.name.split(".")[-1]
                file_path = f"{n_p.strip().lower().replace(' ', '_')}.{file_ext}"
                file_bytes = foto_up.getvalue()
                
                supabase.storage.from_("productos_img").upload(file_path, file_bytes, {"content-type": foto_up.type})
                foto_url = supabase.storage.from_("productos_img").get_public_url(file_path)

            supabase.table("catalogo").insert({
                "nombre": n_p.strip(), "largo": l_p, "ancho": a_p, 
                "tiempo": t_p, "material": m_p, "foto_url": foto_url
            }).execute()
            st.success("Producto agregado correctamente")
            st.rerun()

    # ELIMINAR PRODUCTO
    with subtab_prod_del:
        prods_del = [p for p in CATALOGO.keys() if p != "Personalizado (Medida Libre)"]
        if prods_del:
            p_del = st.selectbox("Producto a eliminar:", prods_del)
            if st.button("Eliminar Definitivamente", key="btn_del_prod"):
                supabase.table("catalogo").delete().eq("nombre", p_del).execute()
                st.success("Producto eliminado")
                st.rerun()import streamlit as st
import pandas as pd
import datetime
import urllib.parse
from PIL import Image
from supabase import create_client, Client

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
# FUNCIONES DE BASE DE DATOS
# ==========================================
def cargar_materiales():
    res = supabase.table("materiales").select("*").execute()
    return {item["nombre"]: float(item["costo_cm2"]) for item in res.data}

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
        df.rename(columns={
            "fecha": "Fecha", "cliente": "Cliente", "telefono": "Teléfono",
            "producto": "Producto", "material": "Material", "cantidad": "Cantidad",
            "precio_unitario": "Precio Unitario", "total_cobrado": "Total Cobrado"
        }, inplace=True)
        return df[["id", "Fecha", "Cliente", "Teléfono", "Producto", "Material", "Cantidad", "Precio Unitario", "Total Cobrado"]]
    return pd.DataFrame()

# Carga inicial
precios_materiales = cargar_materiales()
CATALOGO = cargar_catalogo()

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
            
            if st.button("Ingresar", type="primary", use_container_width=True):
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
    if st.button("🔒 Cerrar Sesión", use_container_width=True):
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

    # CÁLCULO DE COSTOS
    area_con_merma = (largo * ancho) * desperdicio_factor
    costo_mat_unitario = area_con_merma * precios_materiales[material]
    costo_maq_unitario = tiempo * tarifa_minuto
    costo_prod_unitario = costo_mat_unitario + costo_maq_unitario
    precio_unitario_base = costo_prod_unitario / (1 - utilidad_porcentaje)

    descuento_pct = 0.20 if cantidad >= 50 else (0.10 if cantidad >= 12 else 0.00)
    precio_unitario_final = precio_unitario_base * (1 - descuento_pct)
    precio_total_neto = precio_unitario_final * cantidad

    st.markdown("---")
    res_col1, res_col2, res_col3, res_col4 = st.columns(4)
    res_col1.metric("Costo Producción (1 pz)", f"${costo_prod_unitario:.2f} MXN")
    res_col2.metric("Precio Base (1 pz)", f"${precio_unitario_base:.2f} MXN")
    res_col3.metric("Descuento Mayoreo", f"{int(descuento_pct * 100)}%")
    res_col4.metric("PRECIO TOTAL", f"${precio_total_neto:.2f} MXN", delta=f"{cantidad} pieza(s)")

    col_act1, col_act2 = st.columns(2)
    with col_act1:
        cliente_txt = nombre_cliente.strip() if nombre_cliente.strip() else "Cliente"
        msg_wa = (
            f"Hola *{cliente_txt}* 👋\n\n"
            f"Te comparto la cotización de tu pedido de *Z&A Taller Creativo*:\n"
            f"📌 *Producto:* {producto_sel}\n"
            f"📐 *Medidas:* {largo:.1f} x {ancho:.1f} cm\n"
            f"🪵 *Material:* {material}\n"
            f"📦 *Cantidad:* {cantidad} pieza(s)\n"
            f"💵 *Precio Unitario:* ${precio_unitario_final:.2f} MXN\n"
            f"💰 *TOTAL A COBRAR:* *${precio_total_neto:.2f} MXN*\n\n"
            f"_Cotización válida por 15 días. ¡Quedo atento a tus comentarios!_"
        )
        tel_clean = "".join(filter(str.isdigit, telefono_cliente))
        wa_url = f"https://wa.me/{tel_clean}?text={urllib.parse.quote(msg_wa)}" if tel_clean else f"https://wa.me/?text={urllib.parse.quote(msg_wa)}"
        st.link_button("📲 Enviar Cotización por WhatsApp", wa_url, type="primary")

    with col_act2:
        if st.button("💾 Guardar Cotización en Historial"):
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
            st.success("✅ ¡Cotización guardada en Supabase!")

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
                "id": None, # Ocultar ID interno
                "Fecha": st.column_config.TextColumn("Fecha", disabled=True)
            }
        )

        if st.button("💾 Guardar Cambios en Historial", type="primary"):
            # Sincronizar ediciones directo a Supabase
            for _, row in df_editado.iterrows():
                if pd.notnull(row["id"]):
                    supabase.table("historial_cotizaciones").update({
                        "cliente": row["Cliente"],
                        "telefono": row["Teléfono"],
                        "cantidad": int(row["Cantidad"]),
                        "precio_unitario": float(row["Precio Unitario"]),
                        "total_cobrado": float(row["Total Cobrado"])
                    }).eq("id", row["id"]).execute()
            st.success("✅ Historial actualizado.")
            st.rerun()
    else:
        st.info("💡 Aún no hay cotizaciones guardadas.")

# ------------------------------------------
# TAB 3: ADMINISTRACIÓN
# ------------------------------------------
with tab_admin:
    st.header("⚙️ Panel de Administración")
    subtab_mat, subtab_prod_add, subtab_prod_del = st.tabs([
        "🪵 Administrar Materiales", "➕ Agregar Producto", "🗑️ Eliminar Producto"
    ])
    
    # MATERIALES
    with subtab_mat:
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown("#### ➕ Agregar Material")
            nom_m = st.text_input("Nombre Material:")
            p_m = st.number_input("Precio Placa ($):", value=120.0)
            l_m = st.number_input("Largo (cm):", value=122.0)
            a_m = st.number_input("Ancho (cm):", value=244.0)
            if st.button("Guardar Material"):
                c_cm2 = p_m / (l_m * a_m)
                supabase.table("materiales").insert({"nombre": nom_m.strip(), "costo_cm2": c_cm2}).execute()
                st.success("Material agregado")
                st.rerun()

        with col_m2:
            st.markdown("#### 🗑️ Eliminar Material")
            mat_del = st.selectbox("Selecciona material:", list(precios_materiales.keys()))
            if st.button("Eliminar Material"):
                supabase.table("materiales").delete().eq("nombre", mat_del).execute()
                st.success("Material eliminado")
                st.rerun()

    # AGREGAR PRODUCTO
    with subtab_prod_add:
        st.subheader("➕ Agregar Nuevo Producto")
        n_p = st.text_input("Nombre Producto:")
        col_pa, col_pb = st.columns(2)
        l_p = col_pa.number_input("Largo (cm):", value=10.0)
        a_p = col_pb.number_input("Ancho (cm):", value=10.0)
        t_p = col_pa.number_input("Tiempo (min):", value=2.0)
        m_p = col_pb.selectbox("Material default:", list(precios_materiales.keys()))
        foto_up = st.file_uploader("Imagen:", type=["jpg", "png", "jpeg"])

        if st.button("Guardar Producto Nuevo"):
            foto_url = None
            if foto_up:
                file_ext = foto_up.name.split(".")[-1]
                file_path = f"{n_p.strip().lower().replace(' ', '_')}.{file_ext}"
                file_bytes = foto_up.getvalue()
                
                # Subir archivo al bucket de Supabase
                supabase.storage.from_("productos_img").upload(file_path, file_bytes, {"content-type": foto_up.type})
                foto_url = supabase.storage.from_("productos_img").get_public_url(file_path)

            supabase.table("catalogo").insert({
                "nombre": n_p.strip(), "largo": l_p, "ancho": a_p, 
                "tiempo": t_p, "material": m_p, "foto_url": foto_url
            }).execute()
            st.success("Producto agregado correctamente")
            st.rerun()

    # ELIMINAR PRODUCTO
    with subtab_prod_del:
        prods_del = [p for p in CATALOGO.keys() if p != "Personalizado (Medida Libre)"]
        if prods_del:
            p_del = st.selectbox("Producto a eliminar:", prods_del)
            if st.button("Eliminar Definitivamente"):
                supabase.table("catalogo").delete().eq("nombre", p_del).execute()
                st.success("Producto eliminado")
                st.rerun()
import os
import urllib.parse
import pandas as pd
import streamlit as st
from PIL import Image
from supabase import create_client, Client

Image.MAX_IMAGE_PIXELS = None

# ==========================================
# CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="Z&A Taller Creativo - Cotizador",
    page_icon="✂️",
    layout="wide"
)

# Carga e inspección de la imagen una sola vez en caché
@st.cache_data
def obtener_logo():
    for archivo in ["logo.png", "logo.PNG", "LOGO.PNG", "logo.jpg"]:
        if os.path.exists(archivo):
            return archivo
    return None

logo_path = obtener_logo()

# ==========================================
# INICIALIZACIÓN DE SUPABASE & CACHÉ DE DATOS
# ==========================================
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["supabase"]["SUPABASE_URL"]
    key = st.secrets["supabase"]["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

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
        df.rename(columns={
            "fecha": "Fecha", "cliente": "Cliente", "telefono": "Teléfono",
            "producto": "Producto", "material": "Material", "cantidad": "Cantidad",
            "precio_unitario": "Precio Unitario", "total_cobrado": "Total Cobrado"
        }, inplace=True)
        return df[["id", "Fecha", "Cliente", "Teléfono", "Producto", "Material", "Cantidad", "Precio Unitario", "Total Cobrado"]]
    return pd.DataFrame()

# Carga de diccionarios desde caché instantáneo
precios_materiales = cargar_materiales()
CATALOGO = cargar_catalogo()

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
            if logo_path:
                st.image(logo_path, width=200)
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
    if logo_path:
        st.image(logo_path, use_container_width=True)
    st.markdown("<h2 style='text-align: center; color: #4A90E2;'>Z&A TALLER CREATIVO</h2>", unsafe_allow_html=True)
    if st.button("🔒 Cerrar Sesión", use_container_width=True, key="btn_logout"):
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

    # CÁLCULO DE COSTOS
    area_con_merma = (largo * ancho) * desperdicio_factor
    costo_mat_unitario = area_con_merma * precios_materiales[material]
    costo_maq_unitario = tiempo * tarifa_minuto
    costo_prod_unitario = costo_mat_unitario + costo_maq_unitario
    precio_unitario_base = costo_prod_unitario / (1 - utilidad_porcentaje)

    descuento_pct = 0.20 if cantidad >= 50 else (0.10 if cantidad >= 12 else 0.00)
    precio_unitario_final = precio_unitario_base * (1 - descuento_pct)
    precio_total_neto = precio_unitario_final * cantidad

    st.markdown("---")
    res_col1, res_col2, res_col3, res_col4 = st.columns(4)
    res_col1.metric("Costo Producción (1 pz)", f"${costo_prod_unitario:.2f} MXN")
    res_col2.metric("Precio Base (1 pz)", f"${precio_unitario_base:.2f} MXN")
    res_col3.metric("Descuento Mayoreo", f"{int(descuento_pct * 100)}%")
    res_col4.metric("PRECIO TOTAL", f"${precio_total_neto:.2f} MXN", delta=f"{cantidad} pieza(s)")

    col_act1, col_act2 = st.columns(2)
    with col_act1:
        cliente_txt = nombre_cliente.strip() if nombre_cliente.strip() else "Cliente"
        msg_wa = (
            f"Hola *{cliente_txt}* 👋\n\n"
            f"Te comparto la cotización de tu pedido de *Z&A Taller Creativo*:\n"
            f"📌 *Producto:* {producto_sel}\n"
            f"📐 *Medidas:* {largo:.1f} x {ancho:.1f} cm\n"
            f"🪵 *Material:* {material}\n"
            f"📦 *Cantidad:* {cantidad} pieza(s)\n"
            f"💵 *Precio Unitario:* ${precio_unitario_final:.2f} MXN\n"
            f"💰 *TOTAL A COBRAR:* *${precio_total_neto:.2f} MXN*\n\n"
            f"_Cotización válida por 15 días. ¡Quedo atento a tus comentarios!_"
        )
        tel_clean = "".join(filter(str.isdigit, telefono_cliente))
        wa_url = f"https://wa.me/{tel_clean}?text={urllib.parse.quote(msg_wa)}" if tel_clean else f"https://wa.me/?text={urllib.parse.quote(msg_wa)}"
        st.link_button("📲 Enviar Cotización por WhatsApp", wa_url, type="primary")

    with col_act2:
        if st.button("💾 Guardar Cotización en Historial"):
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
            st.success("✅ ¡Cotización guardada en Supabase!")

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
                "Fecha": st.column_config.TextColumn("Fecha", disabled=True)
            }
        )

        if st.button("💾 Guardar Cambios en Historial", type="primary"):
            for _, row in df_editado.iterrows():
                if pd.notnull(row["id"]):
                    supabase.table("historial_cotizaciones").update({
                        "cliente": row["Cliente"],
                        "telefono": row["Teléfono"],
                        "cantidad": int(row["Cantidad"]),
                        "precio_unitario": float(row["Precio Unitario"]),
                        "total_cobrado": float(row["Total Cobrado"])
                    }).eq("id", row["id"]).execute()
            st.success("✅ Historial actualizado.")
            st.rerun()
    else:
        st.info("💡 Aún no hay cotizaciones guardadas.")

# ------------------------------------------
# TAB 3: ADMINISTRACIÓN
# ------------------------------------------
with tab_admin:
    st.header("⚙️ Panel de Administración")
    subtab_mat, subtab_prod_add, subtab_prod_del = st.tabs([
        "🪵 Administrar Materiales", "➕ Agregar Producto", "🗑️ Eliminar Producto"
    ])
    
    # MATERIALES
    with subtab_mat:
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown("#### ➕ Agregar Material")
            nom_m = st.text_input("Nombre Material:")
            p_m = st.number_input("Precio Placa ($):", value=120.0)
            l_m = st.number_input("Largo (cm):", value=122.0)
            a_m = st.number_input("Ancho (cm):", value=244.0)
            if st.button("Guardar Material"):
                c_cm2 = p_m / (l_m * a_m)
                supabase.table("materiales").insert({"nombre": nom_m.strip(), "costo_cm2": c_cm2}).execute()
                st.cache_data.clear()
                st.success("Material agregado")
                st.rerun()

        with col_m2:
            st.markdown("#### 🗑️ Eliminar Material")
            mat_del = st.selectbox("Selecciona material:", list(precios_materiales.keys()))
            if st.button("Eliminar Material"):
                supabase.table("materiales").delete().eq("nombre", mat_del).execute()
                st.cache_data.clear()
                st.success("Material eliminado")
                st.rerun()

    # AGREGAR PRODUCTO
    with subtab_prod_add:
        st.subheader("➕ Agregar Nuevo Producto")
        n_p = st.text_input("Nombre Producto:")
        col_pa, col_pb = st.columns(2)
        l_p = col_pa.number_input("Largo (cm):", value=10.0)
        a_p = col_pb.number_input("Ancho (cm):", value=10.0)
        t_p = col_pa.number_input("Tiempo (min):", value=2.0)
        m_p = col_pb.selectbox("Material default:", list(precios_materiales.keys()))
        foto_up = st.file_uploader("Imagen:", type=["jpg", "png", "jpeg"])

        if st.button("Guardar Producto Nuevo"):
            foto_url = None
            if foto_up:
                file_ext = foto_up.name.split(".")[-1]
                file_path = f"{n_p.strip().lower().replace(' ', '_')}.{file_ext}"
                file_bytes = foto_up.getvalue()
                
                supabase.storage.from_("productos_img").upload(file_path, file_bytes, {"content-type": foto_up.type})
                foto_url = supabase.storage.from_("productos_img").get_public_url(file_path)

            supabase.table("catalogo").insert({
                "nombre": n_p.strip(), "largo": l_p, "ancho": a_p, 
                "tiempo": t_p, "material": m_p, "foto_url": foto_url
            }).execute()
            st.cache_data.clear()
            st.success("Producto agregado correctamente")
            st.rerun()

    # ELIMINAR PRODUCTO
    with subtab_prod_del:
        prods_del = [p for p in CATALOGO.keys() if p != "Personalizado (Medida Libre)"]
        if prods_del:
            p_del = st.selectbox("Producto a eliminar:", prods_del)
            if st.button("Eliminar Definitivamente"):
                supabase.table("catalogo").delete().eq("nombre", p_del).execute()
                st.cache_data.clear()
                st.success("Producto eliminado")
                st.rerun()import streamlit as st
import pandas as pd
import datetime
import urllib.parse
from PIL import Image
from supabase import create_client, Client

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
# FUNCIONES DE BASE DE DATOS
# ==========================================
def cargar_materiales():
    res = supabase.table("materiales").select("*").execute()
    return {item["nombre"]: float(item["costo_cm2"]) for item in res.data}

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
        df.rename(columns={
            "fecha": "Fecha", "cliente": "Cliente", "telefono": "Teléfono",
            "producto": "Producto", "material": "Material", "cantidad": "Cantidad",
            "precio_unitario": "Precio Unitario", "total_cobrado": "Total Cobrado"
        }, inplace=True)
        return df[["id", "Fecha", "Cliente", "Teléfono", "Producto", "Material", "Cantidad", "Precio Unitario", "Total Cobrado"]]
    return pd.DataFrame()

# Carga inicial
precios_materiales = cargar_materiales()
CATALOGO = cargar_catalogo()

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
            
            if st.button("Ingresar", type="primary", use_container_width=True):
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
    if st.button("🔒 Cerrar Sesión", use_container_width=True):
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

    # CÁLCULO DE COSTOS
    area_con_merma = (largo * ancho) * desperdicio_factor
    costo_mat_unitario = area_con_merma * precios_materiales[material]
    costo_maq_unitario = tiempo * tarifa_minuto
    costo_prod_unitario = costo_mat_unitario + costo_maq_unitario
    precio_unitario_base = costo_prod_unitario / (1 - utilidad_porcentaje)

    descuento_pct = 0.20 if cantidad >= 50 else (0.10 if cantidad >= 12 else 0.00)
    precio_unitario_final = precio_unitario_base * (1 - descuento_pct)
    precio_total_neto = precio_unitario_final * cantidad

    st.markdown("---")
    res_col1, res_col2, res_col3, res_col4 = st.columns(4)
    res_col1.metric("Costo Producción (1 pz)", f"${costo_prod_unitario:.2f} MXN")
    res_col2.metric("Precio Base (1 pz)", f"${precio_unitario_base:.2f} MXN")
    res_col3.metric("Descuento Mayoreo", f"{int(descuento_pct * 100)}%")
    res_col4.metric("PRECIO TOTAL", f"${precio_total_neto:.2f} MXN", delta=f"{cantidad} pieza(s)")

    col_act1, col_act2 = st.columns(2)
    with col_act1:
        cliente_txt = nombre_cliente.strip() if nombre_cliente.strip() else "Cliente"
        msg_wa = (
            f"Hola *{cliente_txt}* 👋\n\n"
            f"Te comparto la cotización de tu pedido de *Z&A Taller Creativo*:\n"
            f"📌 *Producto:* {producto_sel}\n"
            f"📐 *Medidas:* {largo:.1f} x {ancho:.1f} cm\n"
            f"🪵 *Material:* {material}\n"
            f"📦 *Cantidad:* {cantidad} pieza(s)\n"
            f"💵 *Precio Unitario:* ${precio_unitario_final:.2f} MXN\n"
            f"💰 *TOTAL A COBRAR:* *${precio_total_neto:.2f} MXN*\n\n"
            f"_Cotización válida por 15 días. ¡Quedo atento a tus comentarios!_"
        )
        tel_clean = "".join(filter(str.isdigit, telefono_cliente))
        wa_url = f"https://wa.me/{tel_clean}?text={urllib.parse.quote(msg_wa)}" if tel_clean else f"https://wa.me/?text={urllib.parse.quote(msg_wa)}"
        st.link_button("📲 Enviar Cotización por WhatsApp", wa_url, type="primary")

    with col_act2:
        if st.button("💾 Guardar Cotización en Historial"):
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
            st.success("✅ ¡Cotización guardada en Supabase!")

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
                "id": None, # Ocultar ID interno
                "Fecha": st.column_config.TextColumn("Fecha", disabled=True)
            }
        )

        if st.button("💾 Guardar Cambios en Historial", type="primary"):
            # Sincronizar ediciones directo a Supabase
            for _, row in df_editado.iterrows():
                if pd.notnull(row["id"]):
                    supabase.table("historial_cotizaciones").update({
                        "cliente": row["Cliente"],
                        "telefono": row["Teléfono"],
                        "cantidad": int(row["Cantidad"]),
                        "precio_unitario": float(row["Precio Unitario"]),
                        "total_cobrado": float(row["Total Cobrado"])
                    }).eq("id", row["id"]).execute()
            st.success("✅ Historial actualizado.")
            st.rerun()
    else:
        st.info("💡 Aún no hay cotizaciones guardadas.")

# ------------------------------------------
# TAB 3: ADMINISTRACIÓN
# ------------------------------------------
with tab_admin:
    st.header("⚙️ Panel de Administración")
    subtab_mat, subtab_prod_add, subtab_prod_del = st.tabs([
        "🪵 Administrar Materiales", "➕ Agregar Producto", "🗑️ Eliminar Producto"
    ])
    
    # MATERIALES
    with subtab_mat:
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown("#### ➕ Agregar Material")
            nom_m = st.text_input("Nombre Material:")
            p_m = st.number_input("Precio Placa ($):", value=120.0)
            l_m = st.number_input("Largo (cm):", value=122.0)
            a_m = st.number_input("Ancho (cm):", value=244.0)
            if st.button("Guardar Material"):
                c_cm2 = p_m / (l_m * a_m)
                supabase.table("materiales").insert({"nombre": nom_m.strip(), "costo_cm2": c_cm2}).execute()
                st.success("Material agregado")
                st.rerun()

        with col_m2:
            st.markdown("#### 🗑️ Eliminar Material")
            mat_del = st.selectbox("Selecciona material:", list(precios_materiales.keys()))
            if st.button("Eliminar Material"):
                supabase.table("materiales").delete().eq("nombre", mat_del).execute()
                st.success("Material eliminado")
                st.rerun()

    # AGREGAR PRODUCTO
    with subtab_prod_add:
        st.subheader("➕ Agregar Nuevo Producto")
        n_p = st.text_input("Nombre Producto:")
        col_pa, col_pb = st.columns(2)
        l_p = col_pa.number_input("Largo (cm):", value=10.0)
        a_p = col_pb.number_input("Ancho (cm):", value=10.0)
        t_p = col_pa.number_input("Tiempo (min):", value=2.0)
        m_p = col_pb.selectbox("Material default:", list(precios_materiales.keys()))
        foto_up = st.file_uploader("Imagen:", type=["jpg", "png", "jpeg"])

        if st.button("Guardar Producto Nuevo"):
            foto_url = None
            if foto_up:
                file_ext = foto_up.name.split(".")[-1]
                file_path = f"{n_p.strip().lower().replace(' ', '_')}.{file_ext}"
                file_bytes = foto_up.getvalue()
                
                # Subir archivo al bucket de Supabase
                supabase.storage.from_("productos_img").upload(file_path, file_bytes, {"content-type": foto_up.type})
                foto_url = supabase.storage.from_("productos_img").get_public_url(file_path)

            supabase.table("catalogo").insert({
                "nombre": n_p.strip(), "largo": l_p, "ancho": a_p, 
                "tiempo": t_p, "material": m_p, "foto_url": foto_url
            }).execute()
            st.success("Producto agregado correctamente")
            st.rerun()

    # ELIMINAR PRODUCTO
    with subtab_prod_del:
        prods_del = [p for p in CATALOGO.keys() if p != "Personalizado (Medida Libre)"]
        if prods_del:
            p_del = st.selectbox("Producto a eliminar:", prods_del)
            if st.button("Eliminar Definitivamente"):
                supabase.table("catalogo").delete().eq("nombre", p_del).execute()
                st.success("Producto eliminado")
                st.rerun()
