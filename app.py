import streamlit as st
import numpy as np
import pandas as pd
import json
import os
import re
import base64
import requests

# ==========================================
# CONFIGURAZIONE PAGINA & STILE GRAFICO (PERGAMENA FANTASY)
# ==========================================
st.set_page_config(
    page_title="MattHammer v1.0 BETA - AoS Tactical Optimizer",
    page_icon="🔨",
    layout="wide",
    initial_sidebar_state="expanded"
)



# Stile CSS Avanzato: Tema Pergamena Antica & Input Arancio Scuro/Bronzo
st.markdown("""
<style>
    /* Sfondo principale dell'app (Cuoio scuro / Tavolo da gioco) */
    .stApp {
        background-color: #16120e;
        color: #fdf6e2;
        font-family: 'Cinzel', 'Georgia', serif;
    }
    
    /* Sidebar personalizzata */
    [data-testid="stSidebar"] {
        background-color: #1f1912;
        border-right: 2px solid #5c4730;
        color: #e6dfcc;
    }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stMarkdown {
        color: #e6dfcc !important;
    }
    
    /* Fogli di pergamena per ogni container/sezione principale */
    div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] {
        background: #f4ecd8 !important;
        border: 2px solid #8c6d46 !important;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4), inset 0 0 40px rgba(210, 180, 140, 0.3);
        color: #2b2318 !important;
        margin-bottom: 15px;
    }
    
    /* Titoli dentro le pergamene: scuri ed eleganti per massima leggibilità */
    div[data-testid="stContainer"] h1, 
    div[data-testid="stContainer"] h2, 
    div[data-testid="stContainer"] h3 {
        color: #2b2318 !important;
        font-weight: 700;
    }
    
    /* Etichette e testi normali dentro le pergamene */
    div[data-testid="stContainer"] p, 
    div[data-testid="stContainer"] label,
    div[data-testid="stContainer"] span {
        color: #3b2f20 !important;
        font-weight: 600;
    }

    /* Titoli fuori dai container (es. sezioni principali) resi più chiari e luminosi */
    h1, h2, h3 {
        color: #fdf6e2 !important;
        font-family: 'Cinzel', serif;
    }

    /* Expander a tema pergamena */
    .streamlit-expanderHeader {
        background-color: #e6dcbe !important;
        border: 1px solid #8c6d46 !important;
        border-radius: 6px;
        color: #2b2318 !important;
        font-weight: bold;
    }

    /* Campi di inserimento in ARANCIO SCURO/BRONZO */
    input, textarea, select {
        background-color: #3d2817 !important;
        color: #fdf6e2 !important;
        border: 1px solid #a67c52 !important;
        border-radius: 4px;
    }
    
    div[data-baseweb="select"] > div {
        background-color: #3d2817 !important;
        color: #fdf6e2 !important;
        border: 1px solid #a67c52 !important;
    }
    div[data-baseweb="select"] span {
        color: #fdf6e2 !important;
    }
    
    button[data-baseweb="button"] {
        background-color: #4a321f !important;
        color: #fdf6e2 !important;
    }

    /* Metric Cards in stile targa di bronzo antico */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #3d3124 100%, #2b2318 0%);
        border: 2px solid #b38b4d;
        padding: 14px;
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.5);
    }
    div[data-testid="metric-container"] label {
        color: #d4af37 !important;
        font-weight: bold;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #fdf6e2 !important;
        font-family: 'Cinzel', serif;
    }

    /* Bottoni principali in stile oro/bronzo antico */
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #996515 0%, #b38b4d 100%);
        color: #fffde6;
        border: 1px solid #d4af37;
        font-weight: bold;
        border-radius: 6px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: all 0.3s ease;
    }
    .stButton button[kind="primary"]:hover {
        background: linear-gradient(135deg, #b38b4d 0%, #d4af37 100%);
        box-shadow: 0 0 12px rgba(212, 175, 55, 0.7);
    }
</style>
""", unsafe_allow_html=True)

DB_FILE = "units_db.json"

# ==========================================
# UNITÀ DI DEFAULT
# ==========================================
DEFAULT_PRESETS = {
    "--- Seleziona o Resetta ---": {
        "fazione": "---",
        "n_modelli": 0, "campione": False, "punti": 0,
        "difesa": {"salute_per_modello": 0, "save": "---", "ward": "---"},
        "armi": [
            {"nome": "---", "attiva": False, "ranged": False, "atk": "---", "hit": "---", "wnd": "---", "rend": "---", "dmg": "---", "crit_type": "Nessuno", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False},
        ]
    }
}

# ==========================================
# GESTIONE DATABASE PERSISTENTE
# ==========================================
def carica_database():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                db_caricato = json.load(f)
                db_completo = DEFAULT_PRESETS.copy()
                db_completo.update(db_caricato)
                return db_completo
        except Exception:
            return DEFAULT_PRESETS.copy()
    else:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_PRESETS, f, indent=4, ensure_ascii=False)
        return DEFAULT_PRESETS.copy()

def salva_nel_database(db_dict):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db_dict, f, indent=4, ensure_ascii=False)
    return True, "Unità salvata nel Database locale dell'App!"

# ==========================================
# SMART TEXT PARSER
# ==========================================
def analizza_testo_copiato(testo_grezzo):
    armi_trovate = []
    linee = [l.strip() for l in testo_grezzo.split("\n") if l.strip()]
    
    pattern_stats = re.compile(
        r"(?:(\d+)\"|\bRange\b)?\s*"
        r"(\d+|D3|D6|2D6|2D3|D3\+1|D6\+1)\s*"
        r"([2-6])\+\s*"
        r"([2-6])\+\s*"
        r"(\-|\d+)\s*"
        r"(\d+|D3|D6|2D6|2D3|D3\+1|D6\+1)"
    )
    
    i = 0
    while i < len(linee):
        linea = linee[i]
        match = pattern_stats.search(linea)
        
        if match:
            range_val = match.group(1)
            ranged_flag = True if range_val is not None or '"' in linea else False
            
            atk_val = match.group(2)
            hit_val = int(match.group(3))
            wnd_val = int(match.group(4))
            rend_raw = match.group(5)
            rend_val = 0 if rend_raw == "-" else int(rend_raw)
            dmg_val = match.group(6)
            
            nome_arma = "Arma Importata"
            if i > 0 and not pattern_stats.search(linee[i-1]):
                prec = linee[i-1]
                if not any(k in prec.upper() for k in ["MELEE", "RANGED", "ATK", "HIT"]):
                    nome_arma = prec
            
            contesto = " ".join(linee[max(0, i-1):min(len(linee), i+2)])
            
            crit_t = "Nessuno"
            if "Crit (Mortal)" in contesto: crit_t = "Crit (Mortal)"
            elif "Crit (Auto-wound)" in contesto or "Crit(Auto-wound)" in contesto: crit_t = "Crit (Auto-wound)"
            elif "Crit (2 Hits)" in contesto: crit_t = "Crit (2 Hits)"

            comp_flag = "Companion" in contesto
            chrg_flag = "Charge (+1 Damage)" in contesto or "Charge" in contesto
            anti_c_flag = "Anti-charge" in contesto.lower()

            anti_t = "Nessuno"
            for k_anti in ["HERO", "INFANTRY", "CAVALRY", "MONSTER", "WAR MACHINE"]:
                if f"Anti-{k_anti}" in contesto or f"Anti-{k_anti.title()}" in contesto:
                    anti_t = k_anti

            armi_trovate.append({
                "nome": nome_arma, "attiva": True, "ranged": ranged_flag,
                "atk": str(atk_val), "hit": hit_val, "wnd": wnd_val, "rend": rend_val, "dmg": str(dmg_val),
                "crit_type": crit_t, "anti_target": anti_t,
                "charge_dmg": chrg_flag, "anti_charge": anti_c_flag, "companion": comp_flag
            })
        i += 1
    return armi_trovate

# ==========================================
# MOTORE MATEMATICO & MONTE CARLO
# ==========================================
def media_dado(val_str):
    val_str = str(val_str).upper().replace(" ", "")
    if val_str.isdigit(): return float(val_str)
    match = re.match(r"^(\d*)D([36])(?:\+(\d+))?$", val_str)
    if match:
        n_dadi = int(match.group(1)) if match.group(1) else 1
        tipo = int(match.group(2))
        bonus = int(match.group(3)) if match.group(3) else 0
        return n_dadi * (2.0 if tipo == 3 else 3.5) + bonus
    return 0.0

def tira_dado_mc(val_str, size):
    val_str = str(val_str).upper().replace(" ", "")
    if val_str.isdigit(): return np.full(size, int(val_str))
    match = re.match(r"^(\d*)D([36])(?:\+(\d+))?$", val_str)
    if match:
        n_dadi = int(match.group(1)) if match.group(1) else 1
        tipo = int(match.group(2))
        bonus = int(match.group(3)) if match.group(3) else 0
        if n_dadi == 0: return np.full(size, bonus)
        lanci = np.random.randint(1, tipo + 1, size=(n_dadi, size))
        return np.sum(lanci, axis=0) + bonus
    return np.zeros(size, dtype=int)

def calcola_arma_analitico(arma, mod_globali, bersaglio):
    if not arma["attiva"] or str(arma["hit"]) == "---" or str(arma["wnd"]) == "---": 
        return {"attacchi": 0, "hits": 0, "wounds": 0, "unsaved": 0, "mortal": 0, "danno_netto": 0}

    atk_per_modello = media_dado(arma["atk"])
    if not arma["companion"]: atk_per_modello += mod_globali["bonus_atk"]
    
    atk_totali = atk_per_modello * mod_globali["n_modelli"]
    if mod_globali["campione"] and not arma["companion"]: atk_totali += 1

    mod_hit_netto = mod_globali["mod_hit"]
    if arma["companion"] and mod_hit_netto > 0 and not mod_globali["all_out_attack"]: mod_hit_netto = 0
    if bersaglio["obscuring"] and arma["ranged"]: mod_hit_netto -= 1
    hit_target = np.clip(int(arma["hit"]) - np.clip(mod_hit_netto, -1, 1), 2, 6)

    soglia_crit = mod_globali["crit_on"]
    prob_crit = (7 - soglia_crit) / 6.0
    prob_hit_totale = (7 - hit_target) / 6.0
    prob_hit_normale = max(0.0, prob_hit_totale - prob_crit)

    danno_per_colpo = media_dado(arma["dmg"])
    if arma["charge_dmg"] and mod_globali["ha_caricato"]: danno_per_colpo += 1
    if not arma["companion"]: danno_per_colpo += mod_globali["bonus_dmg"]

    mortal_da_crit = 0.0
    auto_wounds = 0.0
    hits_che_devono_ferire = atk_totali * prob_hit_normale

    if arma["crit_type"] == "Crit (Mortal)": mortal_da_crit = atk_totali * prob_crit * danno_per_colpo
    elif arma["crit_type"] == "Crit (Auto-wound)": auto_wounds = atk_totali * prob_crit
    elif arma["crit_type"] == "Crit (2 Hits)": hits_che_devono_ferire += atk_totali * prob_crit * 2.0
    else: hits_che_devono_ferire += atk_totali * prob_crit

    hits_totali_visivi = hits_che_devono_ferire + auto_wounds + (atk_totali * prob_crit if arma["crit_type"] == "Crit (Mortal)" else 0)

    mod_wnd_netto = 0 if (arma["companion"] and mod_globali["mod_wnd"] > 0) else mod_globali["mod_wnd"]
    mod_wnd_netto += bersaglio["mod_wnd_nerf"]
    wnd_target = np.clip(int(arma["wnd"]) - np.clip(mod_wnd_netto, -2, 2), 2, 6)
    prob_wnd = (7 - wnd_target) / 6.0
    wounds_totali = (hits_che_devono_ferire * prob_wnd) + auto_wounds

    rend_effettivo = int(arma["rend"]) + (mod_globali["bonus_rend"] if not arma["companion"] else 0)
    if arma["anti_target"] != "Nessuno" and arma["anti_target"] in bersaglio["keywords"]: rend_effettivo += 1
    if arma["anti_charge"] and mod_globali["bersaglio_ha_caricato"]: rend_effettivo += 1

    if bersaglio["save"] >= 7: prob_save_fallito = 1.0
    else:
        bonus_save_positivo = min(2, (1 if bersaglio["cover"] else 0) + (1 if bersaglio["aod"] else 0) + bersaglio["bonus_save_extra"])
        save_target = bersaglio["save"] - bonus_save_positivo + rend_effettivo
        prob_save_fallito = 1.0 if save_target > 6 else 1.0 - ((7 - max(2, save_target)) / 6.0)

    colpi_non_salvati = wounds_totali * prob_save_fallito
    danni_normali_lordi = colpi_non_salvati * danno_per_colpo

    if bersaglio["blocca_ward"]: prob_ward_fallito = 1.0
    else:
        ward_effettivo = bersaglio["ward"] + bersaglio["mod_ward_penalita"]
        prob_ward_fallito = 1.0 if (bersaglio["ward"] >= 7 or ward_effettivo > 6) else 1.0 - ((7 - max(2, ward_effettivo)) / 6.0)
        
    danno_netto = (danni_normali_lordi + mortal_da_crit) * prob_ward_fallito
    return {"attacchi": atk_totali, "hits": hits_totali_visivi, "wounds": wounds_totali, "unsaved": colpi_non_salvati, "mortal": mortal_da_crit, "danno_netto": danno_netto}

def simula_monte_carlo(armi, mod_globali, bersaglio, n_sim=10000):
    danni_totali_sim = np.zeros(n_sim, dtype=float)
    ward_effettivo = bersaglio["ward"] + bersaglio["mod_ward_penalita"]
    ha_ward = (bersaglio["ward"] < 7) and (ward_effettivo <= 6) and (not bersaglio["blocca_ward"])
    ward_target = max(2, ward_effettivo)

    for arma in armi:
        if not arma["attiva"] or str(arma["hit"]) == "---" or str(arma["wnd"]) == "---": continue
        atk_base = tira_dado_mc(arma["atk"], n_sim)
        if not arma["companion"]: atk_base = atk_base + mod_globali["bonus_atk"]
        atk_tot_array = atk_base * mod_globali["n_modelli"]
        if mod_globali["campione"] and not arma["companion"]: atk_tot_array += 1

        n_attacchi_fisici = int(np.round(np.mean(atk_tot_array)))
        if n_attacchi_fisici <= 0: continue

        tiri_hit = np.random.randint(1, 7, size=(n_sim, n_attacchi_fisici))
        mod_hit_netto = mod_globali["mod_hit"]
        if arma["companion"] and mod_hit_netto > 0 and not mod_globali["all_out_attack"]: mod_hit_netto = 0
        if bersaglio["obscuring"] and arma["ranged"]: mod_hit_netto -= 1
        hit_target = np.clip(int(arma["hit"]) - np.clip(mod_hit_netto, -1, 1), 2, 6)

        is_crit = tiri_hit >= mod_globali["crit_on"]
        is_normal_hit = (tiri_hit >= hit_target) & (~is_crit)
        n_crits = np.sum(is_crit, axis=1)
        n_norm_hits = np.sum(is_normal_hit, axis=1)

        mortal_wounds_sim = np.zeros(n_sim)
        auto_wounds_sim = np.zeros(n_sim)
        hits_to_wound = n_norm_hits.copy()
        bonus_dmg_fisso = (1 if (arma["charge_dmg"] and mod_globali["ha_caricato"]) else 0) + (mod_globali["bonus_dmg"] if not arma["companion"] else 0)

        if arma["crit_type"] == "Crit (Mortal)": mortal_wounds_sim = n_crits * (tira_dado_mc(arma["dmg"], n_sim) + bonus_dmg_fisso)
        elif arma["crit_type"] == "Crit (Auto-wound)": auto_wounds_sim = n_crits
        elif arma["crit_type"] == "Crit (2 Hits)": hits_to_wound += n_crits * 2
        else: hits_to_wound += n_crits

        mod_wnd_netto = 0 if (arma["companion"] and mod_globali["mod_wnd"] > 0) else mod_globali["mod_wnd"]
        mod_wnd_netto += bersaglio["mod_wnd_nerf"]
        wnd_target = np.clip(int(arma["wnd"]) - np.clip(mod_wnd_netto, -2, 2), 2, 6)
        wounds_sim = np.random.binomial(hits_to_wound.astype(int), (7 - wnd_target) / 6.0) + auto_wounds_sim

        rend_eff = int(arma["rend"]) + (mod_globali["bonus_rend"] if not arma["companion"] else 0)
        if arma["anti_target"] != "Nessuno" and arma["anti_target"] in bersaglio["keywords"]: rend_eff += 1
        if arma["anti_charge"] and mod_globali["bersaglio_ha_caricato"]: rend_eff += 1

        if bersaglio["save"] >= 7: prob_fail_save = 1.0
        else:
            bonus_save = min(2, (1 if bersaglio["cover"] else 0) + (1 if bersaglio["aod"] else 0) + bersaglio["bonus_save_extra"])
            save_t = bersaglio["save"] - bonus_save + rend_eff
            prob_fail_save = 1.0 if save_t > 6 else 1.0 - ((7 - max(2, save_t)) / 6.0)

        danni_totali_sim += (np.random.binomial(wounds_sim.astype(int), prob_fail_save) * (tira_dado_mc(arma["dmg"], n_sim) + bonus_dmg_fisso)) + mortal_wounds_sim

    mortal_extra_dadi = mod_globali.get("mortal_extra_dadi", 0)
    mortal_extra_tipo = mod_globali.get("mortal_extra_tipo", 6)
    mortal_extra_soglia = mod_globali.get("mortal_extra_soglia", "Nessuna (Somma i valori)")
    mortal_extra_fisso = mod_globali.get("mortal_extra_fisso", 0)

    danni_totali_sim += mortal_extra_fisso
    if mortal_extra_dadi > 0:
        if mortal_extra_soglia == "Nessuna (Somma i valori)":
            lanci_extra = np.random.randint(1, mortal_extra_tipo + 1, size=(mortal_extra_dadi, n_sim))
            danni_totali_sim += np.sum(lanci_extra, axis=0)
        else:
            target_val = int(mortal_extra_soglia[0])
            prob = max(0.0, (mortal_extra_tipo - target_val + 1) / float(mortal_extra_tipo))
            danni_totali_sim += np.random.binomial(mortal_extra_dadi, prob, n_sim)

    if ha_ward: danni_totali_sim = np.random.binomial(danni_totali_sim.astype(int), 1.0 - ((7 - ward_target) / 6.0))
    return danni_totali_sim

# ==========================================
# INIZIALIZZAZIONE SESSION STATE CON "---"
# ==========================================
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


# ==========================================
# SIDEBAR: DIRECTORY E GUIDA RAPIDA
# ==========================================
st.sidebar.title("🔨 MattHammer")
st.sidebar.caption("AoS 4e Tactical Optimizer v4.16")

st.sidebar.markdown("---")

# 1. Directory Database
st.sidebar.subheader("📂 Directory Database")
st.sidebar.caption("Seleziona e carica un'unità salvata.")

albero_fazioni = {"👻 Nighthaunt": [], "🩸 Blades of Khorne": [], "👹 Orruk Kruleboyz": [], "🌲 Sylvaneth": [], "📁 Personale / Altro": []}
for nome_unita, dati_u in st.session_state["db_unita"].items():
    fazione_u = dati_u.get("fazione", "").lower()
    if "nighthaunt" in fazione_u: albero_fazioni["👻 Nighthaunt"].append(nome_unita)
    elif "khorne" in fazione_u: albero_fazioni["🩸 Blades of Khorne"].append(nome_unita)
    elif "kruleboyz" in fazione_u: albero_fazioni["👹 Orruk Kruleboyz"].append(nome_unita)
    elif "sylvaneth" in fazione_u: albero_fazioni["🌲 Sylvaneth"].append(nome_unita)
    else: albero_fazioni["📁 Personale / Altro"].append(nome_unita)

albero_fazioni_attive = {k: v for k, v in albero_fazioni.items() if len(v) > 0}
fazione_selezionata = st.sidebar.selectbox("Seleziona Fazione", list(albero_fazioni_attive.keys()))
unita_della_fazione = albero_fazioni_attive[fazione_selezionata]

preset_scelto = st.sidebar.selectbox(f"Unità ({fazione_selezionata})", unita_della_fazione)

if st.sidebar.button("📥 Carica Unità Selezionata", type="primary"):
    dati_sel = st.session_state["db_unita"][preset_scelto]
    st.session_state["corrente_armi"] = [dict(a) for a in dati_sel["armi"]]
    st.session_state["corrente_modelli"] = dati_sel["n_modelli"]
    st.session_state["corrente_campione"] = dati_sel["campione"]
    st.session_state["corrente_punti"] = dati_sel["punti"]
    st.session_state["corrente_difesa"] = dati_sel.get("difesa", {"salute_per_modello": 0, "save": "---", "ward": "---"})
    st.session_state["form_version"] += 1
    st.rerun()

st.sidebar.markdown("---")

# 2. Pulsante Reset Totale
if st.sidebar.button("🔄 Reset Campi (Nuova Unità)"):
    st.session_state["corrente_armi"] = [
        {"nome": "---", "attiva": False, "ranged": False, "atk": "---", "hit": "---", "wnd": "---", "rend": "---", "dmg": "---", "crit_type": "Nessuno", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False}
    ]
    st.session_state["corrente_modelli"] = 0
    st.session_state["corrente_campione"] = False
    st.session_state["corrente_punti"] = 0
    st.session_state["corrente_difesa"] = {"salute_per_modello": 0, "save": "---", "ward": "---"}
    st.session_state["form_version"] += 1
    st.rerun()

# Eliminazione Unità nel DB
st.sidebar.markdown("---")
st.sidebar.subheader("🗑️ Gestione / Elimina Unità")

# Mostra tutte le unità salvate nel DB per la cancellazione
tutte_le_unita = list(st.session_state["db_unita"].keys())
if tutte_le_unita:
    unita_da_eliminare = st.sidebar.selectbox("Scegli unità da rimuovere", tutte_le_unita, key="del_select")
    
    # Pulsante di eliminazione con conferma visiva
    if st.sidebar.button("❌ Elimina Unità dal DB", type="secondary"):
        if unita_da_eliminare in st.session_state["db_unita"]:
            del st.session_state["db_unita"][unita_da_eliminare]
            
            # Salva il database aggiornato (locale + GitHub cloud)
            salva_nel_database(st.session_state["db_unita"])
            st.sidebar.success(f"Eliminata: {unita_da_eliminare}")
            st.rerun()
else:
    st.sidebar.caption("Nessuna unità nel database.")

st.sidebar.markdown("---")
# Controllo dinamico dello stato della sincronizzazione
if "GITHUB_TOKEN" in st.secrets and "GITHUB_REPO" in st.secrets:
    st.sidebar.success("🌐 Cloud Sync: Attivo (GitHub)")
else:
    st.sidebar.info("💻 Modalità Locale (Offline)")

# ==========================================
# PANNELLO PRINCIPALE
# ==========================================
st.title("🔨 MattHammer - AoS 4e Tactical Optimizer")

st.markdown("---")
st.markdown("### ⚔️ 1. Unità da Analizzare")
st.caption("Inserisci qui le statistiche dell'unità che vuoi testare in combattimento.")
with st.container(border=True):
    st.subheader("📋 Inserimento Rapido da Warscroll")
    st.caption("Copia il blocco di testo dal manuale o da Wahapedia e incollalo qui per compilare automaticamente le armi.")
    
    testo_copiato = st.text_area("Incolla qui il testo:", placeholder="Es: Arma Potente 5 3+ 3+ 2 2", height=80)
    
    if st.button("⚡ Applica ai Profili Attivi", type="primary"):
        armi_estratte = analizza_testo_copiato(testo_copiato)
        if armi_estratte:
            st.session_state["corrente_armi"] = armi_estratte
            st.session_state["form_version"] += 1
            st.success(f"Successo! Applicate {len(armi_estratte)} armi.")
            st.rerun()
        else:
            st.error("Nessun profilo arma riconosciuto.")

col_armi, col_difesa_unita = st.columns(2)
opzioni_dadi_atk_dmg = ["---", "1", "2", "3", "4", "5", "6", "7", "8", "10", "12", "14", "D3", "D3+1", "D6", "D6+1", "D6+2", "2D3", "2D6"]
opzioni_hit_wnd = ["---", 2, 3, 4, 5, 6]
opzioni_save = ["---", 2, 3, 4, 5, 6]
opzioni_ward = ["---", 7, 6, 5, 4]

v_key = st.session_state["form_version"]

with col_armi:
    st.subheader("⚔️ Profili Armi ")
    st.caption("Verifica o modifica i valori di ciascuna arma.")
    if st.button("➕ Aggiungi Nuova Arma"):
        st.session_state["corrente_armi"].append({
            "nome": "---", "attiva": True, "ranged": False, "atk": "---",
            "hit": "---", "wnd": "---", "rend": 0, "dmg": "---", "crit_type": "Nessuno",
            "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False
        })
        st.session_state["form_version"] += 1
        st.rerun()
        
    armi_aggiornate = []
    for idx, p_arma in enumerate(st.session_state["corrente_armi"]):
        with st.expander(f"🗡️ Arma {idx+1}: {p_arma['nome']}", expanded=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            nome_a = c1.text_input("Nome Arma", value=p_arma["nome"], key=f"nome_{idx}_v{v_key}")
            attiva_a = c2.checkbox("Attiva", value=p_arma["attiva"], key=f"att_{idx}_v{v_key}")
            comp_a = c3.checkbox("Companion", value=p_arma["companion"], key=f"comp_{idx}_v{v_key}")

            s1, s2, s3, s4, s5 = st.columns(5)
            atk_str = str(p_arma["atk"])
            idx_atk = opzioni_dadi_atk_dmg.index(atk_str) if atk_str in opzioni_dadi_atk_dmg else 0
            
            hit_val = p_arma["hit"]
            idx_hit = opzioni_hit_wnd.index(hit_val) if hit_val in opzioni_hit_wnd else 0
            
            wnd_val = p_arma["wnd"]
            idx_wnd = opzioni_hit_wnd.index(wnd_val) if wnd_val in opzioni_hit_wnd else 0
            
            rend_val = 0 if p_arma["rend"] == "---" else int(p_arma["rend"])
            
            dmg_str = str(p_arma["dmg"])
            idx_dmg = opzioni_dadi_atk_dmg.index(dmg_str) if dmg_str in opzioni_dadi_atk_dmg else 0

            atk_a = s1.selectbox("Attacks", opzioni_dadi_atk_dmg, index=idx_atk, key=f"atk_{idx}_v{v_key}")
            hit_a = s2.selectbox("Hit (X+)", opzioni_hit_wnd, index=idx_hit, key=f"hit_{idx}_v{v_key}")
            wnd_a = s3.selectbox("Wound (X+)", opzioni_hit_wnd, index=idx_wnd, key=f"wnd_{idx}_v{v_key}")
            rend_a = s4.number_input("Rend", 0, 5, value=rend_val, key=f"rend_{idx}_v{v_key}")
            dmg_a = s5.selectbox("Damage", opzioni_dadi_atk_dmg, index=idx_dmg, key=f"dmg_{idx}_v{v_key}")

            ab1, ab2, ab3 = st.columns(3)
            opz_crit = ["Nessuno", "Crit (Mortal)", "Crit (Auto-wound)", "Crit (2 Hits)"]
            opz_anti = ["Nessuno", "HERO", "INFANTRY", "CAVALRY", "MONSTER", "WAR MACHINE"]
            idx_crit = opz_crit.index(p_arma["crit_type"]) if p_arma["crit_type"] in opz_crit else 0
            idx_anti = opz_anti.index(p_arma["anti_target"]) if p_arma["anti_target"] in opz_anti else 0

            crit_a = ab1.selectbox("Abilità Critico", opz_crit, index=idx_crit, key=f"crit_{idx}_v{v_key}")
            anti_a = ab2.selectbox("Anti-X (+1 Rend)", opz_anti, index=idx_anti, key=f"anti_{idx}_v{v_key}")
            ranged_a = ab3.checkbox("Arma da Tiro", value=p_arma["ranged"], key=f"rng_{idx}_v{v_key}")

            ch1, ch2, ch_del = st.columns(3)
            chrg_dmg_a = ch1.checkbox("Charge (+1 Dmg)", value=p_arma["charge_dmg"], key=f"cdmg_{idx}_v{v_key}")
            anti_chrg_a = ch2.checkbox("Anti-Charge", value=p_arma["anti_charge"], key=f"achrg_{idx}_v{v_key}")
            if ch_del.button("🗑️ Elimina", key=f"del_{idx}_v{v_key}"):
                st.session_state["corrente_armi"].pop(idx)
                st.session_state["form_version"] += 1
                st.rerun()

            armi_aggiornate.append({
                "nome": nome_a, "attiva": attiva_a, "ranged": ranged_a,
                "atk": atk_a, "hit": hit_a, "wnd": wnd_a, "rend": rend_a, "dmg": dmg_a,
                "crit_type": crit_a, "anti_target": anti_a,
                "charge_dmg": chrg_dmg_a, "anti_charge": anti_chrg_a, "companion": comp_a
            })
    st.session_state["corrente_armi"] = armi_aggiornate

with col_difesa_unita:
    st.subheader("🛡️ Caratteristiche Difensive Unità")
    with st.container(border=True):
        st.caption("Imposta le statistiche difensive per ciascun modello dell'unità")
        d_corrente = st.session_state["corrente_difesa"]
        salute_modello = st.number_input("Punti Ferita per Modello", 0, 30, int(d_corrente.get("salute_per_modello", 0)), key=f"def_salute_v{v_key}")
        
        save_val = d_corrente.get("save", "---")
        idx_save = opzioni_save.index(save_val) if save_val in opzioni_save else 0
        save_nativo = st.selectbox("Tiro Salvezza Base (Save X+)", opzioni_save, index=idx_save, key=f"def_save_v{v_key}")
        
        ward_val = d_corrente.get("ward", "---")
        idx_ward = opzioni_ward.index(ward_val) if ward_val in opzioni_ward else 0
        ward_nativo = st.selectbox("Tiro Ward Nativo (X+)", opzioni_ward, index=idx_ward, format_func=lambda x: f"{x}+" if x != "---" else "--- (Non inserito)", key=f"def_ward_v{v_key}")
        
        st.session_state["corrente_difesa"] = {"salute_per_modello": salute_modello, "save": save_nativo, "ward": ward_nativo}

col_comp, col_comandi = st.columns(2)
with col_comp:
    st.subheader("👥 Composizione Unità")
    with st.container(border=True):
        st.caption("Indica quanti modelli compongono l'unità (o se è rinforzata) e il costo totale in punti.")
        cs1, cs2 = st.columns(2)
        n_modelli_base = cs1.number_input("Modelli Base", min_value=0, max_value=60, value=int(st.session_state["corrente_modelli"]))
        rinforzata = cs2.checkbox("Rinforzata (x2)", value=False)
        n_modelli = n_modelli_base * 2 if rinforzata else n_modelli_base
        campione = st.checkbox("Presenza Campione (+1 Atk)", value=bool(st.session_state["corrente_campione"]))
        punti_unita = st.number_input("Costo in Punti", min_value=0, max_value=1200, value=int(st.session_state["corrente_punti"]) * (2 if rinforzata else 1), step=10)

with col_comandi:
    st.subheader("⚡ Comandi e Buff")
    with st.container(border=True):
        st.caption("Attiva se l'unità ha caricato, ha ricevuto comandi o ha bonus speciali.")
        ha_caricato = st.checkbox("🏇 L'unità ha Caricato questo turno", value=False)
        all_out_attack = st.checkbox("🎯 Comando: All-out Attack (+1 Hit)", value=False)
        with st.expander("✨ Altri Buff / Modificatori"):
            mod_hit_extra = st.slider("Altri Modificatori Hit", -2, 2, 0)
            mod_wnd_extra = st.slider("Modificatori Wound", -2, 2, 0)
            bonus_atk = st.number_input("Bonus Attacchi", 0, 5, 0)
            bonus_rend = st.number_input("Bonus Rend Globale", 0, 3, 1)
            bonus_dmg = st.number_input("Bonus Danno Globale", 0, 3, 0)
            crit_on_5 = st.checkbox("Critico al 5+", value=False)

st.subheader("💥 Danni Aggiuntivi ")
with st.container(border=True):
    st.caption("Aggiungi danni extra derivanti da abilità speciali o altre fonti esterne. Lascia a 0 se non applicabile.") 
    mortal_extra_dadi = 0
    mortal_extra_tipo = 6
    mortal_extra_soglia = "Nessuna (Somma i valori)"
    mortal_extra_fisso = 0
    
    st.markdown("**1. Parte Casuale**")
    c1, c2, c3 = st.columns(3)
    mortal_extra_dadi = c1.number_input("Numero Dadi", min_value=0, max_value=100, value=0)
    mortal_extra_tipo = c2.selectbox("Tipo Dado", [3, 6], index=1, format_func=lambda x: f"D{x}")
    mortal_extra_soglia = c3.selectbox("Valore di Successo", ["Nessuna (Somma i valori)", "2+", "3+", "4+", "5+", "6+"])
    
    st.markdown("**2. Parte Fissa**")
    mortal_extra_fisso = st.number_input("Numero fisso da aggiungere ai danni", min_value=0, max_value=100, value=0)

mod_globali = {
    "n_modelli": n_modelli, "campione": campione, "ha_caricato": ha_caricato,
    "all_out_attack": all_out_attack, "mod_hit": mod_hit_extra + (1 if all_out_attack else 0),
    "mod_wnd": mod_wnd_extra, "bonus_atk": bonus_atk, "bonus_rend": bonus_rend,
    "bonus_dmg": bonus_dmg, "crit_on": 5 if crit_on_5 else 6,
    "mortal_extra_dadi": mortal_extra_dadi,
    "mortal_extra_tipo": mortal_extra_tipo,
    "mortal_extra_soglia": mortal_extra_soglia,
    "mortal_extra_fisso": mortal_extra_fisso
}

st.subheader("🗄️ Salva Unità nel Database Locale")
with st.container(border=True):
    st.caption("Seleziona la fazione, dai un nome all'unità e salvala per poterla ricaricare rapidamente in futuro.")
    db_c1, db_c2 = st.columns(2)
    fazione_scelta = db_c1.selectbox("Seleziona Fazione", ["---", "Nighthaunt", "Blades of Khorne", "Orruk Kruleboyz", "Sylvaneth", "Personale / Altro"])
    nuovo_nome = db_c2.text_input("Nome Specifico dell'Unità:", placeholder="Es. Spirit Hosts")
    
    if st.button("💾 Valida e Salva nel DB", type="primary"):
        errori = []
        if fazione_scelta == "---": errori.append("Seleziona una fazione valida.")
        if not nuovo_nome.strip() or nuovo_nome == "---": errori.append("Inserisci un nome valido per l'unità.")
        if n_modelli <= 0: errori.append("Il numero di modelli deve essere maggiore di zero.")
        if punti_unita <= 0: errori.append("Il costo in punti deve essere specificato.")
        
        difesa_corrente = st.session_state["corrente_difesa"]
        if difesa_corrente.get("salute_per_modello") <= 0 or difesa_corrente.get("save") == "---":
            errori.append("I dati difensivi (Salute o Save) contengono campi non inseriti ('---').")
            
        for idx, arm in enumerate(st.session_state["corrente_armi"]):
            if arm["attiva"] and (str(arm["hit"]) == "---" or str(arm["wnd"]) == "---" or str(arm["atk"]) == "---" or str(arm["dmg"]) == "---"):
                errori.append(f"L'Arma {idx+1} ({arm['nome']}) ha parametri non compilati ('---').")

        if len(errori) > 0:
            for err in errori: st.error(f"❌ {err}")
        else:
            chiave_db = f"{fazione_scelta}: {nuovo_nome.strip()}"
            
            # Verifichiamo se l'unità esiste già nel database (per capire se stiamo sovrascrivendo)
            gia_esistente = chiave_db in st.session_state["db_unita"]
            
            # Salvataggio/Aggiornamento nel dizionario del database
            st.session_state["db_unita"][chiave_db] = {
                "fazione": fazione_scelta, 
                "n_modelli": n_modelli_base, 
                "campione": campione, 
                "punti": punti_unita, 
                "difesa": difesa_corrente, 
                "armi": st.session_state["corrente_armi"]
            }
            
            # Esegue il salvataggio (locale e cloud GitHub)
            successo, messaggio = salva_nel_database(st.session_state["db_unita"])
            
            if successo:
                if gia_esistente:
                    st.success(f"🔄 Unità '{chiave_db}' aggiornata con successo (sovrascritta)!")
                else:
                    st.success(f"✨ Nuova unità '{chiave_db}' aggiunta con successo al database!")
                st.rerun()
            else:
                st.error(f"❌ Errore durante il salvataggio: {messaggio}")
                
# ==========================================
# SEZIONE 2: UNITÀ BERSAGLIO
# ==========================================
st.markdown("---")
st.markdown("### 🎯 2. Unità Bersaglio")
st.caption("Configura le difese, i terreni (Cover) e i debuff dell'unità nemica che vuoi attaccare.")
with st.container(border=True):
    b1, b2, b3 = st.columns(3)
    save_b = b1.selectbox("Save Base Bersaglio", [2, 3, 4, 5, 6, 7], index=2, format_func=lambda x: f"{x}+" if x < 7 else "Nessuno (-)")
    ward_b = b2.selectbox("Ward Base Bersaglio", [7, 6, 5, 4], index=0, format_func=lambda x: f"{x}+" if x < 7 else "Nessuno (-)")
    salute_b = b3.number_input("Salute Totale Bersaglio", min_value=1, max_value=100, value=10)
    keywords_b = st.multiselect("Keywords del Bersaglio", ["INFANTRY", "HERO", "CAVALRY", "MONSTER", "WAR MACHINE"], default=["INFANTRY", "HERO"])

    st.markdown("---")
    st.markdown("**🛡️ Buff Difensivi del bersaglio:**")
    dt1, dt2, dt3 = st.columns(3)
    cover_b = dt1.checkbox("🌲 Cover (+1 Save)", value=False)
    aod_b = dt2.checkbox("🛡️ All-out Defence (+1 Save)", value=False)
    extra_save_b = dt3.checkbox("✨ Abilità extra / Scenario (+1 Save)", value=False)
    obscuring_b = dt1.checkbox("🌫️ Terreno Obscuring (-1 Hit al tiro)", value=False)
    bersaglio_carica = dt2.checkbox("⚡ Il Bersaglio ha Caricato", value=False)

    st.markdown("---")
    st.markdown("**💀 Debuff applicati al Bersaglio:**")
    nd1, nd2, nd3 = st.columns(3)
    debuff_ward = nd1.checkbox("💀 Debuff: -1 al tiro Ward", value=False)
    blocca_ward_b = nd2.checkbox("🚫 Ward Annullati", value=False)
    nerf_wound = nd3.selectbox("Modificatore Wound subito dal bersaglio", [0, 1, -1], index=0, format_func=lambda x: f"+{x} a Wound" if x>0 else (f"{x} a Wound" if x<0 else "Nessuno"))

bersaglio_dict = {
    "save": save_b, "ward": ward_b, "salute": salute_b, "keywords": keywords_b,
    "cover": cover_b, "aod": aod_b, "bonus_save_extra": 1 if extra_save_b else 0,
    "obscuring": obscuring_b, "bersaglio_ha_caricato": bersaglio_carica,
    "mod_ward_penalita": 1 if debuff_ward else 0,
    "blocca_ward": blocca_ward_b, "mod_wnd_nerf": nerf_wound
}
mod_globali["bersaglio_ha_caricato"] = bersaglio_carica

# ==========================================
# CALCOLI E SIMULAZIONE
# ==========================================
armi_attive_calcolo = st.session_state["corrente_armi"]
risultati_armi = [calcola_arma_analitico(a, mod_globali, bersaglio_dict) for a in armi_attive_calcolo]
danno_atteso_armi = sum(r["danno_netto"] for r in risultati_armi)

ward_eff = bersaglio_dict["ward"] + bersaglio_dict["mod_ward_penalita"]
moltiplicatore_ward = 0.0 if bersaglio_dict["blocca_ward"] else (1.0 if (bersaglio_dict["ward"] >= 7 or ward_eff > 6) else 1.0 - ((7 - max(2, ward_eff)) / 6.0))

danno_extra_base = float(mortal_extra_fisso)
if mortal_extra_dadi > 0:
    if mortal_extra_soglia == "Nessuna (Somma i valori)":
        danno_extra_base += mortal_extra_dadi * (2.0 if mortal_extra_tipo == 3 else 3.5)
    else:
        target_val = int(mortal_extra_soglia[0])
        prob = max(0.0, (mortal_extra_tipo - target_val + 1) / float(mortal_extra_tipo))
        danno_extra_base += mortal_extra_dadi * prob

danno_extra_atteso = danno_extra_base * moltiplicatore_ward
danno_totale_atteso = danno_atteso_armi + danno_extra_atteso

campioni_mc = simula_monte_carlo(armi_attive_calcolo, mod_globali, bersaglio_dict, n_sim=10000)
prob_uccisione = np.mean(campioni_mc >= salute_b) * 100.0
dev_std = np.std(campioni_mc)
roi_punti = (danno_totale_atteso / punti_unita) * 100.0 if punti_unita > 0 else 0.0

# ==========================================
# SEZIONE 3: ANALISI COMPARATIVA
# ==========================================
st.markdown("---")
st.markdown("### 📊 3. Risultati e Statistiche di Combattimento")

attacchi_totali = sum(r['attacchi'] for r in risultati_armi)
max_rend = max([int(a['rend']) for a in armi_attive_calcolo if a['attiva'] and str(a['rend']) != "---"] + [0])
ha_crit_mortal = any(a['crit_type'] == 'Crit (Mortal)' and a['attiva'] for a in armi_attive_calcolo)
anti_targets = list(set([a['anti_target'] for a in armi_attive_calcolo if a['attiva'] and a['anti_target'] != 'Nessuno']))

difesa_corrente = st.session_state["corrente_difesa"]
ward_unita = int(difesa_corrente.get("ward", 7)) if difesa_corrente.get("ward") != "---" else 7
save_unita = int(difesa_corrente.get("save", 4)) if difesa_corrente.get("save") != "---" else 4
salute_totale_unita = int(difesa_corrente.get("salute_per_modello", 2)) * mod_globali["n_modelli"]

ruoli_trovati = []

if ward_unita <= 5 or (save_unita <= 3 and salute_totale_unita >= 15):
    ruoli_trovati.append("🛡️ **Ancoraggio Difensivo (Tank)**: Ottima resistenza. Utilizza questa unità per presidiare gli obiettivi centrali, bloccare le truppe avversarie o fare da scudo alle tue retrovie.")

if len(anti_targets) > 0:
    targets_str = ", ".join(anti_targets)
    ruoli_trovati.append(f"🎯 **Specialista Anti-{targets_str}**: Letale contro questi bersagli specifici grazie al bonus di penetrazione dell'armatura. Focalizza i suoi attacchi su di essi per massimizzarne l'efficienza.")

if attacchi_totali >= 20:
    ruoli_trovati.append("🗡️ **Sfoltiscitore d'Orde**: Sfrutta l'enorme volume di dadi per saturare le difese nemiche. L'ideale contro unità leggere e numerose.")

if ha_crit_mortal or max_rend >= 2:
    ruoli_trovati.append("⚔️ **Bypassa-Armatura**: Eccelle contro bersagli con armature pesanti (Tiro Salvezza elevato). Ignora la truppa leggera e punta alle unità d'élite.")

if danno_totale_atteso >= 12:
    ruoli_trovati.append("💥 **Damage Dealer Puro**: Unità d'urto ad altissimo impatto offensivo. Infligge danni massicci in modo costante, scatenala contro le minacce principali.")

if not ruoli_trovati:
    ruoli_trovati.append("⚖️ **Combattente Flessibile / Supporto**: Unità tattica bilanciata. Utilizzala per contestare obiettivi secondari, schermare i fianchi o fornire supporto tattico alla linea di battaglia.")

with st.container(border=True):
    st.markdown("**🧠 Il Verdetto Strategico (Ruoli individuati):**")
    for ruolo in ruoli_trovati:
        st.markdown(f"- {ruolo}")

st.markdown("<br>", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("💥 Danno Medio Atteso", f"{danno_totale_atteso:.2f} ferite", f"± {dev_std:.1f} (Std)")
m2.metric("☠️ Prob. Kill (1 Turno)", f"{prob_uccisione:.1f}%", f"vs {salute_b} Salute")
m3.metric("⚖️ ROI Danni (per 100 pt)", f"{roi_punti:.2f} Danni", f"Costo: {punti_unita} pt")
m4.metric("🎲 Attacchi Totali", f"{attacchi_totali:.0f} dadi")

tab1, tab2, tab3 = st.tabs(["🎲 Ripartizione Dadi", "📊 Distribuzione Monte Carlo", "🧠 Consigliere Tattico & Time-to-Kill"])

with tab1:
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.subheader("Ripartizione Danni per Arma")
        righe_armi = []
        for a, r in zip(armi_attive_calcolo, risultati_armi):
            if a["attiva"] and str(a["hit"]) != "---":
                righe_armi.append({
                    "Arma": a["nome"], "Attacchi": round(r["attacchi"], 1),
                    "Hits": round(r["hits"], 2), "Wounds": round(r["wounds"], 2),
                    "Save Falliti": round(r["unsaved"], 2), "Danno Netto": round(r["danno_netto"], 2)
                })
        if righe_armi:
            st.dataframe(pd.DataFrame(righe_armi), use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ Inserisci i dati dell'unità e attiva almeno un'arma per vedere il dettaglio.")

    with col_t2:
        st.subheader("📉 Scomposizione del Flusso d'Attacco")
        st.caption("Mostra quanti dadi/colpi sopravvivono progressivamente in ogni fase del combattimento.")
        
        tot_atk = sum(r["attacchi"] for r in risultati_armi)
        tot_hits = sum(r["hits"] for r in risultati_armi)
        tot_wounds = sum(r["wounds"] for r in risultati_armi)
        tot_unsaved = sum(r["unsaved"] for r in risultati_armi)
        
        if tot_atk > 0:
            # Ordine logico sequenziale delle fasi d'attacco
            df_perdite = pd.DataFrame({
                "Fase": ["1. Attacchi", "2. Colpi (Hit)", "3. Ferite (Wound)", "4. Non Salvati"],
                "Valore": [round(tot_atk, 1), round(tot_hits, 1), round(tot_wounds, 1), round(tot_unsaved, 1)]
            })
            st.bar_chart(df_perdite.set_index("Fase"), color="#b38b4d")
        else:
            st.warning("⚠️ Dati non ancora inseriti o incompleti. Compila i campi dell'unità per visualizzare il grafico.")

with tab2:
    st.subheader("📊Curva di Probabilità Cumulativa (Monte Carlo)")
    max_danno_grafico = int(np.percentile(campioni_mc, 99.5)) + 2 if len(campioni_mc) > 0 else 10
    asse_x = np.arange(1, max(10, max_danno_grafico))
    prob_almeno_x = [np.mean(campioni_mc >= x) * 100.0 for x in asse_x]
    st.line_chart(pd.DataFrame({"Danni Minimi (X)": asse_x, "Probabilità (%)": prob_almeno_x}).set_index("Danni Minimi (X)"), color="#b38b4d")

with tab3:
    st.subheader("⏱️ Stima Sopravvivenza Bersaglio (Time-to-Kill)")
    ttk = salute_b / danno_totale_atteso if danno_totale_atteso > 0 else 99
    
    if ttk <= 1.0: st.success(f"**🔥 Letale!** Questa unità dovrebbe eliminare il bersaglio in **1 singolo turno di combattimento** (Danno atteso {danno_totale_atteso:.1f} vs Salute {salute_b}).")
    elif ttk <= 2.0: st.warning(f"**⚔️ Logoramento:** Saranno necessari circa **2 turni di combattimento** per abbattere questo bersaglio. Seleziona il target con cautela.")
    else: st.error(f"**🛡️ Inefficiente:** Serviranno circa **{int(ttk)+1} turni** per uccidere questo bersaglio. Sconsigliato ingaggiarlo in 1v1 senza supporto alleato.")
        
    st.markdown("---")
    st.subheader("🎯 Matrice Target Priority")
    st.caption("Efficacia del danno netto in base a Save e Ward del bersaglio.")
    saves_lista = [2, 3, 4, 5, 6, 7]
    wards_lista = [7, 6, 5, 4]
    matrice_dati = {}
    for w_val in wards_lista:
        col_nome = f"Ward {w_val}+" if w_val < 7 else "Nessun Ward"
        matrice_dati[col_nome] = [
            round(sum(calcola_arma_analitico(a, mod_globali, {**bersaglio_dict, "save": s_val, "ward": w_val, "blocca_ward": False})["danno_netto"] for a in armi_attive_calcolo), 2)
            for s_val in saves_lista
        ]
    df_matrice = pd.DataFrame(matrice_dati, index=[f"Save {s}+" if s < 7 else "No Save (-)" for s in saves_lista])
    
    st.dataframe(df_matrice.style.background_gradient(cmap="YlOrBr", low=0.1, high=0.8), use_container_width=True)