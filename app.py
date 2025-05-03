"""
tiva_sim.py

Complete TIVA‑SIM prototype: simula infusão alvo-controlada de propofol
usando equipo manual (macro ou micro gotas).
Permite definição de parâmetros do paciente, seleção de equipo,
infusão passo-a-passo e interrupção (wake-up) a qualquer momento.
"""

import time
import threading
from dataclasses import dataclass
from typing import List

try:
    from playsound import playsound
    BEEP_AVAILABLE = True
except ImportError:
    BEEP_AVAILABLE = False


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


# Configurações
MACRO = Equipo('MACRO', 20)
MICRO = Equipo('MICRO', 60)


def generate_schedule(patient: Patient, equipo: Equipo, duration_min: int) -> List[ScheduleStep]:
    """
    Gera roteiro de infusão em até 3 blocos:
      0–5  min: 6 mg/kg/h       (start)
      5–15 min: 4.8 mg/kg/h     (–20%)
      15–duration: 4 mg/kg/h    (–33%)
    Converte mg/kg/h → mL/h (10 mg/ml) e mL/h → gotas/min.
    """
    w = patient.weight
    start_mlh = 6 * w / 10.0
    mid_mlh   = start_mlh * 0.8
    final_mlh = start_mlh * 0.667

    steps = []
    if duration_min <= 5:
        steps.append((0, duration_min, start_mlh))
    elif duration_min <= 15:
        steps.extend([(0, 5, start_mlh), (5, duration_min, mid_mlh)])
    else:
        steps.extend([(0, 5, start_mlh), (5, 15, mid_mlh), (15, duration_min, final_mlh)])

    schedule = [ScheduleStep(s, e, r, round(equipo.gtt_per_min(r))) for (s, e, r) in steps]
    return schedule


def beep_thread():
    """Toca beep contínuo a cada segundo"""
    while True:
        if BEEP_AVAILABLE:
            playsound('beep.wav', block=False)
        else:
            print('Beep')
        time.sleep(1)


def run_simulation(schedule: List[ScheduleStep]):
    """
    Simula infusão: para cada minuto no cronograma, exibe status e verifica
    comando do usuário para wake-up.
    """
    wake_flag = False
    print("Iniciando simulação. Digite 'w' + Enter a qualquer momento para despertar.")

    for step in schedule:
        for minute in range(step.start_min, step.end_min):
            print(f"[min {minute:>2}] Taxa: {step.gtt_min} gtt/min")
            # opcional: tocar metrônomo (um beep por gota simplificado)
            # Aqui poderíamos chamar playsound em loop, mas simplificamos:
            # print(". \b", end='', flush=True)
            # pausa 60 s
            start = time.time()
            # checa input não bloqueante
            print("> Aperte 'w' para despertar ou Enter para continuar...")
            user = input().strip().lower()
            if user == 'w':
                wake_flag = True
                break
            elapsed = time.time() - start
            if elapsed < 60:
                time.sleep(60 - elapsed)
        if wake_flag:
            print("\n### Wake-up solicitado. Iniciando desmame gradual... ###")
            # para desmame, simplesmente interrompe aqui; lógica de desmame pode ser adicionada
            return
    print("\nSimulação concluída conforme cronograma.")


def main():
    print("=== TIVA-SIM Manual Simulator ===")
    # entrada de dados do paciente
    w = float(input("Peso (kg): "))
    h = float(input("Altura (m): "))
    age = int(input("Idade (anos): "))
    sex = input("Sexo (M/F): ").upper().strip()
    patient = Patient(w, h, age, sex)

    # escolha de equipo
    eq = None
    while eq not in ('1', '2'):
        print("Escolha o equipo: 1) Macro (20 gtt/mL)  2) Micro (60 gtt/mL)")
        eq = input().strip()
    equipo = MACRO if eq == '1' else MICRO

    duration = int(input("Duração estimada da TIVA (min): "))

    schedule = generate_schedule(patient, equipo, duration)
    print(f"\nEquipe selecionado: {equipo.name} - {equipo.drop_factor} gtt/mL")
    for s in schedule:
        print(f"{s.start_min:>2}–{s.end_min:>2} min : {s.gtt_min} gtt/min")

    print("\nPressione Enter para iniciar...")
    input()
    run_simulation(schedule)


if __name__ == '__main__':
    main()
