# health-platform — improvement loop log

## Backlog (checklist from client feedback, 4 June review)

### A. Worker-side chat experience
- [x] Match slide 9 layout: "Prevenzione & Salute" header, "I tuoi dati sono sicuri e protetti", chat thread, right-hand "Suggerimenti" panel, bottom "AZIONI" block ("Iscriviti a un programma" + "Fonti evidence-based")
- [x] Opening flow: brief anamnesis (habits, risk factors, **and protective factors**) — implemented as a guided 6-step quick-reply onboarding that persists and captures protective factors
- [x] Chat replies short & structured, 3 tiers (Informazione generale / Consiglio preventivo personalizzato / Indicazione clinica) — enforced by backend prompt + frontend `parseTiered` rendering
- [x] Suggerimenti panel: clickable programs (Sfida 10.000 passi, mindfulness, cucina) + EBM sources (CREA/INRAN, OMS, AMD/SID)
- [x] End of guided path → concrete measurable output (goal persisted to backend, e.g. "Sfida 10.000 passi 5x/sett")
- [x] One realistic weekly action (goals are frequency-per-week, one active focus)
- [x] History/adherence tracker (GoalsPanel: current-week progress + 6-week history, persisted)

### B. Worker-side dashboard/summary
- [x] Lead with plain-language summary across the 6 areas (attività fisica, alimentazione, fumo, alcol, sonno, stress/benessere lavorativo) — HealthOverview derives status from labs + anamnesis
- [x] Charts/exams pushed down as optional deep-dive (collapsible "Esami e andamento nel tempo")

### C. Operator/clinician dashboard
- [x] Per flagged worker: what triggered the flag, since when (date of first abnormal reading), recommended next step — left-rail alert cards
- [x] Interoperability: worker action → operator effect — worker goals/check-ins surface on the doctor "Attività lavoratori" feed in real time (manual refresh)

### D. Risk-threshold escalation logic
- [x] >3 risk conditions (≥4 = Alto) → specific monitoring path + occupational-physician recommendation — consistent across chat/alerts/dashboard badge ("Più di 3 → percorso di monitoraggio specifico · consigliata visita medico del lavoro")

### E. Demo video
- [ ] Demo video pacing + worker→operator transition clip (non-code; do last)

## Session log (most recent first)

**2026-07-29 — Full requirements pass + clean rebuild**
- Rebuilt worker side summary-first (PatientDashboard → HealthOverview + GoalsPanel + TrendChart deep-dive)
- Added prevention data layer: HealthGoal + GoalCheckIn + Patient.anamnesis models; endpoints for goals/checkins/anamnesis/doctor-activity-feed
- Worker anamnesis onboarding (6 quick-reply steps) persists risk + protective factors; dashboard refreshes live after onboarding (window event)
- Rebuilt worker chat: 3-tier display + Suggerimenti (programs/EBM) + AZIONI; anamnesis fed into LLM context
- Operator dashboard: ≥4-factor rule (Alto) consistent with backend; "since when" on alerts; new "Attività lavoratori" feed (the interoperability hook)
- Clinically-coherent seed: 10 monthly encounters/patient with believable trajectories; per-patient anamnesis + 6-week adherence history
- Verified end-to-end in browser (browse): worker onboarding, goal setting, worker→operator activity propagation, Giuseppe ≥4-factor → Alto + occupational physician

**2026-07-29 - Doctor dashboard rebuild (alerts left, patients center, chat right; coherent lab trends)**
- New DoctorDashboard 3-column layout, always-on chat
- New TrendChart (click-to-add lines, reference band, out-of-range points)

## Needs client confirmation
- design-reference/slide9-*.png were never dropped in; UI built from the written spec, not a pixel match to the deck. Drop the PNGs and we can tighten copy/layout.
- Program names and EBM source citations are reasonable placeholders, not confirmed real Eni programs.
