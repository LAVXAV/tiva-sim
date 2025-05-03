import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import time
from models.schnider_full import simulate_schnider_full
import streamlit.components.v1 as components

# Configuração da página
st.set_page_config(page_title="TIVA-SIM", layout="centered")
st.title("💉 TIVA-SIM — Infusão Alvo-Controlada Manual de Propofol")

# Sidebar: parâmetros
with st.sidebar:
    st.header("Parâmetros do Paciente")
    idade = st.number_input("Idade (anos)", 18, 100, 40)
    peso = st.number_input("Peso (kg)", 30.0, 150.0, 70.0)
    altura = st.number_input("Altura (cm)", 100.0, 210.0, 170.0)
    sexo = st.selectbox("Sexo", ["Masculino","Feminino"])
    st.header("Configuração da Infusão")
    tipo_eq = st.selectbox("Tipo de equipo", ["Macro (20 gotas/mL)", "Micro (60 gotas/mL)"])
    conc_sol = st.number_input("Concentração propofol (mg/mL)", 1.0, 20.0, 10.0)
    ce_target = st.slider("Ce alvo (mcg/mL)", 0.5, 6.0, 3.0, 0.1)
    duracao = st.slider("Duração (min)", 1, 60, 30)
    ativar_metro = st.checkbox("Ativar metrônomo sonoro e visual")
    modo_teste = st.checkbox("Modo Teste (acelerado)")
    btn_simular = st.button("▶️ Simular Infusão")

# Cálculo V1 e gotas por mL
V1 = 4.27 - 0.0201*(idade-40)
gotas_ml = 20 if tipo_eq.startswith("Macro") else 60

def render_metronome(interval_s: float):
    html = f"""
    <div id='dot' style='width:12px;height:12px;border-radius:50%;background:red;'></div>
    <script>
      if(window.metInt) clearInterval(window.metInt);
      const dot = document.getElementById('dot');
      let snd = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');
      window.metInt = setInterval(() => {{ snd.play(); dot.style.visibility = dot.style.visibility==='hidden'?'visible':'hidden'; }}, {int(interval_s*1000)});
    </script>
    """
    components.html(html, height=30)

# Simulação dinâmica
if btn_simular:
    st.subheader("📈 Monitoramento em Tempo Real da Infusão")
    # placeholders
    place_rate = st.empty()
    place_gotas = st.empty()
    place_interval = st.empty()
    place_chart = st.empty()

    # calcula taxa e arrays de tempo
    taxa_mgh = ce_target * V1
    taxa_mgmin = taxa_mgh / 60
    gotas_min = taxa_mgmin / conc_sol * gotas_ml
    interval_s = 60 / gotas_min if gotas_min>0 else 0

    # exibe taxa fixa
    place_rate.metric("Taxa infusão (mg/h)", f"{taxa_mgh:.1f}")
    place_gotas.metric("Gotas/min estimadas", f"{gotas_min:.2f}")
    if ativar_metro and interval_s>0:
        place_interval.write(f"🔔 Intervalo: **{interval_s:.1f} s/gota**")
    
    # simula com Schnider
    t, Cp, Ce = simulate_schnider_full(duration_min=duracao, infusion_rate_mg_per_min=taxa_mgmin)
    Cp = np.array(Cp)*1000
    Ce = np.array(Ce)*1000
    df_log = pd.DataFrame(columns=["Tempo","Cp","Ce"])

    # loop de atualização
    for i, tm in enumerate(t):
        # render metronomo a cada segundo
        if ativar_metro and interval_s>0:
            render_metronome(interval_s)
        
        # atualiza gráfico incremental
        fig, ax = plt.subplots()
        ax.plot(t[:i+1], Ce[:i+1], color='orange', label='Ce')
        ax.axhline(ce_target, color='green', linestyle='--', label='Ce alvo')
        ax.set_xlim(0, duracao)
        ax.set_ylim(0, max(ce_target*1.2, max(Ce)*1.1))
        ax.set_xlabel('Tempo (min)')
        ax.set_ylabel('Concentração (mcg/mL)')
        ax.legend()
        place_chart.pyplot(fig)

        # log
        df_log.loc[i] = [tm, Cp[i], Ce[i]]

        # aguarda
        time.sleep(0.1 if modo_teste else 1)

    st.success("✔️ Simulação concluída")
    st.download_button("⬇️ Baixar CSV", df_log.to_csv(index=False).encode(), "tiva_sim.csv", "text/csv")
