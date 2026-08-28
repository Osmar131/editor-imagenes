from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import Response
import cv2
import numpy as np
from PIL import Image
import io
import math

app = FastAPI(title="Editor de Imágenes API", version="2.0")

# ========== FUNCIÓN AUXILIAR CORREGIDA ==========
async def leer_imagen(file):
    """Lee una imagen subida y la convierte a BGR (OpenCV)"""
    img_bytes = await file.read()  # ✅ await
    img_pil = Image.open(io.BytesIO(img_bytes))
    img_rgb = np.array(img_pil)
    if img_rgb.shape[-1] == 4:
        img_rgb = img_rgb[:, :, :3]
    return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

def imagen_a_bytes(img_bgr):
    """Convierte una imagen BGR a bytes PNG"""
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    img_pil = Image.fromarray(img_rgb.astype(np.uint8))
    buf = io.BytesIO()
    img_pil.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

# ========== ENDPOINTS (todos con await en leer_imagen) ==========

@app.post("/ecualizar")
async def ecualizar_imagen(file: UploadFile = File(...), modo: str = Form("color")):
    img = await leer_imagen(file)
    if modo == "gris":
        gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        res = cv2.equalizeHist(gris)
        res = cv2.cvtColor(res, cv2.COLOR_GRAY2BGR)
    elif modo == "clahe":
        gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        res = clahe.apply(gris)
        res = cv2.cvtColor(res, cv2.COLOR_GRAY2BGR)
    else:
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l_eq = cv2.equalizeHist(l)
        lab_eq = cv2.merge((l_eq, a, b))
        res = cv2.cvtColor(lab_eq, cv2.COLOR_LAB2BGR)
    return Response(content=imagen_a_bytes(res), media_type="image/png")

@app.post("/suavizar")
async def suavizar_imagen(
    file: UploadFile = File(...),
    tipo: str = Form("gaussian"),
    ksize: int = Form(5)
):
    img = await leer_imagen(file)
    if tipo == "gaussian":
        res = cv2.GaussianBlur(img, (ksize, ksize), 0)
    elif tipo == "median":
        res = cv2.medianBlur(img, ksize)
    elif tipo == "average":
        res = cv2.blur(img, (ksize, ksize))
    else:
        res = img
    return Response(content=imagen_a_bytes(res), media_type="image/png")

@app.post("/convolucion")
async def convolucion_imagen(
    file: UploadFile = File(...),
    kernel: str = Form("sharpen")
):
    img = await leer_imagen(file)
    kernels = {
        "sharpen": np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]]),
        "edge": np.array([[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]]),
        "emboss": np.array([[-2, -1, 0], [-1, 1, 1], [0, 1, 2]]),
        "blur": np.ones((3,3), np.float32) / 9,
        "identity": np.array([[0, 0, 0], [0, 1, 0], [0, 0, 0]])
    }
    k = kernels.get(kernel, kernels["identity"])
    res = cv2.filter2D(img, -1, k)
    return Response(content=imagen_a_bytes(res), media_type="image/png")

@app.post("/binarizar")
async def binarizar_imagen(
    file: UploadFile = File(...),
    metodo: str = Form("otsu"),
    umbral: int = Form(128),
    block_size: int = Form(11),
    c: int = Form(2)
):
    img = await leer_imagen(file)
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if metodo == "otsu":
        _, res = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif metodo == "adaptive":
        res = cv2.adaptiveThreshold(gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY, block_size, c)
    else:  # manual
        _, res = cv2.threshold(gris, umbral, 255, cv2.THRESH_BINARY)
    res = cv2.cvtColor(res, cv2.COLOR_GRAY2BGR)
    return Response(content=imagen_a_bytes(res), media_type="image/png")

@app.post("/geometric")
async def geometric_imagen(
    file: UploadFile = File(...),
    operacion: str = Form("rotate"),
    angle: float = Form(0.0),
    scale: float = Form(1.0),
    width: int = Form(0),
    height: int = Form(0),
    x: int = Form(0),
    y: int = Form(0),
    crop_w: int = Form(0),
    crop_h: int = Form(0)
):
    img = await leer_imagen(file)
    h, w = img.shape[:2]
    
    if operacion == "rotate":
        centro = (w//2, h//2)
        M = cv2.getRotationMatrix2D(centro, angle, scale)
        cos = abs(M[0,0])
        sin = abs(M[0,1])
        nuevo_w = int((h * sin) + (w * cos))
        nuevo_h = int((h * cos) + (w * sin))
        M[0,2] += (nuevo_w/2) - centro[0]
        M[1,2] += (nuevo_h/2) - centro[1]
        res = cv2.warpAffine(img, M, (nuevo_w, nuevo_h))
    elif operacion == "resize":
        if width == 0 or height == 0:
            nuevo_w = int(w * scale)
            nuevo_h = int(h * scale)
        else:
            nuevo_w = width
            nuevo_h = height
        res = cv2.resize(img, (nuevo_w, nuevo_h))
    elif operacion == "crop":
        x = max(0, min(x, w-1))
        y = max(0, min(y, h-1))
        crop_w = min(crop_w, w - x)
        crop_h = min(crop_h, h - y)
        if crop_w <= 0 or crop_h <= 0:
            res = img
        else:
            res = img[y:y+crop_h, x:x+crop_w]
    else:
        res = img
    return Response(content=imagen_a_bytes(res), media_type="image/png")

### sección imagenfusionadacentral.py
from composicion import procesar_composicion_bytes  # al inicio

@app.post("/componer")
async def componer_imagenes(
    img_sup: UploadFile = File(...),
    img_inf: UploadFile = File(...),
    img_incrustar: UploadFile = File(...),
    porcentaje_fusion: float = Form(10),
    curva_fusion: str = Form("lineal"),
    factor_ampliacion: float = Form(2.0),
    region_tipo: str = Form("central_superior_derecha"),
    x_region: int = Form(0),
    y_region: int = Form(0),
    ancho_region: int = Form(100),
    alto_region: int = Form(100),
    tamaño_ancho_incrustacion: int = Form(25),
    tamaño_alto_incrustacion: int = Form(None),
    posicion_incrustacion: str = Form("derecha_centro"),
    fusion_superior: int = Form(30),
    fusion_inferior: int = Form(30),
    fusion_izquierda: int = Form(30),
    fusion_derecha: int = Form(30),
    margen: int = Form(20),
    radio_difuminado: int = Form(50),
    hacer_cuadrada: bool = Form(True)
):
    # Leer todas las imágenes
    img_sup_bytes = await img_sup.read()
    img_inf_bytes = await img_inf.read()
    img_incrustar_bytes = await img_incrustar.read()
    
    # Procesar
    resultado_bytes = procesar_composicion_bytes(
        img_sup_bytes, img_inf_bytes, img_incrustar_bytes,
        porcentaje_fusion, curva_fusion,
        factor_ampliacion, region_tipo,
        x_region, y_region, ancho_region, alto_region,
        tamaño_ancho_incrustacion, tamaño_alto_incrustacion,
        posicion_incrustacion,
        fusion_superior, fusion_inferior,
        fusion_izquierda, fusion_derecha,
        margen, radio_difuminado,
        hacer_cuadrada
    )
    return Response(content=resultado_bytes, media_type="image/png")

@app.get("/healthz")
async def health_check():
    return {"status": "ok", "message": "Backend funcionando"}
