import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import time
from models.schnider_full import simulate_schnider_full
import streamlit.components.v1 as components
from PIL import Image

# Configuração geral
st.set_page_config(page_title="TIVA-SIM", layout="centered")
st.title("💉 TIVA-SIM — Infusão Alvo-Controlada Manual de Propofol")

# Sidebar: parâmetros
with st.sidebar:
    st.header("Parâmetros do Paciente")
    idade = st.number_input("Idade (anos)", 18, 100, 40)
    peso = st.number_input("Peso (kg)", 30.0, 150.0, 70.0)
    altura = st.number_input("Altura (cm)", 100.0, 210.0, 170.0)
    sexo = st.selectbox("Sexo", ["Masculino","Feminino"])
    st.header("Parâmetros da Infusão")
    tipo_eq = st.selectbox("Tipo de equipo", ["Macro (20 g/mL)", "Micro (60 g/mL)"])
    conc_sol = st.number_input("Conc. propofol (mg/mL)", 1.0, 20.0, 10.0)
    ce_target = st.slider("Concentração Alvo (Ce, mcg/mL)", 0.5, 6.0, 3.0, 0.1)
    duracao = st.slider("Duração (min)", 1, 120, 30)
    ativar_metro = st.checkbox("Ativar metrônomo sonoro e visual")
    modo_teste = st.checkbox("Modo teste (acelerado)")
    simular = st.button("Simular infusão")

# Cálculo de V1
V1 = 4.27 - 0.0201*(idade-40)  # Volume central (L)
gotas_ml = 20 if tipo_eq.startswith("Macro") else 60

# Metronomo
def render_metronome(interval_s):
    ms = int(interval_s*1000)
    html = f"""
    <div id='dot' style='width:12px;height:12px;border-radius:50%;background:red;'></div>
    <script>
      if(window.met) clearInterval(window.met);
      const dot=document.getElementById('dot');
      let snd=new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');
      window.met=setInterval(()=>{{ snd.play(); dot.style.visibility = dot.style.visibility==='hidden'?'visible':'hidden'; }}, {ms});
    </script>
    """
    components.html(html, height=30)

# Simulação
if simular:
    st.subheader("📊 Resultados da Simulação")
    # Infusão constante para Ce_target: taxa (mg/h) = Ce_target * V1
    taxa_mgh = ce_target * V1
    taxa_mgmin = taxa_mgh/60
    gotas_min = taxa_mgmin/conc_sol * gotas_ml
    st.metric("Taxa infusão (mg/h)", f"{taxa_mgh:.1f}")
    st.metric("Gotas/min (aprox.)", f"{gotas_min:.1f}")

    # Metronomo
    if ativar_metro and gotas_min>0:
        intervalo = 60/gotas_min
        st.write(f"🔔 Intervalo: **{intervalo:.1f} s/gota**")
        render_metronome(intervalo)

    # Executa modelo Schnider
    dur = duracao
    t, Cp, Ce = simulate_schnider_full(duration_min=dur, infusion_rate_mg_per_min=taxa_mgmin)
    Cp = np.array(Cp)*1000
    Ce = np.array(Ce)*1000

    # Plota curva
    fig, ax = plt.subplots(figsize=(6,4))
    ax.plot(t, Ce, label='Ce simulado', color='orange')
    ax.axhline(ce_target, linestyle='--', color='green', label='Ce alvo')
    ax.set_xlabel('Tempo (min)')
    ax.set_ylabel('Concentração (mcg/mL)')
    ax.set_title('Evolução da Ce para infusão constante')
    ax.legend()
    st.pyplot(fig)

    # Export data
    df = pd.DataFrame({'Tempo':t, 'Cp':Cp, 'Ce':Ce})
    csv = df.to_csv(index=False).encode()
    st.download_button('⬇️ Baixar CSV', csv, 'tiva_sim.csv', 'text/csv')
