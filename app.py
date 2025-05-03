"""
tiva_sim_schedule.py

Prototype completo do TIVA-SIM: simula infusão alvo-controlada de propofol
usando equipo manual (macro ou micro gotas), com possibilidade de despertar
(interrupção) a qualquer momento via Ctrl+C.
"""

import time
from dataclasses import dataclass
from typing import List

@dataclass
class Patient:
    weight: float   # kg
    height: float   # m
    age: int        # anos
    sex: str        # 'M' ou 'F'

@dataclass
class Equipo:
    name: str
    drop_factor: int  # gotas por mL

    def gtt_per_min(self, rate_ml_h: float) -> float:
        return rate_ml_h * self.drop_factor / 60.0

@dataclass
class ScheduleStep:
    start_min: int
    end_min: int
    rate_ml_h: float
    gtt_min: int

# Equipos disponíveis
MACRO = Equipo('MACRO', 20)
MICRO = Equipo('MICRO', 60)


def generate_schedule(patient: Patient, equipo: Equipo, duration_min: int) -> List[ScheduleStep]:
    """
    Gera roteiro de infusão em até 3 blocos:
      0–5  min: 6 mg/kg/h       (indução/plateau inicial)
      5–15 min: 4.8 mg/kg/h     (redução 20%)
      15–duração: 4 mg/kg/h    (redução 33%)
    Converte mg/kg/h → mL/h (Propofol: 10 mg/mL) e mL/h → gotas/min.
    """
    w = patient.weight
    start_mlh = 6 * w / 10.0
    mid_mlh   = start_mlh * 0.8
    final_mlh = start_mlh * 0.667

    raw = []
    if duration_min <= 5:
        raw.append((0, duration_min, start_mlh))
    elif duration_min <= 15:
        raw.extend([(0, 5, start_mlh), (5, duration_min, mid_mlh)])
    else:
        raw.extend([(0, 5, start_mlh), (5, 15, mid_mlh), (15, duration_min, final_mlh)])

    return [ScheduleStep(s, e, r, round(equipo.gtt_per_min(r))) for s, e, r in raw]


def run_simulation(schedule: List[ScheduleStep]):
    """
    Executa simulação de infusão: mostra cada minuto a taxa em gotas/min,
    e permite despertar a qualquer momento com Ctrl+C.
    """
    print("Iniciando simulação. Pressione Ctrl+C a qualquer momento para despertar.")
    try:
        for step in schedule:
            for minute in range(step.start_min, step.end_min):
                print(f"[min {minute:>2}] Taxa: {step.gtt_min} gtt/min")
                time.sleep(60)  # simula 1 minuto
    except KeyboardInterrupt:
        print("\n### Wake-up solicitado! Interrompendo infusão... ###")
        return
    print("\nSimulação concluída conforme cronograma.")


def main():
    # Entrada de dados
    print("=== TIVA-SIM Manual Simulator ===")
    w = float(input("Peso (kg): "))
    h = float(input("Altura (m): "))
    age = int(input("Idade (anos): "))
    sex = input("Sexo (M/F): ").upper().strip()
    patient = Patient(w, h, age, sex)

    # Seleção de equipo anterior à infusão
    opt = None
    while opt not in ('1', '2'):
        print("Escolha o equipo: 1) Macro (20 gtt/mL)   2) Micro (60 gtt/mL)")
        opt = input().strip()
    equipo = MACRO if opt == '1' else MICRO

    duration = int(input("Duração estimada da TIVA (min): "))
    schedule = generate_schedule(patient, equipo, duration)

    # Exibe resumo
    print(f"\nEquipo selecionado: {equipo.name} ({equipo.drop_factor} gtt/mL)")
    for s in schedule:
        print(f"{s.start_min:>2}–{s.end_min:>2} min : {s.gtt_min} gtt/min")

    input("\nPressione Enter para iniciar...")
    run_simulation(schedule)


if __name__ == '__main__':
    main()
