import streamlit as st
from core_engine import applica_stile_globale, carica_database, salva_nel_database
from view_testa_a_testa import render_testa_a_testa
from view_sala_di_guerra import render_sala_di_guerra
from view_forgia_db import render_forgia_db

# Configurazione della Pagina
st.set_page_config(
    page_title="MATTHAMMER — AoS 4e Tactical Suite",
    page_icon="🔨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Applica lo stile grafico globale dai fogli di pergamena
applica_stile_globale()
#
#
#
# ==========================================
# INIZIALIZZAZIONE SESSION STATE
# ==========================================
#
#
#
if "db_unita" not in st.session_state:
    st.session_state["db_unita"] = carica_database()

# Variabile reale che guida la vista attiva
if "pagina_selezionata" not in st.session_state:
    st.session_state["pagina_selezionata"] = "Portale Principale (Home)"

if "corrente_armi" not in st.session_state:
    st.session_state["corrente_armi"] = [
        {
            "nome": "---", "attiva": False, "ranged": False, "atk": "---",
            "hit": "---", "wnd": "---", "rend": "---", "dmg": "---", "crit_type": "Nessuno",
            "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False
        }
    ]
    st.session_state["corrente_modelli"] = 0
    st.session_state["corrente_campione"] = False
    st.session_state["corrente_punti"] = 0
    st.session_state["corrente_difesa"] = {"salute_per_modello": 0, "save": "---", "ward": "---"}

if "form_version" not in st.session_state:
    st.session_state["form_version"] = 0
if "notifica_salvataggio" not in st.session_state:
    st.session_state["notifica_salvataggio"] = None
if "bersaglio_save" not in st.session_state:
    st.session_state["bersaglio_save"] = 4
if "bersaglio_ward" not in st.session_state:
    st.session_state["bersaglio_ward"] = 7
if "bersaglio_salute" not in st.session_state:
    st.session_state["bersaglio_salute"] = 10
if "bersaglio_punti" not in st.session_state:
    st.session_state["bersaglio_punti"] = 0
if "target_version" not in st.session_state:
    st.session_state["target_version"] = 0

#
#
#
# ==========================================
# CSS PER L'ANIMAZIONE DI BRACI, SCINTILLE & HERO SECTION
# ==========================================
#
#
#
st.markdown("""
<style>
    /* Effetto particelle fluttuanti (braci ardenti e scintille d'oro) */
    .ember-wrapper {
        position: relative;
        overflow: hidden;
        border-radius: 4px 18px 4px 18px;
        background: radial-gradient(circle at 50% 100%, #2e1a0b 0%, #150f0a 65%, #0b0805 100%);
        border: 2px solid #8c6d46;
        border-top: 3px solid #d4af37;
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.8), inset 0 0 50px rgba(212, 175, 55, 0.12);
        padding: 50px 25px 40px 25px;
        text-align: center;
        margin-bottom: 25px;
    }
    
    .ember-wrapper::before, .ember-wrapper::after {
        content: "";
        position: absolute;
        top: -100%;
        left: 0;
        right: 0;
        bottom: 0;
        background-image: 
            radial-gradient(3px 3px at 15% 90%, rgba(255, 170, 50, 0.95), transparent),
            radial-gradient(2px 2px at 30% 80%, rgba(255, 215, 0, 0.9), transparent),
            radial-gradient(3px 3px at 45% 95%, rgba(255, 120, 20, 0.85), transparent),
            radial-gradient(2px 2px at 60% 85%, rgba(255, 200, 80, 0.9), transparent),
            radial-gradient(4px 4px at 75% 92%, rgba(255, 140, 30, 0.9), transparent),
            radial-gradient(2px 2px at 85% 78%, rgba(255, 225, 110, 0.8), transparent);
        background-size: 100% 100%;
        animation: riseEmbers 7s linear infinite;
        pointer-events: none;
    }

    .ember-wrapper::after {
        animation-delay: 3.5s;
        animation-duration: 9s;
        opacity: 0.75;
    }

    @keyframes riseEmbers {
        0% { transform: translateY(100%) scale(0.9); opacity: 0; }
        20% { opacity: 1; }
        80% { opacity: 0.8; }
        100% { transform: translateY(-30%) scale(1.15); opacity: 0; }
    }

    .hero-title {
        font-family: 'Cinzel Decorative', serif !important;
        font-size: 3.4rem !important;
        font-weight: 900 !important;
        color: #f7d57f !important;
        letter-spacing: 5px !important;
        text-transform: uppercase;
        margin-bottom: 4px !important;
        text-shadow: 0 4px 15px rgba(0,0,0,0.9), 0 0 25px rgba(212, 175, 55, 0.45);
    }

    .hero-subtitle {
        font-family: 'Cinzel', serif !important;
        font-size: 1.15rem !important;
        letter-spacing: 2px !important;
        color: #d8c29d !important;
        text-transform: uppercase;
        margin-bottom: 14px !important;
    }

    .hero-desc {
        font-family: 'Crimson Pro', serif !important;
        font-size: 1.18rem !important;
        font-style: italic;
        color: #bfae93 !important;
        max-width: 780px;
        margin: 0 auto !important;
        line-height: 1.5;
    }

    .hub-card {
        background: linear-gradient(135deg, #1f160e 0%, #150f09 100%);
        border: 2px solid #6b4e2d;
        border-top: 3px solid #b38b4d;
        border-radius: 4px 12px 4px 12px;
        padding: 22px;
        height: 100%;
        box-shadow: 0 6px 16px rgba(0,0,0,0.5);
    }
    .hub-card h3 {
        font-family: 'Cinzel', serif !important;
        color: #e6c665 !important;
        border-bottom: 1px solid rgba(179,139,77,0.4);
        padding-bottom: 6px;
        margin-top: 0;
    }
</style>
""", unsafe_allow_html=True)
#
#
#
# ==========================================
# SIDEBAR CONDIVISA
# ==========================================
#
#
#
st.sidebar.title("MATTHAMMER")
st.sidebar.caption("AoS 4e Tactical Suite v4.19")
st.sidebar.markdown("---")

# Iniezione CSS per trasformare il radio button in un menu premium in stile tomo magico
st.markdown("""
<style>
    /* Nasconde i pallini nativi del radio button */
    [data-testid="stSidebar"] div[role="radiogroup"] label div:first-child {
        display: none !important;
    }
    
    /* Stile base per tutti i bottoni del menu */
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        width: 100%;
        padding: 10px 15px;
        margin-bottom: 6px;
        border-radius: 6px;
        border-left: 4px solid transparent;
        background: transparent;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    /* Effetto al passaggio del mouse (Hover) sulle voci inattive */
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background: linear-gradient(90deg, rgba(140, 109, 70, 0.15) 0%, rgba(0,0,0,0) 100%);
        border-left: 4px solid rgba(140, 109, 70, 0.5);
    }
    
    /* Stile per la voce SELEZIONATA (Gradiente dorato luminoso a sinistra che sfuma a destra) */
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background: linear-gradient(90deg, rgba(212, 175, 55, 0.25) 0%, rgba(212, 175, 55, 0.0) 100%) !important;
        border-left: 4px solid #d4af37 !important;
    }
    
    /* Forza il colore del testo oro per la voce selezionata */
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {
        color: #e6c665 !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

# Titolo della sezione (richiama i font e i colori dorati dell'app)
st.sidebar.markdown('<div style="color:#e6c665; font-family:\'Cinzel\', serif; font-size:1.1rem; font-weight: bold; margin-bottom:12px; border-bottom: 1px dashed rgba(140, 109, 70, 0.45); padding-bottom: 5px;">Navigazione del Tomo</div>', unsafe_allow_html=True)

# Dizionario per mostrare nomi belli senza rompere la logica di navigazione pre-esistente dell'app
MAPPA_NAV = {
    "Portale Principale": "Portale Principale (Home)",
    "Laboratorio Tattico": "Laboratorio Tattico (Testa a Testa)",
    "Sala di Guerra (BETA)": "Sala di Guerra (Costruttore Armate)",
    "Forgia del Grimorio": "Forgia del Grimorio (Database)"
}
NOMI_UI = list(MAPPA_NAV.keys())

# Trova il nome UI corrispondente allo stato attuale per mantenere la selezione corretta
stato_attuale_sistema = st.session_state.get("pagina_selezionata", "Portale Principale (Home)")
indice_corrente = 0
for i, (nome_ui, nome_sys) in enumerate(MAPPA_NAV.items()):
    if nome_sys == stato_attuale_sistema:
        indice_corrente = i
        break

def cambio_pagina_da_sidebar():
    # Traduce la scelta UI nel nome tecnico richiesto dal resto dell'app
    scelta_ui = st.session_state["menu_sidebar_ui"]
    st.session_state["pagina_selezionata"] = MAPPA_NAV[scelta_ui]

# Menu di navigazione stilizzato
st.sidebar.radio(
    "Menu Navigazione", # Etichetta nascosta
    NOMI_UI,
    index=indice_corrente,
    label_visibility="collapsed",
    key="menu_sidebar_ui",
    on_change=cambio_pagina_da_sidebar
)

st.sidebar.markdown("---")

# Directory Rapida per Laboratorio Tattico (Solo Lettura/Caricamento)
if st.session_state["pagina_selezionata"] == "Laboratorio Tattico (Testa a Testa)":
    st.sidebar.subheader("Directory Rapida")
    st.sidebar.caption("Carica un profilo salvato nel Laboratorio.")
    
    unita_totali = [k for k in st.session_state["db_unita"].keys() if k != "--- Seleziona o Resetta ---"]
    if unita_totali:
        scelta_rapida = st.sidebar.selectbox("Unità dal Grimorio", unita_totali, key="sb_quick_load")
        if st.sidebar.button("Carica nel Profilo", type="primary", use_container_width=True):
            dati_sel = st.session_state["db_unita"][scelta_rapida]
            st.session_state["corrente_armi"] = [dict(a) for a in dati_sel["armi"]]
            st.session_state["corrente_modelli"] = dati_sel["n_modelli"]
            st.session_state["corrente_campione"] = dati_sel["campione"]
            st.session_state["corrente_punti"] = dati_sel["punti"]
            st.session_state["corrente_difesa"] = dati_sel.get("difesa", {"salute_per_modello": 0, "save": "---", "ward": "---"})
            st.session_state["form_version"] += 1
            st.rerun()

        if st.sidebar.button("Reset Parametri", use_container_width=True):
            st.session_state["corrente_armi"] = [{
                "nome": "---", "attiva": False, "ranged": False, "atk": "---", "hit": "---",
                "wnd": "---", "rend": "---", "dmg": "---", "crit_type": "Nessuno",
                "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False
            }]
            st.session_state["corrente_modelli"] = 0
            st.session_state["corrente_campione"] = False
            st.session_state["corrente_punti"] = 0
            st.session_state["corrente_difesa"] = {"salute_per_modello": 0, "save": "---", "ward": "---"}
            st.session_state["form_version"] += 1
            st.rerun()
            
# Stato Cloud Sync
st.sidebar.markdown("---")
try:
    if "GITHUB_TOKEN" in st.secrets and "GITHUB_REPO" in st.secrets:
        st.sidebar.success("Cloud Sync: Attivo (GitHub)")
    else:
        st.sidebar.info("Modalità Locale (Offline)")
except Exception:
    st.sidebar.info("Modalità Locale (Offline)")
#
#
#
# ==========================================
# FUNZIONE RENDERING: PORTALE PRINCIPALE (HOME)
# ==========================================
#
#
#
def render_homepage():
    # Hero Banner con animazione delle braci e scintille
    st.markdown("""
    <div class="ember-wrapper">
        <div class="hero-title">MATTHAMMER</div>
        <div class="hero-subtitle">Archivio Tattico & Oracolo da Guerra — Warhammer Age of Sigmar 4e</div>
        <p class="hero-desc">
            "Dalle ceneri della forgia alla gloria della carica campale. Calcola probabilità matematiche, 
            ottimizza il rendimento dei Punti Comando e forgia formazioni letali contro le difese nemiche."
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Griglia di Accesso Rapido ai Moduli
    col_lab, col_sala, col_forgia = st.columns(3)

    with col_lab:
        st.markdown("""
        <div class="hub-card">
            <h3>Laboratorio Tattico (Testa a Testa)</h3>
            <p style="color: #c4b59d; font-size: 1.02rem; min-height: 85px;">
                Confronta duelli singoli o coordina assalti combinati multi-unità. Analizza il flusso dei dadi, 
                la curva cumulativa Monte Carlo, la convenienza economica in punti e il verdetto sul Time-to-Kill.
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Apri Laboratorio Tattico", type="primary", use_container_width=True):
            st.session_state["pagina_selezionata"] = "Laboratorio Tattico (Testa a Testa)"
            st.rerun()

    with col_sala:
        st.markdown("""
        <div class="hub-card">
            <h3>Sala di Guerra (Costruttore Armate)</h3>
            <p style="color: #c4b59d; font-size: 1.02rem; min-height: 85px;">
                Componi la tua armata a punti (Path to Glory, 1000, 1500, 2000 pt). Monitora la saturazione dei ruoli, 
                il bilancio tra magia, preghiere e controllo, ed esamina le carenze tattiche del tuo schieramento.
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Entra nella Sala di Guerra", type="primary", use_container_width=True):
            st.session_state["pagina_selezionata"] = "Sala di Guerra (Costruttore Armate)"
            st.rerun()

    with col_forgia:
        st.markdown("""
        <div class="hub-card">
            <h3>Forgia del Grimorio (Database)</h3>
            <p style="color: #c4b59d; font-size: 1.02rem; min-height: 85px;">
                Aggiungi, modifica o aggiorna le warscrolls ufficiali. Inserisci le statistiche complete di movimento, 
                controllo, armi, abilità, reazioni e keywords per popolare il database del tuo esercito.
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Apri la Forgia", type="primary", use_container_width=True):
            st.session_state["pagina_selezionata"] = "Forgia del Grimorio (Database)"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Riquadro di Stato Rapido dell'Archivio
    with st.container(border=True):
        st.subheader("Stato dell'Arsenale & Risorse")
        st.caption("Riepilogo delle forze registrate e dell'integrazione di sistema.")
        
        n_unita_tot = len([k for k in st.session_state["db_unita"].keys() if k != "--- Seleziona o Resetta ---"])
        c_stat1, c_stat2, c_stat3 = st.columns(3)
        c_stat1.metric("Profili nel Grimorio", f"{n_unita_tot} Unità", "Salvate nel DB")
        c_stat2.metric("Regolamento Attivo", "AoS 4ª Edizione", "Modificatori & Ward 4e")
        
        is_cloud = False
        try:
            is_cloud = ("GITHUB_TOKEN" in st.secrets and "GITHUB_REPO" in st.secrets)
        except Exception:
            is_cloud = False
            
        c_stat3.metric("Sincronizzazione", "GitHub Cloud" if is_cloud else "Database Locale", "Attiva" if is_cloud else "Offline")
#
#
#
# ==========================================
# ROUTING DELLE PAGINE (MATCH / CASE)
# ==========================================
#
#
#
match st.session_state["pagina_selezionata"]:
    case "Portale Principale (Home)":
        render_homepage()

    case "Laboratorio Tattico (Testa a Testa)":
        render_testa_a_testa()
        
    case "Sala di Guerra (Costruttore Armate)":
        render_sala_di_guerra()
        
    case "Forgia del Grimorio (Database)":
        render_forgia_db()