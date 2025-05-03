import streamlit as st
import numpy as np
import pandas as pd
import time
import matplotlib.pyplot as plt
import streamlit.components.v1 as components

# === Helper: PK parameters Schnider ===

def schnider_pk(weight, height, age):
    V1 = 4.27 - 0.0201*(age-40)           # L
    V2 = 18.9
    Cl1 = 1.89 + 0.0456*(weight-70) - 0.0681*(height-170)  # L/min
    return V1, Cl1

# === Metrónomo HTML ===

def metronome(interval):
    ms = int(interval*1000)
    return f"""
    <div id='dot' style='width:14px;height:14px;border-radius:50%;background:red;'></div>
    <script>
      if(window.metro) clearInterval(window.metro);
      const d=document.getElementById('dot');
      const snd=new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');
      window.metro=setInterval(()=>{snd.play();d.style.visibility=d.style.visibility==='hidden'?'visible':'hidden';},{ms});
    </script>
    """

# === Sidebar ===

st.sidebar.title('🔧 Configurações')
idade = st.sidebar.number_input('Idade',18,100,40)
peso  = st.sidebar.number_input('Peso (kg)',30.,150.,70.)
altura= st.sidebar.number_input('Altura (cm)',100.,210.,170.)
ce_target = st.sidebar.slider('Ce alvo (mcg/mL)',0.5,6.0,3.0,0.1)
duracao  = st.sidebar.slider('Duração (min)',5,120,30)
team = st.sidebar.selectbox('Equipo',['Macro (20 gotas/mL)','Micro (60 gotas/mL)'])
conc = st.sidebar.number_input('Concentração (mg/mL)',1.,20.,10.)
sonoro = st.sidebar.checkbox('Metrônomo sonoro')
modo_teste = st.sidebar.checkbox('Modo teste (x10)')
start = st.sidebar.button('▶️ Iniciar')

gotas_ml=20 if team.startswith('Macro') else 60

# === Main ===

st.title('TIVA‑SIM • Propofol TCI Manual')

if start:
    V1, Cl1 = schnider_pk(peso,altura,idade)
    bolus_mg = ce_target*V1*1000  # mg
    mant_mg_min = ce_target*Cl1   # mg/min

    # cronômetro controlado por session_state
    if 't0' not in st.session_state: st.session_state.t0=time.time()
    elapsed = (time.time()-st.session_state.t0)*(10 if modo_teste else 1)/60  # minutos

    schedule = pd.DataFrame({
        'Tempo_min': np.arange(0,duracao+1),
        'Taxa_mg_min': mant_mg_min,
    })
    schedule['Gotas_min'] = schedule['Taxa_mg_min']/conc*gotas_ml

    # Panel
    cols=st.columns(4)
    cols[0].metric('Bolus inicial (mg)',f"{bolus_mg:.0f}")
    cols[1].metric('Taxa mant. (mg/min)',f"{mant_mg_min:.2f}")
    cols[2].metric('Gotas/min',f"{schedule['Gotas_min'][0]:.1f}")
    intervalo=60/schedule['Gotas_min'][0] if schedule['Gotas_min'][0]>0 else 0
    cols[3].metric('Intervalo (s)',f"{intervalo:.1f}")

    if sonoro and intervalo>0:
        components.html(metronome(intervalo),height=40)

    st.subheader('Tabela de referência')
    st.dataframe(schedule[['Tempo_min','Gotas_min']])

    # Plot gotas vs tempo
    fig,ax=plt.subplots(figsize=(6,3))
    ax.step(schedule['Tempo_min'],schedule['Gotas_min'],where='post')
    ax.set_xlabel('Tempo (min)');ax.set_ylabel('Gotas/min');ax.set_title('Perfil recomendado')
    st.pyplot(fig)

    # CSV download
    st.download_button('⬇️ CSV',schedule.to_csv(index=False).encode(),'tiva_schedule.csv','text/csv')
