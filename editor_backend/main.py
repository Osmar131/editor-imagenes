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

@app.post("/componer")
async def componer_imagenes(
    fondo: UploadFile = File(...),
    img1: UploadFile = File(...),
    img2: UploadFile = File(...),
    x1: int = Form(0),
    y1: int = Form(0),
    x2: int = Form(0),
    y2: int = Form(0),
    escala1: float = Form(1.0),
    escala2: float = Form(1.0),
    opacidad1: float = Form(1.0),
    opacidad2: float = Form(1.0),
    modo: str = Form("horizontal")  # "horizontal", "vertical", "superponer"
):
    # Leer imágenes
    fondo_img = await leer_imagen(fondo)
    img1_img = await leer_imagen(img1)
    img2_img = await leer_imagen(img2)
    
    # Si el modo es horizontal o vertical, simplemente concatenar
    if modo == "horizontal":
        # Redimensionar para que tengan la misma altura
        h1, w1 = img1_img.shape[:2]
        h2, w2 = img2_img.shape[:2]
        h = min(h1, h2)
        if h1 != h:
            img1_img = cv2.resize(img1_img, (int(w1*h/h1), h))
        if h2 != h:
            img2_img = cv2.resize(img2_img, (int(w2*h/h2), h))
        # Concatenar lado a lado
        res = np.hstack((img1_img, img2_img))
    
    elif modo == "vertical":
        # Redimensionar para que tengan el mismo ancho
        h1, w1 = img1_img.shape[:2]
        h2, w2 = img2_img.shape[:2]
        w = min(w1, w2)
        if w1 != w:
            img1_img = cv2.resize(img1_img, (w, int(h1*w/w1)))
        if w2 != w:
            img2_img = cv2.resize(img2_img, (w, int(h2*w/w2)))
        # Concatenar una encima de la otra
        res = np.vstack((img1_img, img2_img))
    
    else:  # superponer (con posiciones personalizadas)
        # Escalar imágenes si es necesario
        if escala1 != 1.0:
            h, w = img1_img.shape[:2]
            nuevo = (int(w*escala1), int(h*escala1))
            img1_img = cv2.resize(img1_img, nuevo)
        if escala2 != 1.0:
            h, w = img2_img.shape[:2]
            nuevo = (int(w*escala2), int(h*escala2))
            img2_img = cv2.resize(img2_img, nuevo)
        
        # Copiar fondo para no modificarlo directamente
        res = fondo_img.copy()
        h_fondo, w_fondo = res.shape[:2]
        
        # Superponer img1 en (x1, y1)
        h1, w1 = img1_img.shape[:2]
        if x1 + w1 <= w_fondo and y1 + h1 <= h_fondo:
            roi = res[y1:y1+h1, x1:x1+w1]
            if opacidad1 < 1.0:
                cv2.addWeighted(img1_img, opacidad1, roi, 1-opacidad1, 0, roi)
            else:
                res[y1:y1+h1, x1:x1+w1] = img1_img
        
        # Superponer img2 en (x2, y2)
        h2, w2 = img2_img.shape[:2]
        if x2 + w2 <= w_fondo and y2 + h2 <= h_fondo:
            roi = res[y2:y2+h2, x2:x2+w2]
            if opacidad2 < 1.0:
                cv2.addWeighted(img2_img, opacidad2, roi, 1-opacidad2, 0, roi)
            else:
                res[y2:y2+h2, x2:x2+w2] = img2_img
    
    return Response(content=imagen_a_bytes(res), media_type="image/png")
