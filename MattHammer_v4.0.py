import streamlit as st
import numpy as np
import pandas as pd
import json
import os
import re
import base64
import requests

# ==========================================
# CONFIGURAZIONE PAGINA
# ==========================================
st.set_page_config(
    page_title="MattHammer v4.5 - AoS Optimizer",
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
# UNITÀ DI DEFAULT
# ==========================================
DEFAULT_PRESETS = {
    "Personalizzato (Manuale)": {
        "fazione": "Personale / Altro",
        "n_modelli": 10, "campione": True, "punti": 150,
        "difesa": {"salute_per_modello": 2, "save": 4, "ward": 7},
        "armi": [
            {"nome": "Arma Principale", "attiva": True, "ranged": False, "atk": "2", "hit": 3, "wnd": 3, "rend": 1, "dmg": "1", "crit_type": "Nessuno", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False},
        ]
    },
    "Nighthaunt: Kurdoss Valentian": {
        "fazione": "Nighthaunt",
        "n_modelli": 1, "campione": False, "punti": 200,
        "difesa": {"salute_per_modello": 7, "save": 4, "ward": 5},
        "armi": [
            {"nome": "Sepulchral Sceptre", "attiva": True, "ranged": False, "atk": "5", "hit": 3, "wnd": 3, "rend": 2, "dmg": "3", "crit_type": "Crit (Auto-wound)", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False},
        ]
    },
    "Khorne: Warlord Tank (2+ Save)": {
        "fazione": "Khorne",
        "n_modelli": 1, "campione": False, "punti": 250,
        "difesa": {"salute_per_modello": 8, "save": 2, "ward": 7},
        "armi": [
            {"nome": "Lama Sanguinaria", "attiva": True, "ranged": False, "atk": "4", "hit": 3, "wnd": 3, "rend": 1, "dmg": "2", "crit_type": "Nessuno", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False}
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
    
    try:
        if "GITHUB_TOKEN" in st.secrets and "GITHUB_REPO" in st.secrets:
            token = st.secrets["GITHUB_TOKEN"]
            repo = st.secrets["GITHUB_REPO"]
            url = f"https://api.github.com/repos/{repo}/contents/{DB_FILE}"
            headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
            r_get = requests.get(url, headers=headers)
            sha = r_get.json().get("sha") if r_get.status_code == 200 else None
            
            content_b64 = base64.b64encode(json.dumps(db_dict, indent=4, ensure_ascii=False).encode("utf-8")).decode("utf-8")
            payload = {"message": "Aggiornamento DB Unità", "content": content_b64}
            if sha:
                payload["sha"] = sha
            requests.put(url, headers=headers, json=payload)
            return True, "Salvato nel Database Cloud (GitHub Sync attivo)!"
    except Exception as e:
        pass
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
    elif val_str == "D3": return np.random.randint(1, 4, size=size)
    elif val_str == "D3+1": return np.random.randint(1, 4, size=size) + 1
    elif val_str == "D6": return np.random.randint(1, 7, size=size)
    elif val_str == "D6+1": return np.random.randint(1, 7, size=size) + 1
    elif val_str == "D6+2": return np.random.randint(1, 7, size=size) + 2
    elif val_str == "2D3": return np.random.randint(1, 4, size=size) + np.random.randint(1, 4, size=size)
    elif val_str == "2D6": return np.random.randint(1, 7, size=size) + np.random.randint(1, 7, size=size)
    return np.ones(size, dtype=int)

def calcola_arma_analitico(arma, mod_globali, bersaglio):
    if not arma["attiva"]:
        return {"attacchi": 0, "hits": 0, "wounds": 0, "unsaved": 0, "mortal": 0, "danno_netto": 0}

    atk_per_modello = media_dado(arma["atk"])
    if not arma["companion"]: atk_per_modello += mod_globali["bonus_atk"]
    
    atk_totali = atk_per_modello * mod_globali["n_modelli"]
    if mod_globali["campione"] and not arma["companion"]: atk_totali += 1

    mod_hit_netto = mod_globali["mod_hit"]
    if arma["companion"] and mod_hit_netto > 0 and not mod_globali["all_out_attack"]: mod_hit_netto = 0
    if bersaglio["obscuring"] and arma["ranged"]: mod_hit_netto -= 1
    hit_target = np.clip(arma["hit"] - np.clip(mod_hit_netto, -1, 1), 2, 6)

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
    wnd_target = np.clip(arma["wnd"] - np.clip(mod_wnd_netto, -2, 2), 2, 6)
    prob_wnd = (7 - wnd_target) / 6.0
    wounds_totali = (hits_che_devono_ferire * prob_wnd) + auto_wounds

    rend_effettivo = arma["rend"] + (mod_globali["bonus_rend"] if not arma["companion"] else 0)
    if arma["anti_target"] != "Nessuno" and arma["anti_target"] in bersaglio["keywords"]: rend_effettivo += 1
    if arma["anti_charge"] and mod_globali["bersaglio_ha_caricato"]: rend_effettivo += 1

    if bersaglio["save"] >= 7: prob_save_fallito = 1.0
    else:
        bonus_save_positivo = min(2, (1 if bersaglio["cover"] else 0) + (1 if bersaglio["aod"] else 0) + bersaglio["bonus_save_extra"])
        save_target = bersaglio["save"] - bonus_save_positivo + rend_effettivo
        prob_save_fallito = 1.0 if save_target > 6 else 1.0 - ((7 - max(2, save_target)) / 6.0)

    colpi_non_salvati = wounds_totali * prob_save_fallito
    danni_normali_lordi = colpi_non_salvati * danno_per_colpo

    if bersaglio["blocca_ward"]:
        prob_ward_fallito = 1.0
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
        if not arma["attiva"]: continue
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
            mortal_wounds_sim = n_crits * (tira_dado_mc(arma["dmg"], n_sim) + bonus_dmg_fisso)
        elif arma["crit_type"] == "Crit (Auto-wound)": auto_wounds_sim = n_crits
        elif arma["crit_type"] == "Crit (2 Hits)": hits_to_wound += n_crits * 2
        else: hits_to_wound += n_crits

        mod_wnd_netto = 0 if (arma["companion"] and mod_globali["mod_wnd"] > 0) else mod_globali["mod_wnd"]
        mod_wnd_netto += bersaglio["mod_wnd_nerf"]
        wnd_target = np.clip(arma["wnd"] - np.clip(mod_wnd_netto, -2, 2), 2, 6)
        wounds_sim = np.random.binomial(hits_to_wound.astype(int), (7 - wnd_target) / 6.0) + auto_wounds_sim

        rend_eff = arma["rend"] + (mod_globali["bonus_rend"] if not arma["companion"] else 0)
        if arma["anti_target"] != "Nessuno" and arma["anti_target"] in bersaglio["keywords"]: rend_eff += 1
        if arma["anti_charge"] and mod_globali["bersaglio_ha_caricato"]: rend_eff += 1

        if bersaglio["save"] >= 7: prob_fail_save = 1.0
        else:
            bonus_save = min(2, (1 if bersaglio["cover"] else 0) + (1 if bersaglio["aod"] else 0) + bersaglio["bonus_save_extra"])
            save_t = bersaglio["save"] - bonus_save + rend_eff
            prob_fail_save = 1.0 if save_t > 6 else 1.0 - ((7 - max(2, save_t)) / 6.0)

        danni_totali_sim += (np.random.binomial(wounds_sim.astype(int), prob_fail_save) * (tira_dado_mc(arma["dmg"], n_sim) + bonus_dmg_fisso)) + mortal_wounds_sim

    if mod_globali["mortal_extra"] != "0": danni_totali_sim += tira_dado_mc(mod_globali["mortal_extra"], n_sim)
    if ha_ward: danni_totali_sim = np.random.binomial(danni_totali_sim.astype(int), 1.0 - ((7 - ward_target) / 6.0))
    return danni_totali_sim

# ==========================================
# INIZIALIZZAZIONE SESSION STATE
# ==========================================
if "db_unita" not in st.session_state:
    st.session_state["db_unita"] = carica_database()

if "corrente_armi" not in st.session_state:
    st.session_state["corrente_armi"] = DEFAULT_PRESETS["Personalizzato (Manuale)"]["armi"]
    st.session_state["corrente_modelli"] = 10
    st.session_state["corrente_campione"] = True
    st.session_state["corrente_punti"] = 150
    st.session_state["corrente_difesa"] = {"salute_per_modello": 2, "save": 4, "ward": 7}

if "form_version" not in st.session_state:
    st.session_state["form_version"] = 0

# ==========================================
# SIDEBAR
# ==========================================
st.sidebar.title("🔨 MattHammer v4.5")

albero_fazioni = {"👻 Nighthaunt": [], "🩸 Khorne": [], "👹 Kruleboyz": [], "🌲 Sylvaneth": [], "📁 Personale / Altro": []}
for nome_unita, dati_u in st.session_state["db_unita"].items():
    fazione_u = dati_u.get("fazione", "").lower()
    if "nighthaunt" in fazione_u: albero_fazioni["👻 Nighthaunt"].append(nome_unita)
    elif "khorne" in fazione_u: albero_fazioni["🩸 Khorne"].append(nome_unita)
    elif "kruleboyz" in fazione_u: albero_fazioni["👹 Kruleboyz"].append(nome_unita)
    elif "sylvaneth" in fazione_u: albero_fazioni["🌲 Sylvaneth"].append(nome_unita)
    else:
        nome_up = nome_unita.upper()
        if "NIGHTHAUNT" in nome_up: albero_fazioni["👻 Nighthaunt"].append(nome_unita)
        elif "KHORNE" in nome_up: albero_fazioni["🩸 Khorne"].append(nome_unita)
        elif "KRULEBOYZ" in nome_up: albero_fazioni["👹 Kruleboyz"].append(nome_unita)
        elif "SYLVANETH" in nome_up: albero_fazioni["🌲 Sylvaneth"].append(nome_unita)
        else: albero_fazioni["📁 Personale / Altro"].append(nome_unita)

albero_fazioni_attive = {k: v for k, v in albero_fazioni.items() if len(v) > 0}

st.sidebar.subheader("📂 Directory Database")
fazione_selezionata = st.sidebar.selectbox("Seleziona Fazione", list(albero_fazioni_attive.keys()))
unita_della_fazione = albero_fazioni_attive[fazione_selezionata]

preset_scelto = st.sidebar.selectbox(f"Unità ({fazione_selezionata})", unita_della_fazione)

if st.sidebar.button("Carica Unità Selezionata"):
    dati_sel = st.session_state["db_unita"][preset_scelto]
    st.session_state["corrente_armi"] = [dict(a) for a in dati_sel["armi"]]
    st.session_state["corrente_modelli"] = dati_sel["n_modelli"]
    st.session_state["corrente_campione"] = dati_sel["campione"]
    st.session_state["corrente_punti"] = dati_sel["punti"]
    st.session_state["corrente_difesa"] = dati_sel.get("difesa", {"salute_per_modello": 2, "save": 4, "ward": 7})
    st.session_state["form_version"] += 1
    st.rerun()

# ==========================================
# PANNELLO PRINCIPALE
# ==========================================
st.title("🔨 MattHammer - AoS 4e Tactical Optimizer")

# ==========================================
# SEZIONE 1: UNITÀ DA ANALIZZARE
# ==========================================
st.markdown("---")
st.markdown("### UNITÀ ATTACCANTE")

with st.container(border=True):
    st.subheader("📋Riconoscimento Intelligente Armi")
    st.caption("Incolla qui il profilo armi copiato direttamente da Wahapedia e importalo automaticamente completo per la tua unità! ")
    st.caption("NB: inserisci tutti i profili armi contemporaneamente, copiandoli esattamente dalla warscroll")
    
    testo_copiato = st.text_area(
        "Incolla qui il testo:",
        placeholder="Es: Phantasmal Torture Crit (Auto-wound), Shoot in Combat	12\"	4	3+	3+	2	1",
        height=80
    )
    
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
opzioni_dadi = ["1", "2", "3", "4", "5", "6", "7", "8", "10", "12", "14", "D3", "D3+1", "D6", "D6+1", "D6+2", "2D3", "2D6"]
v_key = st.session_state["form_version"]

with col_armi:
    st.subheader("⚔️ Profili Armi dell'Unità")
    if st.button("➕ Aggiungi Nuova Arma"):
        st.session_state["corrente_armi"].append({
            "nome": "Nuova Arma", "attiva": True, "ranged": False, "atk": "2",
            "hit": 4, "wnd": 4, "rend": 0, "dmg": "1", "crit_type": "Nessuno",
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
            idx_atk = opzioni_dadi.index(atk_str) if atk_str in opzioni_dadi else 0
            
            hit_val = int(p_arma["hit"])
            idx_hit = max(0, min(4, hit_val - 2))
            
            wnd_val = int(p_arma["wnd"])
            idx_wnd = max(0, min(4, wnd_val - 2))
            
            rend_val = int(p_arma["rend"])
            dmg_str = str(p_arma["dmg"])
            idx_dmg = opzioni_dadi.index(dmg_str) if dmg_str in opzioni_dadi else 0

            atk_a = s1.selectbox("Attacks", opzioni_dadi, index=idx_atk, key=f"atk_{idx}_v{v_key}")
            hit_a = s2.selectbox("Hit (X+)", [2, 3, 4, 5, 6], index=idx_hit, key=f"hit_{idx}_v{v_key}")
            wnd_a = s3.selectbox("Wound (X+)", [2, 3, 4, 5, 6], index=idx_wnd, key=f"wnd_{idx}_v{v_key}")
            rend_a = s4.number_input("Rend", 0, 5, value=rend_val, key=f"rend_{idx}_v{v_key}")
            dmg_a = s5.selectbox("Damage", opzioni_dadi, index=idx_dmg, key=f"dmg_{idx}_v{v_key}")

            ab1, ab2, ab3 = st.columns(3)
            opz_crit = ["Nessuno", "Crit (Mortal)", "Crit (Auto-wound)", "Crit (2 Hits)"]
            opz_anti = ["Nessuno", "HERO", "INFANTRY", "CAVALRY", "MONSTER", "WAR MACHINE"]
            
            idx_crit = opz_crit.index(p_arma["crit_type"]) if p_arma["crit_type"] in opz_crit else 0
            idx_anti = opz_anti.index(p_arma["anti_target"]) if p_arma["anti_target"] in opz_anti else 0

            crit_a = ab1.selectbox("Abilità Critico", opz_crit, index=idx_crit, key=f"crit_{idx}_v{v_key}")
            anti_a = ab2.selectbox("Anti-X (+1 Rend)", opz_anti, index=idx_anti, key=f"anti_{idx}_v{v_key}")
            ranged_a = ab3.checkbox("Arma da Tiro (Ranged)", value=p_arma["ranged"], key=f"rng_{idx}_v{v_key}")

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
        st.caption("Parametri difensivi intrinseci salvati nel Database.")
        d_corrente = st.session_state["corrente_difesa"]
        
        salute_modello = st.number_input("Punti Ferita (Health) per Modello", 1, 30, int(d_corrente.get("salute_per_modello", 2)), key=f"def_salute_v{v_key}")
        save_nativo = st.selectbox("Tiro Salvezza Base (Save X+)", [2, 3, 4, 5, 6], index=max(0, min(4, int(d_corrente.get("save", 4)) - 2)), key=f"def_save_v{v_key}")
        ward_nativo = st.selectbox("Tiro Ward Nativo (X+)", [7, 6, 5, 4], index=0, format_func=lambda x: f"{x}+" if x < 7 else "Nessuno (-)", key=f"def_ward_v{v_key}")
        
        st.session_state["corrente_difesa"] = {"salute_per_modello": salute_modello, "save": save_nativo, "ward": ward_nativo}

col_comp, col_comandi = st.columns(2)

with col_comp:
    st.subheader("👥 Composizione Unità")
    with st.container(border=True):
        col_s1, col_s2 = st.columns(2)
        n_modelli_base = col_s1.number_input("Modelli Base", min_value=1, max_value=60, value=int(st.session_state["corrente_modelli"]))
        rinforzata = col_s2.checkbox("Rinforzata (x2)", value=False)
        n_modelli = n_modelli_base * 2 if rinforzata else n_modelli_base

        campione = st.checkbox("Presenza Campione (+1 Atk)", value=bool(st.session_state["corrente_campione"]))
        punti_unita = st.number_input("Costo in Punti", min_value=40, max_value=1200, value=int(st.session_state["corrente_punti"]) * (2 if rinforzata else 1), step=10)

with col_comandi:
    st.subheader("⚡ Comandi, Carica e Buff")
    with st.container(border=True):
        ha_caricato = st.checkbox("🏇 L'unità ha Caricato questo turno", value=False)
        all_out_attack = st.checkbox("🎯 Comando: All-out Attack (+1 Hit)", value=False)

        with st.expander("✨ Altri Buff Fazione / Artefatti"):
            mod_hit_extra = st.slider("Altri Modificatori Hit", -2, 2, 0)
            mod_wnd_extra = st.slider("Modificatori Wound", -2, 2, 0)
            bonus_atk = st.number_input("Bonus Attacchi", 0, 5, 0)
            bonus_rend = st.number_input("Bonus Rend Globale", 0, 3, 1)
            bonus_dmg = st.number_input("Bonus Danno Globale", 0, 3, 0)
            crit_on_5 = st.checkbox("Critico al 5+", value=False)
            mortal_extra = st.selectbox("Danni Mortali Extra", ["0", "1", "D3", "D6", "2D3"], index=0)

mod_globali = {
    "n_modelli": n_modelli, "campione": campione, "ha_caricato": ha_caricato,
    "all_out_attack": all_out_attack, "mod_hit": mod_hit_extra + (1 if all_out_attack else 0),
    "mod_wnd": mod_wnd_extra, "bonus_atk": bonus_atk, "bonus_rend": bonus_rend,
    "bonus_dmg": bonus_dmg, "crit_on": 5 if crit_on_5 else 6, "mortal_extra": mortal_extra
}

st.subheader("🗄️ Salva Unità Corrente nel Database")
st.caption("Necessario solo se si vuole salvare il preset attuale dell'unità.")
st.caption("NB: CONTROLLA TUTTE LE STATISTICHE OFFENSIVE E DIFENSIVE PRIMA DI SALVARE !")

with st.container(border=True):
    db_c1, db_c2 = st.columns(2)
    fazione_scelta = db_c1.selectbox("Seleziona Fazione di Appartenenza", ["Nighthaunt", "Khorne", "Kruleboyz", "Sylvaneth", "Personale / Altro"])
    nuovo_nome = db_c2.text_input("Nome Specifico dell'Unità:", placeholder="Es. Grimghast Reapers")
    
    if st.button("💾 Valida e Salva nel DB", type="primary"):
        errori = []
        if not nuovo_nome.strip():
            errori.append("Inserisci un nome valido per l'unità.")
        if not st.session_state["corrente_armi"] or len(st.session_state["corrente_armi"]) == 0:
            errori.append("Devi specificare almeno un profilo arma.")
        if n_modelli <= 0:
            errori.append("Il numero di modelli deve essere maggiore di zero.")
        if punti_unita <= 0:
            errori.append("Il costo in punti deve essere specificato.")
        
        difesa_corrente = st.session_state["corrente_difesa"]
        if not difesa_corrente.get("salute_per_modello") or not difesa_corrente.get("save"):
            errori.append("Mancano i dati difensivi (Salute per modello o Tiro Salvezza base).")

        if len(errori) > 0:
            for err in errori:
                st.error(f"❌ {err}")
        else:
            chiave_db = f"{fazione_scelta}: {nuovo_nome.strip()}"
            st.session_state["db_unita"][chiave_db] = {
                "fazione": fazione_scelta,
                "n_modelli": n_modelli_base, 
                "campione": campione, 
                "punti": punti_unita,
                "difesa": difesa_corrente,
                "armi": st.session_state["corrente_armi"]
            }
            salva_nel_database(st.session_state["db_unita"])
            st.success(f"✅ Unità '{chiave_db}' salvata con successo!")

# ==========================================
# SEZIONE 2: UNITÀ BERSAGLIO
# ==========================================
st.markdown("---")
st.markdown("### UNITÀ BERSAGLIO")

with st.container(border=True):
    b1, b2, b3 = st.columns(3)
    save_b = b1.selectbox("Save Base Bersaglio", [2, 3, 4, 5, 6, 7], index=2, format_func=lambda x: f"{x}+" if x < 7 else "Nessuno (-)")
    ward_b = b2.selectbox("Ward Base Bersaglio", [7, 6, 5, 4], index=0, format_func=lambda x: f"{x}+" if x < 7 else "Nessuno (-)")
    salute_b = b3.number_input("Salute Totale Bersaglio", min_value=1, max_value=100, value=10)

    keywords_b = st.multiselect("Keywords del Bersaglio", ["INFANTRY", "HERO", "CAVALRY", "MONSTER", "WAR MACHINE"], default=["INFANTRY", "HERO"])

    st.markdown("---")
    st.markdown("**🛡️ Buff Difensivi / Terreni del Bersaglio:**")
    dt1, dt2, dt3 = st.columns(3)
    cover_b = dt1.checkbox("🌲 Cover (+1 Save)", value=False)
    aod_b = dt2.checkbox("🛡️ All-out Defence (+1 Save)", value=False)
    extra_save_b = dt3.checkbox("✨ Abilità extra / Scenario (+1 Save)", value=False)
    obscuring_b = dt1.checkbox("🌫️ Terreno Obscuring (-1 Hit al tiro)", value=False)
    bersaglio_carica = dt2.checkbox("⚡ Il Bersaglio ha Caricato", value=False)

    st.markdown("---")
    st.markdown("**💀 Nerf / Debuff applicati al Bersaglio:**")
    nd1, nd2, nd3 = st.columns(3)
    debuff_ward = nd1.checkbox("💀 Debuff: -1 al tiro Ward", value=False)
    blocca_ward_b = nd2.checkbox("🚫 Ward Annullati", value=False)
    nerf_wound = nd3.selectbox("Modificatore Wound subito dal bersaglio", [0, 1, -1], index=0, format_func=lambda x: f"+{x} a Wound" if x>0 else (f"{x} a Wound" if x<0 else "Nessuno"))

bersaglio_dict = {
    "save": save_b, "ward": ward_b, "salute": salute_b, "keywords": keywords_b,
    "cover": cover_b, "aod": aod_b, "bonus_save_extra": 1 if extra_save_b else 0,
    "obscuring": obscuring_b, "bersaglio_ha_caricato": bersaglio_carica,
    "mod_ward_penalita": 1 if debuff_ward else 0,
    "blocca_ward": blocca_ward_b,
    "mod_wnd_nerf": nerf_wound
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
danno_extra_atteso = (media_dado(mortal_extra) if mortal_extra != "0" else 0.0) * moltiplicatore_ward
danno_totale_atteso = danno_atteso_armi + danno_extra_atteso

campioni_mc = simula_monte_carlo(armi_attive_calcolo, mod_globali, bersaglio_dict, n_sim=10000)
prob_uccisione = np.mean(campioni_mc >= salute_b) * 100.0
dev_std = np.std(campioni_mc)
roi_punti = (danno_totale_atteso / punti_unita) * 100.0

# ==========================================
# SEZIONE 3: ANALISI COMPARATIVA
# ==========================================
st.markdown("---")
st.markdown("### 📊 3. Analisi comparativa")

# --- LOGICA DINAMICA: IL VERDETTO STRATEGICO (ROLE TAGS) ---
attacchi_totali = sum(r['attacchi'] for r in risultati_armi)
max_rend = max([int(a['rend']) for a in armi_attive_calcolo if a['attiva']] + [0])
ha_crit_mortal = any(a['crit_type'] == 'Crit (Mortal)' and a['attiva'] for a in armi_attive_calcolo)

# Raccoglie tutti i target Anti-X univoci presenti nelle armi attive
anti_targets = list(set([a['anti_target'] for a in armi_attive_calcolo if a['attiva'] and a['anti_target'] != 'Nessuno']))

difesa_corrente = st.session_state["corrente_difesa"]
ward_unita = int(difesa_corrente.get("ward", 7))
save_unita = int(difesa_corrente.get("save", 4))
salute_totale_unita = int(difesa_corrente.get("salute_per_modello", 2)) * mod_globali["n_modelli"]

# Assegnazione del ruolo tattico in base alle statistiche
if ward_unita <= 5 or (save_unita <= 3 and salute_totale_unita >= 15):
    st.info("**🧠 Il Verdetto Strategico: 🛡️ Tank / Ancoraggio Difensivo**\n\nOttima resistenza. Utilizza questa unità per presidiare gli obiettivi centrali, bloccare le unità più pericolose dell'avversario o fare da scudo ai tuoi eroi di supporto. Evita di sprecarla in inseguimenti.")
elif len(anti_targets) > 0:
    targets_str = ", ".join(anti_targets)
    st.warning(f"**🧠 Il Verdetto Strategico: 🎯 Specialista Anti-{targets_str}**\n\nUnità letale contro {targets_str} grazie al bonus di penetrazione dell'armatura (+1 Rend). Focalizza i suoi attacchi e i suoi movimenti di carica esclusivamente su questi bersagli per massimizzarne l'efficienza.")
elif ha_crit_mortal or max_rend >= 2:
    st.error("**🧠 Il Verdetto Strategico: ⚔️ Cacciatore Corazzati / Bypassa-Armatura**\n\nEccelle contro bersagli con Tiro Salvezza (Save) elevato. Ignora le truppe leggere e punta dritto alle unità d'élite pesantemente corazzate per capitalizzare i danni mortali o l'alta penetrazione.")
elif attacchi_totali >= 20:
    st.success("**🧠 Il Verdetto Strategico: 🗡️ Sfoltiscitore d'Orde**\n\nSfrutta l'enorme volume di dadi per saturare le difese nemiche. L'ideale è lanciarla contro unità composte da molti modelli leggeri per massimizzare i danni ed evitare che l'avversario contesti gli obiettivi.")
elif danno_totale_atteso >= 12:
    st.error("**🧠 Il Verdetto Strategico: 💥 Damage Dealer Puro**\n\nUnità d'urto ad altissimo impatto. Infligge danni massicci in modo costante. Supportala con incantesimi o buff per farla arrivare intatta in mischia e scatenala contro le minacce principali.")
else:
    st.success("**🧠 Il Verdetto Strategico: ⚖️ Combattente Flessibile / Supporto**\n\nUnità tattica bilanciata. Utilizzala per contestare obiettivi secondari, schermare i fianchi o fornire supporto alleato dove la linea di battaglia ne ha più bisogno.")

st.markdown("<br>", unsafe_allow_html=True)

# --- METRICHE AVANZATE ---
m1, m2, m3, m4 = st.columns(4)
m1.metric("💥 Danno Medio Atteso", f"{danno_totale_atteso:.2f} ferite", f"± {dev_std:.1f} (Std)")
m2.metric("☠️ Prob. Kill (1 Turno)", f"{prob_uccisione:.1f}%", f"vs {salute_b} Salute")
m3.metric("⚖️ ROI Danni (per 100 pt)", f"{roi_punti:.2f} Danni", f"Costo: {punti_unita} pt")
m4.metric("🎲 Attacchi Totali", f"{attacchi_totali:.0f} dadi")

tab1, tab2, tab3 = st.tabs([
    "📊 Analisi Funnel & Armi",
    "🎲 Distribuzione Monte Carlo",
    "🧠 Consigliere Tattico & Time-to-Kill"
])

with tab1:
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.subheader("Ripartizione Danni per Arma")
        righe_armi = []
        for a, r in zip(armi_attive_calcolo, risultati_armi):
            if a["attiva"]:
                righe_armi.append({
                    "Arma": a["nome"], "Attacchi": round(r["attacchi"], 1),
                    "Hits": round(r["hits"], 2), "Wounds": round(r["wounds"], 2),
                    "Save Falliti": round(r["unsaved"], 2), "Danno Netto": round(r["danno_netto"], 2)
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
    st.subheader("Curva di Probabilità Cumulativa (Monte Carlo)")
    max_danno_grafico = int(np.percentile(campioni_mc, 99.5)) + 2
    asse_x = np.arange(1, max(10, max_danno_grafico))
    prob_almeno_x = [np.mean(campioni_mc >= x) * 100.0 for x in asse_x]
    st.line_chart(pd.DataFrame({"Danni Minimi (X)": asse_x, "Probabilità (%)": prob_almeno_x}).set_index("Danni Minimi (X)"))

with tab3:
    st.subheader("⏱️ Stima Sopravvivenza Bersaglio (Time-to-Kill)")
    ttk = salute_b / danno_totale_atteso if danno_totale_atteso > 0 else 99
    
    if ttk <= 1.0:
        st.success(f"**🔥 Letale!** Questa unità dovrebbe eliminare il bersaglio in **1 singolo turno di combattimento** (Danno atteso {danno_totale_atteso:.1f} vs Salute {salute_b}).")
    elif ttk <= 2.0:
        st.warning(f"**⚔️ Logoramento:** Saranno necessari circa **2 turni di combattimento** per abbattere questo bersaglio. Seleziona il target con cautela.")
    else:
        st.error(f"**🛡️ Inefficiente:** Serviranno circa **{int(ttk)+1} turni** per uccidere questo bersaglio. Sconsigliato ingaggiarlo in 1v1 senza supporto magico o alleati.")
        
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
    st.dataframe(df_matrice.style.background_gradient(cmap="YlOrRd"), use_container_width=True)