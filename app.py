import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# =========================================================
# 1. CONFIGURACION Y ESTILO CSS
# =========================================================
st.set_page_config(page_title="Meteorologia Nacional Pro", layout="wide")

# Colores de la paleta original
ACENTO_NEON = "#00FFCC"

st.markdown(f"""
    <style>
    /* Eliminar animaciones de fade para mayor rapidez */
    .stApp {{
        animation: none !important;
        transition: none !important;
    }}
    
    [data-testid="stMetricValue"] {{ font-size: 28px; color: {ACENTO_NEON}; }}
    [data-testid="stMetricLabel"] {{ font-size: 14px; color: #ADB5BD; }}
    div[data-testid="metric-container"] {{
        background-color: #1E1E1E;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 10px;
    }}

    /* Ajuste de ancho de sidebar para que el grid quepa bien */
    section[data-testid="stSidebar"] {{
        min-width: 320px !important;
    }}
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def cargar_datos():
    try:
        df_temp = pd.read_csv("MAESTRO_TEMPERATURAS_FINAL_COMPLETO.csv")
        df_lluvia = pd.read_csv("MAESTRO_PRECIPITACIONES_FINAL_COMPLETO.csv")
        df_coords = pd.read_csv("Coordenadas.csv") 

        df_temp['fecha'] = pd.to_datetime(dict(year=df_temp['Ano'], month=df_temp['Mes'], day=df_temp['Dia']))
        df_lluvia['fecha'] = pd.to_datetime(dict(year=df_lluvia['Ano'], month=df_lluvia['Mes'], day=df_lluvia['Dia']))

        df_clima = pd.merge(df_temp, df_lluvia, on=['fecha', 'CodigoNacional', 'NombreEstacion'], how='inner')
        df_coords_clean = df_coords[['CodigoNacional', 'Latitud', 'Longitud', 'Altura']].drop_duplicates()
        df_final = pd.merge(df_clima, df_coords_clean, on='CodigoNacional', how='left')

        df_final['Year'] = df_final['fecha'].dt.year
        df_final['DayOfYear'] = df_final['fecha'].dt.dayofyear
        
        df_final['Media_Hist_Max'] = df_final.groupby(['NombreEstacion', 'DayOfYear'])['T.Maxima'].transform('mean')
        df_final['Anomalia'] = df_final['T.Maxima'] - df_final['Media_Hist_Max']
        
        return df_final
    except Exception as e:
        st.error(f"Error al cargar los datos: {e}")
        return None

df = cargar_datos()

if df is not None:
    PALETA_APP = px.colors.sequential.Cividis

    # =========================================================
    # 2. SELECCION DE ESTACION Y AÑO
    # =========================================================
    st.title("Red Meteorológica Nacional: Inteligencia Climatica")
    
    col_map, col_metrics = st.columns([2.5, 1])

    with col_map:
        df_mapa = df.drop_duplicates(subset=['NombreEstacion'])
        fig_map = px.scatter_mapbox(df_mapa, lat="Latitud", lon="Longitud", hover_name="NombreEstacion",
                                    zoom=3.8, height=450, color_discrete_sequence=[ACENTO_NEON])
        fig_map.update_layout(mapbox_style="carto-darkmatter", margin={"r":0,"t":0,"l":0,"b":0})
        event_data = st.plotly_chart(fig_map, use_container_width=True, on_select="rerun")

    # Lógica de selección (Mapa o Sidebar)
    if event_data and len(event_data.selection.points) > 0:
        estacion_sel = event_data.selection.points[0]['hovertext']
    else:
        estacion_sel = st.sidebar.selectbox("Buscar Estación:", sorted(df['NombreEstacion'].unique()))

    df_estacion = df[df['NombreEstacion'] == estacion_sel].copy()
    years = sorted(df_estacion['Year'].unique(), reverse=True)

    # --- NUEVA SIDEBAR DE AÑOS (GRID 5x2) ---
    st.sidebar.markdown("### Año de Análisis")
    
    # Inicializar estado si no existe
    if 'year_sel' not in st.session_state:
        st.session_state.year_sel = years[0]

    # Dibujar grid de botones
    with st.sidebar:
        grid_cols = st.columns(2)
        for i, y in enumerate(years):
            # Usamos el índice para alternar entre columna 0 y 1
            if grid_cols[i % 2].button(
                str(y), 
                use_container_width=True, 
                type="primary" if st.session_state.year_sel == y else "secondary"
            ):
                st.session_state.year_sel = y
                st.rerun()

    year_sel = st.session_state.year_sel
    df_year = df_estacion[df_estacion['Year'] == year_sel]

    # --- INDICADORES ---
    with col_metrics:
        st.subheader("Indicadores de la Estación")
        
        anom_media = df_year['Anomalia'].mean()
        st.metric("Anomalía Térmica Media", f"{anom_media:+.2f} °C", 
                  delta=f"{anom_media:.2f} °C vs Histórico", delta_color="inverse")

        st.metric("Precipitación Acumulada", f"{df_year['SumaDiaria'].sum():.1f} mm")
        st.metric("Elevación", f"{df_year['Altura'].iloc[0]}m")
        
        dia_max = df_year.loc[df_year['T.Maxima'].idxmax()]
        p95_hist = df_estacion['T.Maxima'].quantile(0.95)
        st.warning(f"Récord {year_sel}: {dia_max['T.Maxima']}°C ({dia_max['fecha'].strftime('%d/%m')}). "
                   f"El umbral de calor extremo (P95) es {p95_hist:.1f}°C.")

    # =========================================================
    # 3. PESTAÑAS DE ANÁLISIS
    # =========================================================
    t1, t2, t3, t4, t5 = st.tabs([
        "Rango y Variabilidad", 
        "Tendencias de Largo Plazo", 
        "Distribución Estadística", 
        "Impacto Hídrico",
        "Anomalías Diarias"
    ])

    with t1:
        st.subheader(f"Dinámica Térmica e Incertidumbre - {year_sel}")
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=df_year['fecha'], y=df_year['Media_Hist_Max'],
            name="Normal Histórica",
            line=dict(color="rgba(255, 255, 255, 0.3)", dash="dash")
        ))
        fig_line.add_trace(go.Scatter(
            x=df_year['fecha'], y=df_year['T.Maxima'], 
            name="Máxima Diaria", 
            line=dict(color=ACENTO_NEON, width=1.5)
        ))
        fig_line.add_trace(go.Scatter(
            x=df_year['fecha'], y=df_year['T.Maxima'].rolling(7).mean(), 
            name="Tendencia 7 días", 
            line=dict(color="#FFB703", width=2)
        ))
        fig_line.update_layout(template="plotly_dark", hovermode="x unified", margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_line, use_container_width=True)

    with t2:
        st.subheader("Análisis de Tendencia Interanual")
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Desplazamiento de la Media Anual**")
            df_tendencia_anual = df_estacion.groupby('Year')['T.Maxima'].mean().reset_index()
            fig_trend = px.scatter(df_tendencia_anual, x="Year", y="T.Maxima", 
                                   trendline="ols", 
                                   color_discrete_sequence=[ACENTO_NEON],
                                   template="plotly_dark")
            st.plotly_chart(fig_trend, use_container_width=True)
        with c2:
            st.write("**Correlación Térmico-Hídrica**")
            fig_scat = px.scatter(df_estacion, x="T.Maxima", y="SumaDiaria", color="Year", 
                                  size="SumaDiaria", opacity=0.4,
                                  color_continuous_scale=PALETA_APP, template="plotly_dark")
            st.plotly_chart(fig_scat, use_container_width=True)

    with t3:
        st.subheader("Asimetría y Extremos Térmicos")
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(x=df_estacion['T.Maxima'], name="Histórico Total", marker_color="#333", opacity=0.5))
        fig_hist.add_trace(go.Histogram(x=df_year['T.Maxima'], name=f"Año {year_sel}", marker_color=ACENTO_NEON, opacity=0.7))
        fig_hist.update_layout(barmode='overlay', template="plotly_dark")
        st.plotly_chart(fig_hist, use_container_width=True)

    with t4:
        st.subheader("Análisis de Estrés Hídrico")
        df_estacion['Estado'] = df_estacion['SumaDiaria'].apply(lambda x: 'Día Lluvioso' if x > 0.1 else 'Día Seco')
        fig_violin = px.violin(df_estacion, y="T.Maxima", x="Estado", color="Estado", box=True, points="outliers",
                               color_discrete_map={'Día Lluvioso': '#00B4D8', 'Día Seco': '#FFB703'}, template="plotly_dark")
        st.plotly_chart(fig_violin, use_container_width=True)

    with t5:
        st.subheader("Mapa de Calor de Anomalías (Z-Score)")
        fig_anom = px.bar(df_year, x="fecha", y="Anomalia", color="Anomalia",
                          color_continuous_scale="RdBu_r", 
                          range_color=[-5, 5],
                          template="plotly_dark")
        fig_anom.add_hline(y=0, line_dash="solid", line_color="white")
        st.plotly_chart(fig_anom, use_container_width=True)

else:
    st.error("Error crítico: No se pudieron cargar los datos. Verifica que los archivos CSV estén en la carpeta raíz.")