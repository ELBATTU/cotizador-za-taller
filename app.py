import os
import urllib.parse
import pandas as pd
import streamlit as st
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

# Carga del logo local
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")

@st.cache_data
def cargar_logo_cache():
    if os.path.exists(LOGO_PATH):
        try:
            return Image.open(LOGO_PATH)
        except Exception:
            return None
    return None

logo_img = cargar_logo_cache()

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
    res = supabase.table("materiales").select("*").order("nombre").execute()
    return {item["nombre"]: float(item["costo_cm2"]) for item in res.data}

def cargar_catalogo():
    res = supabase.table("catalogo").select("*").order("nombre").execute()
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
            if logo_img:
                st.image(logo_img, width=220)
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
    if logo_img:
        st.image(logo_img, use_container_width=True)
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
    col_hdr_logo, col_hdr_txt = st.columns([1, 5], vertical_alignment="center")
    with col_hdr_logo:
        if logo_img:
            st.image(logo_img, width=120)
    with col_hdr_txt:
        st.markdown("<h1 style='color: #1E88E5; margin:0;'>Z&A Taller Creativo</h1>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 18px; color: #888; margin:0;'>Cotizador Interactivo - Corte & Grabado Láser CNC</p>", unsafe_allow_html=True)
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

    # DESGROSE TÉCNICO COMPLETO
    with st.expander("🔍 Ver Desglose Técnico de Costos Completo", expanded=False):
        st.markdown(f"""
        | Concepto | Valor / Calculo | Costo Estimado |
        | :--- | :--- | :--- |
        | **Área Real Pieza** | {largo} x {ancho} cm | {largo * ancho:.2f} cm² |
        | **Área + Merma (10%)** | Area x 1.10 | {area_con_merma:.2f} cm² |
        | **Costo Material (1 pz)** | {area_con_merma:.2f} cm² x ${precios_materiales[material]:.6f} | **${costo_mat_unitario:.2f} MXN** |
        | **Costo Maquinado (1 pz)** | {tiempo} min x ${tarifa_minuto:.2f}/min | **${costo_maq_unitario:.2f} MXN** |
        | **Costo Producción Total (1 pz)** | Material + Maquinado | **${costo_prod_unitario:.2f} MXN** |
        | **Precio Unitario (Margen {int(utilidad_porcentaje*100)}%)** | Costo / (1 - Margen) | **${precio_unitario_base:.2f} MXN** |
        | **Descuento Aplicado** | Tier Mayoreo ({int(descuento_pct*100)}%) | -${precio_unitario_base - precio_unitario_final:.2f} MXN / pz |
        | **Precio Final Unitario** | Con descuento aplicado | **${precio_unitario_final:.2f} MXN** |
        | **GRAN TOTAL ({cantidad} pz)** | Precio Final x {cantidad} pz | **${precio_total_neto:.2f} MXN** |
        """)

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
        st.link_button("📲 Enviar Cotización por WhatsApp", wa_url, type="primary", use_container_width=True)

    with col_act2:
        if st.button("💾 Guardar Cotización en Historial", use_container_width=True):
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
            st.toast("✅ ¡Cotización guardada exitosamente en el historial!", icon="💾")
            st.success("✅ Cotización registrada correctamente.")

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

        if st.button("💾 Guardar Cambios en Historial (Actualizar/Eliminar)", type="primary"):
            ids_actuales = set(df_editado["id"].dropna().tolist())
            ids_originales = set(df_historial["id"].tolist())
            
            # 1. Eliminar filas borradas en el editor
            ids_eliminados = ids_originales - ids_actuales
            for id_del in ids_eliminados:
                supabase.table("historial_cotizaciones").delete().eq("id", id_del).execute()
            
            # 2. Actualizar filas modificadas
            for _, row in df_editado.iterrows():
                if pd.notnull(row["id"]):
                    supabase.table("historial_cotizaciones").update({
                        "cliente": row["Cliente"],
                        "telefono": row["Teléfono"],
                        "producto": row["Producto"],
                        "material": row["Material"],
                        "cantidad": int(row["Cantidad"]),
                        "precio_unitario": float(row["Precio Unitario"]),
                        "total_cobrado": float(row["Total Cobrado"])
                    }).eq("id", row["id"]).execute()
            
            st.toast("✅ Base de datos sincronizada correctamente.", icon="🧹")
            st.success("✅ Cambios e historial de eliminaciones guardados en Supabase.")
            st.rerun()
    else:
        st.info("💡 Aún no hay cotizaciones guardadas.")

# ------------------------------------------
# TAB 3: ADMINISTRACIÓN
# ------------------------------------------
with tab_admin:
    st.header("⚙️ Panel de Administración")
    subtab_mat, subtab_prod = st.tabs(["🪵 Gestión de Materiales", "📦 Gestión de Productos"])
    
    # GESTIÓN DE MATERIALES
    with subtab_mat:
        st.subheader("🪵 Catálogo Actual de Materiales")
        df_mat = pd.DataFrame([{"Material": k, "Costo cm² ($)": v} for k, v in precios_materiales.items()])
        st.dataframe(df_mat, use_container_width=True)
        st.markdown("---")

        col_m_add, col_m_edit, col_m_del = st.columns(3)

        with col_m_add:
            st.markdown("#### ➕ Agregar Material")
            nom_m = st.text_input("Nombre Material:", key="add_m_nom")
            p_m = st.number_input("Precio Placa ($):", value=120.0, key="add_m_p")
            l_m = st.number_input("Largo Placa (cm):", value=122.0, key="add_m_l")
            a_m = st.number_input("Ancho Placa (cm):", value=244.0, key="add_m_a")
            if st.button("➕ Crear Material", use_container_width=True):
                if nom_m.strip():
                    c_cm2 = p_m / (l_m * a_m)
                    supabase.table("materiales").insert({"nombre": nom_m.strip(), "costo_cm2": c_cm2}).execute()
                    st.toast(f"Material '{nom_m.strip()}' agregado exitosamente", icon="✅")
                    st.success(f"✅ Se agregó '{nom_m.strip()}' con costo de ${c_cm2:.6f} por cm²")
                    st.rerun()
                else:
                    st.error("Escribe un nombre válido.")

        with col_m_edit:
            st.markdown("#### ✏️ Editar Material")
            mat_edit_sel = st.selectbox("Seleccionar para editar:", list(precios_materiales.keys()), key="sel_m_edit")
            p_m_e = st.number_input("Nuevo Precio Placa ($):", value=120.0, key="edit_m_p")
            l_m_e = st.number_input("Largo Placa (cm):", value=122.0, key="edit_m_l")
            a_m_e = st.number_input("Ancho Placa (cm):", value=244.0, key="edit_m_a")
            if st.button("✏️ Actualizar Material", use_container_width=True):
                c_cm2_new = p_m_e / (l_m_e * a_m_e)
                supabase.table("materiales").update({"costo_cm2": c_cm2_new}).eq("nombre", mat_edit_sel).execute()
                st.toast(f"Material '{mat_edit_sel}' actualizado", icon="📝")
                st.success(f"✅ Se actualizó el costo de '{mat_edit_sel}'")
                st.rerun()

        with col_m_del:
            st.markdown("#### 🗑️ Eliminar Material")
            mat_del_sel = st.selectbox("Seleccionar para eliminar:", list(precios_materiales.keys()), key="sel_m_del")
            st.warning("⚠️ Esta acción es permanente.")
            if st.button("🗑️ Eliminar Material", type="primary", use_container_width=True):
                supabase.table("materiales").delete().eq("nombre", mat_del_sel).execute()
                st.toast(f"Material '{mat_del_sel}' eliminado", icon="🗑️")
                st.success(f"✅ Material '{mat_del_sel}' eliminado correctamente")
                st.rerun()

# GESTIÓN DE PRODUCTOS
    with subtab_prod:
        st.subheader("📦 Catálogo de Productos Registrados")
        
        # Construcción limpia de la tabla de productos
        lista_prod_tabla = []
        for nombre_p, datos_p in CATALOGO.items():
            lista_prod_tabla.append({
                "Producto": nombre_p, 
                "Largo (cm)": datos_p["largo"], 
                "Ancho (cm)": datos_p["ancho"], 
                "Tiempo (min)": datos_p["tiempo"], 
                "Material Default": datos_p["material"], 
                "Tiene Foto": "Sí" if datos_p["foto"] else "No"
            })
            
        df_prod_disp = pd.DataFrame(lista_prod_tabla)
        st.dataframe(df_prod_disp, use_container_width=True)
        st.markdown("---")

        subtab_p_add, subtab_p_edit, subtab_p_del = st.tabs(["➕ Agregar Producto", "✏️ Editar Producto", "🗑️ Eliminar Producto"])

        with subtab_p_add:
            n_p = st.text_input("Nombre Producto:", key="add_p_name")
            col_pa, col_pb = st.columns(2)
            l_p = col_pa.number_input("Largo (cm):", value=10.0, key="add_p_l")
            a_p = col_pb.number_input("Ancho (cm):", value=10.0, key="add_p_a")
            t_p = col_pa.number_input("Tiempo (min):", value=2.0, key="add_p_t")
            m_p = col_pb.selectbox("Material default:", list(precios_materiales.keys()), key="add_p_m")
            foto_up = st.file_uploader("Imagen del producto:", type=["jpg", "png", "jpeg"], key="add_p_f")

            if st.button("➕ Crear Producto Nuevo", type="primary"):
                if n_p.strip():
                    foto_url = None
                    if foto_up:
                        file_ext = foto_up.name.split(".")[-1]
                        file_path = f"{n_p.strip().lower().replace(' ', '_')}.{file_ext}"
                        file_bytes = foto_up.getvalue()
                        supabase.storage.from_("productos_img").upload(file_path, file_bytes, {"content-type": foto_up.type, "x-upsert": "true"})
                        foto_url = supabase.storage.from_("productos_img").get_public_url(file_path)

                    supabase.table("catalogo").insert({
                        "nombre": n_p.strip(), "largo": l_p, "ancho": a_p, 
                        "tiempo": t_p, "material": m_p, "foto_url": foto_url
                    }).execute()
                    st.toast(f"Producto '{n_p.strip()}' registrado", icon="📦")
                    st.success(f"✅ Producto '{n_p.strip()}' agregado al catálogo exitosamente.")
                    st.rerun()
                else:
                    st.error("Por favor ingresa un nombre para el producto.")

        with subtab_p_edit:
            prods_editables = [p for p in CATALOGO.keys() if p != "Personalizado (Medida Libre)"]
            if prods_editables:
                p_edit_sel = st.selectbox("Selecciona producto a editar:", prods_editables, key="sel_p_edit")
                curr_p = CATALOGO[p_edit_sel]

                col_pe1, col_pe2 = st.columns(2)
                l_p_e = col_pe1.number_input("Nuevo Largo (cm):", value=float(curr_p["largo"]), key="e_p_l")
                a_p_e = col_pe2.number_input("Nuevo Ancho (cm):", value=float(curr_p["ancho"]), key="e_p_a")
                t_p_e = col_pe1.number_input("Nuevo Tiempo (min):", value=float(curr_p["tiempo"]), key="e_p_t")
                
                m_list = list(precios_materiales.keys())
                m_idx = m_list.index(curr_p["material"]) if curr_p["material"] in m_list else 0
                m_p_e = col_pe2.selectbox("Nuevo Material default:", m_list, index=m_idx, key="e_p_m")
                
                foto_up_e = st.file_uploader("Reemplazar Imagen (opcional):", type=["jpg", "png", "jpeg"], key="e_p_f")

                if st.button("✏️ Guardar Cambios del Producto", type="primary"):
                    foto_url_e = curr_p["foto"]
                    if foto_up_e:
                        file_ext = foto_up_e.name.split(".")[-1]
                        file_path = f"{p_edit_sel.strip().lower().replace(' ', '_')}.{file_ext}"
                        file_bytes = foto_up_e.getvalue()
                        supabase.storage.from_("productos_img").upload(file_path, file_bytes, {"content-type": foto_up_e.type, "x-upsert": "true"})
                        foto_url_e = supabase.storage.from_("productos_img").get_public_url(file_path)

                    supabase.table("catalogo").update({
                        "largo": l_p_e, "ancho": a_p_e, "tiempo": t_p_e, 
                        "material": m_p_e, "foto_url": foto_url_e
                    }).eq("nombre", p_edit_sel).execute()

                    st.toast(f"Producto '{p_edit_sel}' actualizado", icon="📝")
                    st.success(f"✅ Se actualizaron las especificaciones de '{p_edit_sel}'.")
                    st.rerun()
            else:
                st.info("No hay productos registrados para editar.")

        with subtab_p_del:
            prods_del = [p for p in CATALOGO.keys() if p != "Personalizado (Medida Libre)"]
            if prods_del:
                p_del = st.selectbox("Selecciona producto a eliminar:", prods_del, key="sel_p_del")
                st.warning("⚠️ Esta acción eliminará el producto del catálogo.")
                if st.button("🗑️ Eliminar Producto Definitivamente", type="primary"):
                    supabase.table("catalogo").delete().eq("nombre", p_del).execute()
                    st.toast(f"Producto '{p_del}' eliminado", icon="🗑️")
                    st.success(f"✅ Producto '{p_del}' eliminado del catálogo.")
                    st.rerun()
            else:
                st.info("No hay productos disponibles para eliminar.")
