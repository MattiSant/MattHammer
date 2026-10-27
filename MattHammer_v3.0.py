import streamlit as st
import numpy as np
import pandas as pd
import json
import os
import re
import base64
import requests
from bs4 import BeautifulSoup

# ==========================================
# CONFIGURAZIONE PAGINA
# ==========================================
st.set_page_config(
    page_title="MattHammer v3.0 - AoS Optimizer",
    page_icon="🔨",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background-color: rgba(28, 131, 225, 0.1);
        border: 1px solid rgba(28, 131, 225, 0.3);
        padding: 12px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

DB_FILE = "units_db.json"

# ==========================================
# UNITÀ DI DEFAULT (Dal tuo Notebook AoS)
# ==========================================
DEFAULT_PRESETS = {
    "Personalizzato (Manuale)": {
        "n_modelli": 10, "campione": True, "punti": 150,
        "armi": [
            {"nome": "Arma Principale", "attiva": True, "ranged": False, "atk": "2", "hit": 3, "wnd": 3, "rend": 1, "dmg": "1", "crit_type": "Nessuno", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False},
            {"nome": "Arma Cavalcatura / Secondaria", "attiva": False, "ranged": False, "atk": "2", "hit": 4, "wnd": 4, "rend": 0, "dmg": "1", "crit_type": "Nessuno", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": True},
        ]
    },
    "Nighthaunt: Kurdoss Valentian": {
        "n_modelli": 1, "campione": False, "punti": 200,
        "armi": [
            {"nome": "Sepulchral Sceptre", "attiva": True, "ranged": False, "atk": "5", "hit": 3, "wnd": 3, "rend": 2, "dmg": "3", "crit_type": "Crit (Auto-wound)", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False},
            {"nome": "Nessuna", "attiva": False, "ranged": False, "atk": "1", "hit": 4, "wnd": 4, "rend": 0, "dmg": "1", "crit_type": "Nessuno", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False},
        ]
    },
    "Nighthaunt: Reikenor The Grimhailer": {
        "n_modelli": 1, "campione": False, "punti": 210,
        "armi": [
            {"nome": "Fellreaper", "attiva": True, "ranged": False, "atk": "5", "hit": 3, "wnd": 3, "rend": 2, "dmg": "2", "crit_type": "Crit (Auto-wound)", "anti_target": "Nessuno", "charge_dmg": True, "anti_charge": False, "companion": False},
            {"nome": "Kyllaron's Ghostly Hooves", "attiva": True, "ranged": False, "atk": "3", "hit": 5, "wnd": 3, "rend": 0, "dmg": "1", "crit_type": "Crit (Auto-wound)", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": True},
        ]
    },
    "Nighthaunt: Hexwraiths (5 Modelli)": {
        "n_modelli": 5, "campione": True, "punti": 200,
        "armi": [
            {"nome": "Spectral Scythe", "attiva": True, "ranged": False, "atk": "2", "hit": 4, "wnd": 4, "rend": 1, "dmg": "1", "crit_type": "Crit (Auto-wound)", "anti_target": "Nessuno", "charge_dmg": True, "anti_charge": False, "companion": False},
            {"nome": "Ethereal Steed's Hooves", "attiva": True, "ranged": False, "atk": "2", "hit": 5, "wnd": 3, "rend": 0, "dmg": "1", "crit_type": "Crit (Auto-wound)", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": True},
        ]
    },
    "Nighthaunt: Bladegheist Revenants (10 Modelli)": {
        "n_modelli": 10, "campione": True, "punti": 180,
        "armi": [
            {"nome": "Tomb Greatblade", "attiva": True, "ranged": False, "atk": "2", "hit": 3, "wnd": 3, "rend": 1, "dmg": "1", "crit_type": "Crit (Auto-wound)", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False},
            {"nome": "Nessuna", "attiva": False, "ranged": False, "atk": "1", "hit": 4, "wnd": 4, "rend": 0, "dmg": "1", "crit_type": "Nessuno", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False},
        ]
    },
    "Kruleboyz: Gobsprakk, The Mouth of Mork": {
        "n_modelli": 1, "campione": False, "punti": 380,
        "armi": [
            {"nome": "Bogbark Staff", "attiva": True, "ranged": False, "atk": "3", "hit": 4, "wnd": 3, "rend": 0, "dmg": "D3", "crit_type": "Crit (Mortal)", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False},
            {"nome": "Killabeak's Stinger", "attiva": True, "ranged": False, "atk": "1", "hit": 3, "wnd": 2, "rend": 1, "dmg": "D6", "crit_type": "Crit (Mortal)", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": True},
        ]
    },
    "Kruleboyz: Swampboss Skumdrekk": {
        "n_modelli": 1, "campione": False, "punti": 220,
        "armi": [
            {"nome": "Sloppklaw's Talons", "attiva": True, "ranged": False, "atk": "6", "hit": 4, "wnd": 2, "rend": 1, "dmg": "2", "crit_type": "Crit (Mortal)", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": True},
            {"nome": "Snatcha-stikk", "attiva": True, "ranged": False, "atk": "4", "hit": 4, "wnd": 3, "rend": 1, "dmg": "2", "crit_type": "Crit (Mortal)", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False},
        ]
    },
    "Sylvaneth: Branchwych": {
        "n_modelli": 1, "campione": False, "punti": 120,
        "armi": [
            {"nome": "Greenwood Scythe and Bittergrub", "attiva": True, "ranged": False, "atk": "3", "hit": 3, "wnd": 4, "rend": 1, "dmg": "D3", "crit_type": "Nessuno", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False},
            {"nome": "Nessuna", "attiva": False, "ranged": False, "atk": "1", "hit": 4, "wnd": 4, "rend": 0, "dmg": "1", "crit_type": "Nessuno", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False},
        ]
    },
    "Blades of Khorne: Khornate Warlord on Juggernaut": {
        "n_modelli": 1, "campione": False, "punti": 250,
        "armi": [
            {"nome": "Great Blood-slick Weapon", "attiva": True, "ranged": False, "atk": "5", "hit": 3, "wnd": 3, "rend": 1, "dmg": "2", "crit_type": "Crit (2 Hits)", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False},
            {"nome": "Juggernaut's Brass-shod Hooves", "attiva": True, "ranged": False, "atk": "2", "hit": 4, "wnd": 3, "rend": 1, "dmg": "D3", "crit_type": "Nessuno", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": True},
        ]
    }
}

# ==========================================
# GESTIONE DATABASE PERSISTENTE (Locale + GitHub Cloud)
# ==========================================
def carica_database():
    """Carica il database dal file JSON locale o inizializza con i default."""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                db_caricato = json.load(f)
                # Unisce i default con quelli salvati dagli utenti
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
    """Salva nel file JSON locale e, se configurato nei Secrets, sincronizza su GitHub."""
    # 1. Salvataggio su file locale
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db_dict, f, indent=4, ensure_ascii=False)
    
    # 2. Sincronizzazione automatica su GitHub (Opzionale ma raccomandata per il Cloud)
    if "GITHUB_TOKEN" in st.secrets and "GITHUB_REPO" in st.secrets:
        try:
            token = st.secrets["GITHUB_TOKEN"]
            repo = st.secrets["GITHUB_REPO"]  # formato: "tuo-username/MattHammer"
            url = f"https://api.github.com/repos/{repo}/contents/{DB_FILE}"
            headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
            
            # Controlla se il file esiste già su GitHub per ottenere lo SHA
            r_get = requests.get(url, headers=headers)
            sha = r_get.json().get("sha") if r_get.status_code == 200 else None
            
            content_b64 = base64.b64encode(json.dumps(db_dict, indent=4, ensure_ascii=False).encode("utf-8")).decode("utf-8")
            payload = {
                "message": "Aggiornamento DB Unità da MattHammer App",
                "content": content_b64
            }
            if sha:
                payload["sha"] = sha
            requests.put(url, headers=headers, json=payload)
            return True, "Salvato nel Database Cloud (GitHub Sync attivo)!"
        except Exception as e:
            return True, f"Salvato localmente (Sync GitHub non riuscito: {e})"
    return True, "Unità salvata nel Database dell'App!"

# ==========================================
# PARSER WAHAPEDIA (URL Scraper + Smart Text Regex)
# ==========================================
def analizza_testo_wahapedia(testo_grezzo):
    """
    Estrae profili d'arma incollati da Wahapedia usando Espressioni Regolari.
    Esempio riconosciuto: 'Sloppklaw’s Talons 6 4+ 2+ 1 2' o 'Killabeak’s Stinger 1 3+ 2+ 1 D6'
    """
    armi_trovate = []
    # Pattern Regex: Nome Arma | eventuale Range | Atk | Hit+ | Wnd+ | Rend (- o numero) | Dmg
    pattern = re.compile(
        r"([A-Za-z’'\-\s]{3,40}?)\s+(?:(\d+\")\s+)?(\d+|D3|D6|2D6|2D3|D3\+1|D6\+1)\s+([2-6])\+\s+([2-6])\+\s+(\-|\d+)\s+(\d+|D3|D6|2D6|2D3|D3\+1|D6\+1)"
    )
    
    linee = testo_grezzo.split("\n")
    for i, linea in enumerate(linee):
        match = pattern.search(linea)
        if match:
            nome_raw = match.group(1).strip()
            # Ignora intestazioni di tabella
            if any(k in nome_raw.upper() for k in ["MELEE WEAPONS", "RANGED WEAPONS", "ATK HIT WND"]):
                continue
            ranged_flag = bool(match.group(2))
            atk_val = match.group(3)
            hit_val = int(match.group(4))
            wnd_val = int(match.group(5))
            rend_raw = match.group(6)
            rend_val = 0 if rend_raw == "-" else int(rend_raw)
            dmg_val = match.group(7)

            # Cerca abilità nella stessa riga o nella riga successiva (come fa Wahapedia)
            contesto_abilita = linea + (" " + linee[i+1] if i+1 < len(linee) else "")
            crit_t = "Nessuno"
            if "Crit (Mortal)" in contesto_abilita:
                crit_t = "Crit (Mortal)"
            elif "Crit (Auto-wound)" in contesto_abilita:
                crit_t = "Crit (Auto-wound)"
            elif "Crit (2 Hits)" in contesto_abilita:
                crit_t = "Crit (2 Hits)"

            comp_flag = "Companion" in contesto_abilita
            chrg_flag = "Charge (+1 Damage)" in contesto_abilita
            anti_c_flag = "Anti-charge" in contesto_abilita.lower()

            anti_t = "Nessuno"
            for k_anti in ["HERO", "INFANTRY", "CAVALRY", "MONSTER", "WAR MACHINE"]:
                if f"Anti-{k_anti}" in contesto_abilita or f"Anti-{k_anti.title()}" in contesto_abilita:
                    anti_t = k_anti

            armi_trovate.append({
                "nome": nome_raw,
                "attiva": True,
                "ranged": ranged_flag,
                "atk": atk_val if atk_val in ["1","2","3","4","5","6","14","D3","D3+1","D6","D6+1","2D3","2D6"] else "2",
                "hit": hit_val,
                "wnd": wnd_val,
                "rend": rend_val,
                "dmg": dmg_val if dmg_val in ["1","2","3","4","5","6","D3","D3+1","D6","D6+1","2D3","2D6"] else "1",
                "crit_type": crit_t,
                "anti_target": anti_t,
                "charge_dmg": chrg_flag,
                "anti_charge": anti_c_flag,
                "companion": comp_flag
            })
    return armi_trovate

def scarica_da_url_wahapedia(url):
    """Prova a scaricare la pagina Wahapedia ed estrarre il testo delle armi."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code != 200:
        raise Exception(f"Wahapedia ha bloccato la richiesta automatica (Codice {resp.status_code}). Usa il Copia-Incolla Testo qui a fianco!")
    soup = BeautifulSoup(resp.text, "html.parser")
    testo_pagina = soup.get_text(separator="\n")
    return analizza_testo_wahapedia(testo_pagina)

# ==========================================
# FUNZIONI MATEMATICHE E MONTE CARLO
# ==========================================
def media_dado(val_str):
    mappa = {
        "1": 1.0, "2": 2.0, "3": 3.0, "4": 4.0, "5": 5.0, "6": 6.0,
        "7": 7.0, "8": 8.0, "10": 10.0, "12": 12.0, "14": 14.0,
        "D3": 2.0, "D3+1": 3.0, "D6": 3.5, "D6+1": 4.5, "D6+2": 5.5,
        "2D3": 4.0, "2D6": 7.0
    }
    return mappa.get(str(val_str), float(val_str) if str(val_str).isdigit() else 1.0)

def tira_dado_mc(val_str, size):
    val_str = str(val_str)
    if val_str.isdigit():
        return np.full(size, int(val_str))
    elif val_str == "D3":
        return np.random.randint(1, 4, size=size)
    elif val_str == "D3+1":
        return np.random.randint(1, 4, size=size) + 1
    elif val_str == "D6":
        return np.random.randint(1, 7, size=size)
    elif val_str == "D6+1":
        return np.random.randint(1, 7, size=size) + 1
    elif val_str == "D6+2":
        return np.random.randint(1, 7, size=size) + 2
    elif val_str == "2D3":
        return np.random.randint(1, 4, size=size) + np.random.randint(1, 4, size=size)
    elif val_str == "2D6":
        return np.random.randint(1, 7, size=size) + np.random.randint(1, 7, size=size)
    return np.ones(size, dtype=int)

def calcola_arma_analitico(arma, mod_globali, bersaglio):
    if not arma["attiva"]:
        return {"attacchi": 0, "hits": 0, "wounds": 0, "unsaved": 0, "mortal": 0, "danno_netto": 0}

    atk_per_modello = media_dado(arma["atk"])
    if not arma["companion"]:
        atk_per_modello += mod_globali["bonus_atk"]
    
    atk_totali = atk_per_modello * mod_globali["n_modelli"]
    if mod_globali["campione"] and not arma["companion"]:
        atk_totali += 1

    mod_hit_netto = mod_globali["mod_hit"]
    if arma["companion"] and mod_hit_netto > 0 and not mod_globali["all_out_attack"]:
        mod_hit_netto = 0
    if bersaglio["obscuring"] and arma["ranged"]:
        mod_hit_netto -= 1
    mod_hit_capped = np.clip(mod_hit_netto, -1, 1)
    hit_target = np.clip(arma["hit"] - mod_hit_capped, 2, 6)

    soglia_crit = mod_globali["crit_on"]
    prob_crit = (7 - soglia_crit) / 6.0
    prob_hit_totale = (7 - hit_target) / 6.0
    prob_hit_normale = max(0.0, prob_hit_totale - prob_crit)

    danno_per_colpo = media_dado(arma["dmg"])
    if arma["charge_dmg"] and mod_globali["ha_caricato"]:
        danno_per_colpo += 1
    if not arma["companion"]:
        danno_per_colpo += mod_globali["bonus_dmg"]

    mortal_da_crit = 0.0
    auto_wounds = 0.0
    hits_che_devono_ferire = atk_totali * prob_hit_normale

    if arma["crit_type"] == "Crit (Mortal)":
        mortal_da_crit = atk_totali * prob_crit * danno_per_colpo
    elif arma["crit_type"] == "Crit (Auto-wound)":
        auto_wounds = atk_totali * prob_crit
    elif arma["crit_type"] == "Crit (2 Hits)":
        hits_che_devono_ferire += atk_totali * prob_crit * 2.0
    else:
        hits_che_devono_ferire += atk_totali * prob_crit

    hits_totali_visivi = hits_che_devono_ferire + auto_wounds + (atk_totali * prob_crit if arma["crit_type"] == "Crit (Mortal)" else 0)

    mod_wnd_netto = 0 if (arma["companion"] and mod_globali["mod_wnd"] > 0) else mod_globali["mod_wnd"]
    mod_wnd_capped = np.clip(mod_wnd_netto, -1, 1)
    wnd_target = np.clip(arma["wnd"] - mod_wnd_capped, 2, 6)
    prob_wnd = (7 - wnd_target) / 6.0

    wounds_totali = (hits_che_devono_ferire * prob_wnd) + auto_wounds

    rend_effettivo = arma["rend"] + (mod_globali["bonus_rend"] if not arma["companion"] else 0)
    if arma["anti_target"] != "Nessuno" and arma["anti_target"] in bersaglio["keywords"]:
        rend_effettivo += 1
    if arma["anti_charge"] and mod_globali["bersaglio_ha_caricato"]:
        rend_effettivo += 1

    if bersaglio["save"] >= 7:
        prob_save_fallito = 1.0
    else:
        bonus_save_positivo = min(1, (1 if bersaglio["cover"] else 0) + (1 if bersaglio["aod"] else 0))
        save_target = bersaglio["save"] - bonus_save_positivo + rend_effettivo
        if save_target > 6:
            prob_save_fallito = 1.0
        else:
            save_target = max(2, save_target)
            prob_save_fallito = 1.0 - ((7 - save_target) / 6.0)

    colpi_non_salvati = wounds_totali * prob_save_fallito
    danni_normali_lordi = colpi_non_salvati * danno_per_colpo

    ward_effettivo = bersaglio["ward"] + bersaglio["mod_ward_penalita"]
    if bersaglio["ward"] >= 7 or ward_effettivo > 6:
        prob_ward_fallito = 1.0
    else:
        ward_effettivo = max(2, ward_effettivo)
        prob_ward_fallito = 1.0 - ((7 - ward_effettivo) / 6.0)

    danno_netto = (danni_normali_lordi + mortal_da_crit) * prob_ward_fallito

    return {
        "attacchi": atk_totali, "hits": hits_totali_visivi, "wounds": wounds_totali,
        "unsaved": colpi_non_salvati, "mortal": mortal_da_crit, "danno_netto": danno_netto
    }

def simula_monte_carlo(armi, mod_globali, bersaglio, n_sim=10000):
    danni_totali_sim = np.zeros(n_sim, dtype=float)
    ward_effettivo = bersaglio["ward"] + bersaglio["mod_ward_penalita"]
    ha_ward = (bersaglio["ward"] < 7) and (ward_effettivo <= 6)
    ward_target = max(2, ward_effettivo)

    for arma in armi:
        if not arma["attiva"]:
            continue

        atk_base = tira_dado_mc(arma["atk"], n_sim)
        if not arma["companion"]:
            atk_base = atk_base + mod_globali["bonus_atk"]
        atk_tot_array = atk_base * mod_globali["n_modelli"]
        if mod_globali["campione"] and not arma["companion"]:
            atk_tot_array += 1

        n_attacchi_fisici = int(np.round(np.mean(atk_tot_array)))
        if n_attacchi_fisici <= 0:
            continue

        tiri_hit = np.random.randint(1, 7, size=(n_sim, n_attacchi_fisici))

        mod_hit_netto = mod_globali["mod_hit"]
        if arma["companion"] and mod_hit_netto > 0 and not mod_globali["all_out_attack"]:
            mod_hit_netto = 0
        if bersaglio["obscuring"] and arma["ranged"]:
            mod_hit_netto -= 1
        hit_target = np.clip(arma["hit"] - np.clip(mod_hit_netto, -1, 1), 2, 6)

        is_crit = tiri_hit >= mod_globali["crit_on"]
        is_normal_hit = (tiri_hit >= hit_target) & (~is_crit)

        n_crits = np.sum(is_crit, axis=1)
        n_norm_hits = np.sum(is_normal_hit, axis=1)

        mortal_wounds_sim = np.zeros(n_sim)
        auto_wounds_sim = np.zeros(n_sim)
        hits_to_wound = n_norm_hits.copy()

        bonus_dmg_fisso = (1 if (arma["charge_dmg"] and mod_globali["ha_caricato"]) else 0) + (mod_globali["bonus_dmg"] if not arma["companion"] else 0)

        if arma["crit_type"] == "Crit (Mortal)":
            dmg_unit = tira_dado_mc(arma["dmg"], n_sim) + bonus_dmg_fisso
            mortal_wounds_sim = n_crits * dmg_unit
        elif arma["crit_type"] == "Crit (Auto-wound)":
            auto_wounds_sim = n_crits
        elif arma["crit_type"] == "Crit (2 Hits)":
            hits_to_wound += n_crits * 2
        else:
            hits_to_wound += n_crits

        mod_wnd_netto = 0 if (arma["companion"] and mod_globali["mod_wnd"] > 0) else mod_globali["mod_wnd"]
        wnd_target = np.clip(arma["wnd"] - np.clip(mod_wnd_netto, -1, 1), 2, 6)
        prob_wnd = (7 - wnd_target) / 6.0

        wounds_sim = np.random.binomial(hits_to_wound.astype(int), prob_wnd) + auto_wounds_sim

        rend_eff = arma["rend"] + (mod_globali["bonus_rend"] if not arma["companion"] else 0)
        if arma["anti_target"] != "Nessuno" and arma["anti_target"] in bersaglio["keywords"]:
            rend_eff += 1
        if arma["anti_charge"] and mod_globali["bersaglio_ha_caricato"]:
            rend_eff += 1

        if bersaglio["save"] >= 7:
            prob_fail_save = 1.0
        else:
            bonus_save = min(1, (1 if bersaglio["cover"] else 0) + (1 if bersaglio["aod"] else 0))
            save_t = bersaglio["save"] - bonus_save + rend_eff
            prob_fail_save = 1.0 if save_t > 6 else 1.0 - ((7 - max(2, save_t)) / 6.0)

        unsaved_sim = np.random.binomial(wounds_sim.astype(int), prob_fail_save)
        dmg_per_unsaved = tira_dado_mc(arma["dmg"], n_sim) + bonus_dmg_fisso
        danni_lordi_arma = (unsaved_sim * dmg_per_unsaved) + mortal_wounds_sim

        danni_totali_sim += danni_lordi_arma

    if mod_globali["mortal_extra"] != "0":
        danni_totali_sim += tira_dado_mc(mod_globali["mortal_extra"], n_sim)

    if ha_ward:
        prob_fail_ward = 1.0 - ((7 - ward_target) / 6.0)
        danni_totali_sim = np.random.binomial(danni_totali_sim.astype(int), prob_fail_ward)

    return danni_totali_sim

# ==========================================
# INIZIALIZZAZIONE STATO & DB
# ==========================================
if "db_unita" not in st.session_state:
    st.session_state["db_unita"] = carica_database()

# ==========================================
# SIDEBAR: SELEZIONE UNITA' (Directory Tree per Fazione)
# ==========================================
st.sidebar.title("🔨 MattHammer v3.0")

lista_nomi_unita = list(st.session_state["db_unita"].keys())
idx_default = st.session_state.get("idx_selezionato", 0)
if idx_default >= len(lista_nomi_unita):
    idx_default = 0

# Organizziamo le unità del database in categorie (Directory Tree)
albero_fazioni = {
    "👻 Nighthaunt": [],
    "🩸 Khorne": [],
    "👹 Kruleboyz": [],
    "🌲 Sylvaneth": [],
    "📁 Personale / Altro": []
}

# Suddivide automaticamente le unità del DB nelle rispettive cartelle in base al nome
for nome_unita in st.session_state["db_unita"].keys():
    nome_up = nome_unita.upper()
    if "NIGHTHAUNT" in nome_up:
        albero_fazioni["👻 Nighthaunt"].append(nome_unita)
    elif "KHORNE" in nome_up:
        albero_fazioni["🩸 Khorne"].append(nome_unita)
    elif "KRULEBOYZ" in nome_up:
        albero_fazioni["👹 Kruleboyz"].append(nome_unita)
    elif "SYLVANETH" in nome_up:
        albero_fazioni["🌲 Sylvaneth"].append(nome_unita)
    else:
        albero_fazioni["📁 Personale / Altro"].append(nome_unita)

# Rimuove le categorie vuote se non contengono unità
albero_fazioni_attive = {k: v for k, v in albero_fazioni.items() if len(v) > 0}

st.sidebar.subheader("📂 Directory Database")
fazione_selezionata = st.sidebar.selectbox("Seleziona Fazione", list(albero_fazioni_attive.keys()))

# Sotto-menu con le unità della fazione scelta
unita_della_fazione = albero_fazioni_attive[fazione_selezionata]
preset_scelto = st.sidebar.selectbox(f"Unità ({fazione_selezionata})", unita_della_fazione)

dati_preset = st.session_state["db_unita"][preset_scelto]

st.sidebar.divider()
st.sidebar.subheader("👥 Composizione Unità")
col_s1, col_s2 = st.sidebar.columns(2)
n_modelli_base = col_s1.number_input("Modelli Base", min_value=1, max_value=60, value=int(dati_preset.get("n_modelli", 5)))
rinforzata = col_s2.checkbox("Rinforzata (x2)", value=False)
n_modelli = n_modelli_base * 2 if rinforzata else n_modelli_base

campione = st.sidebar.checkbox("Presenza Campione (+1 Atk)", value=bool(dati_preset.get("campione", False)))
punti_unita = st.sidebar.number_input("Costo in Punti", min_value=40, max_value=1200, value=int(dati_preset.get("punti", 150)) * (2 if rinforzata else 1), step=10)

st.sidebar.divider()
st.sidebar.subheader("⚡ Comandi, Carica e Buff")
ha_caricato = st.sidebar.checkbox("🏇 L'unità ha Caricato questo turno", value=False)
all_out_attack = st.sidebar.checkbox("🎯 Comando: All-out Attack (+1 Hit)", value=False)

with st.sidebar.expander("✨ Altri Buff Fazione / Artefatti"):
    mod_hit_extra = st.slider("Altri Modificatori Hit", -2, 2, 0)
    mod_wnd_extra = st.slider("Modificatori Wound", -2, 2, 0)
    bonus_atk = st.number_input("Bonus Attacchi", 0, 5, 0)
    bonus_rend = st.number_input("Bonus Rend Globale", 0, 3, 0)
    bonus_dmg = st.number_input("Bonus Danno Globale", 0, 3, 0)
    crit_on_5 = st.checkbox("Critico al 5+", value=False)
    mortal_extra = st.selectbox("Danni Mortali Extra", ["0", "1", "D3", "D6", "2D3"], index=0)

mod_globali = {
    "n_modelli": n_modelli, "campione": campione, "ha_caricato": ha_caricato,
    "all_out_attack": all_out_attack, "mod_hit": mod_hit_extra + (1 if all_out_attack else 0),
    "mod_wnd": mod_wnd_extra, "bonus_atk": bonus_atk, "bonus_rend": bonus_rend,
    "bonus_dmg": bonus_dmg, "crit_on": 5 if crit_on_5 else 6, "mortal_extra": mortal_extra
}

# ==========================================
# PANNELLO PRINCIPALE
# ==========================================
st.title("🔨 MattHammer - AoS 4e Tactical Optimizer")

# SEZIONE IMPORTAZIONE WAHAPEDIA & SALVATAGGIO DB
with st.expander("🌐 Importa da Wahapedia o Salva Nuova Unità nel Database Condiviso"):
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        st.markdown("#### 1️⃣ Importa da Wahapedia")
        testo_waha = st.text_area(
            "📋 Incolla qui il testo delle armi copiato da Wahapedia (Metodo infallibile):",
            placeholder="Esempio:\nSloppklaw’s Talons 6 4+ 2+ 1 2\nCrit (Mortal), Companion",
            height=100
        )
        url_waha = st.text_input("🔗 Oppure inserisci URL diretto Warscroll Wahapedia:")
        
        if st.button("🔍 Estrai Armi da Wahapedia"):
            armi_estratte = []
            try:
                if testo_waha.strip():
                    armi_estratte = analizza_testo_wahapedia(testo_waha)
                elif url_waha.strip():
                    armi_estratte = scarica_da_url_wahapedia(url_waha.strip())
                
                if armi_estratte:
                    # Aggiorna l'unità temporanea con le armi estratte
                    while len(armi_estratte) < 2:
                        armi_estratte.append({"nome": "Nessuna", "attiva": False, "ranged": False, "atk": "1", "hit": 4, "wnd": 4, "rend": 0, "dmg": "1", "crit_type": "Nessuno", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False})
                    st.session_state["db_unita"]["🔥 Importata da Wahapedia"] = {
                        "n_modelli": n_modelli_base, "campione": campione, "punti": punti_unita,
                        "armi": armi_estratte[:3]
                    }
                    st.session_state["idx_selezionato"] = list(st.session_state["db_unita"].keys()).index("🔥 Importata da Wahapedia")
                    st.success(f"Trovate {len(armi_estratte)} armi! Selezionata '🔥 Importata da Wahapedia'.")
                    st.rerun()
                else:
                    st.warning("Nessun profilo arma riconosciuto. Assicurati di copiare la riga con Atk, Hit, Wnd, Rnd, Dmg.")
            except Exception as e:
                st.error(str(e))

    with col_w2:
        st.markdown("#### 2️⃣ Salva Unità nel Database Condiviso")
        st.caption("Configura le armi qui sotto, scegli un nome e clicca su Salva: rimarrà disponibile per te e i tuoi amici!")
        nuovo_nome = st.text_input("Nome Fazione e Unità da salvare:", placeholder="Es. Sylvaneth: Kurnoth Hunters (Scythes)")
        salva_btn = st.button("💾 Salva Unità nel DB Permanente", type="primary")

col_armi, col_difesa = st.columns([1.3, 1])

armi_configurate = []
opzioni_dadi = ["1", "2", "3", "4", "5", "6", "7", "8", "10", "12", "14", "D3", "D3+1", "D6", "D6+1", "D6+2", "2D3", "2D6"]

with col_armi:
    st.subheader("⚔️ Profili Armi dell'Unità")
    armi_lista_preset = dati_preset.get("armi", [])
    for idx, p_arma in enumerate(armi_lista_preset):
        with st.expander(f"🗡️ Arma {idx+1}: {p_arma['nome']}", expanded=(idx == 0 or p_arma["attiva"])):
            c1, c2, c3 = st.columns([2, 1, 1])
            nome_a = c1.text_input("Nome Arma", value=p_arma["nome"], key=f"{preset_scelto}_nome_{idx}")
            attiva_a = c2.checkbox("Attiva", value=p_arma["attiva"], key=f"{preset_scelto}_att_{idx}")
            comp_a = c3.checkbox("Companion", value=p_arma["companion"], key=f"{preset_scelto}_comp_{idx}")

            s1, s2, s3, s4, s5 = st.columns(5)
            idx_atk = opzioni_dadi.index(str(p_arma["atk"])) if str(p_arma["atk"]) in opzioni_dadi else 0
            idx_dmg = opzioni_dadi.index(str(p_arma["dmg"])) if str(p_arma["dmg"]) in opzioni_dadi else 0

            atk_a = s1.selectbox("Attacks", opzioni_dadi, index=idx_atk, key=f"{preset_scelto}_atk_{idx}")
            hit_a = s2.selectbox("Hit (X+)", [2, 3, 4, 5, 6], index=int(p_arma["hit"])-2, key=f"{preset_scelto}_hit_{idx}")
            wnd_a = s3.selectbox("Wound (X+)", [2, 3, 4, 5, 6], index=int(p_arma["wnd"])-2, key=f"{preset_scelto}_wnd_{idx}")
            rend_a = s4.number_input("Rend", 0, 5, value=int(p_arma["rend"]), key=f"{preset_scelto}_rend_{idx}")
            dmg_a = s5.selectbox("Damage", opzioni_dadi, index=idx_dmg, key=f"{preset_scelto}_dmg_{idx}")

            ab1, ab2, ab3 = st.columns(3)
            opz_crit = ["Nessuno", "Crit (Mortal)", "Crit (Auto-wound)", "Crit (2 Hits)"]
            opz_anti = ["Nessuno", "HERO", "INFANTRY", "CAVALRY", "MONSTER", "WAR MACHINE"]
            crit_a = ab1.selectbox("Abilità Critico", opz_crit, index=opz_crit.index(p_arma["crit_type"]) if p_arma["crit_type"] in opz_crit else 0, key=f"{preset_scelto}_crit_{idx}")
            anti_a = ab2.selectbox("Anti-X (+1 Rend)", opz_anti, index=opz_anti.index(p_arma["anti_target"]) if p_arma["anti_target"] in opz_anti else 0, key=f"{preset_scelto}_anti_{idx}")
            ranged_a = ab3.checkbox("Arma da Tiro (Ranged)", value=p_arma["ranged"], key=f"{preset_scelto}_rng_{idx}")

            ch1, ch2 = st.columns(2)
            chrg_dmg_a = ch1.checkbox("Charge (+1 Damage)", value=p_arma["charge_dmg"], key=f"{preset_scelto}_cdmg_{idx}")
            anti_chrg_a = ch2.checkbox("Anti-Charge (+1 Rend)", value=p_arma["anti_charge"], key=f"{preset_scelto}_achrg_{idx}")

            armi_configurate.append({
                "nome": nome_a, "attiva": attiva_a, "ranged": ranged_a,
                "atk": atk_a, "hit": hit_a, "wnd": wnd_a, "rend": rend_a, "dmg": dmg_a,
                "crit_type": crit_a, "anti_target": anti_a,
                "charge_dmg": chrg_dmg_a, "anti_charge": anti_chrg_a, "companion": comp_a
            })

# Gestione del click su Salva Unità nel DB
if salva_btn:
    if not nuovo_nome.strip():
        st.error("Inserisci un nome valido per l'unità prima di salvare!")
    else:
        nuova_voce = {
            "n_modelli": n_modelli_base,
            "campione": campione,
            "punti": punti_unita,
            "armi": armi_configurate
        }
        st.session_state["db_unita"][nuovo_nome.strip()] = nuova_voce
        ok, msg = salva_nel_database(st.session_state["db_unita"])
        st.session_state["idx_selezionato"] = list(st.session_state["db_unita"].keys()).index(nuovo_nome.strip())
        st.success(f"✅ '{nuovo_nome.strip()}' salvata! {msg}")
        st.rerun()

with col_difesa:
    st.subheader("🛡️ Profilo Bersaglio & Terreno")
    with st.container(border=True):
        d1, d2, d3 = st.columns(3)
        save_b = d1.selectbox("Save Bersaglio", [2, 3, 4, 5, 6, 7], index=2, format_func=lambda x: f"{x}+" if x < 7 else "Nessuno (-)")
        ward_b = d2.selectbox("Ward Bersaglio", [7, 6, 5, 4], index=0, format_func=lambda x: f"{x}+" if x < 7 else "Nessuno (-)")
        salute_b = d3.number_input("Salute Totale Bersaglio", min_value=1, max_value=100, value=10)

        keywords_b = st.multiselect("Keywords del Bersaglio", ["INFANTRY", "HERO", "CAVALRY", "MONSTER", "WAR MACHINE"], default=["INFANTRY"])

        st.markdown("**Condizioni Difensive e Terreni (GHB 2024-25):**")
        t1, t2 = st.columns(2)
        cover_b = t1.checkbox("🌲 Bersaglio in Cover (+1 Save)", value=False)
        aod_b = t2.checkbox("🛡️ Comando: All-out Defence (+1 Save)", value=False)
        obscuring_b = t1.checkbox("🌫️ Terreno Obscuring (-1 Hit al tiro)", value=False)
        bersaglio_carica = t2.checkbox("⚡ Il Bersaglio ha Caricato", value=False)
        debuff_ward = st.checkbox("💀 Debuff: -1 al tiro Ward (es. Vitiating Vapours)", value=False)

bersaglio_dict = {
    "save": save_b, "ward": ward_b, "salute": salute_b, "keywords": keywords_b,
    "cover": cover_b, "aod": aod_b, "obscuring": obscuring_b,
    "bersaglio_ha_caricato": bersaglio_carica,
    "mod_ward_penalita": 1 if debuff_ward else 0
}
mod_globali["bersaglio_ha_caricato"] = bersaglio_carica

# ==========================================
# CALCOLI E SIMULAZIONE
# ==========================================
risultati_armi = [calcola_arma_analitico(a, mod_globali, bersaglio_dict) for a in armi_configurate]
danno_atteso_armi = sum(r["danno_netto"] for r in risultati_armi)

ward_eff = bersaglio_dict["ward"] + bersaglio_dict["mod_ward_penalita"]
moltiplicatore_ward = 1.0 if (bersaglio_dict["ward"] >= 7 or ward_eff > 6) else 1.0 - ((7 - max(2, ward_eff)) / 6.0)
danno_extra_atteso = (media_dado(mortal_extra) if mortal_extra != "0" else 0.0) * moltiplicatore_ward
danno_totale_atteso = danno_atteso_armi + danno_extra_atteso

campioni_mc = simula_monte_carlo(armi_configurate, mod_globali, bersaglio_dict, n_sim=10000)
prob_uccisione = np.mean(campioni_mc >= salute_b) * 100.0
dev_std = np.std(campioni_mc)
roi_punti = (danno_totale_atteso / punti_unita) * 100.0

st.divider()

m1, m2, m3, m4 = st.columns(4)
m1.metric("💥 Danno Medio Atteso E[D]", f"{danno_totale_atteso:.2f} ferite", f"± {dev_std:.1f} (Deviazione Std)")
m2.metric("☠️ Probabilità Wipeout (Kill)", f"{prob_uccisione:.1f}%", f"vs {salute_b} Salute Totale")
m3.metric("⚖️ Efficienza per 100 Punti", f"{roi_punti:.2f} Danni", f"Costo: {punti_unita} pt")
m4.metric("🎲 Attacchi Totali Lanciati", f"{sum(r['attacchi'] for r in risultati_armi):.0f} dadi")

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Analisi Funnel & Armi",
    "🎲 Distribuzione Monte Carlo",
    "🧠 Consigliere Tattico & Heatmap",
    "🗄️ Gestione Database Unità"
])

with tab1:
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.subheader("Ripartizione Danni per Arma")
        righe_armi = []
        for a, r in zip(armi_configurate, risultati_armi):
            if a["attiva"]:
                righe_armi.append({
                    "Arma": a["nome"], "Attacchi": round(r["attacchi"], 1),
                    "Hits Totali": round(r["hits"], 2), "Wounds": round(r["wounds"], 2),
                    "Save Falliti": round(r["unsaved"], 2), "Mortali Crit": round(r["mortal"], 2),
                    "Danno Netto": round(r["danno_netto"], 2)
                })
        st.dataframe(pd.DataFrame(righe_armi), use_container_width=True, hide_index=True)

    with col_t2:
        st.subheader("Funnel di Conversione Dadi")
        df_funnel = pd.DataFrame({
            "Fase": ["1. Attacchi", "2. Colpi (Hits)", "3. Ferite (Wounds)", "4. Save Falliti", "5. Danno Netto Finale"],
            "Valore": [
                sum(r["attacchi"] for r in risultati_armi), sum(r["hits"] for r in risultati_armi),
                sum(r["wounds"] for r in risultati_armi), sum(r["unsaved"] for r in risultati_armi),
                danno_totale_atteso
            ]
        })
        st.bar_chart(df_funnel.set_index("Fase"))

with tab2:
    st.subheader("Curva di Probabilità Cumulativa: Probabilità di infliggere ALMENO X Danni")
    max_danno_grafico = int(np.percentile(campioni_mc, 99.5)) + 2
    asse_x = np.arange(1, max(10, max_danno_grafico))
    prob_almeno_x = [np.mean(campioni_mc >= x) * 100.0 for x in asse_x]
    st.line_chart(pd.DataFrame({"Danni Minimi (X)": asse_x, "Probabilità (%)": prob_almeno_x}).set_index("Danni Minimi (X)"))

with tab3:
    st.subheader("🎯 Matrice Target Priority")
    saves_lista = [2, 3, 4, 5, 6, 7]
    wards_lista = [7, 6, 5, 4]
    matrice_dati = {}
    for w_val in wards_lista:
        col_nome = f"Ward {w_val}+" if w_val < 7 else "Nessun Ward"
        matrice_dati[col_nome] = [
            round(sum(calcola_arma_analitico(a, mod_globali, {**bersaglio_dict, "save": s_val, "ward": w_val, "mod_ward_penalita": 0})["danno_netto"] for a in armi_configurate), 2)
            for s_val in saves_lista
        ]
    df_matrice = pd.DataFrame(matrice_dati, index=[f"Save {s}+" if s < 7 else "No Save (-)" for s in saves_lista])
    st.dataframe(df_matrice.style.background_gradient(cmap="YlOrRd"), use_container_width=True)

with tab4:
    st.subheader("🗄️ Esporta / Importa Database JSON")
    st.caption("Scarica il backup di tutte le unità create o carica un file JSON condiviso.")
    json_str = json.dumps(st.session_state["db_unita"], indent=4, ensure_ascii=False)
    st.download_button("⬇️ Scarica Database Completo (units_db.json)", data=json_str, file_name="units_db.json", mime="application/json")