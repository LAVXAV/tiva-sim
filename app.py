"""
app.py – TIVA-SIM (versão "Lite TCI")

Simulador de infusão alvo-controlada de propofol usando equipo manual,
baseado em modelo Schnider PK/PD, com Curva Ce em tempo real,
autoatualização via tag HTML e simulação de washout e previsão de recobro.
"""

import time
import math
from dataclasses import dataclass
from typing import List
import streamlit as st
import pandas as pd
import altair as alt

# ──────────────────────────── Modelos & utilidades ──────────────────────────── #

@dataclass
class Patient:
    weight: float   # kg
    height: float   # m
    age: int        # anos
    sex: str        # 'M' ou 'F'

@dataclass
class Equipo:
    name: str
    drop_factor: int  # gotas por mL

    def gtt_per_min(self, rate_ml_h: float) -> int:
        return round(rate_ml_h * self.drop_factor / 60)

@dataclass
class ScheduleStep:
    start_min: int
    end_min: int
    rate_ml_h: float
    gtt_min: int

# Equipos disponíveis
MACRO = Equipo("Macro", 20)
MICRO = Equipo("Micro", 60)
EQUIPOS = {e.name: e for e in (MACRO, MICRO)}

# Conversão empírica Ce → mg·kg⁻¹·h⁻¹
MGKGH_FACTOR = 2.0

def generate_schedule(patient: Patient, equipo: Equipo, duration_min: int, ce_target: float) -> List[ScheduleStep]:
    mgkg_start = MGKGH_FACTOR * ce_target  # mg·kg⁻¹·h⁻¹
    w = patient.weight
    mlh_start = mgkg_start * w / 10        # mL/h (10 mg/mL)
    mlh_mid   = mlh_start * 0.8
    mlh_final = mlh_start * 0.667

    raw = []
    if duration_min <= 5:
        raw.append((0, duration_min, mlh_start))
    elif duration_min <= 15:
        raw.extend([(0,5,mlh_start),(5,duration_min,mlh_mid)])
    else:
        raw.extend([(0,5,mlh_start),(5,15,mlh_mid),(15,duration_min,mlh_final)])

    return [ScheduleStep(s,e,r,equipo.gtt_per_min(r)) for (s,e,r) in raw]


def estimate_ce_curve_schnider(patient: Patient, schedule: List[ScheduleStep], total_duration_min: int, resolution_sec: float = 1.0, stop_min: float = None) -> List[float]:
    # Parâmetros Schnider fixos
    V1, V2 = 4.27, 18.9
    Cl1, Cl2 = 1.89, 1.29
    ke0 = 0.26

    steps = int(total_duration_min * 60 / resolution_sec)
    Ce = [0.0]; C1 = 0.0; C2 = 0.0
    dt = resolution_sec / 60

    for i in range(1, steps):
        t_min = i * resolution_sec / 60
        # Taxa zero após despertar
        if stop_min and t_min >= stop_min:
            rate_ml_h = 0.0
        else:
            rate_ml_h = next((s.rate_ml_h for s in schedule if s.start_min <= t_min < s.end_min), schedule[-1].rate_ml_h)
        dose_mg = (rate_ml_h / 60) * 10

        # Modelagem bicompartimental
        dC1 = (dose_mg - Cl1*C1 - Cl2*(C1 - C2)) / V1
        dC2 = (Cl2*(C1 - C2)) / V2
        C1 += dC1 * dt; C2 += dC2 * dt

        Ce_prev = Ce[-1]
        Ce_now = Ce_prev + dt * ke0 * (C1 - Ce_prev)
        Ce.append(round(Ce_now, 3))

    Ce[0] = Ce[1] / 2
    return Ce


def predict_wake_recovery_time(ce_values: List[float], start_min: float, threshold: float = 1.0) -> float:
    for i, ce in enumerate(ce_values):
        t = i / 60
        if t > start_min and ce < threshold:
            return round(t - start_min, 1)
    return None


def init_session_state():
    defaults = {
        "page": "setup",
        "start_time": None,
        "schedule": None,
        "patient": None,
        "equipo": None,
        "ce_target": 3.0,
        "wake_time_min": None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ────────────────────────────────── App ────────────────────────────────────── #

st.set_page_config(page_title="TIVA-SIM Lite", layout="centered")
init_session_state()

if st.session_state.page == "setup":
    st.title("TIVA-SIM – Configuração Rápida")
    col1, col2 = st.columns(2)
    with col1:
        weight = st.number_input("Peso (kg)", 30.0, 200.0, 70.0)
        height = st.number_input("Altura (m)", 1.0, 2.5, 1.70, step=0.01)
        age = st.number_input("Idade (anos)", 0, 100, 30)
    with col2:
        sex = st.radio("Sexo", ["M","F"], index=0)
        eq_name = st.selectbox("Equipo", list(EQUIPOS.keys()))
        equipo = EQUIPOS[eq_name]
        ce_target = st.slider("Ce alvo (µg/mL)", 1.0, 6.0, 3.0, 0.1)
        duration = st.slider("Duração prevista (min)", 5, 120, 60)

    if st.button("Iniciar Infusão"):
        st.session_state.patient = Patient(weight, height, age, sex)
        st.session_state.equipo = equipo
        st.session_state.ce_target = ce_target
        st.session_state.schedule = generate_schedule(st.session_state.patient, equipo, duration, ce_target)
        st.session_state.start_time = time.time()
        st.session_state.page = "running"
        st.experimental_rerun()

elif st.session_state.page == "running":
    # Tag HTML para autoatualização a cada segundo
    st.markdown("<meta http-equiv=\"refresh\" content=\"1\">", unsafe_allow_html=True)

    patient = st.session_state.patient
    schedule = st.session_state.schedule
    equipo = st.session_state.equipo
    wake_time = st.session_state.wake_time_min

    elapsed_sec = int(time.time() - st.session_state.start_time)
    elapsed_min = elapsed_sec // 60
    total_dur = schedule[-1].end_min
    sim_dur = (wake_time + 20) if wake_time else total_dur

    st.title("TIVA-SIM – Infusão Ativa")
    step = next((s for s in schedule if s.start_min <= elapsed_min < s.end_min), schedule[-1])
    st.metric("Gotejamento (gtt/min)", step.gtt_min if not wake_time else 0)
    st.progress(min(elapsed_min/sim_dur,1.0))

    ce_vals = estimate_ce_curve_schnider(patient, schedule, sim_dur, 1.0, stop_min=wake_time)
    data = []
    for i, ce in enumerate(ce_vals):
        t = round(i/60,2)
        gtt = next((s.gtt_min for s in schedule if s.start_min <= t < s.end_min), schedule[-1].gtt_min)
        if wake_time and t>=wake_time:
            gtt = 0
        data.append({"Minuto": t, "Gotas/min": gtt, "Ce (µg/mL)": ce})
    df = pd.DataFrame(data)
    chart = alt.Chart(df).transform_fold(["Gotas/min","Ce (µg/mL)"], as_=["Tipo","Valor"]).mark_line().encode(
        x="Minuto:Q", y=alt.Y("Valor:Q", scale=alt.Scale(zero=False)), color="Tipo:N"
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)

    if wake_time:
        rec = predict_wake_recovery_time(ce_vals, wake_time)
        if rec:
            st.success(f"Ce<1 µg/mL em {rec} min pós-despertar.")
        else:
            st.warning("Ce ainda >1 µg/mL; continue observação.")

    col1, col2 = st.columns([1,4])
    if col1.button("Despertar agora"):
        st.session_state.wake_time_min = elapsed_min
        st.experimental_rerun()
    with col2:
        st.caption("Interrompe infusão e simula washout de Ce.")

else:
    st.title("TIVA-SIM – Sessão Encerrada")
    st.success("Infusão finalizada ou despertada com sucesso.")
    if st.button("Nova Sessão"):
        for k in ["page","start_time","schedule","patient","equipo","ce_target","wake_time_min"]:
            del st.session_state[k]
        init_session_state()
        st.experimental_rerun()
