import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from models.schnider_full import simulate_schnider_full

# Configurações da página
st.set_page_config(page_title="TIVA-SIM", layout="centered")
st.title("💉 TIVA-SIM — Simulador de TIVA com equipo simples")
st.subheader("Simulação com modelo farmacodinâmico de Schnider (Propofol)")

# Dados do paciente
st.sidebar.header("📋 Dados do Paciente")
idade = st.sidebar.number_input("Idade", 18, 100, 40)
peso = st.sidebar.number_input("Peso (kg)", 30.0, 150.0, 70.0)
altura = st.sidebar.number_input("Altura (cm)", 100.0, 210.0, 170.0)
sexo = st.sidebar.selectbox("Sexo", ["Masculino", "Feminino"])

# Alvos de concentração
st.markdown("### 🎯 Concentração Alvo (Ce)")
propofol_ce = st.slider("Propofol (mcg/mL)", 0.5, 6.0, 3.0, 0.1)

# Controle do metrônomo
ativar_metronomo = st.checkbox("🕒 Ativar metrônomo para ajuste manual (gotas/min)")

# Simulação
if st.button("▶️ Iniciar Infusão"):
    # Cálculo aproximado para estimar taxa de infusão (mg/min)
    V1 = 4.27  # volume central (L) do modelo Schnider
    infusion_rate = propofol_ce * V1           # Ce x V1 = carga total (mg)
    infusion_rate_mg_per_min = infusion_rate / 60  # transforma para mg/min
    infusion_rate_mg_per_h = infusion_rate_mg_per_min * 60

    # Simulação usando o modelo completo
    t, Cp, Ce = simulate_schnider_full(
        duration_min=30,
        infusion_rate_mg_per_min=infusion_rate_mg_per_min
    )

    # Conversão para mcg/mL
    Cp = np.array(Cp) * 1000
    Ce = np.array(Ce) * 1000

    # Cálculo de gotas por minuto
    concentracao_solucao = 10  # mg/mL (propofol puro)
    equipo_macro = 20  # gotas/mL
    volume_por_min = infusion_rate_mg_per_min / concentracao_solucao  # mL/min
    gotas_por_min = volume_por_min * equipo_macro

    # Resultado da simulação
    st.success("💡 Simulação concluída!")
    st.markdown(f"💉 Taxa de infusão simulada: **{infusion_rate_mg_per_h:.1f} mg/h**")
    st.markdown(f"🧪 Ce alvo: **{propofol_ce:.2f} mcg/mL**")
    st.markdown(f"💧 Infusão estimada: **{gotas_por_min:.1f} gotas/min**")

    if ativar_metronomo:
        tempo_entre_gotas = 60 / gotas_por_min if gotas_por_min > 0 else 0
        st.markdown(f"⏱️ <b>Metrônomo:</b> Goteje a cada <b>{tempo_entre_gotas:.1f} segundos</b>", unsafe_allow_html=True)
        st.markdown("🔄 <i>Use um cronômetro ou clique no botão no tempo indicado para manter a infusão estável.</i>", unsafe_allow_html=True)

    # Gráfico da curva
    fig, ax = plt.subplots()
    ax.plot(t, Cp, '--', label="Cp (Plasma)")
    ax.plot(t, Ce, '-', linewidth=2, label="Ce (Efeito)")
    ax.axvline(x=0, color='gray', linestyle=':', label="Início da infusão")
    ax.set_xlabel("Tempo (min)")
    ax.set_ylabel("Concentração (mcg/mL)")
    ax.set_title("Curvas simuladas — Modelo Schnider")
    ax.legend()
    ax.grid(True)
    st.pyplot(fig)
