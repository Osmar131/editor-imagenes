# 🎨 Editor de Imágenes Pro

Aplicación de procesamiento de imágenes con Streamlit (frontend) y FastAPI (backend).

## 🚀 Funcionalidades

- Ecualización de histograma (color, gris, CLAHE)
- Suavizado (Gaussiano, Mediana, Promedio)
- Convolución (Sharpen, Edge, Emboss, Blur)
- Binarizado (Otsu, Adaptativo, Manual)
- Operaciones geométricas (Rotar, Redimensionar, Recortar)
- Composición de imágenes (fusión, ampliación de región)

## 🛠️ Tecnologías

- Python 3.11+
- Streamlit
- FastAPI
- OpenCV
- Pillow
- Matplotlib

## 📦 Instalación local

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
