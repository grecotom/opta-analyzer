import streamlit as st
import pandas as pd
from mplsoccer import Pitch
from kloppy import opta

st.set_page_config(layout="wide")
st.title("🔁 Análisis de Secuencias (Opta)")

f7_files = st.file_uploader("Subí archivos F7 (alineaciones)", type="xml", accept_multiple_files=True)
f24_files = st.file_uploader("Subí archivos F24 (eventos)", type="xml", accept_multiple_files=True)

dataframes = []

if f7_files and f24_files:
    f24_dict = {f.name.replace("_f24.xml", ""): f for f in f24_files}

    for f7 in f7_files:
        nombre_base = f7.name.replace("_f7.xml", "")
        if nombre_base in f24_dict:
            f24 = f24_dict[nombre_base]
            try:
                dataset = opta.load(f7_data=f7, f24_data=f24, coordinates="opta")
                df = dataset.to_df()
                df["match_id"] = nombre_base

                player_id_map = {
                    player.player_id: player.full_name
                    for team in dataset.metadata.teams
                    for player in team.players
                }
                team_id_map = {
                    team.team_id: team.name
                    for team in dataset.metadata.teams
                }

                df["player_name"] = df["player_id"].map(player_id_map)
                df["team_name"] = df["team_id"].map(team_id_map)

                dataframes.append(df)
            except Exception as e:
                st.error(f"❌ Error en '{nombre_base}': {e}")
        else:
            st.warning(f"⚠️ F24 faltante para '{nombre_base}'")

if dataframes:
    df = pd.concat(dataframes, ignore_index=True)
    st.subheader("📈 Secuencias: Recepción + Pase siguiente")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("📍 Zona de recepción")
        rx_min = st.slider("Rec X min", 0, 100, 30, key="rx_min")
        rx_max = st.slider("Rec X max", 0, 100, 70, key="rx_max")
        ry_min = st.slider("Rec Y min", 0, 100, 30, key="ry_min")
        ry_max = st.slider("Rec Y max", 0, 100, 70, key="ry_max")
    with col2:
        st.markdown("🎯 Zona del siguiente pase")
        px_min = st.slider("Pase X min", 0, 100, 30, key="px_min")
        px_max = st.slider("Pase X max", 0, 100, 70, key="px_max")
        py_min = st.slider("Pase Y min", 0, 100, 30, key="py_min")
        py_max = st.slider("Pase Y max", 0, 100, 70, key="py_max")

    pases = df[df['event_type'] == 'PASS'].copy()
    pases = pases.sort_values(by='timestamp')

    pases_recibidos = pases.rename(columns={
        'receiver_player_id': 'player_id',
        'end_coordinates_x': 'rec_x',
        'end_coordinates_y': 'rec_y',
        'team_name': 'receiver_team',
        'player_name': 'receiver_name',
        'timestamp': 'rec_timestamp'
    })[['player_id', 'rec_x', 'rec_y', 'rec_timestamp', 'receiver_team', 'receiver_name']]

    merged = pd.merge_asof(
        pases_recibidos.sort_values("rec_timestamp"),
        pases.sort_values("timestamp"),
        by="player_id",
        left_on="rec_timestamp",
        right_on="timestamp",
        direction="forward",
        tolerance=pd.Timedelta("20s")
    )

    cond_recepcion = (
        (merged['rec_x'] >= rx_min) & (merged['rec_x'] <= rx_max) &
        (merged['rec_y'] >= ry_min) & (merged['rec_y'] <= ry_max)
    )
    cond_pase = (
        (merged['coordinates_x'] >= px_min) & (merged['coordinates_x'] <= px_max) &
        (merged['coordinates_y'] >= py_min) & (merged['coordinates_y'] <= py_max)
    )

    secuencias = merged[cond_recepcion & cond_pase]

    st.success(f"🔎 {len(secuencias)} secuencias encontradas.")
    st.dataframe(
        secuencias.groupby(['receiver_name', 'receiver_team'])
        .size()
        .reset_index(name='Cantidad')
        .rename(columns={'receiver_name': 'Jugador', 'receiver_team': 'Equipo'})
        .sort_values(by='Cantidad', ascending=False)
    )
