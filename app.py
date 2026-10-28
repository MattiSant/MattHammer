import streamlit as st
from core_engine import applica_stile_globale, carica_database, salva_nel_database
from view_testa_a_testa import render_testa_a_testa
from view_sala_di_guerra import render_sala_di_guerra

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

opzioni_menu = [
    "Portale Principale (Home)",
    "Laboratorio Tattico (Testa a Testa)",
    "Sala di Guerra (Costruttore Armate)"
]

# Sincronizziamo la chiave del widget PRIMA che venga renderizzato
if "menu_sidebar_radio" not in st.session_state or st.session_state["menu_sidebar_radio"] != st.session_state["pagina_selezionata"]:
    st.session_state["menu_sidebar_radio"] = st.session_state["pagina_selezionata"]

def cambio_pagina_da_sidebar():
    st.session_state["pagina_selezionata"] = st.session_state["menu_sidebar_radio"]

st.sidebar.radio(
    "Navigazione del Tomo",
    opzioni_menu,
    key="menu_sidebar_radio",
    on_change=cambio_pagina_da_sidebar
)

st.sidebar.markdown("---")

# Mostra Directory e Gestione Database solo se non siamo sulla Home
if st.session_state["pagina_selezionata"] != "Portale Principale (Home)":
    st.sidebar.subheader("Directory Database")
    st.sidebar.caption("Seleziona e carica un'unità salvata.")

    albero_fazioni = {"Nighthaunt": [], "Blades of Khorne": [], "Orruk Kruleboyz": [], "Sylvaneth": [], "Personale / Altro": []}
    for nome_unita, dati_u in st.session_state["db_unita"].items():
        fazione_u = dati_u.get("fazione", "").lower()
        if "nighthaunt" in fazione_u: albero_fazioni["Nighthaunt"].append(nome_unita)
        elif "khorne" in fazione_u: albero_fazioni["Blades of Khorne"].append(nome_unita)
        elif "kruleboyz" in fazione_u: albero_fazioni["Orruk Kruleboyz"].append(nome_unita)
        elif "sylvaneth" in fazione_u: albero_fazioni["Sylvaneth"].append(nome_unita)
        else: albero_fazioni["Personale / Altro"].append(nome_unita)

    albero_fazioni_attive = {k: v for k, v in albero_fazioni.items() if len(v) > 0}
    if albero_fazioni_attive:
        fazione_selezionata = st.sidebar.selectbox("Fazione", list(albero_fazioni_attive.keys()))
        preset_scelto = st.sidebar.selectbox(f"Unità ({fazione_selezionata})", albero_fazioni_attive[fazione_selezionata])

        if st.sidebar.button("Carica nel Profilo", type="primary"):
            dati_sel = st.session_state["db_unita"][preset_scelto]
            st.session_state["corrente_armi"] = [dict(a) for a in dati_sel["armi"]]
            st.session_state["corrente_modelli"] = dati_sel["n_modelli"]
            st.session_state["corrente_campione"] = dati_sel["campione"]
            st.session_state["corrente_punti"] = dati_sel["punti"]
            st.session_state["corrente_difesa"] = dati_sel.get("difesa", {"salute_per_modello": 0, "save": "---", "ward": "---"})
            st.session_state["form_version"] += 1
            st.rerun()

    st.sidebar.markdown("---")
    if st.sidebar.button("Reset Parametri"):
        st.session_state["corrente_armi"] = [
            {"nome": "---", "attiva": False, "ranged": False, "atk": "---", "hit": "---", "wnd": "---", "rend": "---", "dmg": "---", "crit_type": "Nessuno", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False}
        ]
        st.session_state["corrente_modelli"] = 0
        st.session_state["corrente_campione"] = False
        st.session_state["corrente_punti"] = 0
        st.session_state["corrente_difesa"] = {"salute_per_modello": 0, "save": "---", "ward": "---"}
        st.session_state["form_version"] += 1
        st.rerun()

    tutte_le_unita = [u for u in st.session_state["db_unita"].keys() if u != "--- Seleziona o Resetta ---"]
    if tutte_le_unita:
        st.sidebar.markdown("---")
        st.sidebar.subheader("Gestione / Elimina")
        unita_da_eliminare = st.sidebar.selectbox("Rimuovi unità dal DB", tutte_le_unita, key="del_select")
        if st.sidebar.button("Elimina Unità", type="secondary"):
            if unita_da_eliminare in st.session_state["db_unita"]:
                del st.session_state["db_unita"][unita_da_eliminare]
                salva_nel_database(st.session_state["db_unita"])
                st.sidebar.success(f"Eliminata: {unita_da_eliminare}")
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
    col_lab, col_sala = st.columns(2)

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