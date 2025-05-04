// File: package.json
{
  "name": "tiva-sim",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.0.0",
    "react-dom": "^18.0.0",
    "zustand": "^4.0.0",
    "plotly.js": "^2.20.0",
    "tone": "^14.7.77",
    "pyodide": "^0.23.2"
  },
  "devDependencies": {
    "vite": "^4.0.0",
    "@vitejs/plugin-react": "^3.0.0"
  }
}

// File: vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: { port: 3000 }
});

// File: src/main.jsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// File: src/index.css
@tailwind base;
@tailwind components;
@tailwind utilities;

// File: src/stores/agentStore.js
import create from 'zustand';

export const useAgentStore = create((set) => ({
  agents: [],
  addAgent: (agent) => set(state => ({ agents: [...state.agents, agent] })),
  updateAgent: (id, data) => set(state => ({
    agents: state.agents.map(a => a.id === id ? { ...a, ...data } : a)
  })),
  reset: () => set({ agents: [] })
}));

// File: src/utils/pkpdEngine.js
// Initialize Pyodide and expose compute functions
import { loadPyodide } from 'pyodide';

let pyodide = null;
export async function initPyodide() {
  if (!pyodide) pyodide = await loadPyodide({ indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.23.2/full/' });
  await pyodide.loadPackage(['numpy']);
  const code = `
import numpy as np

def simulate_cp(rate_ml_h, weight, ke0, dt, duration):
    # simple one-compartment simulation placeholder
    steps = int(duration/dt)
    cp = np.zeros(steps)
    for i in range(1, steps):
        cp[i] = cp[i-1] + (rate_ml_h/60.0 - ke0*cp[i-1]) * dt
    return cp.tolist()
`;
  pyodide.runPython(code);
  return pyodide;
}

export function computeCP(rate, weight, ke0, dt, duration) {
  return pyodide.globals.get('simulate_cp')(rate, weight, ke0, dt, duration);
}

// File: src/components/AgentPanel.jsx
import React, { useEffect, useState } from 'react';
import Plot from 'react-plotly.js';
import { initPyodide, computeCP } from '../utils/pkpdEngine';
import { useAgentStore } from '../stores/agentStore';
import * as Tone from 'tone';

export default function AgentPanel({ agent }) {
  const { updateAgent } = useAgentStore();
  const [cpData, setCpData] = useState([]);
  const [ceData, setCeData] = useState([]);
  const [pyReady, setPyReady] = useState(false);

  useEffect(() => {
    initPyodide().then(() => setPyReady(true));
  }, []);

  useEffect(() => {
    if (!pyReady) return;
    const dt = 1/60; // 1 second
    const duration = agent.timeElapsed/60;
    const cp = computeCP(agent.rate, agent.weight, agent.ke0, dt, duration);
    const ce = cp.map((c, i) => agent.cePrev + agent.ke0 * (c - agent.cePrev) * dt);
    setCpData(cp);
    setCeData(ce);
  }, [agent.timeElapsed, agent.rate, pyReady]);

  // Metrônomo e alarme
  const startTone = () => {
    const synth = new Tone.MembraneSynth().toDestination();
    Tone.Transport.scheduleRepeat(time => synth.triggerAttackRelease('C2', '8n', time), '0.5');
    Tone.Transport.start();
  };

  return (
    <div className="p-4 bg-white dark:bg-gray-800 rounded-2xl shadow-md mb-4">
      <h2 className="text-xl font-semibold">{agent.name}</h2>
      <div>Ce: {ceData.at(-1)?.toFixed(2)} {agent.unit}</div>
      <div>Cp: {cpData.at(-1)?.toFixed(2)} {agent.unit}</div>
      <div>Rate: {agent.rate} mL/h ({agent.gtt} gtt/min)</div>
      <Plot
        data={[
          { x: cpData.map((_, i) => i), y: cpData, name: 'Cp' },
          { x: ceData.map((_, i) => i), y: ceData, name: 'Ce', line: { dash: 'dash' } }
        ]}
        layout={{ width: 400, height: 250, title: 'Ce & Cp' }}
      />
      <button onClick={startTone} className="mt-2 px-4 py-2 bg-blue-500 text-white rounded">Metrônomo</button>
    </div>
  );
}

// File: src/App.jsx
import React, { useState } from 'react';
import { useAgentStore } from './stores/agentStore';
import AgentPanel from './components/AgentPanel';
import { v4 as uuidv4 } from 'uuid';

export default function App() {
  const [config, setConfig] = useState({ weight: '', height: '', age: '', sex: 'M', agent: 'propofol', targetType: 'Ce', target: 3.5 });
  const { agents, addAgent } = useAgentStore();

  const startSimulation = () => {
    const id = uuidv4();
    const ke0 = config.agent === 'propofol' ? 0.456 : 0.595;
    const unit = config.agent === 'propofol' ? 'µg/mL' : 'ng/mL';
    const rate = ((config.target * config.weight) / (ke0 * 60)).toFixed(1); // simplificado
    const gtt = rate * (config.target < 4 ? 60 : 20);
    addAgent({ id, name: config.agent, ...config, ke0, unit, rate, gtt, timeElapsed: 0, cePrev: 0 });
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 p-6">
      <div className="max-w-md mx-auto mb-6 p-4 bg-white dark:bg-gray-800 rounded-2xl shadow">
        <h1 className="text-2xl font-bold mb-4">TIVA-SIM Configuração</h1>
        {/* Inputs de configuração */}
        {/* ... campos de peso, altura, idade, sexo, agente, tipo alvo, slider, botão */}
        <button onClick={startSimulation} className="mt-4 w-full py-2 bg-green-500 text-white rounded">Iniciar Simulação</button>
      </div>
      <div>
        {agents.map(agent => <AgentPanel key={agent.id} agent={agent} />)}
      </div>
    </div>
  );
}

// End of codebase
