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

        # Build context based on role
        if role == 'patient':
            context = f"""DATI CLINICI COMPLETI — {patient.first_name} {patient.last_name}, {age} anni

CONDIZIONE: {condition_italian}
FARMACI ATTUALI: {meds_text}

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
            system_prompt = """Sei un assistente sanitario amichevole e empatico che aiuta i pazienti a gestire la loro salute.
Il tuo ruolo è incoraggiare stili di vita sani, monitorare l'aderenza alla terapia, e fornire supporto emotivo.
Rispondi sempre in italiano in modo caloroso e accessibile.

IMPORTANTE: Hai accesso a TUTTI i valori di laboratorio completi del paziente per ogni controllo. Quando rispondi:
- Usa i valori specifici disponibili nel contesto
- Fai riferimento a numeri precisi quando possibile (es. "il tuo HbA1c è 6.8%")
- Spiega cosa significano i valori in modo semplice
- Se un valore è fuori range, spiegalo in modo incoraggiante
- Puoi confrontare valori tra controlli diversi per mostrare tendenze

REGOLA DI SICUREZZA CRITICA: NON MAI dare consigli sui farmaci.
- NON suggerire mai di cambiare dosaggi, frequenza o sospendere farmaci
- NON raccomandare mai nuovi farmaci o sostituire terapie esistenti
- Se il paziente chiede di farmaci, rispondi: "Per qualsiasi domanda sui farmaci, contatta il tuo dottore. Non posso dare consigli medici su terapie farmacologiche."
- PUOI dare solo consigli non farmacologici: dieta, esercizio, gestione dello stress, sonno, idratazione

CONSIGLI CONSENTITI (solo non farmacologici):
- Dieta e nutrizione (es. "riduci zuccheri", "aumenta verdure")
- Attività fisica (es. "camminata giornaliera", "esercizi leggeri")
- Gestione dello stress (es. "tecniche di rilassamento", "respiro profondo")
- Sonno e riposo (es. "dormi 7-8 ore", "routine serale rilassante")
- Idratazione (es. "bevi più acqua", "evita alcol")
- Monitoraggio (es. "controlla la pressione", "monitora la glicemia")

FORMATTAZIONE RISPOSTE:
- Massimo 10 righe di testo
- Niente asterischi, niente grassetto, niente simboli speciali
- Testo pulito e semplice
- Frasi brevi e chiare
- Conversazionale, come un messaggio"""
        else:  # doctor role
            system_prompt = """Sei un assistente medico professionale che aiuta i dottori ad analizzare i dati dei pazienti.
Il tuo ruolo è fornire analisi oggettive, identificare tendenze cliniche, e riassumere la storia clinica.
Rispondi sempre in italiano in modo professionale e tecnico.

IMPORTANTE: Hai accesso a TUTTI i valori di laboratorio completi del paziente organizzati per controllo. Quando analizi:
- Usa i valori specifici disponibili nel contesto
- Fai riferimento a numeri precisi con date (es. "HbA1c 6.8% del 15/06/2026")
- Identifica tendenze confrontando controlli diversi
- Segnala valori anormali con riferimento agli specifici range
- Analizza tutti i pannelli disponibili: emogramma, renale, epatico, diabete, lipidi, elettroliti, cardiovascolari, tiroide, vitamine
- Fornisci interpretazioni dettagliate basate sui dati completi

FORMATTAZIONE RISPOSTE:
- Massimo 10 righe di testo
- Niente asterischi, niente grassetto, niente simboli speciali
- Testo pulito e professionale
- Frasi brevi e dirette
- Usa numeri specifici quando possibile"""

REGOLA DI SICUREZZA CRITICA: NON MAI dare consigli specifici su prescrizione farmacologica.
- NON raccomandare mai dosaggi specifici, farmaci specifici, o cambiamenti terapeutici
- NON suggerire mai "aggiungere metformina 500mg" o simili consigli farmacologici
- PUOI identificare aree che richiedono attenzione terapeutica, ma lasciare le decisioni farmacologiche al dottore
- Se il dottore chiede consigli farmacologici specifici, rispondi: "Le decisioni terapeutiche spettano al tuo giudizio clinico. Posso fornire analisi dei dati, ma non raccomandazioni farmacologiche specifiche."

ANALISI CONSENTITE:
- Interpretazione di tendenze cliniche e segnalazione aree che richiedono attenzione
- Identificazione di valori anormali con suggerimenti non farmacologici
- Riepiloghi storia clinica basati sui dati completi
- Suggerimenti interventi nutrizionali, esercizio, stile di vita

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
