import streamlit as st
import requests
from PIL import Image
import io

st.set_page_config(page_title="Editor de Imágenes Pro", page_icon="🎨", layout="wide")
st.title("🎨 Editor de Imágenes Pro")
st.markdown("Procesa imágenes con filtros tradicionales y operaciones geométricas.")

BACKEND_URL = "http://localhost:8000"

# ========== SIDEBAR CON OPCIONES ==========
st.sidebar.header("⚙️ Configuración")
categoria = st.sidebar.selectbox(
    "Categoría de operación",
    ["Ecualización", "Suavizado", "Convolución", "Binarizado", "Geométrica"]
)

# ========== SUBIR IMAGEN ==========
archivo = st.file_uploader("Elige una imagen...", type=["jpg", "jpeg", "png"])

if archivo is None:
    st.info("👆 Sube una imagen para comenzar.")
    st.stop()

# Cargar imagen original
imagen_original = Image.open(archivo)
st.image(imagen_original, caption="Imagen original", width='stretch')

# ========== CONFIGURACIÓN SEGÚN CATEGORÍA ==========
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

else:  # Geométrica
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

# ========== PROCESAR ==========
if st.button(boton, type="primary"):
    with st.spinner("Procesando..."):
        try:
            # Preparar archivo
            files = {"file": archivo.getvalue()}
            data = params
            
            response = requests.post(f"{BACKEND_URL}{endpoint}", files=files, data=data)
            
            if response.status_code == 200:
                # Mostrar original y resultado lado a lado
                col1, col2 = st.columns(2)
                with col1:
                    st.image(imagen_original, caption="Original", width='stretch')
                with col2:
                    resultado = Image.open(io.BytesIO(response.content))
                    st.image(resultado, caption="Resultado", width='stretch')
                
                # Botón de descarga
                st.download_button(
                    label="📥 Descargar resultado",
                    data=response.content,
                    file_name=f"resultado.png",
                    mime="image/png"
                )
            else:
                st.error(f"Error: {response.status_code} - {response.text}")
        except requests.exceptions.ConnectionError:
            st.error("❌ No se pudo conectar al backend. Asegúrate de que esté corriendo.")
        except Exception as e:
            st.error(f"Error inesperado: {str(e)}")
