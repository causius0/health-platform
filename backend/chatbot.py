"""
Chatbot integration with OpenRouter API.
Builds patient context and manages LLM API calls.
"""
from datetime import datetime, timedelta
from models import LabResult, Visit, Patient
import requests
import os

# OpenRouter API Configuration
OPENROUTER_API_KEY = "***REMOVED***"
OPENROUTER_MODEL = "mistralai/ministral-3b-2512"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def build_patient_context(patient_id, role='patient', db_session=None):
    """
    Build Italian patient context for LLM prompt.

    Args:
        patient_id: Patient ID
        role: 'patient' or 'doctor'
        db_session: SQLAlchemy session (optional)

    Returns:
        Formatted Italian context string
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # Create session if not provided
    if db_session:
        session = db_session
        should_close = False
    else:
        engine = create_engine('sqlite:///database.db', echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()
        should_close = True

    try:
        # Doctor general mode: no specific patient -> give an overview of all patients
        if role == 'doctor' and not patient_id:
            return _build_doctor_overview(session)

        # Get patient data
        patient = session.query(Patient).get(patient_id)
        if not patient:
            return "Errore: paziente non trovato."

        # Calculate age
        if patient.birth_date:
            try:
                birth_year = int(patient.birth_date.split('-')[0])
                age = datetime.now().year - birth_year
            except:
                age = "sconosciuto"
        else:
            age = "sconosciuto"

        # Get recent lab results (6 months) - REMOVED LIMIT to get all comprehensive data
        six_months_ago = datetime.now() - timedelta(days=180)
        recent_labs = session.query(LabResult)\
            .filter_by(patient_id=patient_id)\
            .filter(LabResult.date >= six_months_ago.strftime('%Y-%m-%d'))\
            .order_by(LabResult.date.desc(), LabResult.test_name.asc())\
            .all()  # NO LIMIT - get all comprehensive lab data

        # Format lab results by encounter date for better AI understanding
        labs_text = ""
        if recent_labs:
            # Group labs by encounter date
            from collections import defaultdict
            labs_by_date = defaultdict(list)
            for lab in recent_labs:
                labs_by_date[lab.date].append(lab)

            labs_text = "ESAMI LABORATORIO COMPLETI (ultimi 6 mesi):\n\n"
            # Sort dates (newest first)
            sorted_dates = sorted(labs_by_date.keys(), key=lambda x: datetime.strptime(x.split()[0], '%Y-%m-%d'), reverse=True)

            for date in sorted_dates[:12]:  # Last 12 encounters max
                encounter_date = date.split()[0]  # Remove time if present
                try:
                    formatted_date = datetime.strptime(encounter_date, '%Y-%m-%d').strftime('%d/%m/%Y')
                except:
                    formatted_date = encounter_date

                labs_text += f"Controllo del {formatted_date}:\n"

                # Group tests by panel type for this encounter
                encounter_labs = labs_by_date[date]

                # Define panel groupings
                blood_count = ['Emoglobina', 'Ematocrito', 'Globuli bianchi', 'Piastrine', 'RBC', 'MCV', 'MCH', 'MCHC']
                kidney = ['Creatinina', 'BUN azoto', 'eGFR', 'Microalbuminuria', 'Urea', 'Acido urico']
                liver = ['ALT', 'AST', 'Gamma-GT', 'Bilirubina totale', 'Bilirubina diretta', 'Albumina', 'Proteine totali']
                diabetes = ['HbA1c', 'Glicemia a digiuno', 'Glicemia postprandiale', 'Insulina', 'Peptide C']
                lipids = ['Colesterolo totale', 'Colesterolo LDL', 'Colesterolo HDL', 'Trigliceridi']
                electrolytes = ['Sodio', 'Potassio', 'Cloro', 'Magnesio', 'Calcio', 'Fosforo']
                cardio = ['Omocisteina', 'Troponina', 'BNP', 'PCR', 'VES']
                thyroid = ['TSH', 'T3 libero', 'T4 libero']
                vitamins = ['Vitamina D', 'Vitamina B12', 'Acido folico', 'Ferritina', 'Ferro sierico']

                # Organize by panel
                panels = [
                    ("Emogramma", blood_count),
                    ("Funzionalità Renale", kidney),
                    ("Funzionalità Epatica", liver),
                    ("Panel Diabete", diabetes),
                    ("Profilo Lipidico", lipids),
                    ("Elettroliti", electrolytes),
                    ("Marcatori Cardiovascolari", cardio),
                    ("Funzionalità Tiroidea", thyroid),
                    ("Vitamine", vitamins)
                ]

                for panel_name, test_names in panels:
                    panel_tests = [lab for lab in encounter_labs if lab.test_name in test_names]
                    if panel_tests:
                        labs_text += f"  {panel_name}: "
                        test_values = []
                        for lab in panel_tests:
                            test_values.append(f"{lab.test_name}={lab.test_value}{lab.unit or ''}")
                        labs_text += ", ".join(test_values) + "\n"

                labs_text += "\n"

        # Get recent visits (6 months)
        recent_visits = session.query(Visit)\
            .filter_by(patient_id=patient_id)\
            .filter(Visit.visit_date >= six_months_ago.strftime('%Y-%m-%d'))\
            .order_by(Visit.visit_date.desc())\
            .limit(5)\
            .all()

        # Format visits
        visits_text = ""
        if recent_visits:
            visits_text = "\nVisite recenti:\n"
            for visit in recent_visits:
                visits_text += f"- {visit.visit_date}: {visit.visit_type} - {visit.doctor_notes or 'Nessuna nota'}\n"

        # Translate condition to Italian
        condition_map = {
            'diabetes': 'diabete',
            'diabetes type 1': 'diabete tipo 1',
            'diabetes type 2': 'diabete tipo 2',
            'hypertension': 'ipertensione',
            'diabete tipo 2': 'diabete tipo 2',
            'diabete tipo 1': 'diabete tipo 1',
            'ipertensione': 'ipertensione'
        }
        condition_italian = condition_map.get(patient.condition.lower(), patient.condition)

        # Parse medications JSON
        try:
            import json
            medications = json.loads(patient.medications) if patient.medications else []
            meds_text = ', '.join(medications) if medications else 'Nessun farmaco'
        except:
            meds_text = patient.medications if patient.medications else 'Nessun farmaco'

        # Anamnesis (lifestyle: risk + protective factors)
        anamnesis_text = ''
        if patient.anamnesis:
            try:
                import json as _json
                an = _json.loads(patient.anamnesis)
                protective = an.get('protective', [])
                anamnesis_text = "\nANAMNESI STILE DI VITA:\n"
                anamnesis_text += f"- Attivita fisica: {an.get('physical_activity','non specificato')}\n"
                anamnesis_text += f"- Alimentazione: {an.get('nutrition','non specificata')}\n"
                anamnesis_text += f"- Fumo: {an.get('smoking','non specificato')}\n"
                anamnesis_text += f"- Alcol: {an.get('alcohol','non specificato')}\n"
                anamnesis_text += f"- Sonno: {an.get('sleep','non specificato')}\n"
                anamnesis_text += f"- Stress: {an.get('stress','non specificato')}\n"
                if protective:
                    anamnesis_text += f"- FATTORI DI PROTEZIONE (riconoscili sempre, incoraggia su questi): {', '.join(protective)}\n"
            except Exception:
                pass

        # Build context based on role
        if role == 'patient':
            context = f"""DATI CLINICI COMPLETI — {patient.first_name} {patient.last_name}, {age} anni

CONDIZIONE: {condition_italian}
FARMACI ATTUALI: {meds_text}
{anamnesis_text}
{labs_text}{visits_text}

ISTRUZIONI IMPORTANTI:
1. Tutti i valori di laboratorio mostrati sopra sono COMPLETI e aggiornati per ogni controllo
2. Quando il paziente chiede di valori specifici, usa i dati del controllo più recente
3. Puoi fare riferimento a valori specifici es. "il tuo HbA1c è 6.8%" o "la tua glicemia a digiuno è 105 mg/dL"
4. Se un valore è fuori dal range normative, menzionalo in modo semplice e incoraggiante
5. Puoi tracciare tendenze confrontando valori tra controlli diversi

Il tuo ruolo è incoraggiare {patient.first_name} a prendersi cura della sua salute in modo amichevole. Usa i valori specifici disponibili per dare consigli personalizzati."""

        else:  # doctor role
            context = f"""DATI CLINICI COMPLETI — Paziente: {patient.first_name} {patient.last_name}, {age} anni

CONDIZIONE: {condition_italian}
FARMACI ATTUALI: {meds_text}

{labs_text}{visits_text}

ISTRUZIONI IMPORTANTI:
1. Tutti i valori di laboratorio mostrati sopra sono COMPLETI e organizzati per controllo
2. Quando analizi, puoi fare riferimento a valori specifici es. "HbA1c 6.8% nel controllo del 15/06/2026"
3. Identifica tendenze confrontando valori tra controlli diversi (es. "HbA1c è migliorato da 7.2% a 6.8%")
4. Segnala valori anormali facendo riferimento agli specifici numeri e range di riferimento
5. Puoi analizzare qualsiasi parametro: emogramma, funzionalità renale/epatica, diabete, lipidi, elettroliti, etc.

Il tuo ruolo è aiutare il dottore ad analizzare i dati clinici completi, identificare tendenze, e fornire interpretazioni dettagliate basate su TUTTI i valori disponibili."""

        return context

    finally:
        if should_close:
            session.close()


def _build_doctor_overview(session):
    """Build a concise overview of all the doctor's patients for general chat mode."""
    from collections import defaultdict

    patients = session.query(Patient).filter_by(doctor_id=1).all()
    if not patients:
        return "Nessun paziente assegnato al momento."

    lines = ["PANORAMICA PAZIENTI - Dr. Bianchi", "", "Riepilogo dell'ultimo controllo per ciascun paziente:"]

    # Key metric per condition
    def latest(patient_id, test_name):
        r = session.query(LabResult).filter_by(patient_id=patient_id, test_name=test_name) \
            .order_by(LabResult.date.desc()).first()
        return r

    for p in patients:
        is_diabetes = 'diabete' in (p.condition or '').lower()
        key = 'HbA1c' if is_diabetes else 'Pressione sistolica'
        key_lab = latest(p.id, key)
        crea = latest(p.id, 'Creatinina')
        ldl = latest(p.id, 'Colesterolo LDL')

        flags = []
        if key_lab:
            try:
                v = float(key_lab.test_value)
                if is_diabetes and v > 7.0:
                    flags.append(f"HbA1c {v}% sopra target")
                elif not is_diabetes and v > 130:
                    flags.append(f"Pressione {int(v)} mmHg elevata")
            except ValueError:
                pass
        if ldl:
            try:
                if int(float(ldl.test_value)) > 130:
                    flags.append(f"LDL {ldl.test_value} elevato");
            except ValueError:
                pass
        if crea:
            try:
                if float(crea.test_value) > 1.3:
                    flags.append(f"Creatinina {crea.test_value} elevata");
            except ValueError:
                pass

        age = "?"
        try:
            age = datetime.now().year - int(p.birth_date.split('-')[0])
        except Exception:
            pass

        lines.append(f"\n- {p.first_name} {p.last_name} ({age}aa, {p.condition})")
        vals = []
        if key_lab:
            vals.append(f"{key_lab.test_name}={key_lab.test_value}{key_lab.unit}")
        if crea:
            vals.append(f"Creatinina={crea.test_value}{crea.unit}")
        if ldl:
            vals.append(f"LDL={ldl.test_value}{ldl.unit}")
        lines.append(f"  Ultimi valori: {', '.join(vals)}")
        if flags:
            lines.append(f"  ATTENZIONE: {'; '.join(flags)}")

    lines.append("\nISTRUZIONI: Stai aiutando il dottore in modalita' generale (nessun paziente selezionato).")
    lines.append("- Per analisi dettagliate o tendenze di un singolo paziente, suggerisci di selezionarlo dall'elenco.")
    lines.append("- Sii sintetico e focalizzato sui valori fuori target.")
    return "\n".join(lines)


def mock_llm_response(user_message, context, role):
    """
    Generate mock LLM response in Italian (placeholder for real LLM).
    This simulates Mistral 1B responses before real integration.

    Args:
        user_message: User's message
        context: Patient context string
        role: 'patient' or 'doctor'

    Returns:
        Italian response string
    """
    # Simple keyword-based responses for demo
    message_lower = user_message.lower()

    if role == 'patient':
        # Patient health coaching responses
        if 'ciao' in message_lower or 'buongiorno' in message_lower:
            return f"Ciao! Sono qui per aiutarti con la tua salute. Come ti senti oggi?"

        elif 'stamg bene' in message_lower or 'tutto bene' in message_lower:
            return "Sono contento che tu stia bene. Ricorda di controllare i valori regolarmente e prendere i farmaci. Hai notato qualche cambiamento ultimamente?"

        elif 'mangiato' in message_lower or 'cibo' in message_lower or 'pranzo' in message_lower or 'cena' in message_lower:
            return "Una dieta equilibrata è importante. Cerca di includere più verdure e ridurre gli zuccheri. Hai fatto attività fisica oggi?"

        elif 'attività fisica' in message_lower or 'sport' in message_lower or 'camminato' in message_lower or 'esercizio' in message_lower:
            return "Ottimo! L attività fisica regolare aiuta molto. Anche 30 minuti di camminata al giorno possono fare la differenza. Continua così."

        elif 'farmaci' in message_lower or 'medicina' in message_lower:
            return "È fondamentale prendere i farmaci regolarmente ogni giorno alla stessa ora. Hai dimenticato qualche dose di recente?"

        elif 'grazie' in message_lower or 'arrivederci' in message_lower:
            return "Prego! Sono qui per aiutarti. Prenditi cura della tua salute e ci sentiamo presto."

        else:
            return "Per gestire al meglio la tua condizione, è importante mantenere uno stile di vita sano, monitorare i valori, e seguire le raccomandazioni del tuo dottore. C'è qualcos'altro su cui posso aiutarti?"

    else:  # doctor role
        # Doctor data analysis responses
        if 'ciao' in message_lower or 'buongiorno' in message_lower:
            return "Buongiorno dottore. Sono qui per aiutarla ad analizzare i dati dei pazienti e identificare aree di interesse."

        elif 'come sta' in message_lower or 'stato' in message_lower or 'condizione' in message_lower:
            return "In base ai dati disponibili, il paziente mostra una condizione cronica stabile ma richiede monitoraggio regolare. Consiglier di rivedere i recenti esami di laboratorio per valutare l'andamento."

        elif 'hba1c' in message_lower or 'glicemia' in message_lower or 'esami' in message_lower:
            return "Dall'analisi degli esami recenti, i valori glicemici mostrano una tendenza che richiede attenzione. L'HbA1c è leggermente sopra l'obiettivo ideale. Consigli di intensificare il monitoraggio e rivedere la terapia."

        elif 'terapia' in message_lower or 'farmaci' in message_lower:
            return "Il regime farmacologico attuale sembra appropriato per la condizione. Basandomi sui dati, suggerire di valutare se ci sono stati effetti collaterali segnalati o problemi di aderenza al trattamento."

        elif 'visita' in message_lower or 'controllo' in message_lower:
            return "Le recenti visite mostrano che il paziente è stato regolare nei controlli, il che è positivo. L'ultima visita ha rilevato alcuni aspetti da monitorare. Consiglio di mantenere la frequenza attuale delle visite."

        else:
            return "In base ai dati clinici disponibili, il paziente richiede un follow-up regolare. I valori di laboratorio più recenti indicano alcune aree che meritano attenzione. Desidera approfondire qualche aspetto specifico?"


def clean_response(text):
    """
    Clean and format AI response to meet formatting requirements.

    Args:
        text: Raw AI response text

    Returns:
        Cleaned text with max 10 lines, no special formatting
    """
    # Remove asterisks and special formatting
    text = text.replace('*', '')
    text = text.replace('#', '')
    text = text.replace('**', '')
    text = text.replace('##', '')
    text = text.replace('__', '')
    text = text.replace('###', '')
    text = text.replace('-', '')  # Remove markdown bullets
    text = text.replace('•', '')  # Remove bullet points

    # Clean up multiple spaces
    import re
    text = re.sub(r'\s+', ' ', text)

    # Split into lines and clean each line
    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        if line:  # Only keep non-empty lines
            # Remove any remaining special characters at start/end
            line = line.strip('.,;:!()[]{}<>|/\\')
            cleaned_lines.append(line)

    # Limit to 10 lines max
    if len(cleaned_lines) > 10:
        cleaned_lines = cleaned_lines[:10]

    # Join back into clean text
    clean_text = ' '.join(cleaned_lines)  # Use spaces instead of newlines

    # Ensure it ends cleanly
    clean_text = clean_text.strip()

    return clean_text


def get_llm_response(user_message, context, role):
    """
    Get LLM response from OpenRouter API using Mistral model.

    Args:
        user_message: User's message
        context: Patient context string
        role: 'patient' or 'doctor'

    Returns:
        Italian response string from AI model
    """
    try:
        # Build system prompt based on role
        if role == 'patient':
            system_prompt = """Sei un assistente sanitario amichevole e empatico specializzato in prevenzione e promozione della salute.
Il tuo ruolo è incoraggiare stili di vita sani e fornire informazioni educative basate sull'evidenza.
Rispondi sempre in italiano in modo caloroso e accessibile.

IMPORTANTE: Organizza ogni risposta in TRE LIVELLI SEPARATI e chiaramente etichettati:

1. INFORMAZIONE GENERALE: Spiega cosa significa il parametro o la condizione in modo semplice e educativo
2. CONSIGLIO PREVENTIVO PERSONALIZZATO: Fornisci un consiglio pratico e realistico basato sui valori specifici del paziente
3. INDICAZIONE CLINICA: SOLO se clinicamente warranted (es. valori pericolosi, tendenze preoccupanti), raccomanda di consultare il medico

FORMATTAZIONE OBBLIGATORIA:
Ogni risposta DEVE seguire questa struttura:

INFORMAZIONE GENERALE: [spiegazione educativa semplice]
CONSIGLIO PREVENTIVO PERSONALIZZATO: [UNA SOLA azione settimanale specifica e realistica basata sui valori del paziente]
INDICAZIONE CLINICA: [SOLO SE NECESSARIO - altrimenti scrivi "Non necessaria in questo caso"]

REGOLA FONDAMENTALE PER I CONSIGLI:
- DARE UNA SOLA azione specifica per questa settimana
- Deve essere REALISTICA e ATTUABILE
- Basata sui valori specifici del paziente
- Concreta: non "mangia meglio", ma "questa settimana sostituisci la dessert con la frutta 3 volte"

Esempio di risposta corretta:
INFORMAZIONE GENERALE: La glicemia a digiuno misura lo zucchero nel sangue dopo 8 ore di digiuno. Valori normali sono sotto 100 mg/dL.
CONSIGLIO PREVENTIVO PERSONALIZZATO: Il tuo valore è 105 mg/dL. Quest'azione settimana: sostituisci lo zucchero nel caffè con stevia o dolcificante zero calorie.
INDICAZIONE CLINICA: Non necessaria in questo caso.

VALORI DI LABORATORIO:
- Hai accesso a TUTTI i valori completi per ogni controllo
- Usa i numeri specifici quando possibile (es. "il tuo HbA1c è 6.8%")
- Confronta valori tra controlli per mostrare tendenze
- Se un valore è fuori range, spiegalo in modo incoraggiante

REGOLA DI SICUREZZA CRITICA: NON MAI dare consigli sui farmaci.
- Se il paziente chiede di farmaci: "Per qualsiasi domanda sui farmaci, contatta il tuo dottore. Non posso dare consigli medici su terapie farmacologiche."
- PUOI dare solo consigli non farmacologici: dieta, esercizio, stress, sonno, idratazione

LUNGHEZZA: Massimo 10 righe totali, testo pulito senza asterischi o simboli speciali."""
        else:  # doctor role
            system_prompt = """Sei un assistente medico professionale che aiuta i dottori ad analizzare i dati dei pazienti.
Il tuo ruolo è fornire analisi oggettive, identificare tendenze cliniche, e riassumere la storia clinica.
Rispondi sempre in italiano in modo professionale e tecnico.

IMPORTANTE: Hai accesso a TUTTI i valori di laboratorio completi del paziente organizzati per controllo. Quando analizi:
- Usa i valori specifici disponibili nel contesto con date precise
- Fai riferimento a numeri con date (es. "HbA1c 6.8% del 15/06/2026")
- Identifica tendenze confrontando controlli diversi
- Segnala valori anormali con riferimento agli specifici range
- Analizza tutti i pannelli: emogramma, renale, epatico, diabete, lipidi, elettroliti, cardiovascolari, tiroide, vitamine

ORGANIZZA LE RISPOSTE IN TRE SEZIONI:

1. ANALISI DEI DATI: Interpretazione obiettiva dei valori attuali con tendenze nel tempo
2. AREE DI ATTENZIONE: Valori anormali o tendenze preoccupanti che meritano monitoraggio
3. SUGGERIMENTI CLINICI: Raccomandazioni non farmacologiche o aree da valutare nelle decisioni terapeutiche

FORMATTAZIONE:
ANALISI DEI DATI: [interpretazione obiettiva con numeri specifici e date]
AREE DI ATTENZIONE: [elenco valori anomali o tendenze preoccupanti]
SUGGERIMENTI CLINICI: [raccomandazioni per valutazione o interventi non farmacologici]

REGOLA DI SICUREZZA CRITICA: NON dare consigli farmacologici specifici.
- Se il dottore chiede consigli farmacologici: "Le decisioni terapeutiche spettano al tuo giudizio clinico. Posso fornire analisi dei dati, ma non raccomandazioni farmacologiche specifiche."
- PUOI identificare aree che richiedono attenzione terapeutica, ma lasciare le decisioni al dottore

LUNGHEZZA: Massimo 10 righe totali, testo pulito senza simboli speciali."""

        # Prepare messages for OpenRouter API
        messages = [
            {
                "role": "system",
                "content": f"{system_prompt}\n\n{context}"
            },
            {
                "role": "user",
                "content": user_message
            }
        ]

        # Make API request to OpenRouter
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",  # Required by OpenRouter
            "X-Title": "Health Platform Chat"  # Required by OpenRouter
        }

        payload = {
            "model": OPENROUTER_MODEL,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 500
        }

        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        # Extract response
        data = response.json()
        ai_message = data['choices'][0]['message']['content']

        # Clean and format response
        return clean_response(ai_message)

    except requests.exceptions.RequestException as e:
        # Fallback to mock on API error
        print(f"OpenRouter API error: {e}")
        return clean_response(mock_llm_response(user_message, context, role))
    except (KeyError, IndexError) as e:
        # Fallback on parsing error
        print(f"Response parsing error: {e}")
        return clean_response(mock_llm_response(user_message, context, role))
    except Exception as e:
        # Fallback on any error
        print(f"Unexpected error in get_llm_response: {e}")
        return clean_response(mock_llm_response(user_message, context, role))
