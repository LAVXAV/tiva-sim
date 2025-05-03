"""
app.py – TIVA‑SIM (versão "Lite TCI")

Objetivo: aproximar a experiência de uma bomba alvo‑controlada usando apenas
um equipo macro ou micro. Baseado nos requisitos definidos:
  • Entrada mínima (peso, idade, sexo, equipo, profundidade/target Ce)
  • Escolha do equipo ANTES de iniciar (não muda durante)
  • Infusão guiada em gotas/min, metrônomo opcional
  • Botão de DESPERTAR a qualquer momento
  • Três estágios (0‑5, 5‑15, 15‑wake) com taxas derivadas do modelo Schnider
  • Interface de 2 telas (Configuração → Infusão) em Streamlit
"""

import time
import math
from dataclasses import dataclass
from typing import List
import streamlit as st

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
        """Converte mL/h em gotas/min arredondando para o inteiro mais próximo."""
        return round(rate_ml_h * self.drop_factor / 60)

@dataclass
class ScheduleStep:
    start_min: int
    end_min: int
    rate_ml_h: float
    gtt_min: int

# Equipos fixos
MACRO = Equipo("Macro", 20)
MICRO = Equipo("Micro", 60)
EQUIPOS = {e.name: e for e in (MACRO, MICRO)}

# Conversão simples Ce → mg·kg⁻¹·h⁻¹ (empírico: 2 × Ce)  
# Ex.: Ce 3 → 6 mg/kg/h (igual à nossa curva básica)
MGKGH_FACTOR = 2.0


def generate_schedule(patient: Patient, equipo: Equipo, duration_min: int, ce_target: float) -> List[ScheduleStep]:
    """Gera roteiro em 3 blocos usando fatores % fixos (100%, 80%, 67%)."""
    mgkg_start = MGKGH_FACTOR * ce_target          # mg·kg⁻¹·h⁻¹
    w = patient.weight
    mlh_start = mgkg_start * w / 10                # mL/h (10 mg/mL)
    mlh_mid   = mlh_start * 0.8
    mlh_final = mlh_start * 0.667

    raw = []
    if duration_min <= 5:
        raw.append((0, duration_min, mlh_start))
    elif duration_min <= 15:
        raw.extend([(0, 5, mlh_start), (5, duration_min, mlh_mid)])
    else:
        raw.extend([(0, 5, mlh_start), (5, 15, mlh_mid), (15, duration_min, mlh_final)])

    return [ScheduleStep(s, e, r, equipo.gtt_per_min(r)) for (s, e, r) in raw]

# ──────────────────────────────── UI helpers ───────────────────────────────── #

def init_session_state():
    if "page" not in st.session_state:
        st.session_state.page = "setup"  # or "running"/"finished"
    if "start_time" not in st.session_state:
        st.session_state.start_time = None
    if "schedule" not in st.session_state:
        st.session_state.schedule = None
    if "ce_target" not in st.session_state:
        st.session_state.ce_target = 3.0

# ─────────────────────────────────── App ────────────────────────────────────── #

st.set_page_config(page_title="TIVA‑SIM Lite", layout="centered")
init_session_state()

if st.session_state.page == "setup":
    st.title("TIVA‑SIM – Configuração Rápida")
    col1, col2 = st.columns(2)
    with col1:
        weight = st.number_input("Peso (kg)", 30.0, 200.0, 70.0)
        height = st.number_input("Altura (m)", 1.0, 2.5, 1.70, step=0.01)
        age = st.number_input("Idade (anos)", 0, 100, 30)
    with col2:
        sex = st.radio("Sexo", ["M", "F"], index=0)
        equipo_name = st.selectbox("Equipo", list(EQUIPOS.keys()), index=0)
        equipo = EQUIPOS[equipo_name]
        ce_target = st.slider("Profundidade / Ce alvo (µg/mL)", 1.0, 6.0, 3.0, 0.1)
        duration = st.slider("Duração estimada (min)", 5, 120, 60)

    if st.button("Iniciar Infusão"):
        patient = Patient(weight, height, age, sex)
        schedule = generate_schedule(patient, equipo, duration, ce_target)
        st.session_state.schedule = schedule
        st.session_state.start_time = time.time()
        st.session_state.equipo = equipo
        st.session_state.ce_target = ce_target
        st.session_state.page = "running"
        st.experimental_rerun()

# ───────────────────────────────── Running ─────────────────────────────────── #

if st.session_state.page == "running":
    schedule: List[ScheduleStep] = st.session_state.schedule
    equipo:   Equipo           = st.session_state.equipo
    ce_target                      = st.session_state.ce_target

    st.title("TIVA‑SIM – Infusão Ativa")
    elapsed_min = int((time.time() - st.session_state.start_time) / 60)
    total_duration = schedule[-1].end_min
    if elapsed_min >= total_duration:
        st.session_state.page = "finished"
        st.experimental_rerun()

    current_step = next((s for s in schedule if s.start_min <= elapsed_min < s.end_min), schedule[-1])

    st.metric("Gotejamento atual", f"{current_step.gtt_min} gtt/min")
    st.progress(min(elapsed_min / total_duration, 1.0))

    with st.expander("Cronograma completo"):
        st.table({"Início": [s.start_min for s in schedule],
                  "Fim":    [s.end_min   for s in schedule],
                  "Gotas/min": [s.gtt_min for s in schedule]})

    cols = st.columns(3)
    with cols[0]:
        if st.button("Despertar Agora"):
            st.session_state.page = "finished"
            st.experimental_rerun()
    with cols[1]:
        if st.button("+0,1 µg/mL"):
            st.session_state.ce_target = round(min(6.0, ce_target + 0.1), 1)
            st.session_state.schedule = generate_schedule(
                Patient(st.session_state.schedule[0].gtt_min, 0, 0, "M"),  # dummy height/age
                equipo, total_duration - elapsed_min, st.session_state.ce_target
            )
            st.experimental_rerun()
    with cols[2]:
        if st.button("-0,1 µg/mL"):
            st.session_state.ce_target = round(max(1.0, ce_target - 0.1), 1)
            st.session_state.schedule = generate_schedule(
                Patient(st.session_state.schedule[0].gtt_min, 0, 0, "M"),
                equipo, total_duration - elapsed_min, st.session_state.ce_target
            )
            st.experimental_rerun()

    st.caption("Pressione F5 para atualizar se o gotejamento não se renovar automaticamente.")

# ─────────────────────────────── Finished ──────────────────────────────────── #

if st.session_state.page == "finished":
    st.title("TIVA‑SIM – Infusão Encerrada")
    st.success("Infusão concluída ou despertada com sucesso.")
    if st.button("Nova Sessão"):
        st.session_state.clear()
        init_session_state()
        st.experimental_rerun()
