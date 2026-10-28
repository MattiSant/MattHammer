import streamlit as st
from core_engine import applica_stile_globale, carica_database, salva_nel_database
from view_testa_a_testa import render_testa_a_testa
from view_sala_di_guerra import render_sala_di_guerra

st.set_page_config(
    page_title="MattHammer v1.2 - AoS Tactical Suite",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Applica lo stile estetico unificato per tutte le schermate
applica_stile_globale()

# Inizializzazione Session State condiviso
if "db_unita" not in st.session_state:
    st.session_state["db_unita"] = carica_database()

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

# ==========================================
# SIDEBAR CONDIVISA
# ==========================================
st.sidebar.title("MattHammer")
st.sidebar.caption("AoS 4e Tactical Suite v4.18")
st.sidebar.markdown("---")

# Selettore Modalità Operativa con match/case
modalita = st.sidebar.radio(
    "Modalità Operativa",
    [
        "Laboratorio Tattico (Testa a Testa)",
        "Sala di Guerra (Costruttore Armate)"
    ],
    index=0
)

st.sidebar.markdown("---")

# Gestione Database e Preset nella Sidebar
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
fazione_selezionata = st.sidebar.selectbox("Seleziona Fazione", list(albero_fazioni_attive.keys()))
unita_della_fazione = albero_fazioni_attive[fazione_selezionata]

preset_scelto = st.sidebar.selectbox(f"Unità ({fazione_selezionata})", unita_della_fazione)

if st.sidebar.button("Carica Unità Selezionata", type="primary"):
    dati_sel = st.session_state["db_unita"][preset_scelto]
    st.session_state["corrente_armi"] = [dict(a) for a in dati_sel["armi"]]
    st.session_state["corrente_modelli"] = dati_sel["n_modelli"]
    st.session_state["corrente_campione"] = dati_sel["campione"]
    st.session_state["corrente_punti"] = dati_sel["punti"]
    st.session_state["corrente_difesa"] = dati_sel.get("difesa", {"salute_per_modello": 0, "save": "---", "ward": "---"})
    st.session_state["form_version"] += 1
    st.rerun()

st.sidebar.markdown("---")

if st.sidebar.button("Reset Campi (Nuova Unità)"):
    st.session_state["corrente_armi"] = [
        {"nome": "---", "attiva": False, "ranged": False, "atk": "---", "hit": "---", "wnd": "---", "rend": "---", "dmg": "---", "crit_type": "Nessuno", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False}
    ]
    st.session_state["corrente_modelli"] = 0
    st.session_state["corrente_campione"] = False
    st.session_state["corrente_punti"] = 0
    st.session_state["corrente_difesa"] = {"salute_per_modello": 0, "save": "---", "ward": "---"}
    st.session_state["form_version"] += 1
    st.rerun()

# Eliminazione unità
tutte_le_unita = [u for u in st.session_state["db_unita"].keys() if u != "--- Seleziona o Resetta ---"]
if tutte_le_unita:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Gestione / Elimina Unità")
    unita_da_eliminare = st.sidebar.selectbox("Scegli unità da rimuovere", tutte_le_unita, key="del_select")
    if st.sidebar.button("Elimina Unità dal DB", type="secondary"):
        if unita_da_eliminare in st.session_state["db_unita"]:
            del st.session_state["db_unita"][unita_da_eliminare]
            salva_nel_database(st.session_state["db_unita"])
            st.sidebar.success(f"Eliminata: {unita_da_eliminare}")
            st.rerun()

st.sidebar.markdown("---")
try:
    if "GITHUB_TOKEN" in st.secrets and "GITHUB_REPO" in st.secrets:
        st.sidebar.success("Cloud Sync: Attivo (GitHub)")
    else:
        st.sidebar.info("Modalità Locale (Offline)")
except Exception:
    st.sidebar.info("Modalità Locale (Offline)")

# ==========================================
# ROUTING DELLE PAGINE (MATCH / CASE)
# ==========================================
match modalita:
    case "Laboratorio Tattico (Testa a Testa)":
        render_testa_a_testa()
        
    case "Sala di Guerra (Costruttore Armate)":
        render_sala_di_guerra()