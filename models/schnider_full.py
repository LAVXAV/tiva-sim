import numpy as np
from scipy.integrate import odeint

# Modelo Schnider completo com compartimentos e biophase
def schnider_pkpd_model(y, t, infusion_schedule, params):
    A1, A2, A3, Ce = y

    V1 = params["V1"]
    V2 = params["V2"]
    V3 = params["V3"]
    Cl1 = params["Cl1"]
    Cl2 = params["Cl2"]
    Cl3 = params["Cl3"]
    ke0 = params["ke0"]

    Cp = A1 / V1
    infusion_rate = infusion_schedule(t)

    dA1dt = infusion_rate - (Cl1 + Cl2 + Cl3) * Cp + Cl2 * (A2 / V2) + Cl3 * (A3 / V3)
    dA2dt = Cl2 * (Cp - A2 / V2)
    dA3dt = Cl3 * (Cp - A3 / V3)
    dCedt = ke0 * (Cp - Ce)

    return [dA1dt, dA2dt, dA3dt, dCedt]

def simulate_schnider_full(duration_min=30, step=0.1, infusion_rate_mg_per_min=100/60):
    params = {
        "V1": 4.27,
        "V2": 18.9,
        "V3": 238.0,
        "Cl1": 1.89,
        "Cl2": 1.29,
        "Cl3": 0.836,
        "ke0": 0.456
    }

    t = np.arange(0, duration_min + step, step)

    def infusion_schedule(t): return infusion_rate_mg_per_min

    y0 = [0, 0, 0, 0]  # Estado inicial

    sol = odeint(schnider_pkpd_model, y0, t, args=(infusion_schedule, params))

    Cp = sol[:, 0] / params["V1"]
    Ce = sol[:, 3]

    return t, Cp, Ce
