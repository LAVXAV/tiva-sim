import streamlit as st
import matplotlib.pyplot as plt
from models.schnider_full import simulate_schnider_full

# Configurações da página
st.set_page_config(page_title="TIVA-SIM", layout="centered")
st.title("💉 TIVA-SIM — Simulador de Infusão Alvo-Controlada")

# Dados do paciente
st.sidebar.header("📋 Dados do Paciente")
peso = st.sidebar.number_input("Peso (kg)", min_value=30.0, max_value=200.0, value=70.0)
altura = st.sidebar.number_input("Altura (cm)", min_value=140.0, max_value=210.0, value=170.0)
idade = st.sidebar.number_input("Idade", min_value=18, max_value=100, value=40)
sexo = st.sidebar.selectbox("Sexo", ["Masculino", "Feminino"])

# Parâmetro de entrada clínica
st.sidebar.header("🎯 Objetivo Clínico")
propofol_ce = st.sidebar.slider("Concentração-alvo de Propofol (Ce) em mcg/mL", min_value=0.5, max_value=6.0, value=3.0, step=0.1)

st.markdown("Clique no botão abaixo para iniciar a simulação com o **modelo farmacocinético-farmacodinâmico completo de Schnider**.")

if st.button("▶️ Iniciar Infusão"):
    # Estimar taxa de infusão a partir da Ce alvo (aproximado)
    V1 = 4.27  # L
    infusion_rate = propofol_ce * V1  # mg para atingir Ce alvo
    infusion_rate_mg_per_min = infusion_rate / 60

    # Simula por 30 minutos com passo de 0.1 min
    t, Cp, Ce = simulate_schnider_full(
        duration_min=30,
        infusion_rate_mg_per_min=infusion_rate_mg_per_min
    )

    st.success("✅ Simulação concluída com o modelo Schnider completo!")
    st.markdown(f"💉 Infusão contínua estimada: **{infusion_rate:.1f} mg/h**")
    st.markdown(f"🧠 Ce alvo: **{propofol_ce:.2f} mcg/mL** — atingido progressivamente")

    # Gráfico
    fig, ax = plt.subplots()
    ax.plot(t, Cp, label="Cp (Plasma)", linestyle="--")
    ax.plot(t, Ce, label="Ce (Efeito)", linewidth=2)
    ax.set_xlabel("Tempo (min)")
    ax.set_ylabel("Concentração (mg/L)")
    ax.set_title("Curvas simuladas — Modelo Schnider Completo")
    ax.legend()
    ax.grid(True)
    st.pyplot(fig)
