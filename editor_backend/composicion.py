import cv2
import numpy as np
from PIL import Image, ImageFilter
import io

def leer_imagen_desde_bytes(img_bytes):
    """Convierte bytes de imagen a array RGB (PIL)"""
    img_pil = Image.open(io.BytesIO(img_bytes)).convert('RGB')
    return np.array(img_pil)

def imagen_bytes_a_pil(img_bytes):
    """Convierte bytes a imagen PIL"""
    return Image.open(io.BytesIO(img_bytes)).convert('RGB')

def concatenar_con_fusion(img_sup_bytes, img_inf_bytes, porcentaje_fusion=10, curva='lineal'):
    """
    Concatena dos imágenes verticalmente con fusión de píxeles
    Retorna array RGB
    """
    img_sup = Image.open(io.BytesIO(img_sup_bytes)).convert('RGB')
    img_inf = Image.open(io.BytesIO(img_inf_bytes)).convert('RGB')
    
    # Ajustar ancho
    ancho_objetivo = img_inf.width
    nuevo_alto = int(img_sup.height * (ancho_objetivo / img_sup.width))
    img_sup = img_sup.resize((ancho_objetivo, nuevo_alto), Image.LANCZOS)
    
    # Calcular zona de fusión
    alto_fusion = int(img_sup.height * (porcentaje_fusion / 100))
    
    # Extraer zonas de fusión
    zona_fusion_sup = np.array(img_sup.crop((0, img_sup.height - alto_fusion, 
                                             img_sup.width, img_sup.height)))
    zona_fusion_inf = np.array(img_inf.crop((0, 0, img_inf.width, alto_fusion)))
    
    # Crear curva de fusión
    x = np.linspace(0, 1, alto_fusion)
    if curva == 'lineal':
        alpha = x
    elif curva == 'suave':
        alpha = 1 / (1 + np.exp(-10 * (x - 0.5)))
    elif curva == 'exponencial':
        alpha = x ** 2
    elif curva == 'logaritmica':
        alpha = np.sqrt(x)
    else:
        alpha = x
    alpha = alpha.reshape(alto_fusion, 1, 1)
    
    # Aplicar fusión
    zona_fusion = (zona_fusion_sup * (1 - alpha) + zona_fusion_inf * alpha).astype(np.uint8)
    
    # Construir imagen final
    parte_superior = np.array(img_sup.crop((0, 0, img_sup.width, img_sup.height - alto_fusion)))
    parte_inferior = np.array(img_inf.crop((0, alto_fusion, img_inf.width, img_inf.height)))
    
    imagen_concatenada = np.vstack([parte_superior, zona_fusion, parte_inferior])
    return imagen_concatenada

def extraer_region_ampliada(img_bytes, factor_ampliacion=2.0, 
                            region_tipo='central_superior_derecha',
                            x=None, y=None, ancho=None, alto=None):
    """
    Extrae una región de la imagen y la amplía.
    region_tipo: 'central_superior_derecha' o 'personalizada'
    Si es personalizada, se usan x, y, ancho, alto.
    """
    img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
    img_array = np.array(img)
    alto_img, ancho_img = img_array.shape[:2]
    
    if region_tipo == 'central_superior_derecha':
        # Región del 25% del tamaño en el cuadrante superior derecho, centrado
        ancho_region = ancho_img // 4
        alto_region = alto_img // 4
        x_inicio = ancho_img - ancho_region - (ancho_img // 8)
        y_inicio = alto_img // 4 - alto_region // 2
        # Ajustar límites
        x_inicio = max(0, min(x_inicio, ancho_img - ancho_region))
        y_inicio = max(0, min(y_inicio, alto_img - alto_region))
    else:  # personalizada
        x_inicio = max(0, min(x, ancho_img - 1))
        y_inicio = max(0, min(y, alto_img - 1))
        ancho_region = min(ancho, ancho_img - x_inicio)
        alto_region = min(alto, alto_img - y_inicio)
        if ancho_region <= 0 or alto_region <= 0:
            raise ValueError("Región inválida")
    
    region = img_array[y_inicio:y_inicio+alto_region, x_inicio:x_inicio+ancho_region]
    # Ampliar
    nuevo_ancho = int(ancho_region * factor_ampliacion)
    nuevo_alto = int(alto_region * factor_ampliacion)
    region_pil = Image.fromarray(region)
    region_ampliada = region_pil.resize((nuevo_ancho, nuevo_alto), Image.LANCZOS)
    return np.array(region_ampliada)

def incrustar_con_fusion(imagen_base_array, imagen_incrustar_array,
                         tamaño_ancho_porcentaje=25,
                         tamaño_alto_porcentaje=None,
                         posicion='derecha_centro',
                         fusion_superior=30,
                         fusion_inferior=30,
                         fusion_izquierda=30,
                         fusion_derecha=30,
                         margen=20):
    """
    Incrusta una imagen sobre la base con fusión ajustable.
    """
    alto_base, ancho_base = imagen_base_array.shape[:2]
    alto_inc, ancho_inc = imagen_incrustar_array.shape[:2]
    
    # Calcular nuevo tamaño
    nuevo_ancho = int(ancho_base * (tamaño_ancho_porcentaje / 100))
    if tamaño_alto_porcentaje is None:
        nuevo_alto = int(alto_inc * (nuevo_ancho / ancho_inc))
    else:
        nuevo_alto = int(alto_base * (tamaño_alto_porcentaje / 100))
    
    img_incrustar_pil = Image.fromarray(imagen_incrustar_array)
    img_incrustar_redim = img_incrustar_pil.resize((nuevo_ancho, nuevo_alto), Image.LANCZOS)
    img_incrustar_array = np.array(img_incrustar_redim)
    
    alto_inc, ancho_inc = img_incrustar_array.shape[:2]
    
    # Calcular posición
    if posicion == 'derecha_centro':
        x = ancho_base - ancho_inc - margen
        y = (alto_base - alto_inc) // 2
    elif posicion == 'derecha_arriba':
        x = ancho_base - ancho_inc - margen
        y = alto_base // 4 - alto_inc // 2
    elif posicion == 'derecha_abajo':
        x = ancho_base - ancho_inc - margen
        y = 3 * alto_base // 4 - alto_inc // 2
    elif posicion == 'esquina_superior_derecha':
        x = ancho_base - ancho_inc - margen
        y = margen
    elif posicion == 'esquina_inferior_derecha':
        x = ancho_base - ancho_inc - margen
        y = alto_base - alto_inc - margen
    # NUEVAS POSICIONES
    elif posicion == 'centro_centro':
        x = (ancho_base - ancho_inc) // 2
        y = (alto_base - alto_inc) // 2
    elif posicion == 'centro_arriba':
        x = (ancho_base - ancho_inc) // 2
        y = margen
    elif posicion == 'centro_abajo':
        x = (ancho_base - ancho_inc) // 2
        y = alto_base - alto_inc - margen
    elif posicion == 'izquierda_centro':
        x = margen
        y = (alto_base - alto_inc) // 2
    elif posicion == 'izquierda_arriba':
        x = margen
        y = margen
    elif posicion == 'esquina_superior_izquierda':
        x = margen
        y = margen
    elif posicion == 'esquina_inferior_izquierda':
        x = margen
        y = alto_base - alto_inc - margen
    else:
        # fallback
        x = ancho_base - ancho_inc - margen
        y = (alto_base - alto_inc) // 2
    
    # Convertir porcentajes a píxeles
    fusion_sup_px = int(alto_inc * (fusion_superior / 100))
    fusion_inf_px = int(alto_inc * (fusion_inferior / 100))
    fusion_izq_px = int(ancho_inc * (fusion_izquierda / 100))
    fusion_der_px = int(ancho_inc * (fusion_derecha / 100))
    
    # Crear máscara de fusión
    mascara_fusion = np.ones((alto_inc, ancho_inc))
    
    # Borde superior
    for i in range(min(fusion_sup_px, alto_inc)):
        progreso = i / fusion_sup_px if fusion_sup_px > 0 else 1
        mascara_fusion[i, :] *= progreso
    # Borde inferior
    for i in range(alto_inc - fusion_inf_px, alto_inc):
        if i >= 0 and fusion_inf_px > 0:
            progreso = (alto_inc - i - 1) / fusion_inf_px
            mascara_fusion[i, :] *= progreso
    # Borde izquierdo
    for j in range(min(fusion_izq_px, ancho_inc)):
        progreso = j / fusion_izq_px if fusion_izq_px > 0 else 1
        mascara_fusion[:, j] *= progreso
    # Borde derecho
    for j in range(ancho_inc - fusion_der_px, ancho_inc):
        if j >= 0 and fusion_der_px > 0:
            progreso = (ancho_inc - j - 1) / fusion_der_px
            mascara_fusion[:, j] *= progreso
    
    mascara_fusion = np.clip(mascara_fusion, 0, 1)
    
    # Aplicar fusión
    resultado = imagen_base_array.copy()
    for i in range(alto_inc):
        for j in range(ancho_inc):
            img_y, img_x = y + i, x + j
            if 0 <= img_y < alto_base and 0 <= img_x < ancho_base:
                alpha = mascara_fusion[i, j]
                pixel_inc = img_incrustar_array[i, j]
                pixel_base = resultado[img_y, img_x]
                resultado[img_y, img_x] = (pixel_base * (1 - alpha) + 
                                          pixel_inc * alpha).astype(np.uint8)
    return resultado

def hacer_cuadrada_con_fondo(imagen_array, radio_difuminado=50):
    """
    Convierte una imagen a formato cuadrado con fondo difuminado.
    """
    alto, ancho = imagen_array.shape[:2]
    lado = max(alto, ancho)
    
    img_pil = Image.fromarray(imagen_array)
    fondo = img_pil.resize((lado, lado), Image.LANCZOS)
    fondo = fondo.filter(ImageFilter.GaussianBlur(radius=radio_difuminado))
    fondo_array = np.array(fondo)
    
    inicio_y = (lado - alto) // 2
    inicio_x = (lado - ancho) // 2
    fondo_array[inicio_y:inicio_y+alto, inicio_x:inicio_x+ancho] = imagen_array
    
    return fondo_array

def procesar_composicion_bytes(img_sup_bytes, img_inf_bytes, img_incrustar_bytes,
                               porcentaje_fusion=10, curva_fusion='lineal',
                               factor_ampliacion=2.0, region_tipo='central_superior_derecha',
                               x_region=0, y_region=0, ancho_region=100, alto_region=100,
                               tamaño_ancho_incrustacion=25, tamaño_alto_incrustacion=None,
                               posicion_incrustacion='derecha_centro',
                               fusion_superior=30, fusion_inferior=30,
                               fusion_izquierda=30, fusion_derecha=30,
                               margen=20, radio_difuminado=50,
                               hacer_cuadrada=True):
    """
    Función principal que ejecuta todo el flujo de composición.
    Retorna bytes de la imagen final en PNG.
    """
    # Paso 1: Concatenar
    concatenada = concatenar_con_fusion(img_sup_bytes, img_inf_bytes, porcentaje_fusion, curva_fusion)
    
    # Paso 2: Extraer y ampliar región
    region_ampliada = extraer_region_ampliada(img_incrustar_bytes, factor_ampliacion,
                                              region_tipo, x_region, y_region,
                                              ancho_region, alto_region)
    
    # Paso 3: Incrustar
    con_incrustacion = incrustar_con_fusion(concatenada, region_ampliada,
                                            tamaño_ancho_incrustacion,
                                            tamaño_alto_incrustacion,
                                            posicion_incrustacion,
                                            fusion_superior, fusion_inferior,
                                            fusion_izquierda, fusion_derecha,
                                            margen)
    
    # Paso 4: Hacer cuadrada (opcional)
    if hacer_cuadrada:
        final = hacer_cuadrada_con_fondo(con_incrustacion, radio_difuminado)
    else:
        final = con_incrustacion
    
    # Convertir a bytes
    final_pil = Image.fromarray(final.astype(np.uint8))
    buf = io.BytesIO()
    final_pil.save(buf, format='PNG')
    buf.seek(0)
    return buf.getvalue()




