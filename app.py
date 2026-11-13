"""Atmósfera: condiciones iniciales del GFS en la malla FV3."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import xarray as xr

# ---------------------------------------------------------------------------
VARIABLES = {
    'Temperatura (°C)': ('t', 1, -273.15, 'RdYlBu_r'),
    'Humedad específica (g/kg)': ('sphum', 1000, 0, 'YlGnBu'),
    'Ozono (ppb)': ('o3mr', 6.04e8, 0, 'magma'),
}

LUGARES = {
    'Ciudad de México': (19.43, -99.13),
    'Querétaro': (20.59, -100.39),
    'Monterrey': (25.69, -100.31),
    'Mérida': (20.97, -89.62),
    'Acapulco': (16.85, -99.88),
    'Miami': (25.76, -80.19),
    'Houston': (29.76, -95.37),
}

COLOR_1 = '#1B9AAA'
COLOR_2 = '#EF476F'

plt.style.use('seaborn-v0_8-whitegrid')

# ---------------------------------------------------------------------------
st.set_page_config(
    page_title='Atmósfera · GFS',
    page_icon='🌐',
    layout='wide',
)

st.title('Condiciones iniciales del GFS')
st.caption('Explora temperatura, humedad y ozono sobre el dominio del recorte · malla FV3')


@st.cache_resource
def cargar():
    return xr.open_dataset('gfs_recorte.nc')


ds = cargar()


def convertir(datos, nombre):
    _, factor, suma, _ = VARIABLES[nombre]
    return datos * factor + suma


def punto_mas_cercano(lat, lon):
    lon = lon % 360
    distancia = (ds['geolat'] - lat) ** 2 + (ds['geolon'] - lon) ** 2
    fila, columna = np.unravel_index(np.argmin(distancia.values), distancia.shape)
    return int(fila), int(columna)


def alturas(fila, columna):
    zh = ds['zh'].sel(lat=fila, lon=columna)
    techo = zh.sel(levp=slice(1, 65))
    piso = zh.sel(levp=slice(2, 66))
    return ((techo + piso) / 2 / 1000).values


# ---------------------------------------------------------------------------
with st.sidebar:
    st.header('Controles')
    nombre_var = st.selectbox('Variable', list(VARIABLES))
    st.divider()
    st.caption('Datos: condiciones iniciales del GFS, malla FV3.')

variable, _, _, cmap = VARIABLES[nombre_var]

tab_mapa, tab_perfil, tab_info = st.tabs(['Mapa', 'Perfil vertical', 'Acerca de'])

# ---------------------------- Mapa ----------------------------
with tab_mapa:
    nivel = st.slider(
        'Nivel del modelo',
        min_value=1,
        max_value=64,
        value=64,
        help='64 ≈ superficie; 1 ≈ alta atmósfera',
    )
    campo = convertir(ds[variable].sel(lev=nivel), nombre_var)

    m1, m2, m3 = st.columns(3)
    m1.metric('Mínimo', f'{float(campo.min()):.3g}')
    m2.metric('Promedio', f'{float(campo.mean()):.3g}')
    m3.metric('Máximo', f'{float(campo.max()):.3g}')

    g1, g2 = st.columns([3, 2])
    with g1:
        fig, ax = plt.subplots(figsize=(8, 5))
        campo.plot(
            ax=ax,
            x='geolon',
            y='geolat',
            cmap=cmap,
            cbar_kwargs={'label': nombre_var},
        )
        ax.set_xlabel('Longitud (°)')
        ax.set_ylabel('Latitud (°)')
        ax.set_title(f'{nombre_var} · nivel {nivel}')
        st.pyplot(fig)
        plt.close(fig)

    with g2:
        fig, ax = plt.subplots(figsize=(5, 5))
        campo.plot.hist(ax=ax, bins=40, color=COLOR_1)
        ax.set_xlabel(nombre_var)
        ax.set_ylabel('Número de celdas')
        ax.set_title('Distribución')
        st.pyplot(fig)
        plt.close(fig)

# ----------------------- Perfil vertical -----------------------
with tab_perfil:
    c1, c2, c3 = st.columns(3)
    lugar = c1.selectbox('Lugar', list(LUGARES))
    comparar = c2.selectbox(
        'Comparar con',
        ['Ninguno'] + list(LUGARES),
        index=2,  # otra ciudad por defecto, para ver la diferencia
    )
    altura_max = c3.slider('Altura máxima (km)', min_value=5, max_value=60, value=20)

    elegidos = [lugar] if comparar in ('Ninguno', lugar) else [lugar, comparar]

    # Valor cerca de superficie (nivel 64) para ver que sí cambian
    cols = st.columns(len(elegidos))
    for col, nombre, color in zip(cols, elegidos, [COLOR_1, COLOR_2]):
        fila, columna = punto_mas_cercano(*LUGARES[nombre])
        valor_sup = float(
            convertir(ds[variable].sel(lat=fila, lon=columna, lev=64), nombre_var)
        )
        col.metric(f'{nombre} · superficie', f'{valor_sup:.2f}')

    g1, g2 = st.columns([2, 3])
    with g1:
        fig, ax = plt.subplots(figsize=(5, 6))
        for nombre, color in zip(elegidos, [COLOR_1, COLOR_2]):
            fila, columna = punto_mas_cercano(*LUGARES[nombre])
            perfil = convertir(
                ds[variable].sel(lat=fila, lon=columna, lev=slice(1, 65)),
                nombre_var,
            ).values
            z = alturas(fila, columna)
            ax.plot(perfil, z, color=color, linewidth=2.2, label=nombre)
        ax.set_ylim(0, altura_max)
        ax.set_xlabel(nombre_var)
        ax.set_ylabel('Altura (km)')
        ax.legend(frameon=True, fancybox=False, framealpha=1, edgecolor='#DDDDDD')
        ax.set_title('Perfil vertical')
        st.pyplot(fig)
        plt.close(fig)

    with g2:
        fig, ax = plt.subplots(figsize=(7, 6))
        superficie = convertir(ds[variable].sel(lev=64), nombre_var)
        superficie.plot(
            ax=ax,
            x='geolon',
            y='geolat',
            cmap=cmap,
            cbar_kwargs={'label': f'{nombre_var} en superficie'},
        )
        for nombre, color in zip(elegidos, [COLOR_1, COLOR_2]):
            lat, lon = LUGARES[nombre]
            ax.plot(
                lon % 360,
                lat,
                'o',
                color=color,
                markersize=10,
                markeredgecolor='white',
            )
            ax.annotate(
                nombre,
                (lon % 360, lat),
                textcoords='offset points',
                xytext=(8, 8),
                fontsize=9,
                color=color,
                fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.25', facecolor='white', edgecolor='none', alpha=0.9),
            )
        ax.set_xlabel('Longitud (°)')
        ax.set_ylabel('Latitud (°)')
        ax.set_title(' · '.join(elegidos))
        st.pyplot(fig)
        plt.close(fig)

# -------------------------- Acerca de --------------------------
with tab_info:
    st.markdown(
        """
### Los datos
Condiciones iniciales del modelo **GFS**, interpoladas a la malla del **FV3**.
Cada punto tiene su latitud y longitud en `geolat` y `geolon`.

### Los niveles
Se usan las capas **1 a 64** (de arriba hacia abajo). La **64** es la más
cercana a la superficie. La altura se calcula con `zh`.

### Unidades
Temperatura en **°C**, humedad en **g/kg**, ozono en **ppb** (aproximado).
"""
    )
