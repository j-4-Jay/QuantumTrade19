# File 18 — Intelligence Monitor Engine (Master Build Prompt)
**Depends on:** File 17 locked. **Pipeline:** build → check → debug → re-check → lock → proceed.

## 1. Plain Explanation
This is where real AI joins the team — but as an advisor who whispers suggestions, never as the one holding the trade button. The live trading path stays 100% rule-based and fast; the AI thinks in the background and only nudges things between trades.

## 2. Tier 1 — Workers

1. **Fast_Inference_Worker** — runs a small, quantized, locally-hosted model (via ONNX Runtime or an equivalently lightweight local runtime, never a cloud API call) so there is no network round-trip latency risk during volatile moves. This Worker is the only one allowed to load/run a model file.
2. **ML_Signal_Worker** — a supervised model trained on the Journal's historical data, predicting the likely quality of a new setup before it confirms, output as an additional advisory score shown alongside (never replacing) the rule-based Confidence Score.
3. **RL_Policy_Worker** — a reinforcement-learning policy trained via the Backtest_Replay_Worker's replay environment, proposing trailing-method choices or confidence-threshold nudges, always routed through the same shadow/canary approval flow as Phase 4's Learning Monitor — never given direct order authority.

**Check gate:** benchmark Fast_Inference_Worker's response time under real load and confirm it never adds more than a few milliseconds to any path it touches (and confirm it touches zero live-execution paths directly); confirm ML_Signal_Worker's advisory score is clearly visually separated from the rule-based Confidence Score everywhere it's shown, so the two are never confused; confirm RL_Policy_Worker's proposals go through the exact same canary/approve/reject flow as any other Learning Monitor proposal, with no shortcut path to live trading.

## 3. Tier 2 — Intelligence_Monitor Assembly
Interface: `get_advisory_score(setup)`, `get_rl_suggestion(symbol)` — both purely advisory, read-only outputs.

**Check gate:** confirm disabling this entire Monitor (a single settings switch) leaves every other part of the software — Alert, Trading, Learning — fully functional with zero behavior change, proving the AI layer is genuinely optional and non-blocking.

## 4. Deliverable
Lock this file once both gates pass. Version → v3.1.0-beta. Proceed to file 19.
