import streamlit as st
import matplotlib.pyplot as plt
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

# Simulação
if st.button("▶️ Iniciar Infusão"):
    # Cálculo aproximado para estimar taxa de infusão (mg/min)
    V1 = 4.27  # volume central (L) do modelo Schnider
    infusion_rate = propofol_ce * V1           # Ce x V1 = carga total (mg)
    infusion_rate_mg_per_min = infusion_rate / 60  # transforma para mg/min

    # Simulação usando o modelo completo
    t, Cp, Ce = simulate_schnider_full(
        duration_min=30,
        infusion_rate_mg_per_min=infusion_rate_mg_per_min
    )

    # Resultados
    st.success("💡 Simulação concluída!")
    st.markdown(f"💉 Taxa de infusão simulada: **{infusion_rate:.1f} mg/h**")
    st.markdown(f"📈 Ce alvo: **{propofol_ce:.2f} mcg/mL**")

    # Gráfico
    fig, ax = plt.subplots()
    ax.plot(t, Cp, '--', label="Cp (Plasma)")
    ax.plot(t, Ce, '-', linewidth=2, label="Ce (Efeito)")
    ax.set_xlabel("Tempo (min)")
    ax.set_ylabel("Concentração (mg/L)")
    ax.set_title("Curvas simuladas — Modelo Schnider")
    ax.legend()
    ax.grid(True)
    st.pyplot(fig)
