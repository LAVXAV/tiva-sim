import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import time
import io
import os
from fpdf import FPDF
from models.schnider_full import simulate_schnider_full
import streamlit.components.v1 as components

# Configuração da página
st.set_page_config(page_title="TIVA-SIM", layout="wide")
st.title("💉 TIVA-SIM — Simulador de TIVA com equipo simples")

# Abas
tab1, tab2, tab3 = st.tabs(["🧪 Parâmetros", "📈 Monitor", "📑 Relatórios"])

# --- Aba 1: Parâmetros --- #
with tab1:
    st.subheader("🧬 Parâmetros do Paciente e Simulação")
    c1, c2 = st.columns(2)
    with c1:
        idade = st.number_input("Idade (anos)", 18, 100, 40)
        peso = st.number_input("Peso (kg)", 30.0, 150.0, 70.0)
        altura = st.number_input("Altura (cm)", 100.0, 210.0, 170.0)
        sexo = st.selectbox("Sexo", ["Masculino", "Feminino"])
    with c2:
        tipo_equipo = st.selectbox("💧 Tipo de equipo", ["Macro (20 gotas/mL)", "Micro (60 gotas/mL)"])
        ce_custom = st.checkbox("🎛️ Ajustar fases manualmente")
        if ce_custom:
            ce_inducao = st.slider("🎯 Ce Indução (mcg/mL)", 3.0, 6.0, 4.0, 0.1)
            ce_manutencao = st.slider("🧩 Ce Manutenção (mcg/mL)", 2.0, 4.0, 2.5, 0.1)
            ce_despertar = st.slider("🌅 Ce Despertar (mcg/mL)", 0.5, 2.5, 1.0, 0.1)
        else:
            ce_inducao, ce_manutencao, ce_despertar = 4.0, 2.5, 1.0

    # Antevisão de viabilidade
    V1 = 4.27 - 0.0201 * (idade - 40)
    gotas_por_ml = 20 if "Macro" in tipo_equipo else 60
    ce_vals = [ce_inducao, ce_manutencao, ce_despertar]
    intervalos = [(60 / ((ce * V1 / 60 / 10) * gotas_por_ml)) for ce in ce_vals]
    with st.expander("ℹ️ Verificação de viabilidade manual"):
        st.markdown(f"- Intervalo mínimo: {min(intervalos):.1f} s/gota")
        st.markdown(f"- Intervalo máximo: {max(intervalos):.1f} s/gota")
        if min(intervalos) < 0.5:
            st.warning("⚠️ Infusão muito rápida para controle manual; considere microgota ou bomba.")
        if max(intervalos) > 10:
            st.warning("⚠️ Infusão muito lenta; ajuste diluição ou equipamento.")

    ativar_metro = st.checkbox("🎵 Ativar/Desativar Metrônomo")
    modo_teste = st.checkbox("⚡ Modo Teste (acelerado)")
    btn_start = st.button("🚀 Iniciar Simulação")

# --- Aba 2: Monitoramento --- #
with tab2:
    st.subheader("📊 Acompanhamento Dinâmico da Infusão")
    left, right = st.columns([1,3])
    with left:
        m_tempo = st.empty()
        m_fase = st.empty()
        m_ce = st.empty()
        m_taxa = st.empty()
        m_metro = st.empty()
    with right:
        graf = st.empty()
    prog = st.progress(0)

# --- Aba 3: Relatórios --- #
with tab3:
    st.subheader("📑 Exportação de Resultados")
    dl_csv = st.empty()
    dl_pdf = st.empty()

# Execução da simulação
if btn_start:
    t, Cp, Ce = simulate_schnider_full(duration_min=30, infusion_rate_mg_per_min=0.1)
    Cp, Ce = np.array(Cp) * 1000, np.array(Ce) * 1000
    fases = {"Indução": ce_inducao, "Manutenção": ce_manutencao, "Despertar": ce_despertar}
    fase = "Indução"
    log = []

    for i, tm in enumerate(t):
        ce_alvo = fases[fase]
        taxa = ce_alvo * V1             # mg/h
        taxa_min = taxa / 60            # mg/min
        gotas = (taxa_min/10) * gotas_por_ml
        ce_mod = Ce[i]

        # Atualiza métricas
        m_tempo.metric("Tempo", f"{tm:.1f} min")
        m_fase.metric("Fase", fase)
        m_ce.markdown(f"**Ce alvo:** {ce_alvo:.2f}  **Ce sim.:** {ce_mod:.2f}")
        m_taxa.markdown(f"**Gotas/min:** {gotas:.1f}")

        # Metrônomo sonoro
        if ativar_metro and gotas>0:
            intervalo = 60/gotas
            js = f"""
            <script>
            if(window.metInt) clearInterval(window.metInt);
            let snd=new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');
            window.metInt=setInterval(()=>snd.play(),{int(intervalo*1000)});
            </script>
            """
            components.html(js, height=0)
            m_metro.markdown(f"🔔 {intervalo:.1f}s/gota")

        # Gráfico otimizado
        fig, ax = plt.subplots(figsize=(6,3), dpi=100)
        ax.plot(t[:i+1], Ce[:i+1], color='orange', label='Ce')
        ax.plot(t[:i+1], Cp[:i+1], '--', color='blue', label='Cp')
        ax.set_ylim(0, max(ce_vals)*1.2)
        ax.set_xlabel('Tempo (min)')
        ax.set_ylabel('mcg/mL')
        ax.legend()
        graf.pyplot(fig)

        prog.progress(int((i+1)/len(t)*100))
        time.sleep(0.1 if modo_teste else 60)
        log.append({'Tempo':tm,'Fase':fase,'Ce_sim':ce_mod,'Ce_alvo':ce_alvo,'Gotas/min':gotas})

    st.success("✅ Simulação concluída!")
    df=pd.DataFrame(log)
    dl_csv.download_button("⬇️ CSV", df.to_csv(index=False).encode(),"rel.csv","text/csv")
    # PDF se desejado
    buffer=io.BytesIO()
    pdf=FPDF()
    pdf.add_page()
    pdf.set_font('Arial','B',12)
    pdf.cell(0,10,'TIVA-SIM Relatorio',ln=True)
    for row in log[:5]: pdf.cell(0,8,str(row),ln=True)
    pdf.output(buffer)
    buffer.seek(0)
    dl_pdf.download_button('📄 PDF',buffer,'rel.pdf','application/pdf')
