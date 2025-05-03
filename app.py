from models.schnider_full import simulate_schnider_full

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# Título do app
st.set_page_config(page_title="TIVA-SIM", layout="centered")
st.title("💉 TIVA-SIM")
st.subheader("Simulador de TIVA com equipo simples")

# Dados do paciente
st.sidebar.header("📋 Dados do paciente")
idade = st.sidebar.number_input("Idade", 18, 100, 40)
peso = st.sidebar.number_input("Peso (kg)", 30.0, 150.0, 70.0)
altura = st.sidebar.number_input("Altura (cm)", 100.0, 210.0, 170.0)
sexo = st.sidebar.selectbox("Sexo", ["Masculino", "Feminino"])

# Alvos de Ce
st.markdown("### 🎯 Concentração Alvo (Ce)")
propofol_ce = st.slider("Propofol (mcg/mL)", 0.5, 6.0, 3.0, 0.1)
remi_ce = st.slider("Remifentanil (ng/mL)", 0.5, 5.0, 2.5, 0.1)
dex_ce = st.slider("Dexmedetomidina (ng/mL estimada)", 0.2, 1.2, 0.6, 0.1)

# Botão de simulação
if st.button("▶️ Iniciar Infusão"):
    # Simulação de Ce fictícia para início
    tempo = np.arange(0, 20, 1)
    curva_ce = propofol_ce * (1 - np.exp(-0.3 * tempo))

    st.success("Infusão simulada! Veja a curva abaixo:")

    fig, ax = plt.subplots()
    ax.plot(tempo, curva_ce, label="Ce Propofol")
    ax.set_xlabel("Minutos")
    ax.set_ylabel("Ce (mcg/mL)")
    ax.set_title("Curva simulada de Ce")
    ax.legend()
    st.pyplot(fig)
