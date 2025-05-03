"""
app.py

Streamlit app do TIVA-SIM: simula infusão alvo-controlada de propofol usando equipo manual
(meta: modelo Schnider, três blocos de infusão) e permite simulação interativa via slider.
"""
import streamlit as st
from dataclasses import dataclass
from typing import List

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
        return round(rate_ml_h * self.drop_factor / 60.0)

@dataclass
class ScheduleStep:
    start_min: int
    end_min: int
    gtt_min: int

# Equipos disponíveis
MACRO = Equipo('MACRO', 20)
MICRO = Equipo('MICRO', 60)

# Função de geração de cronograma
def generate_schedule(patient: Patient, equipo: Equipo, duration_min: int) -> List[ScheduleStep]:
    w = patient.weight
    # taxas mg/kg/h → mL/h (10 mg/mL)
    start_mlh = 6 * w / 10.0
    mid_mlh   = start_mlh * 0.8
    final_mlh = start_mlh * 0.667
    raw = []
    if duration_min <= 5:
        raw.append((0, duration_min, start_mlh))
    elif duration_min <= 15:
        raw.extend([(0, 5, start_mlh), (5, duration_min, mid_mlh)])
    else:
        raw.extend([(0, 5, start_mlh), (5, 15, mid_mlh), (15, duration_min, final_mlh)])
    return [ScheduleStep(s, e, equipo.gtt_per_min(r)) for s, e, r in raw]

# UI
st.title("TIVA‑SIM Manual (Streamlit)")
with st.sidebar:
    st.header("Parâmetros do Paciente & Equipo")
    weight = st.number_input("Peso (kg)", min_value=1.0, max_value=200.0, value=70.0)
    height = st.number_input("Altura (m)", min_value=0.5, max_value=2.5, value=1.70)
    age = st.number_input("Idade (anos)", min_value=0, max_value=120, value=30)
    sex = st.radio("Sexo", options=["M", "F"], index=0)
    equipo_choice = st.selectbox("Equipo de gotas", ["MACRO (20 gtt/mL)", "MICRO (60 gtt/mL)"])
    equipo = MACRO if equipo_choice.startswith('MACRO') else MICRO
    duration = st.slider("Duração TIVA (min)", min_value=1, max_value=120, value=60)

if st.button("Gerar Cronograma"):
    patient = Patient(weight, height, age, sex)
    schedule = generate_schedule(patient, equipo, duration)
    # tabela de cronograma
    table = [{"Início (min)": s.start_min, "Fim (min)": s.end_min, "Gotas/min": s.gtt_min} for s in schedule]
    st.subheader("Cronograma de Infusão")
    st.table(table)
    # simulação interativa
    minute = st.slider("Minuto Atual", min_value=0, max_value=duration, value=0)
    current = next((s for s in schedule if s.start_min <= minute < s.end_min), None)
    if current:
        st.metric("Gotas por minuto", f"{current.gtt_min}")
    # botão de despertar
    if st.button("Despertar Paciente"):
        st.warning("Wake-up solicitado! Interrompendo infusão...")
