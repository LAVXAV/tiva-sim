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

st.set_page_config(page_title="TIVA-SIM", layout="wide")
st.title("💉 TIVA-SIM — Simulador de TIVA com equipo simples")

aba1, aba2, aba3 = st.tabs(["🧪 Painel de Controle", "📈 Monitoramento", "📑 Relatórios"])

with aba1:
    st.subheader("📋 Parâmetros do Paciente")
    col1, col2 = st.columns(2)
    with col1:
        idade = st.number_input("Idade", 18, 100, 40)
        peso = st.number_input("Peso (kg)", 30.0, 150.0, 70.0)
        altura = st.number_input("Altura (cm)", 100.0, 210.0, 170.0)
    with col2:
        sexo = st.selectbox("Sexo", ["Masculino", "Feminino"])
        obs_clinicas = st.text_area("📝 Observações Clínicas (opcional)")
        ce_custom = st.checkbox("🔧 Ajuste fino de Ce por fase")

    tipo_equipo = st.selectbox("💧 Tipo de equipo", ["Macro (20 gotas/mL)", "Micro (60 gotas/mL)"])

    st.subheader("⚙️ Configurações da Simulação")
    col3, col4 = st.columns(2)
    with col3:
        ativar_metronomo = st.checkbox("🕒 Metrônomo (gotas/min)")
        acelerar_simulacao = st.checkbox("⚡ Modo Teste (acelerado)")

    if ce_custom:
        ce_inducao = st.slider("🎯 Ce Indução (mcg/mL)", 3.0, 6.0, 4.0, 0.1)
        ce_manutencao = st.slider("🎯 Ce Manutenção (mcg/mL)", 2.0, 4.0, 2.5, 0.1)
        ce_despertar = st.slider("🎯 Ce Despertar (mcg/mL)", 0.5, 2.5, 1.0, 0.1)
    else:
        ce_inducao = 4.0
        ce_manutencao = 2.5
        ce_despertar = 1.0

    V1_preview = 4.27 - 0.0201 * (idade - 40)
    gotas_por_ml_preview = 20 if "Macro" in tipo_equipo else 60
    ce_values = [ce_inducao, ce_manutencao, ce_despertar]
    intervalos = [(60 / ((ce * V1_preview / 60 / 10) * gotas_por_ml_preview)) for ce in ce_values]
    min_intervalo = min(intervalos)
    max_intervalo = max(intervalos)
    if max_intervalo > 10:
        st.warning("⚠️ O ritmo de infusão pode ser muito lento com equipo simples. Considere ajuste de diluição ou bomba.")
    elif min_intervalo < 0.5:
        st.warning("⚠️ O ritmo de infusão pode ser rápido demais para controle manual. Ajustes finos podem ser imprecisos.")

    iniciar = st.button("▶️ Iniciar Infusão")
    parar = st.button("⏹️ Parar Simulação")

with aba2:
    st.subheader("📈 Acompanhamento da Infusão e Concentração")
    cronometro = st.empty()
    fase_display = st.empty()
    fase_seletor = st.empty()
    info_taxa = st.empty()
    info_gotejamento = st.empty()
    metrônomo_display = st.empty()
    grafico_ce = st.empty()
    barra_progresso = st.progress(0, text="Progresso da simulação")

with aba3:
    st.subheader("📑 Exportação dos Dados e Gráficos")
    relatorio_csv = st.empty()

if iniciar:
    concentracao_solucao = 10
    equipo_macro = 20 if "Macro" in tipo_equipo else 60

    t, Cp, Ce = simulate_schnider_full(duration_min=30, infusion_rate_mg_per_min=0.1)
    Cp = np.array(Cp) * 1000
    Ce = np.array(Ce) * 1000

    V1 = 4.27 - 0.0201 * (idade - 40)
    fase_opcoes = {"Indução": ce_inducao, "Manutenção": ce_manutencao, "Despertar": ce_despertar}
    fase_atual = "Indução"
    fases_log = [(0, fase_atual)]
    dados_log = []
    marcadores_criticos = []

    for i in range(1, len(t)):
        tempo_min = t[i]
        nova_fase = fase_seletor.radio("🔄 Alterar fase em tempo real:", list(fase_opcoes.keys()), index=list(fase_opcoes.keys()).index(fase_atual), key=f"fase_{i}")
        if nova_fase != fase_atual:
            fase_atual = nova_fase
            fases_log.append((tempo_min, fase_atual))
            marcadores_criticos.append((tempo_min, f"Mudança: {fase_atual}"))

        propofol_ce = fase_opcoes[fase_atual]
        infusion_rate = propofol_ce * V1
        infusion_rate_mg_per_min = infusion_rate / 60
        infusion_rate_mg_per_h = infusion_rate
        volume_por_min = infusion_rate_mg_per_min / concentracao_solucao
        gotas_por_min = volume_por_min * equipo_macro
        ce_atual = Ce[i]

        if abs(ce_atual - propofol_ce) > 0.5:
            marcadores_criticos.append((tempo_min, f"Ajustar infusão (Ce={ce_atual:.1f})"))
        if gotas_por_min < 1:
            marcadores_criticos.append((tempo_min, f"Gotejamento <1 gota/min — considerar microgotas"))
        if i > 1:
            gotas_anterior = dados_log[-1]['Gotas/min']
            if abs(gotas_por_min - gotas_anterior) / max(gotas_anterior, 1) > 0.2:
                marcadores_criticos.append((tempo_min, f"Variação >20% no gotejamento"))

        dados_log.append({
            "Tempo (min)": tempo_min,
            "Fase": fase_atual,
            "Ce (mcg/mL)": ce_atual,
            "Taxa (mg/h)": infusion_rate_mg_per_h,
            "Gotas/min": gotas_por_min
        })

        cronometro.markdown(f"⏱️ Tempo: **{tempo_min:.1f} min**")
        fase_display.markdown(f"""
        <b>Fase atual:</b> {fase_atual}<br>
        🎯 <b>Ce alvo (ajustado):</b> {propofol_ce:.1f} mcg/mL ±0.5<br>
        🧠 <b>Ce estimada (modelo):</b> {ce_atual:.2f} mcg/mL<br><br>
        <button onclick=\"alert('📘 Ce (efeito): concentração simulada no compartimento efetor, calculada pelo modelo farmacodinâmico Schnider.\n\n📘 Cp (plasma): concentração no plasma.\n\n🔍 O modelo presume paciente padrão. Diferenças fisiológicas podem afetar o efeito real.')\">❓ O que é Ce e Cp?</button><br>
        <button onclick=\"alert('✅ Ce dentro da faixa desejada: seguir infusão conforme planejado.\n\nℹ️ Ce próxima do alvo: considerar ajuste em breve.\n\n⚠️ Ce fora do intervalo: ajuste da infusão recomendado.')\">❓ Como interpretar os alertas?</button><br>
        <button onclick=\"alert('📋 Guia rápido do TIVA-SIM:\n\n1️⃣ Insira os dados do paciente e selecione o tipo de equipo.\n2️⃣ Ajuste os alvos de Ce conforme desejado.\n3️⃣ Inicie a simulação para visualizar a curva de infusão.\n4️⃣ Observe o gráfico e as orientações de ajuste manual.\n5️⃣ Baixe os relatórios ao final (CSV, gráfico e PDF).')\">📘 Guia rápido do TIVA-SIM</button>
        """, unsafe_allow_html=True)

        if abs(ce_atual - propofol_ce) > 0.5:
            st.warning("⚠️ Ce estimada está fora da faixa esperada. Ajuste manual pode ser necessário.")
        elif abs(ce_atual - propofol_ce) > 0.3:
            st.info("ℹ️ Ce estimada próxima do alvo. Acompanhar evolução antes de ajustar.")
        else:
            st.success("✅ Ce estimada dentro da faixa desejada para esta fase.")

        tempo_entre_gotas = 60 / gotas_por_min if gotas_por_min > 0 else 0
        if ativar_metronomo:
            js_metronomo = f"""
            <script>
            if (window.metronomeInterval) clearInterval(window.metronomeInterval);
            let audio = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');
            window.metronomeInterval = setInterval(() => {{ audio.play(); }}, {int(tempo_entre_gotas * 1000)});
            </script>
            """
        else:
            js_metronomo = """
            <script>
            if (window.metronomeInterval) clearInterval(window.metronomeInterval);
            </script>
            """
        components.html(js_metronomo, height=0)
        metrônomo_display.markdown(f"🎵 Intervalo estimado: <b>{tempo_entre_gotas:.1f} s/gota</b>", unsafe_allow_html=True)

        fig, ax = plt.subplots()
        ax.plot(t[:i], Cp[:i], '--', label="Cp (Plasma)")
        ax.plot(t[:i], Ce[:i], '-', linewidth=2, label="Ce (Efeito)")
        for tempo_fase, nome_fase in fases_log:
            ax.axvline(x=tempo_fase, linestyle=':', color='red', alpha=0.5)
            ax.text(tempo_fase, max(Ce)*0.95, nome_fase, rotation=90, fontsize=8, color='red')
        for tempo_evento, evento in marcadores_criticos:
            ax.axvline(x=tempo_evento, linestyle='--', color='orange', alpha=0.5)
            ax.text(tempo_evento, max(Ce)*0.80, evento, rotation=90, fontsize=7, color='orange')
        ax.set_xlabel("Tempo (min)")
        ax.set_ylabel("Concentração (mcg/mL)")
        ax.set_title("Curvas simuladas — Modelo Schnider")
        ax.legend()
        ax.grid(True)
        grafico_ce.pyplot(fig)

        barra_progresso.progress(int((i / len(t)) * 100), text=f"{tempo_min:.1f} minutos de 30")

        time.sleep(0.1 if acelerar_simulacao else 60)

    st.success("🟢 Simulação finalizada.")

    df_log = pd.DataFrame(dados_log)
    relatorio_csv.download_button("⬇️ Baixar CSV", data=df_log.to_csv(index=False).encode("utf-8"), file_name="tiva_sim_log.csv", mime="text/csv")
