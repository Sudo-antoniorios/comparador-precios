"""Comparador de precios CSV vs Amazon.

Sube un CSV, extrae nombre / EAN / precio, busca cada EAN en Amazon.es
y genera un PDF descargable con la comparativa.
"""

import io
import re
import time

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from amazon_scraper import buscar_precio_amazon

st.set_page_config(page_title="Comparador de Precios", page_icon="🛒", layout="centered")


# --------------------------------------------------------------------------
# Utilidades de procesamiento del CSV
# --------------------------------------------------------------------------
def detectar_columna(columnas, claves):
    """Devuelve el nombre de la primera columna cuyo texto contiene una clave."""
    for col in columnas:
        normal = str(col).strip().lower()
        for clave in claves:
            if clave in normal:
                return col
    return None


def limpiar_ean(valor):
    """Quita el prefijo 'EAN:' y cualquier carácter no numérico.

    Devuelve '' si no queda ningún dígito (fila a ignorar).
    """
    if valor is None:
        return ""
    texto = str(valor).strip()
    if texto.lower() in ("nan", "none", ""):
        return ""
    solo_digitos = re.sub(r"\D", "", texto)
    return solo_digitos


def leer_csv(archivo):
    """Lee el CSV probando varios separadores y codificaciones habituales."""
    contenido = archivo.getvalue()
    ultimo_error = None
    for sep in (",", ";", "\t"):
        for enc in ("utf-8-sig", "latin-1"):
            try:
                df = pd.read_csv(io.BytesIO(contenido), sep=sep, encoding=enc, dtype=str)
                if df.shape[1] >= 2:
                    return df
            except Exception as exc:  # noqa: BLE001
                ultimo_error = exc
    raise ValueError(f"No se pudo leer el CSV: {ultimo_error}")


def procesar_dataframe(df):
    """Extrae y limpia las columnas nombre / EAN / precio."""
    col_nombre = detectar_columna(df.columns, ["nombre", "name", "producto", "descrip", "title"])
    col_ean = detectar_columna(df.columns, ["ean", "codigo", "código", "barcode", "gtin"])
    col_precio = detectar_columna(df.columns, ["precio", "price", "pvp", "importe", "coste"])

    if col_ean is None:
        raise ValueError(
            "No se encontró una columna de EAN. "
            f"Columnas detectadas: {list(df.columns)}"
        )

    filas = []
    for _, fila in df.iterrows():
        ean = limpiar_ean(fila.get(col_ean))
        if not ean:
            continue  # Se ignoran las filas sin EAN.
        nombre = str(fila.get(col_nombre, "")).strip() if col_nombre else ""
        if nombre.lower() in ("nan", "none"):
            nombre = ""
        precio = str(fila.get(col_precio, "")).strip() if col_precio else ""
        if precio.lower() in ("nan", "none"):
            precio = ""
        filas.append({
            "EAN": ean,
            "Nombre del Producto": nombre or "(sin nombre)",
            "Precio en CSV": precio or "-",
        })

    resultado = pd.DataFrame(filas)
    return resultado, (col_nombre, col_ean, col_precio)


# --------------------------------------------------------------------------
# Generación del PDF
# --------------------------------------------------------------------------
def generar_pdf(df):
    """Construye un PDF en memoria con la tabla comparativa."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    estilos = getSampleStyleSheet()
    celda = estilos["BodyText"]
    celda.fontSize = 8
    celda.leading = 10
    cabecera = estilos["BodyText"].clone("cab")
    cabecera.fontSize = 8
    cabecera.leading = 10
    cabecera.textColor = colors.white

    elementos = [
        Paragraph("Comparativa de Precios: CSV vs Amazon", estilos["Title"]),
        Paragraph(
            time.strftime("Generado el %d/%m/%Y a las %H:%M"),
            estilos["Normal"],
        ),
        Spacer(1, 8 * mm),
    ]

    columnas = ["EAN", "Nombre del Producto", "Precio en CSV", "Precio en Amazon"]
    datos = [[Paragraph(f"<b>{c}</b>", cabecera) for c in columnas]]
    for _, fila in df.iterrows():
        datos.append([
            Paragraph(str(fila["EAN"]), celda),
            Paragraph(str(fila["Nombre del Producto"]), celda),
            Paragraph(str(fila["Precio en CSV"]), celda),
            Paragraph(str(fila["Precio en Amazon"]), celda),
        ])

    tabla = Table(datos, colWidths=[32 * mm, 70 * mm, 30 * mm, 38 * mm], repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#232F3E")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elementos.append(tabla)

    doc.build(elementos)
    buffer.seek(0)
    return buffer


# --------------------------------------------------------------------------
# Interfaz Streamlit
# --------------------------------------------------------------------------
st.title("🛒 Comparador de Precios")
st.caption("Sube un CSV con productos y compara sus precios contra Amazon.es")

archivo = st.file_uploader("Sube tu archivo CSV", type=["csv"])

if archivo is not None:
    try:
        df_bruto = leer_csv(archivo)
        df_proc, cols = procesar_dataframe(df_bruto)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Error al procesar el CSV: {exc}")
        st.stop()

    if df_proc.empty:
        st.warning("No se encontró ninguna fila con EAN válido en el archivo.")
        st.stop()

    st.success(
        f"Se detectaron {len(df_proc)} productos con EAN válido. "
        f"(Columnas usadas → nombre: {cols[0]}, EAN: {cols[1]}, precio: {cols[2]})"
    )
    st.dataframe(df_proc, use_container_width=True)

    if st.button("🔍 Buscar precios en Amazon", type="primary"):
        precios_amazon = []
        barra = st.progress(0.0, text="Iniciando búsqueda...")
        total = len(df_proc)

        for i, (_, fila) in enumerate(df_proc.iterrows()):
            ean = fila["EAN"]
            barra.progress((i) / total, text=f"Buscando EAN {ean} ({i + 1}/{total})")
            precio = buscar_precio_amazon(ean)
            precios_amazon.append(precio)
            time.sleep(1.0)  # Pausa para no saturar a Amazon.

        barra.progress(1.0, text="Búsqueda completada")

        df_final = df_proc.copy()
        df_final["Precio en Amazon"] = precios_amazon

        st.subheader("Resultado de la comparativa")
        st.dataframe(df_final, use_container_width=True)

        encontrados = sum(
            1 for p in precios_amazon if p not in ("No encontrado",) and "bloque" not in p.lower()
        )
        st.info(f"Precios encontrados en Amazon: {encontrados} de {total}")

        pdf = generar_pdf(df_final)
        st.download_button(
            label="📄 Descargar PDF con la comparativa",
            data=pdf,
            file_name="comparativa_precios.pdf",
            mime="application/pdf",
            type="primary",
        )
else:
    st.info("Esperando a que subas un archivo CSV...")

with st.expander("ℹ️ Notas sobre el scraping de Amazon"):
    st.markdown(
        "- Amazon tiene sistemas anti-bot agresivos. Si bloquea las peticiones "
        "(error 503 / captcha), el precio aparecerá como **No encontrado** o "
        "**Amazon bloqueó la petición** en lugar de romper la app.\n"
        "- Para un uso intensivo y fiable conviene una API especializada "
        "(Rainforest API, ScrapingBee, etc.).\n"
        "- Ejecutándola en local suele funcionar mejor que en servidores "
        "gratuitos, cuyas IPs suelen estar ya bloqueadas."
    )
