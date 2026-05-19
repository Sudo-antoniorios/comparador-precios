# 🛒 Comparador de Precios (CSV vs Amazon)

Aplicación web en Streamlit que sube un CSV, extrae **nombre / EAN / precio**,
busca cada EAN en **Amazon.es** y genera un **PDF descargable** con la comparativa.

## Archivos

| Archivo | Descripción |
|---|---|
| `app.py` | Interfaz Streamlit + lectura de CSV + generación de PDF |
| `amazon_scraper.py` | Búsqueda de precios en Amazon (con manejo de bloqueos 503) |
| `requirements.txt` | Dependencias de Python |
| `ejemplo.csv` | CSV de prueba |
| `iniciar.bat` | Arranca la app en local (http://localhost:8501) |
| `tunel_publico.bat` | Crea un enlace público temporal con Cloudflare |

## Uso en local

Doble clic en **`iniciar.bat`** → abre http://localhost:8501

O por terminal:

```powershell
& "C:\Users\Comet\AppData\Local\Programs\Python\Python312\python.exe" -m streamlit run app.py
```

## Enlace público temporal

Con la app ya corriendo, doble clic en **`tunel_publico.bat`**.
Devuelve una URL `https://....trycloudflare.com` que cualquiera puede abrir.
El enlace deja de funcionar al cerrar esa ventana.

## Cómo funciona el procesamiento del CSV

- Detecta automáticamente las columnas (nombre / EAN / precio) por su nombre.
- Limpia el prefijo `EAN: ` y deja solo los dígitos (`EAN: 8435527828196` → `8435527828196`).
- **Ignora las filas sin EAN.**

## Notas sobre el scraping de Amazon

Amazon bloquea bots de forma agresiva. Si responde con error 503 o captcha,
el precio aparece como **"No encontrado"** o **"Amazon bloqueó la petición"**
en lugar de romper la app. Para uso intensivo y fiable conviene una API
especializada (Rainforest API, ScrapingBee, etc.).

## Despliegue permanente en Streamlit Community Cloud (gratis)

1. Sube esta carpeta a un repositorio de GitHub.
2. Entra en https://share.streamlit.io → *New app*.
3. Selecciona el repo y el archivo `app.py`. Listo.

> ⚠️ El scraping puede fallar en servidores en la nube porque sus IPs suelen
> estar ya bloqueadas por Amazon. En ese caso, ejecutarla en local es lo más fiable.
