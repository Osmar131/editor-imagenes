import streamlit as st
import requests
from PIL import Image
import io
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

st.set_page_config(page_title="Editor de Imágenes Pro", page_icon="🎨", layout="wide")
st.title("🎨 Editor de Imágenes Pro")
st.markdown("Procesa imágenes con filtros tradicionales y operaciones geométricas.")

BACKEND_URL = "http://localhost:8000"

# Diccionario con rutas de imágenes de ejemplo (ajusta los nombres según tus archivos)
imagenes_ejemplo = {
    "Ecualización": "sample_images/ecualizacion_ejemplo.png",
    "Suavizado": "sample_images/suavizado_ejemplo.png",
    "Convolución": "sample_images/convolucion_ejemplo.png",
    "Binarizado": "sample_images/binarizacion_ejemplo.png",
    "Geométrica": "sample_images/geometrica_ejemplo.png",
    # Composición no tiene imagen de ejemplo por defecto (usa 3 imágenes)
}

# ====================================================
# NUEVA FUNCIÓN PARA PREVISUALIZACIÓN CON RECTÁNGULOS
# ====================================================
def dibujar_region_ampliada(img_pil, x, y, w, h, factor):
    """
    Muestra la imagen original con un rectángulo indicando la región a ampliar,
    y la región ampliada al lado.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    
    # Imagen original con rectángulo
    ax1.imshow(img_pil)
    rect = patches.Rectangle((x, y), w, h, linewidth=3, edgecolor='lime', facecolor='none')
    ax1.add_patch(rect)
    ax1.set_title(f"Región seleccionada ({w}x{h})")
    ax1.axis('off')
    
    # Región ampliada
    region = img_pil.crop((x, y, x+w, y+h))
    nuevo_ancho = int(w * factor)
    nuevo_alto = int(h * factor)
    region_ampliada = region.resize((nuevo_ancho, nuevo_alto), Image.LANCZOS)
    ax2.imshow(region_ampliada)
    ax2.set_title(f"Región ampliada x{factor} ({nuevo_ancho}x{nuevo_alto})")
    ax2.axis('off')
    
    plt.tight_layout()
    return fig

def dibujar_previsualizacion(ancho_base, alto_base, 
                             x_inc, y_inc, ancho_inc, alto_inc,
                             x_sup=0, y_sup=0, ancho_sup=0, alto_sup=0,
                             x_inf=0, y_inf=0, ancho_inf=0, alto_inf=0):
    """
    Dibuja un lienzo con rectángulos representando las imágenes.
    - Fondo: rectángulo gris (concatenada)
    - im3: rectángulo rojo (imagen a incrustar)
    - opcional: im1, im2 si se desea
    """
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_xlim(0, ancho_base)
    ax.set_ylim(0, alto_base)
    ax.set_facecolor('#f0f0f0')
    ax.set_aspect('equal')
    
    # Fondo (concatenada)
    fondo_rect = patches.Rectangle((0, 0), ancho_base, alto_base, 
                                   linewidth=2, edgecolor='gray', facecolor='#e0e0e0', alpha=0.5)
    ax.add_patch(fondo_rect)
    ax.text(ancho_base/2, alto_base/2, 'Fondo (concatenada)', 
            color='gray', ha='center', va='center', fontsize=12, alpha=0.7)
    
    # Imagen incrustada (im3)
    inc_rect = patches.Rectangle((x_inc, y_inc), ancho_inc, alto_inc, 
                                 linewidth=3, edgecolor='red', facecolor='none')
    ax.add_patch(inc_rect)
    ax.text(x_inc + ancho_inc/2, y_inc + alto_inc/2, 'im3', 
            color='red', ha='center', va='center', fontsize=12, fontweight='bold')
    
    # Opcional: mostrar im1 e im2 si se desea
    if ancho_sup > 0 and alto_sup > 0:
        sup_rect = patches.Rectangle((x_sup, y_sup), ancho_sup, alto_sup, 
                                     linewidth=2, edgecolor='blue', facecolor='none', linestyle='--')
        ax.add_patch(sup_rect)
        ax.text(x_sup + ancho_sup/2, y_sup + alto_sup/2, 'im1', 
                color='blue', ha='center', va='center', fontsize=10)
    
    if ancho_inf > 0 and alto_inf > 0:
        inf_rect = patches.Rectangle((x_inf, y_inf), ancho_inf, alto_inf, 
                                     linewidth=2, edgecolor='green', facecolor='none', linestyle='--')
        ax.add_patch(inf_rect)
        ax.text(x_inf + ancho_inf/2, y_inf + alto_inf/2, 'im2', 
                color='green', ha='center', va='center', fontsize=10)
    
    ax.invert_yaxis()  # Para que Y=0 sea la parte superior
    plt.axis('off')
    plt.tight_layout()
    return fig

# ====================================================
# SIDEBAR CON OPCIONES
# ====================================================
st.sidebar.header("⚙️ Configuración")
categoria = st.sidebar.selectbox(
    "Categoría de operación",
    ["Ecualización", "Suavizado", "Convolución", "Binarizado", "Geométrica", "Composición"]
)

# ====================================================
# SUBIR IMAGEN (si no es Composición, solo una imagen)
# ====================================================
if categoria != "Composición":
    archivo = st.file_uploader("Elige una imagen...", type=["jpg", "jpeg", "png"])
else:
    # Para Composición, la subida de imágenes se maneja dentro de su bloque
    archivo = None

if categoria != "Composición" and archivo is None:
    st.info("👆 Sube una imagen para comenzar.")
    st.stop()

# ====================================================
# VISUALIZACIÓN EN DOS COLUMNAS (SOLO PARA CATEGORÍAS ≠ COMPOSICIÓN)
# ====================================================
if categoria != "Composición":
    # Cargar imagen original
    imagen_original = Image.open(archivo)
    
    # --- CAMBIO: Dos columnas, original a la izquierda (500px) y placeholder a la derecha ---
    col_orig, col_res = st.columns(2)
    with col_orig:
        st.image(imagen_original, caption="Imagen original", width=500)
    with col_res:
        # Placeholder para el resultado
        placeholder = st.empty()
        placeholder.info("El resultado aparecerá aquí después de procesar.")
    
    # Guardar la imagen original en session_state para usarla en el procesamiento
    st.session_state['imagen_original'] = imagen_original
else:
    # Para Composición, no mostramos esta vista dual; solo mostramos una miniatura de referencia si se sube una imagen (opcional)
    # Pero la subida de imágenes se hace dentro del bloque, así que no hacemos nada aquí.
    pass

# ====================================================
# CONFIGURACIÓN SEGÚN CATEGORÍA (PARÁMETROS)
# ====================================================
params = {}  # Para construir la petición

if categoria == "Ecualización":
    modo = st.selectbox("Tipo", ["Color (LAB)", "Gris", "CLAHE (Adaptativa)"])
    modo_map = {"Color (LAB)": "color", "Gris": "gris", "CLAHE (Adaptativa)": "clahe"}
    endpoint = "/ecualizar"
    params["modo"] = modo_map[modo]
    boton = "Ecualizar"

elif categoria == "Suavizado":
    tipo = st.selectbox("Tipo", ["Gaussiano", "Mediana", "Promedio"])
    ksize = st.slider("Tamaño del kernel (impar)", 3, 15, 5, step=2)
    tipo_map = {"Gaussiano": "gaussian", "Mediana": "median", "Promedio": "average"}
    endpoint = "/suavizar"
    params["tipo"] = tipo_map[tipo]
    params["ksize"] = ksize
    boton = "Suavizar"

elif categoria == "Convolución":
    kernel = st.selectbox("Kernel", ["Sharpen", "Edge Detection", "Emboss", "Blur", "Identity"])
    kernel_map = {
        "Sharpen": "sharpen",
        "Edge Detection": "edge",
        "Emboss": "emboss",
        "Blur": "blur",
        "Identity": "identity"
    }
    endpoint = "/convolucion"
    params["kernel"] = kernel_map[kernel]
    boton = "Aplicar convolución"

elif categoria == "Binarizado":
    metodo = st.selectbox("Método", ["Otsu", "Adaptativo", "Manual"])
    if metodo == "Manual":
        umbral = st.slider("Umbral", 0, 255, 128)
        params["umbral"] = umbral
    elif metodo == "Adaptativo":
        block_size = st.slider("Tamaño de bloque (impar)", 3, 25, 11, step=2)
        c = st.slider("Constante C", 0, 10, 2)
        params["block_size"] = block_size
        params["c"] = c
    metodo_map = {"Otsu": "otsu", "Adaptativo": "adaptive", "Manual": "manual"}
    endpoint = "/binarizar"
    params["metodo"] = metodo_map[metodo]
    boton = "Binarizar"

elif categoria == "Geométrica":
    operacion = st.selectbox("Operación", ["Rotar", "Redimensionar", "Recortar"])
    if operacion == "Rotar":
        angle = st.slider("Ángulo (°)", -180, 180, 0)
        scale = st.slider("Escala", 0.1, 3.0, 1.0, 0.1)
        endpoint = "/geometric"
        params["operacion"] = "rotate"
        params["angle"] = angle
        params["scale"] = scale
    elif operacion == "Redimensionar":
        escala = st.slider("Escala", 0.1, 3.0, 1.0, 0.1)
        ancho = st.number_input("Ancho (px, 0=automático)", min_value=0, value=0)
        alto = st.number_input("Alto (px, 0=automático)", min_value=0, value=0)
        endpoint = "/geometric"
        params["operacion"] = "resize"
        params["scale"] = escala
        params["width"] = ancho
        params["height"] = alto
    else:  # Recortar
        col1, col2 = st.columns(2)
        with col1:
            x = st.number_input("X (inicio)", min_value=0, value=0)
            y = st.number_input("Y (inicio)", min_value=0, value=0)
        with col2:
            w_crop = st.number_input("Ancho", min_value=1, value=100)
            h_crop = st.number_input("Alto", min_value=1, value=100)
        endpoint = "/geometric"
        params["operacion"] = "crop"
        params["x"] = x
        params["y"] = y
        params["crop_w"] = w_crop
        params["crop_h"] = h_crop
    boton = "Aplicar"

# ====================================================
# BLOQUE DE COMPOSICIÓN (MANEJO PROPIO)
# ====================================================
elif categoria == "Composición":
    # --- CAMBIO: Este bloque ahora tiene su propio botón y no usa el global ---
    st.subheader("📸 Composición de Imágenes")
    
    # Subir tres imágenes
    img_sup = st.file_uploader("Imagen superior", type=["jpg","png"], key="sup")
    img_inf = st.file_uploader("Imagen inferior", type=["jpg","png"], key="inf")
    img_inc = st.file_uploader("Imagen a incrustar", type=["jpg","png"], key="inc")
    
    if img_sup and img_inf and img_inc:
        # Mostrar miniaturas
        col1, col2, col3 = st.columns(3)
        with col1:
            st.image(Image.open(img_sup), caption="Superior", width=100)
        with col2:
            st.image(Image.open(img_inf), caption="Inferior", width=100)
        with col3:
            st.image(Image.open(img_inc), caption="Incrustar", width=100)
        
        # Parámetros de fusión de concatenación
        st.subheader("Fusión de concatenación")
        col1, col2 = st.columns(2)
        with col1:
            porcentaje_fusion = st.slider("Fusión (%)", 0, 50, 10)
            curva_fusion = st.selectbox("Curva", ["lineal", "suave", "exponencial", "logaritmica"])
        with col2:
            pass
        
# ====================================================
# AMPLIACIÓN DE REGIÓN (de la imagen a incrustar)
# ====================================================
# Esta sección permite extraer una subregión de la imagen "img_inc" (la tercera imagen)
# y ampliarla antes de incrustarla sobre la concatenada.
#
# Parámetros:
# - factor_ampliacion: multiplicador del tamaño de la región extraída (ej: 2.0 = doble)
# - region_tipo: 'central_superior_derecha' (predefinida) o 'personalizada' (coordenadas manuales)
#   * 'central_superior_derecha': toma el 25% del tamaño de la imagen en el cuadrante superior derecho, centrado verticalmente.
#   * 'personalizada': usa los valores X, Y, Ancho, Alto que ingresa el usuario.
#
# Flujo:
#   1. Se extrae la región de la imagen original.
#   2. Se redimensiona aplicando factor_ampliacion.
#   3. La región ampliada se usa como la imagen a incrustar (im3).
#
# Esto permite enfatizar un detalle específico de la imagen antes de fusionarla con el fondo.
# ====================================================

# ====================================================
# AMPLIACIÓN DE REGIÓN (de la imagen a incrustar)
# ====================================================
# ====================================================
# AMPLIACIÓN DE REGIÓN (de la imagen a incrustar)
# ====================================================
        st.subheader("Ampliación de región de la imagen a incrustar")

        # Cargar la imagen de incrustación para obtener dimensiones (solo una vez)
        if img_inc and 'img_inc_pil' not in st.session_state:
            st.session_state.img_inc_pil = Image.open(img_inc)
            st.session_state.ancho_img, st.session_state.alto_img = st.session_state.img_inc_pil.size

        if 'img_inc_pil' in st.session_state:
            ancho_img = st.session_state.ancho_img
            alto_img = st.session_state.alto_img
        else:
            ancho_img, alto_img = 1000, 1000  # fallback

        col1, col2 = st.columns(2)
        with col1:
            factor_ampliacion = st.slider("Factor ampliación", 1.0, 5.0, 2.0, 0.1)
            region_tipo = st.selectbox("Tipo región", ["central_superior_derecha", "personalizada", "toda_la_imagen"])
        with col2:
            if region_tipo == "personalizada":
                # Mostrar dimensiones actuales
                st.caption(f"Dimensiones de la imagen: {ancho_img} x {alto_img} px")
                
                # Botón para seleccionar toda la imagen
                if st.button("📐 Seleccionar toda la imagen", key="btn_toda_imagen"):
                    # Actualizar valores en session_state
                    st.session_state.x_region = 0
                    st.session_state.y_region = 0
                    st.session_state.ancho_region = ancho_img
                    st.session_state.alto_region = alto_img
                    # Forzar recarga (no es necesario con st.rerun, pero por si acaso)
                    st.rerun()
                
                col_x, col_y = st.columns(2)
                with col_x:
                    x_region = st.number_input(
                        f"X (0 - {ancho_img-1})",
                        min_value=0,
                        max_value=ancho_img-1,
                        value=st.session_state.get('x_region', 0),
                        key="x_region",
                        step=1
                    )
                    ancho_region = st.number_input(
                        f"Ancho (1 - {ancho_img})",
                        min_value=1,
                        max_value=ancho_img,
                        value=st.session_state.get('ancho_region', ancho_img),
                        key="ancho_region",
                        step=1
                    )
                with col_y:
                    y_region = st.number_input(
                        f"Y (0 - {alto_img-1})",
                        min_value=0,
                        max_value=alto_img-1,
                        value=st.session_state.get('y_region', 0),
                        key="y_region",
                        step=1
                    )
                    alto_region = st.number_input(
                        f"Alto (1 - {alto_img})",
                        min_value=1,
                        max_value=alto_img,
                        value=st.session_state.get('alto_region', alto_img),
                        key="alto_region",
                        step=1
                    )
            elif region_tipo == "toda_la_imagen":
                # Automáticamente selecciona toda la imagen
                x_region = 0
                y_region = 0
                ancho_region = ancho_img
                alto_region = alto_img
                st.success(f"✅ Región: toda la imagen ({ancho_img} x {alto_img} px)")
            else:  # central_superior_derecha
                x_region = y_region = ancho_region = alto_region = 0
                # Para este tipo, se calcula automáticamente más abajo
# ====================================================
# PREVISUALIZACIÓN DE LA REGIÓN SELECCIONADA
# ====================================================

        if 'img_inc_pil' in st.session_state:
            img_inc_pil = st.session_state.img_inc_pil
            ancho_img, alto_img = img_inc_pil.size
            
            if region_tipo == "central_superior_derecha":
                ancho_region_calc = ancho_img // 4
                alto_region_calc = alto_img // 4
                x_reg = ancho_img - ancho_region_calc - (ancho_img // 8)
                y_reg = alto_img // 4 - alto_region_calc // 2
                x_reg = max(0, min(x_reg, ancho_img - ancho_region_calc))
                y_reg = max(0, min(y_reg, alto_img - alto_region_calc))
                w_reg = ancho_region_calc
                h_reg = alto_region_calc
            elif region_tipo == "toda_la_imagen":
                x_reg = 0
                y_reg = 0
                w_reg = ancho_img
                h_reg = alto_img
            else:  # personalizada
                x_reg = x_region
                y_reg = y_region
                w_reg = ancho_region
                h_reg = alto_region
                # Recorte automático si se sale de los límites
                w_reg = min(w_reg, ancho_img - x_reg)
                h_reg = min(h_reg, alto_img - y_reg)
            
            if w_reg > 0 and h_reg > 0:
                fig_region = dibujar_region_ampliada(img_inc_pil, x_reg, y_reg, w_reg, h_reg, factor_ampliacion)
                st.pyplot(fig_region)
            else:
                st.warning("⚠️ La región seleccionada no es válida. Ajusta las coordenadas.")

        # Incrustación
        st.subheader("Incrustación de la región ampliada")
        col1, col2 = st.columns(2)
        with col1:
            tamaño_ancho_incrustacion = st.slider("Ancho incrustación (%)", 5, 80, 25)
            posicion_incrustacion = st.selectbox("Posición", 
    [
        "derecha_centro", "derecha_arriba", "derecha_abajo",
        "esquina_superior_derecha", "esquina_inferior_derecha",
        "centro_centro", "centro_arriba", "centro_abajo",
        "izquierda_centro", "izquierda_arriba",
        "esquina_superior_izquierda", "esquina_inferior_izquierda"
    ])
            margen = st.slider("Margen (px)", 0, 100, 20)
        with col2:
            fusion_superior = st.slider("Fusión superior (%)", 0, 100, 30)
            fusion_inferior = st.slider("Fusión inferior (%)", 0, 100, 30)
            fusion_izquierda = st.slider("Fusión izquierda (%)", 0, 100, 30)
            fusion_derecha = st.slider("Fusión derecha (%)", 0, 100, 30)
        
        # Formato final
        st.subheader("Formato final")
        hacer_cuadrada = st.checkbox("Convertir a cuadrado con fondo difuminado", value=True)
        if hacer_cuadrada:
            radio_difuminado = st.slider("Radio de difuminado del fondo", 10, 100, 50)
        else:
            radio_difuminado = 50

        # ====================================================
        # NUEVO: PREVISUALIZACIÓN CON RECTÁNGULOS (sin backend)
        # ====================================================
        # Calcular tamaño y posición de la imagen incrustada para la previsualización
        ancho_base = 600
        alto_base = 400
        ancho_inc = int(ancho_base * tamaño_ancho_incrustacion / 100)
        # Obtener relación de aspecto de la imagen incrustada si está cargada
        if img_inc:
            img_inc_pil = Image.open(img_inc)
            rel_aspecto = img_inc_pil.height / img_inc_pil.width
            alto_inc = int(ancho_inc * rel_aspecto)
        else:
            alto_inc = ancho_inc  # cuadrado por defecto

        # Calcular posición según posicion_incrustacion y margen
        if posicion_incrustacion == 'derecha_centro':
            x_inc = ancho_base - ancho_inc - margen
            y_inc = (alto_base - alto_inc) // 2
        elif posicion_incrustacion == 'derecha_arriba':
            x_inc = ancho_base - ancho_inc - margen
            y_inc = alto_base // 4 - alto_inc // 2
        elif posicion_incrustacion == 'derecha_abajo':
            x_inc = ancho_base - ancho_inc - margen
            y_inc = 3 * alto_base // 4 - alto_inc // 2
        elif posicion_incrustacion == 'esquina_superior_derecha':
            x_inc = ancho_base - ancho_inc - margen
            y_inc = margen
        elif posicion_incrustacion == 'esquina_inferior_derecha':
            x_inc = ancho_base - ancho_inc - margen
            y_inc = alto_base - alto_inc - margen
        # NUEVAS POSICIONES
        elif posicion_incrustacion == 'centro_centro':
            x_inc = (ancho_base - ancho_inc) // 2
            y_inc = (alto_base - alto_inc) // 2
        elif posicion_incrustacion == 'centro_arriba':
            x_inc = (ancho_base - ancho_inc) // 2
            y_inc = margen
        elif posicion_incrustacion == 'centro_abajo':
            x_inc = (ancho_base - ancho_inc) // 2
            y_inc = alto_base - alto_inc - margen
        elif posicion_incrustacion == 'izquierda_centro':
            x_inc = margen
            y_inc = (alto_base - alto_inc) // 2
        elif posicion_incrustacion == 'izquierda_arriba':
            x_inc = margen
            y_inc = margen
        elif posicion_incrustacion == 'esquina_superior_izquierda':
            x_inc = margen
            y_inc = margen
        elif posicion_incrustacion == 'esquina_inferior_izquierda':
            x_inc = margen
            y_inc = alto_base - alto_inc - margen
        else:
            # fallback
            x_inc = ancho_base - ancho_inc - margen
            y_inc = (alto_base - alto_inc) // 2

        # Dibujar la previsualización
        fig = dibujar_previsualizacion(
            ancho_base, alto_base,
            x_inc, y_inc, ancho_inc, alto_inc
        )
        st.pyplot(fig)
        
        # Botón procesar (con key única)
        if st.button("Componer", type="primary", key="componer_btn"):
            with st.spinner("Procesando..."):
                files = {
                    "img_sup": img_sup.getvalue(),
                    "img_inf": img_inf.getvalue(),
                    "img_incrustar": img_inc.getvalue()
                }
                data = {
                    "porcentaje_fusion": porcentaje_fusion,
                    "curva_fusion": curva_fusion,
                    "factor_ampliacion": factor_ampliacion,
                    "region_tipo": region_tipo,
                    "x_region": x_region,
                    "y_region": y_region,
                    "ancho_region": ancho_region,
                    "alto_region": alto_region,
                    "tamaño_ancho_incrustacion": tamaño_ancho_incrustacion,
                    "tamaño_alto_incrustacion": "",  # se puede omitir en backend
                    "posicion_incrustacion": posicion_incrustacion,
                    "fusion_superior": fusion_superior,
                    "fusion_inferior": fusion_inferior,
                    "fusion_izquierda": fusion_izquierda,
                    "fusion_derecha": fusion_derecha,
                    "margen": margen,
                    "radio_difuminado": radio_difuminado,
                    "hacer_cuadrada": hacer_cuadrada
                }
                response = requests.post(f"{BACKEND_URL}/componer", files=files, data=data)
                
                if response.status_code == 200:
                    resultado = Image.open(io.BytesIO(response.content))
                    st.image(resultado, caption="Resultado", width=500)
                    st.download_button("Descargar", response.content, file_name="composicion.png", mime="image/png", key="descargar_composicion")
                else:
                    st.error(f"Error: {response.status_code}")

# ====================================================
# PROCESAMIENTO GLOBAL (SOLO PARA CATEGORÍAS ≠ COMPOSICIÓN)
# ====================================================

if categoria != "Composición":
    # --- CAMBIO: El botón global ahora tiene key única y usa placeholder ---
    if st.button(boton, type="primary", key="procesar_global"):
        with st.spinner("Procesando..."):
            try:
                # Preparar archivo
                files = {"file": archivo.getvalue()}
                data = params
                
                response = requests.post(f"{BACKEND_URL}{endpoint}", files=files, data=data)
                
                if response.status_code == 200:
                    resultado = Image.open(io.BytesIO(response.content))
                    # Mostrar resultado en el placeholder de la columna derecha
                    placeholder.image(resultado, caption="Resultado", width=500)
                    # Botón de descarga (con key única)
                    st.download_button(
                        label="📥 Descargar resultado",
                        data=response.content,
                        file_name="resultado.png",
                        mime="image/png",
                        key="descargar_global"
                    )
                else:
                    placeholder.error(f"Error: {response.status_code} - {response.text}")
            except requests.exceptions.ConnectionError:
                placeholder.error("❌ No se pudo conectar al backend. Asegúrate de que esté corriendo.")
            except Exception as e:
                placeholder.error(f"Error inesperado: {str(e)}")

# ====================================================
# SECCIÓN EDUCATIVA: EXPLICACIÓN DE CADA FILTRO
# ====================================================
st.divider()
st.subheader("📖 ¿Qué hace cada filtro?")

# Diccionario con descripciones y rutas de imágenes de ejemplo
descripciones = {
    "Ecualización": {
        "desc": "La **ecualización de histograma** mejora el contraste de una imagen al redistribuir los valores de intensidad de los píxeles. Es útil para imágenes con poca luz o bajo contraste.",
        "ejemplo": "sample_images/ecualizacion_ejemplo.png"
    },
    "Suavizado": {
        "desc": "El **suavizado** reduce el ruido y los detalles finos aplicando un filtro de paso bajo. Los tipos más comunes son el **Gaussiano** (difuminado suave), **Mediana** (elimina ruido sal-y-pimienta) y **Promedio** (difuminado uniforme).",
        "ejemplo": "sample_images/suavizado_ejemplo.png"
    },
    "Convolución": {
        "desc": "La **convolución** aplica una máscara (kernel) para realzar o modificar características de la imagen. Por ejemplo, **Sharpen** resalta bordes, **Edge Detection** detecta contornos, **Emboss** da efecto relieve, **Blur** difumina y **Identity** no hace cambios.",
        "ejemplo": "sample_images/convolucion_ejemplo.png"
    },
    "Binarizado": {
        "desc": "El **binarizado** convierte la imagen a blanco y negro (binario) usando un umbral. **Otsu** calcula el umbral automáticamente, **Adaptativo** ajusta el umbral por regiones, y **Manual** permite definir un valor fijo. Ideal para segmentación y análisis de formas.",
        "ejemplo": "sample_images/binarizacion_ejemplo.png"
    },
    "Geométrica": {
        "desc": "Las **operaciones geométricas** modifican la posición o tamaño de la imagen: **Rotar** la gira un ángulo, **Redimensionar** cambia sus dimensiones (escala o píxeles), y **Recortar** extrae una región rectangular.",
        "ejemplo": "sample_images/geometrica_ejemplo.png"
    },
    "Composición": {
        "desc": "La **composición** combina tres imágenes: concatena dos (superior e inferior) con fusión, extrae y amplía una región de la tercera, la incrusta sobre la concatenada con fusión ajustable, y opcionalmente la convierte a formato cuadrado con fondo difuminado.",
        "ejemplo": "sample_images/composicion_ejemplo.png"  # No hay una imagen de ejemplo simple para composición
    }
}

# Mostrar la descripción correspondiente a la categoría actual
if categoria in descripciones:
    info = descripciones[categoria]
    st.markdown(f"**{categoria}**")
    st.markdown(info["desc"])
    
    # Si existe imagen de ejemplo para esta categoría, mostrarla
    if info["ejemplo"] and os.path.exists(info["ejemplo"]):
        img_ejemplo = Image.open(info["ejemplo"])
        st.image(img_ejemplo, caption=f"Ejemplo de {categoria}", width=300)
    else:
        st.caption("ℹ️ No hay imagen de ejemplo para esta categoría.")
else:
    st.caption("ℹ️ Selecciona una categoría para ver su descripción.")
