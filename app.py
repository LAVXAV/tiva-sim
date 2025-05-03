"""
app.py – TIVA‑SIM (versão "Lite TCI")

Agora com cálculo confiável da curva Ce baseada no modelo farmacocinético/farmacodinâmico de Schnider,
com atualização em tempo contínuo (a cada segundo), autoatualização da interface e simulação de washout após despertar.
"""

import time
import math
from dataclasses import dataclass
from typing import List
import streamlit as st
import pandas as pd
import altair as alt
from streamlit_extras.st_autorefresh import st_autorefresh

# ... [classes e funções anteriores permanecem iguais]

def estimate_ce_curve_schnider(patient: Patient, schedule: List[ScheduleStep], total_duration_min: int, resolution_sec: float = 1.0, stop_min: float = None) -> List[float]:
    V1 = 4.27
    V2 = 18.9
    Cl1 = 1.89
    Cl2 = 1.29
    ke0 = 0.26

    steps = int(total_duration_min * 60 / resolution_sec)
    Ce = [0.0]
    C1 = 0.0
    C2 = 0.0
    dt = resolution_sec / 60

    for i in range(1, steps):
        t_min = i * resolution_sec / 60

        if stop_min and t_min >= stop_min:
            rate_now = 0.0  # parada da infusão
        else:
            rate_now = next((s.rate_ml_h for s in schedule if s.start_min <= t_min < s.end_min), schedule[-1].rate_ml_h)

        dose = (rate_now / 60) * 10

        dC1 = (dose - Cl1 * C1 - Cl2 * (C1 - C2)) / V1
        dC2 = (Cl2 * (C1 - C2)) / V2

        C1 += dC1 * dt
        C2 += dC2 * dt

        Ce_prev = Ce[-1]
        Ce_now = Ce_prev + dt * ke0 * (C1 - Ce_prev)
        Ce.append(round(Ce_now, 3))

    Ce[0] = Ce[1] / 2
    return Ce

# ───────────────────────────────── Running ─────────────────────────────────── #

def predict_wake_recovery_time(ce_values: List[float], start_min: float, threshold: float = 1.0) -> float:
    """Retorna o tempo em minutos após o despertar em que Ce cai abaixo do limiar."""
    for i, ce in enumerate(ce_values):
        t = i / 60
        if t > start_min and ce < threshold:
            return round(t - start_min, 1)
    return None  # não caiu abaixo


if st.session_state.page == "running":
    st_autorefresh(interval=3000, key="tiva_refresh")

    schedule: List[ScheduleStep] = st.session_state.schedule
    equipo: Equipo = st.session_state.equipo
    ce_target = st.session_state.ce_target
    patient = st.session_state.patient
    wake_time_min = st.session_state.get("wake_time_min")  # None até despertar

    st.title("TIVA‑SIM – Infusão Ativa")
    elapsed_sec = int(time.time() - st.session_state.start_time)
    elapsed_min = elapsed_sec // 60
    total_duration = schedule[-1].end_min
    if wake_time_min:
        sim_duration = wake_time_min + 20  # simula até 20 min após despertar
    else:
        sim_duration = total_duration

    if elapsed_min >= sim_duration:
        st.session_state.page = "finished"
        st.experimental_rerun()

    current_step = next((s for s in schedule if s.start_min <= elapsed_min < s.end_min), schedule[-1])

    st.metric("Gotejamento atual", f"{current_step.gtt_min if not wake_time_min else 0} gtt/min")
    st.progress(min(elapsed_min / sim_duration, 1.0))

    ce_values = estimate_ce_curve_schnider(patient, schedule, sim_duration, resolution_sec=1.0, stop_min=wake_time_min)
    timeline = []
    for i, ce in enumerate(ce_values):
        t_min = round(i / 60, 2)
        step = next((s for s in schedule if s.start_min <= t_min < s.end_min), schedule[-1])
        gtt = step.gtt_min if not wake_time_min or t_min < wake_time_min else 0
        timeline.append({"Minuto": t_min, "Gotas/min": gtt, "Ce (µg/mL)": ce})
    df = pd.DataFrame(timeline)

    chart = alt.Chart(df).transform_fold(
        ["Gotas/min", "Ce (µg/mL)"], as_=["Tipo", "Valor"]
    ).mark_line().encode(
        x="Minuto:Q",
        y=alt.Y("Valor:Q", scale=alt.Scale(zero=False)),
        color="Tipo:N"
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)

    if wake_time_min:
        time_to_ce1 = predict_wake_recovery_time(ce_values, wake_time_min)
        if time_to_ce1 is not None:
            st.success(f"Previsão: Ce < 1 µg/mL em {time_to_ce1} minutos após o despertar.")
        else:
            st.warning("Ce ainda não caiu abaixo de 1 µg/mL. Continue monitorando.")

    col1, col2 = st.columns([1, 4])
    if col1.button("Despertar agora"):
        st.session_state.wake_time_min = elapsed_min
        st.experimental_rerun()
    with col2:
        st.caption("Clique para simular a interrupção da infusão e observar washout de Ce.")

# [restante do código permanece igual]
