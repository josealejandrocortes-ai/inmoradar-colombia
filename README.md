# 🏙️ InmoRadar Colombia — Plataforma de Inversión Inmobiliaria

Plataforma inteligente de monitoreo, valoración y detección de oportunidades de inversión inmobiliaria en Colombia (Bogotá, Medellín, Cali, Barranquilla y Cartagena), con análisis financiero adaptado al mercado colombiano (Yield Bruto/Neto, Estrato socioeconómico 1 a 6, gastos notariales y de registro del 2.71%, y plusvalía estimada vs mediana del sector).

---

## 🚀 Despliegue Gratuito en la Nube (Sin Costo)

Tienes **dos opciones gratuitas excelentes** para poner a correr la aplicación en la nube:

### 🌟 Opción 1: Despliegue Completo en Render.com (Recomendado)
*Ejecuta tanto el backend en Python FastAPI como el frontend con todas las funciones de API y escaneo.*

1. **Sube este proyecto a tu GitHub:**
   - Crea un repositorio nuevo en [github.com/new](https://github.com/new) llamado `inmoradar-colombia`.
   - Sube los archivos del proyecto (puedes arrastrar el contenido o usar Git).
2. **Conéctalo a Render:**
   - Entra a [render.com](https://render.com) y regístrate gratis con tu cuenta de GitHub.
   - Haz clic en **New +** > **Web Service**.
   - Selecciona tu repositorio `inmoradar-colombia`.
   - Render detectará automáticamente el archivo `render.yaml` y la configuración:
     - **Runtime:** `Python 3`
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
     - **Plan:** `Free ($0/mes)`
   - Haz clic en **Create Web Service**.
3. **¡Listo!** En unos minutos tendrás tu URL pública HTTPS gratuita:
   `https://inmoradar-colombia.onrender.com`

---

### 🌐 Opción 2: Despliegue Inmediato en GitHub Pages (Solo Frontend)
*Si solo quieres una página web estática accesible al instante desde cualquier celular o PC sin configurar servidores.*

1. Sube los archivos a tu repositorio en GitHub.
2. En tu repositorio de GitHub, entra a **Settings** > **Pages** (en el menú lateral izquierdo).
3. En **Build and deployment > Branch**, selecciona:
   - Rama: `main`
   - Carpeta: `/ (root)`
4. Haz clic en **Save**.
5. En 60 segundos tendrás tu enlace público 100% gratuito:
   `https://<tu-usuario>.github.io/inmoradar-colombia/`

*(El frontend incluye el catálogo auditado de 9 propiedades colombianas reales y toda la lógica de filtrado, cálculo de rendimientos y simulación financiera en el navegador).*

---

## 💻 Ejecución Local en tu Computador

Si deseas ejecutar la aplicación en tu máquina local:

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Iniciar el servidor
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
O simplemente haz doble clic en el archivo `iniciar_app.bat`.

---

## 📁 Estructura del Proyecto

```text
├── index.html                   # Página principal para GitHub Pages
├── requirements.txt             # Dependencias Python (FastAPI, Uvicorn, Pydantic, HTTPX)
├── render.yaml                  # Configuración 1-clic para Render.com
├── Procfile                     # Comando de arranque para servidores cloud
├── Dockerfile                   # Contenedor para Hugging Face Spaces / Railway / Fly.io
├── vercel.json                  # Configuración serverless para Vercel
├── backend/
│   ├── main.py                  # API FastAPI y servidor de rutas
│   ├── models.py                # Modelos de datos colombianos (estrato, moneda COP)
│   ├── opportunity_engine.py    # Motor de cálculo de Cap Rate, Yield y Scores
│   ├── deduplication.py         # Motor de arbitraje entre portales
│   └── scrapers/
│       └── scanner_service.py   # Servicio de rastreo y verificación JSON-LD
├── data/
│   ├── sample_opportunities.json        # Base canónica de inmuebles verificados
│   └── colombia_market_benchmarks.json  # Precios medianos por m² y arriendo
└── frontend/
    └── index.html               # Dashboard interactivo con Tailwind CSS
```

---

## 📄 Licencia
Proyecto de código abierto bajo licencia MIT.
