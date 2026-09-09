"""Evidence-based education library (the "Education" menu of HAHA2022).

Content is data: brief, actionable cards in Italian, each with its source.
Areas mirror the behavioural indicators of the study matrix.
"""

ARTICLES = [
    {
        "id": "attivita_fisica_oms",
        "area": "attività fisica",
        "title": "Muoversi di più: le 150 minuti a settimana",
        "read_minutes": 3,
        "source": "OMS, Linee guida sull'attività fisica e sedentarietà, 2020",
        "summary": "Quanto muoversi, come misurarla e come iniziare se sei sedentario.",
        "body": [
            "Gli adulti dovrebbero accumulare almeno 150–300 minuti a settimana di attività aerobica moderata (camminata veloce, bici) oppure 75–150 minuti di attività intensa.",
            "Ogni movimento conta: anche interruptions della sedentarietà di 2–3 minuti ogni ora hanno effetti misurabili su glicemia e pressione.",
            "Il rafforzamento muscolare (esercizi con carichi o a corpo libero) è raccomandato almeno 2 giorni a settimana.",
            "Per chi parte da zero: iniziare con 10 minuti al giorno e aumentare del 10% a settimana riduce il rischio di infortuni e aumenta la probabilità di mantenere l'abitudine.",
        ],
        "tips": [
            "Cammina 30 minuti veloci 5 giorni a settimana.",
            "Sostituisci il ascensore con le scale per i piani brevi.",
            "In ufficio: alzati ogni ora per 2–3 minuti.",
        ],
    },
    {
        "id": "nutrizione_mediterranea",
        "area": "alimentazione",
        "title": "Alimentazione mediterranea: cosa mettere nel piatto",
        "read_minutes": 4,
        "source": "Linee guida per una sana alimentazione, CREA — Centro di ricerca Alimenti e Nutrizione",
        "summary": "La base del piatto, i grassi giusti e cosa limitare davvero.",
        "body": [
            "Il piatto ideale: metà verdura e frutta, un quarto cereali integrali, un quarto proteiche (legumi, pesce, pollame, con uova e formaggi con moderazione).",
            "Grassi: olio extravergine d'oliva come condimento principale; pesce azzurro 2–3 volte a settimana per gli omega-3.",
            "Da limitare: sale (< 5 g al giorno), zuccheri liberi (< 10% dell'energia), carni processate e bevande zuccherate.",
            "Per chi ha il diabete la distribuzione dei carboidrati nei pasti conta quanto la quantità: preferisci cereali integrali e legumi.",
        ],
        "tips": [
            "Riempi metà del piatto di verdura a ogni pasto principale.",
            "Sostituisci il pane bianco con pane integrale 3 giorni a settimana.",
            "Le erbe e le spezie riducono il sale senza perdere sapore.",
        ],
    },
    {
        "id": "fumo_cessazione",
        "area": "fumo",
        "title": "Smettere di fumare: cosa succede al tuo corpo",
        "read_minutes": 3,
        "source": "OMS — tabacco e salute cardiovascolare; US Surgeon General 2010",
        "summary": "I benefici nel tempo e le strategie che funzionano davvero.",
        "body": [
            "Dopo 20 minuti cala la frequenza cardiaca; dopo 12 ore cala il monossido di carbonio; dopo 12 mesi il rischio di coronaropatia è circa dimezzato rispetto a chi continua a fumare.",
            "Il 'fumo leggero' non è sicuro: anche 1–5 sigarette al giorno mantengono un rischio cardiovascolare significativo.",
            "Le strategie con più evidenza: fissare una data di cessazione, informare le persone vicine, rimuovere gli oggetti legati al fumo e considerare un supporto farmacologico con il medico.",
        ],
        "tips": [
            "Identifica i 3 momenti del giorno più difficili e prepara un'alternativa per ciascuno.",
            "Bevi un bicchiere d'acqua lentamente quando arriva la voglia: passa in 3–5 minuti.",
        ],
    },
    {
        "id": "alcol_limiti",
        "area": "alcol",
        "title": "Alcol: dove passa il confine del rischio",
        "read_minutes": 2,
        "source": "OMS — nessuna soglia completamente sicura; linee guida nazionali",
        "summary": "Le quantità, le situazioni da evitare e come ridurre senza sforzo.",
        "body": [
            "L'evidenza attuale non individua una soglia di consumo completamente sicura: il rischio cresce in modo dose-dipendente, in particolare per tumori e ipertensione.",
            "Linee guida operative: non più di 2 unità al giorno per gli uomini, 1 per le donne, e non tutti i giorni.",
            "Situazioni da evitare sempre: prima di guidare, in gravidanza, con terapie interagenti, in presenza di ipertensione non controllata o aritmie.",
        ],
        "tips": [
            "Alternare bicchieri di acqua e vino rallenta il consumo senza sforzo.",
            "Dedica almeno 3 giorni a settimana da astemio: aiuta a rompere l'abitudine.",
        ],
    },
    {
        "id": "sonno_igiene",
        "area": "sonno",
        "title": "Dormire 7–9 ore: l'igiene del sonno che funziona",
        "read_minutes": 3,
        "source": "American Academy of Sleep Medicine; meta-analisi Cappuccio et al. 2010",
        "summary": "Perché il sonno corto fa male e le 5 regole con più evidenza.",
        "body": [
            "Dormire regolarmente meno di 6 ore (o più di 9) si associa a maggiore rischio di ipertensione, diabete e aumento di peso, indipendentemente dalla dieta.",
            "Le regole con più evidenza: orari regolari di sonno e sveglia (± 30 minuti), luce naturale al mattino, niente schermi nell'ultima ora, caffe entro le prime 8–10 ore dalla sveglia.",
            "Il pomeriggio di sonno, se serve, meglio prima delle 15:00 e non oltre 20–30 minuti.",
        ],
        "tips": [
            "Fissa l'orario di spegnimento luci come un appuntamento: 5 notti su 7.",
            "La camera: buio, silenzio, 17–19 °C.",
        ],
    },
    {
        "id": "stress_gestione",
        "area": "stress",
        "title": "Stress lavorativo: tecniche con evidenza",
        "read_minutes": 3,
        "source": "Job Content Questionnaire (Karasek); revisioni su mindfulness sul lavoro",
        "summary": "Alta richiesta e basso controllo: come intervenire su ciò che dipende da te.",
        "body": [
            "Il job strain (alta richiesta + basso controllo) si associa a rischio cardiovascolare aumentato. Non tutto il carico dipende da te, ma recupero e confini sì.",
            "Le tecniche con più evidenza per il recupero: respirazione lenta (6 atti al minuto per 10 minuti), attività fisica, e confini chiari tra lavoro e tempo personale (nessuna email dopo un'ora concordata).",
            "Micro-pause programmate ogni 90–120 minuti mantengono la concentrazione e riducono la tensione muscolare.",
        ],
        "tips": [
            "Respirazione 4-6: inspira 4 secondi, espira 6, per 10 minuti la sera.",
            "A fine giornata scrivi le 3 priorità del giorno dopo: scarica la mente.",
        ],
    },
    {
        "id": "diabete_autogestione",
        "area": "diabete",
        "title": "Diabete: l'autogestione che cambia i valori",
        "read_minutes": 4,
        "source": "Standard AMD-SID per la cura del diabete mellito",
        "summary": "Autocontrollo, piedi, occhi e le scadenze dello screening.",
        "body": [
            "L'autocontrollo glicemico ha senso se cambia le tue decisioni (terapia, pasti, movimento): registra glicemia e contesto, non solo il numero.",
            "Screening obbligatori per le complicanze: fondo oculare annuale, esame dei piedi a ogni controllo, microalbuminuria e profilo lipidico almeno annuale.",
            "L'attività fisica post-pastuale (10–15 minuti di camminata dopo i pasti principali) riduce i picchi glicemici in modo misurabile.",
        ],
        "tips": [
            "Cammina 10–15 minuti dopo il pasto principale.",
            "Controlla i piedi una volta a settimana: pelle, unghie, arrossamenti.",
        ],
    },
    {
        "id": "ipertensione_autogestione",
        "area": "ipertensione",
        "title": "Pressione: misurare bene a casa",
        "read_minutes": 3,
        "source": "Linee guida ESC/ESH 2018; raccomandazioni misurazione domiciliare",
        "summary": "La tecnica corretta e come costruire la media che conta.",
        "body": [
            "Misura sempre nella stessa condizioni: seduto da 5 minuti, schiena appoggiata, braccio sul tavolo, cuffia all'altezza del cuore, niente caffe o fumo nei 30 minuti precedenti.",
            "Fai 2 misurazioni a distanza di 1–2 minuti, mattina e sera; scarta la prima se è molto diversa.",
            "La media settimanale è il valore che conta per le decisioni: registra sulla piattaforma e condividila con il medico.",
            "Ridurre il sale a meno di 5 g al giorno abbassa la pressione in modo misurabile in 4–6 settimane.",
        ],
        "tips": [
            "Programma le misurazioni: mattina prima di colazione e sera prima di cena.",
            "Il sale nascosto (pane, conservi, salumi) conta più del sale sulla tavola.",
        ],
    },
]

AREAS = sorted({a["area"] for a in ARTICLES})


def find(article_id: str):
    return next((a for a in ARTICLES if a["id"] == article_id), None)


def summary_list():
    return [{k: v for k, v in a.items() if k != "body"} for a in ARTICLES]
