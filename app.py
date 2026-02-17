import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# =========================================================
# 1. CONFIGURACION Y ESTILO CSS
# =========================================================
st.set_page_config(page_title="Meteorologia Nacional Pro", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #00FFCC; }
    [data-testid="stMetricLabel"] { font-size: 14px; color: #ADB5BD; }
    div[data-testid="metric-container"] {
        background-color: #1E1E1E;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def cargar_datos():
    try:
        df_temp = pd.read_csv("MAESTRO_TEMPERATURAS_FINAL_COMPLETO.csv")
        df_lluvia = pd.read_csv("MAESTRO_PRECIPITACIONES_FINAL_COMPLETO.csv")
        df_coords = pd.read_csv("coordenadas.csv") 

        df_temp['fecha'] = pd.to_datetime(dict(year=df_temp['Ano'], month=df_temp['Mes'], day=df_temp['Dia']))
        df_lluvia['fecha'] = pd.to_datetime(dict(year=df_lluvia['Ano'], month=df_lluvia['Mes'], day=df_lluvia['Dia']))

        df_clima = pd.merge(df_temp, df_lluvia, on=['fecha', 'CodigoNacional', 'NombreEstacion'], how='inner')
        df_coords_clean = df_coords[['CodigoNacional', 'Latitud', 'Longitud', 'Altura']].drop_duplicates()
        df_final = pd.merge(df_clima, df_coords_clean, on='CodigoNacional', how='left')

        df_final['Year'] = df_final['fecha'].dt.year
        df_final['DayOfYear'] = df_final['fecha'].dt.dayofyear
        return df_final
    except: return None

df = cargar_datos()

if df is not None:
    ACENTO_NEON = "#00FFCC"
    PALETA_APP = px.colors.sequential.Cividis

    # =========================================================
    # 2. SELECCION DE ESTACION Y AÑO
    # =========================================================
    st.title("Red Meteorologica Nacional: Inteligencia Climatica")
    
    col_map, col_metrics = st.columns([2.5, 1])

    with col_map:
        df_mapa = df.drop_duplicates(subset=['NombreEstacion'])
        fig_map = px.scatter_mapbox(df_mapa, lat="Latitud", lon="Longitud", hover_name="NombreEstacion",
                                    zoom=3.8, height=450, color_discrete_sequence=[ACENTO_NEON])
        fig_map.update_layout(mapbox_style="carto-darkmatter", margin={"r":0,"t":0,"l":0,"b":0})
        event_data = st.plotly_chart(fig_map, use_container_width=True, on_select="rerun")

    if event_data and len(event_data.selection.points) > 0:
        estacion_sel = event_data.selection.points[0]['hovertext']
    else:
        estacion_sel = st.sidebar.selectbox("Buscar Estacion:", sorted(df['NombreEstacion'].unique()))

    df_estacion = df[df['NombreEstacion'] == estacion_sel].copy()
    years = sorted(df_estacion['Year'].unique(), reverse=True)
    year_sel = st.sidebar.segmented_control("Año de Analisis:", options=years, default=years[0])
    df_year = df_estacion[df_estacion['Year'] == year_sel]

    with col_metrics:
        st.subheader("Estadisticas Clave")
        st.metric("Max. Promedio", f"{df_year['T.Maxima'].mean():.1f}C")
        st.metric("PP Acumulada", f"{df_year['SumaDiaria'].sum():.1f} mm")
        st.metric("Elevacion", f"{df_year['Altura'].iloc[0]}m")
        
        dia_max = df_year.loc[df_year['T.Maxima'].idxmax()]
        st.warning(f"Record {year_sel}: {dia_max['T.Maxima']}C el {dia_max['fecha'].strftime('%d/%m')}")

    # =========================================================
    # 3. PESTAÑAS ACUMULATIVAS
    # =========================================================
    t1, t2, t3, t4, t5 = st.tabs([
        "Tendencia Anual", 
        "Regresion Historica", 
        "Variabilidad Estacional", 
        "Analisis de Impacto",
        "Anomalias Historicas"
    ])

    with t1:
        st.subheader(f"Evolucion Diaria - {year_sel}")
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=df_year['fecha'], y=df_year['T.Maxima'], name="Maxima Diaria", line=dict(color=ACENTO_NEON, width=1)))
        fig_line.add_trace(go.Scatter(x=df_year['fecha'], y=df_year['T.Maxima'].rolling(7).mean(), name="Media Movil 7d", line=dict(color="#FFB703", width=2)))
        fig_line.update_layout(template="plotly_dark", hovermode="x unified", margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_line, use_container_width=True)

    with t2:
        st.subheader("Cambios climaticos en la estacion")
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Tendencia de Temperaturas Maximas Anuales**")
            df_tendencia_anual = df_estacion.groupby('Year')['T.Maxima'].mean().reset_index()
            
            fig_trend = px.scatter(df_tendencia_anual, x="Year", y="T.Maxima", 
                                   trendline="ols", 
                                   title="Promedio Anual de Maximas",
                                   color_discrete_sequence=[ACENTO_NEON],
                                   template="plotly_dark")
            st.plotly_chart(fig_trend, use_container_width=True)
            st.info("Esta linea muestra si la temperatura promedio ha subido o bajado en los ultimos años.")
            
        with c2:
            st.write("**Relacion Lluvia vs Calor (Todos los años)**")
            fig_scat = px.scatter(df_estacion, x="T.Maxima", y="SumaDiaria", color="Year", 
                                  size="SumaDiaria", opacity=0.6,
                                  color_continuous_scale=PALETA_APP, template="plotly_dark")
            st.plotly_chart(fig_scat, use_container_width=True)

    with t3:
        st.subheader("Distribucion y Variabilidad")
        fig_hist = px.histogram(df_estacion, x="T.Maxima", color="Year", marginal="box", 
                                color_discrete_sequence=PALETA_APP, template="plotly_dark")
        st.plotly_chart(fig_hist, use_container_width=True)

    with t4:
        st.subheader("Efecto de la lluvia en la temperatura")
        df_estacion['Estado'] = df_estacion['SumaDiaria'].apply(lambda x: 'Dia Lluvioso' if x > 0.1 else 'Dia Seco')
        fig_violin = px.violin(df_estacion, y="T.Maxima", x="Estado", color="Estado", box=True, points="all",
                               color_discrete_map={'Dia Lluvioso': '#00B4D8', 'Dia Seco': '#FFB703'}, template="plotly_dark")
        st.plotly_chart(fig_violin, use_container_width=True)

    with t5:
        st.subheader("Anomalias: Desviacion del Promedio Historico")
        media_historica = df_estacion.groupby('DayOfYear')['T.Maxima'].transform('mean')
        df_estacion['Anomalia'] = df_estacion['T.Maxima'] - media_historica
        df_anom_year = df_estacion[df_estacion['Year'] == year_sel]
        
        fig_anom = px.scatter(df_anom_year, x="fecha", y="Anomalia", color="Anomalia",
                              color_continuous_scale="RdBu_r", template="plotly_dark")
        fig_anom.add_hline(y=0, line_dash="dash", line_color="white")
        st.plotly_chart(fig_anom, use_container_width=True)

else:
    st.error("No se pudieron cargar los datos. Revisa los nombres de los archivos CSV.")