import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import time
import io
import os
from models.schnider_full import simulate_schnider_full
import streamlit.components.v1 as components
from PIL import Image

# Desativar checagem DecompressionBomb
Image.MAX_IMAGE_PIXELS = None

# Configuração da página
st.set_page_config(page_title="TIVA-SIM", layout="wide")
st.title("💉 TIVA-SIM — Simulador de TIVA com equipo simples")

# Abas principais
tab1, tab2, tab3 = st.tabs(["🧪 Parâmetros", "📈 Monitor", "📑 Relatórios"])

# --- Aba 1: Parâmetros --- #
with tab1:
    st.subheader("🧬 Dados do Paciente e Parâmetros")
    c1, c2, c3 = st.columns(3)
    with c1:
        idade = st.number_input("Idade (anos)", 18, 100, 40)
        peso = st.number_input("Peso (kg)", 30.0, 150.0, 70.0)
    with c2:
        altura = st.number_input("Altura (cm)", 100.0, 210.0, 170.0)
        sexo = st.selectbox("Sexo", ["Masculino", "Feminino"])
    with c3:
        tipo_equipo = st.selectbox("💧 Tipo de equipo", ["Macro (20 gotas/mL)", "Micro (60 gotas/mL)"])
        ajuste_manual = st.checkbox("🎛️ Ajustar fases manualmente")

    # Alvos de Ce por fase
    if ajuste_manual:
        ce_inducao = st.slider("🎯 Ce Indução (mcg/mL)", 3.0, 6.0, 4.0, 0.1)
        ce_manutencao = st.slider("🧩 Ce Manutenção (mcg/mL)", 2.0, 4.0, 2.5, 0.1)
        ce_despertar = st.slider("🌅 Ce Despertar (mcg/mL)", 0.5, 2.5, 1.0, 0.1)
    else:
        ce_inducao, ce_manutencao, ce_despertar = 4.0, 2.5, 1.0

    # Viabilidade pré-simulação
    V1 = 4.27 - 0.0201 * (idade - 40)
    gotas_ml = 20 if "Macro" in tipo_equipo else 60
    ce_vals = [ce_inducao, ce_manutencao, ce_despertar]
    intervals = [(60 / ((c * V1 / 60 / 10) * gotas_ml)) for c in ce_vals]
    with st.expander("🔍 Verificar viabilidade manual"):
        st.write(f"Intervalo mínimo: {min(intervals):.1f} s/gota")
        st.write(f"Intervalo máximo: {max(intervals):.1f} s/gota")
        if min(intervals) < 0.5:
            st.warning("⚠️ Infusão muito rápida para controle manual; considere microgota ou bomba.")
        if max(intervals) > 10:
            st.warning("⚠️ Infusão muito lenta para controle manual; ajuste diluição ou equipamento.")

    ativar_metro = st.checkbox("🔔 Metrônomo ativo")
    modo_teste = st.checkbox("⚡ Modo Teste (acelerado)")
    iniciar = st.button("▶️ Iniciar Simulação")

# --- Aba 2: Monitoramento --- #
with tab2:
    st.subheader("📊 Acompanhamento em Tempo Real")
    metrics_col, plot_col = st.columns([1, 3])
    tempo_m = metrics_col.empty()
    fase_m = metrics_col.empty()
    ceinfo_m = metrics_col.empty()
    gotas_m = metrics_col.empty()
    rec_m = metrics_col.empty()
    metro_m = metrics_col.empty()
    plot_area = plot_col.empty()
    progresso = st.progress(0)

# --- Aba 3: Relatórios --- #
with tab3:
    st.subheader("📑 Exportar Resultados")
    csv_dl = st.empty()

# Simulação
if iniciar:
    # Executa modelo Schnider
    t, Cp, Ce = simulate_schnider_full(duration_min=30, infusion_rate_mg_per_min=0.1)
    Cp, Ce = np.array(Cp) * 1000, np.array(Ce) * 1000
    fases = {"Indução": ce_inducao, "Manutenção": ce_manutencao, "Despertar": ce_despertar}
    fase = "Indução"
    log = []

    for i, tm in enumerate(t):
        ce_alvo = fases[fase]
        taxa_h = ce_alvo * V1
        taxa_min = taxa_h / 60
        gotas = (taxa_min / 10) * gotas_ml
        ce_sim = Ce[i]

        # Recomendações de gotejamento
        rec_gotas = (ce_alvo * V1 / 60 / 10) * gotas_ml

        # Atualiza painel de métricas
        tempo_m.metric("Tempo", f"{tm:.1f} min")
        fase_m.metric("Fase", fase)
        ceinfo_m.markdown(f"🎯 Ce alvo: **{ce_alvo:.2f}** | 🧠 Ce sim.: **{ce_sim:.2f}**")
        gotas_m.markdown(f"💧 Gotas/min atual: **{gotas:.1f}**")
        rec_m.info(f"💡 Recomendado: **{rec_gotas:.1f} gotas/min** para fase {fase}")

        # Metrônomo sonoro
        if ativar_metro and gotas > 0:
            interval = 60 / gotas
            metro_m.markdown(f"🔔 Intervalo: **{interval:.1f} s/gota**")
            # Inicia metronomo sonoro e visual via JavaScript
            js = f"""
            <div id='metroBlink' style='width:20px;height:20px;border-radius:50%;background:red;margin-bottom:5px;'></div>
            <script>
              if(window.metInt) clearInterval(window.metInt);
              const blink = document.getElementById('metroBlink');
              let audio = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');
              window.metInt = setInterval(()=>{{
                audio.play();
                blink.style.visibility = (blink.style.visibility === 'hidden' ? 'visible' : 'hidden');
              }}, {int(interval*1000)});
            </script>
            """
            components.html(js, height=60)

        # Gráfico simplificado
        fig, ax = plt.subplots(figsize=(6,3), dpi=100)
        ax.plot(t[:i+1], Ce[:i+1], color='orange', label='Ce sim')
        ax.plot(t[:i+1], Cp[:i+1], '--', color='blue', label='Cp sim')
        ax.axhline(ce_alvo, color='green', linestyle=':', label='Ce alvo')
        ax.set_xlabel('Tempo (min)')
        ax.set_ylabel('mcg/mL')
        ax.legend(loc='upper right')
        plot_area.pyplot(fig)

        progresso.progress(int((i+1)/len(t)*100))
        time.sleep(0.1 if modo_teste else 60)

        # Log de dados
        log.append({
            'Tempo': tm,
            'Fase': fase,
            'Ce_sim': ce_sim,
            'Ce_alvo': ce_alvo,
            'Gotas_min': gotas,
            'Rec_gotas': rec_gotas
        })

    # Fim da simulação
    st.success("✅ Simulação concluída.")
    df = pd.DataFrame(log)
    csv_dl.download_button("⬇️ Baixar CSV", df.to_csv(index=False).encode(), "tiva_sim.csv", "text/csv")
