import streamlit as st
import numpy as np
import pandas as pd

# ==========================================
# CONFIGURAZIONE PAGINA (Ottimizzata Mobile)
# ==========================================
st.set_page_config(
    page_title="MattHammer - AoS 4e Optimizer",
    page_icon="🔨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Stile CSS custom per rendere le metriche perfette su smartphone
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

# ==========================================
# FUNZIONI MATEMATICHE E MONTE CARLO (Stile MATLAB)
# ==========================================
def media_dado(val_str):
    """Restituisce il valore atteso matematico di una stringa dado."""
    mappa = {
        "1": 1.0, "2": 2.0, "3": 3.0, "4": 4.0, "5": 5.0, "6": 6.0,
        "D3": 2.0, "D3+1": 3.0, "D6": 3.5, "D6+1": 4.5, "D6+2": 5.5,
        "2D3": 4.0, "2D6": 7.0
    }
    return mappa.get(str(val_str), 1.0)

def tira_dado_mc(val_str, size):
    """Genera array vettoriali di tiri di dado per la simulazione Monte Carlo."""
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
    """Calcola il valore atteso esatto (Expected Value) per una singola arma."""
    if not arma["attiva"]:
        return {"attacchi": 0, "hits": 0, "wounds": 0, "unsaved": 0, "mortal": 0, "danno_netto": 0}

    # 1. Calcolo Numero Attacchi Totale
    atk_per_modello = media_dado(arma["atk"])
    # I buff agli attacchi (es. Lightshard) non si applicano alle armi Companion
    if not arma["companion"]:
        atk_per_modello += mod_globali["bonus_atk"]
    
    atk_totali = atk_per_modello * mod_globali["n_modelli"]
    if mod_globali["campione"] and not arma["companion"]:
        atk_totali += 1  # Il campione aggiunge +1 attacco all'arma principale

    # 2. Modificatori Hit (Cap di AoS: +1 / -1, tranne penalità cumulabili prima del cap)
    mod_hit_netto = mod_globali["mod_hit"]
    if arma["companion"] and mod_hit_netto > 0 and not mod_globali["all_out_attack"]:
        # Le armi Companion ignorano i buff positivi al Hit a meno che non sia All-out Attack
        mod_hit_netto = 0
    if bersaglio["obscuring"] and arma["ranged"]:
        mod_hit_netto -= 1
    mod_hit_capped = np.clip(mod_hit_netto, -1, 1)
    hit_target = np.clip(arma["hit"] - mod_hit_capped, 2, 6)

    # Probabilità Critico (6 naturale, o 5+ se abilitato)
    soglia_crit = mod_globali["crit_on"]
    prob_crit = (7 - soglia_crit) / 6.0
    prob_hit_totale = (7 - hit_target) / 6.0
    prob_hit_normale = max(0.0, prob_hit_totale - prob_crit)

    # 3. Gestione Effetti Critici (Crit Mortal, Auto-wound, 2 Hits)
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

    # 4. Fase di Wound
    mod_wnd_netto = 0 if (arma["companion"] and mod_globali["mod_wnd"] > 0) else mod_globali["mod_wnd"]
    mod_wnd_capped = np.clip(mod_wnd_netto, -1, 1)
    wnd_target = np.clip(arma["wnd"] - mod_wnd_capped, 2, 6)
    prob_wnd = (7 - wnd_target) / 6.0

    wounds_totali = (hits_che_devono_ferire * prob_wnd) + auto_wounds

    # 5. Calcolo Rend e Fase di Save
    rend_effettivo = arma["rend"] + (mod_globali["bonus_rend"] if not arma["companion"] else 0)
    if arma["anti_target"] != "Nessuno" and arma["anti_target"] in bersaglio["keywords"]:
        rend_effettivo += 1
    if arma["anti_charge"] and mod_globali["bersaglio_ha_caricato"]:
        rend_effettivo += 1

    if bersaglio["save"] >= 7:  # Nessun Save
        prob_save_fallito = 1.0
    else:
        # Modificatori positivi al Save (Cover + All-out Defence) hanno un cap di +1
        bonus_save_positivo = min(1, (1 if bersaglio["cover"] else 0) + (1 if bersaglio["aod"] else 0))
        save_target = bersaglio["save"] - bonus_save_positivo + rend_effettivo
        if save_target > 6:
            prob_save_fallito = 1.0
        else:
            save_target = max(2, save_target)
            prob_save_fallito = 1.0 - ((7 - save_target) / 6.0)

    colpi_non_salvati = wounds_totali * prob_save_fallito
    danni_normali_lordi = colpi_non_salvati * danno_per_colpo

    # 6. Fase di Ward (incluso debuff come Vitiating Vapours del Corpse Cart)
    ward_effettivo = bersaglio["ward"] + bersaglio["mod_ward_penalita"]
    if bersaglio["ward"] >= 7 or ward_effettivo > 6:
        prob_ward_fallito = 1.0
    else:
        ward_effettivo = max(2, ward_effettivo)
        prob_ward_fallito = 1.0 - ((7 - ward_effettivo) / 6.0)

    danno_netto = (danni_normali_lordi + mortal_da_crit) * prob_ward_fallito

    return {
        "attacchi": atk_totali,
        "hits": hits_totali_visivi,
        "wounds": wounds_totali,
        "unsaved": colpi_non_salvati,
        "mortal": mortal_da_crit,
        "danno_netto": danno_netto
    }

def simula_monte_carlo(armi, mod_globali, bersaglio, n_sim=10000):
    """Simulazione vettoriale stile MATLAB di 10.000 combattimenti."""
    danni_totali_sim = np.zeros(n_sim, dtype=float)

    # Calcolo soglia Ward
    ward_effettivo = bersaglio["ward"] + bersaglio["mod_ward_penalita"]
    ha_ward = (bersaglio["ward"] < 7) and (ward_effettivo <= 6)
    ward_target = max(2, ward_effettivo)

    for arma in armi:
        if not arma["attiva"]:
            continue

        # Determina numero di attacchi per ogni simulazione
        atk_base = tira_dado_mc(arma["atk"], n_sim)
        if not arma["companion"]:
            atk_base = atk_base + mod_globali["bonus_atk"]
        atk_tot_array = atk_base * mod_globali["n_modelli"]
        if mod_globali["campione"] and not arma["companion"]:
            atk_tot_array += 1

        # Usiamo la media degli attacchi se costante o campioniamo per velocità vettoriale
        n_attacchi_fisici = int(np.round(np.mean(atk_tot_array)))
        if n_attacchi_fisici <= 0:
            continue

        # Matrice (n_sim x n_attacchi_fisici) di tiri per colpire
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

        # Gestione Critici
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

        # Probabilità Wound e Save Binomiale Vettoriale
        mod_wnd_netto = 0 if (arma["companion"] and mod_globali["mod_wnd"] > 0) else mod_globali["mod_wnd"]
        wnd_target = np.clip(arma["wnd"] - np.clip(mod_wnd_netto, -1, 1), 2, 6)
        prob_wnd = (7 - wnd_target) / 6.0

        wounds_sim = np.random.binomial(hits_to_wound.astype(int), prob_wnd) + auto_wounds_sim

        # Save
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

    # Aggiungi eventuali Danni Mortali Extra (es. Impatto in Carica / Magie)
    if mod_globali["mortal_extra"] != "0":
        danni_totali_sim += tira_dado_mc(mod_globali["mortal_extra"], n_sim)

    # Applica Tiro Ward sul totale dei punti danno
    if ha_ward:
        prob_fail_ward = 1.0 - ((7 - ward_target) / 6.0)
        danni_totali_sim = np.random.binomial(danni_totali_sim.astype(int), prob_fail_ward)

    return danni_totali_sim


# ==========================================
# DATABASE PRESET (Dalle tue Fonti AoS)
# ==========================================
PRESETS = {
    "Personalizzato (Manuale)": {
        "n_modelli": 10, "campione": True, "punti": 150,
        "armi": [
            {"nome": "Arma Principale", "attiva": True, "ranged": False, "atk": "2", "hit": 3, "wnd": 3, "rend": 1, "dmg": "1", "crit_type": "Nessuno", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False},
            {"nome": "Arma Cavalcatura / Secondaria", "attiva": False, "ranged": False, "atk": "2", "hit": 4, "wnd": 4, "rend": 0, "dmg": "1", "crit_type": "Nessuno", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": True},
        ]
    },
    "Nighthaunt: Hexwraiths (5 Modelli)": {
        "n_modelli": 5, "campione": True, "punti": 200,
        "armi": [
            {"nome": "Spectral Scythe", "attiva": True, "ranged": False, "atk": "2", "hit": 4, "wnd": 4, "rend": 1, "dmg": "1", "crit_type": "Crit (Auto-wound)", "anti_target": "Nessuno", "charge_dmg": True, "anti_charge": False, "companion": False},
            {"nome": "Ethereal Steed's Hooves", "attiva": True, "ranged": False, "atk": "2", "hit": 5, "wnd": 3, "rend": 0, "dmg": "1", "crit_type": "Nessuno", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": True},
        ]
    },
    "Nighthaunt: Eroe Anvil of Apotheosis (con War Machine Hooves)": {
        "n_modelli": 1, "campione": False, "punti": 250,
        "armi": [
            {"nome": "Malignant Blade", "attiva": True, "ranged": False, "atk": "3", "hit": 4, "wnd": 3, "rend": 1, "dmg": "2", "crit_type": "Crit (Auto-wound)", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False},
            {"nome": "Hooves (Battle Mount)", "attiva": True, "ranged": False, "atk": "14", "hit": 4, "wnd": 4, "rend": 0, "dmg": "1", "crit_type": "Crit (Auto-wound)", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": True},
        ]
    },
    "Nighthaunt: Lord Executioner": {
        "n_modelli": 1, "campione": False, "punti": 170,
        "armi": [
            {"nome": "Decapitating Greataxe", "attiva": True, "ranged": False, "atk": "5", "hit": 3, "wnd": 3, "rend": 2, "dmg": "2", "crit_type": "Crit (Auto-wound)", "anti_target": "HERO", "charge_dmg": False, "anti_charge": False, "companion": False},
            {"nome": "Nessuna", "attiva": False, "ranged": False, "atk": "1", "hit": 4, "wnd": 4, "rend": 0, "dmg": "1", "crit_type": "Nessuno", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False},
        ]
    },
    "Kruleboyz: Killaboss on Great Gnashtoof": {
        "n_modelli": 1, "campione": False, "punti": 190,
        "armi": [
            {"nome": "Jagged Boss-stikk", "attiva": True, "ranged": False, "atk": "4", "hit": 4, "wnd": 3, "rend": 1, "dmg": "2", "crit_type": "Crit (Mortal)", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False},
            {"nome": "Sloppklaw's Bite and Talons", "attiva": True, "ranged": False, "atk": "6", "hit": 4, "wnd": 2, "rend": 1, "dmg": "3", "crit_type": "Crit (Mortal)", "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": True},
        ]
    }
}

# ==========================================
# SIDEBAR: INPUT VELOCI E SINERGIE GLOBALI
# ==========================================
st.sidebar.title("🔨 MattHammer v2.0")
st.sidebar.caption("AoS 4th Edition Tactical Engine")

preset_scelto = st.sidebar.selectbox("📂 Carica Unità Preimpostata", list(PRESETS.keys()))
dati_preset = PRESETS[preset_scelto]

st.sidebar.divider()
st.sidebar.subheader("👥 Composizione Unità")
col_s1, col_s2 = st.sidebar.columns(2)
n_modelli_base = col_s1.number_input("Modelli Base", min_value=1, max_value=60, value=dati_preset["n_modelli"])
rinforzata = col_s2.checkbox("Rinforzata (x2)", value=False, help="Raddoppia il numero di modelli dell'unità")
n_modelli = n_modelli_base * 2 if rinforzata else n_modelli_base

campione = st.sidebar.checkbox("Presenza Campione (+1 Atk)", value=dati_preset["campione"])
punti_unita = st.sidebar.number_input("Costo in Punti Unità", min_value=50, max_value=1000, value=dati_preset["punti"] * (2 if rinforzata else 1), step=10)

st.sidebar.divider()
st.sidebar.subheader("⚡ Comandi, Carica e Buff")
ha_caricato = st.sidebar.checkbox("🏇 L'unità ha Caricato questo turno", value=False)
all_out_attack = st.sidebar.checkbox("🎯 Comando: All-out Attack (+1 Hit)", value=False)

with st.sidebar.expander("✨ Altri Buff Fazione / Artefatti"):
    mod_hit_extra = st.slider("Altri Modificatori Hit", -2, 2, 0)
    mod_wnd_extra = st.slider("Modificatori Wound", -2, 2, 0)
    bonus_atk = st.number_input("Bonus Attacchi (es. Lightshard +1)", 0, 5, 0, help="Come l'artefatto Lightshard of the Harvest Moon (+1 Atk melee)")
    bonus_rend = st.number_input("Bonus Rend Globale", 0, 3, 0)
    bonus_dmg = st.number_input("Bonus Danno Globale", 0, 3, 0)
    crit_on_5 = st.checkbox("Critico al 5+ (es. Kruleboyz Venoms)", value=False)
    mortal_extra = st.selectbox("Danni Mortali Extra (es. Carica/Magia)", ["0", "1", "D3", "D6", "2D3"], index=0)

mod_globali = {
    "n_modelli": n_modelli,
    "campione": campione,
    "ha_caricato": ha_caricato,
    "all_out_attack": all_out_attack,
    "mod_hit": mod_hit_extra + (1 if all_out_attack else 0),
    "mod_wnd": mod_wnd_extra,
    "bonus_atk": bonus_atk,
    "bonus_rend": bonus_rend,
    "bonus_dmg": bonus_dmg,
    "crit_on": 5 if crit_on_5 else 6,
    "mortal_extra": mortal_extra
}

# ==========================================
# PANNELLO PRINCIPALE: CONFIGURAZIONE ARMI & BERSAGLIO
# ==========================================
st.title("🔨 MattHammer - AoS 4e Tactical Optimizer")

col_armi, col_difesa = st.columns([1.3, 1])

armi_configurate = []
opzioni_dadi = ["1", "2", "3", "4", "5", "6", "14", "D3", "D3+1", "D6", "D6+1", "D6+2", "2D3", "2D6"]

with col_armi:
    st.subheader("⚔️ Profili Armi dell'Unità")
    for idx, p_arma in enumerate(dati_preset["armi"]):
        with st.expander(f"🗡️ Arma {idx+1}: {p_arma['nome']}", expanded=(idx == 0 or p_arma["attiva"])):
            c1, c2, c3 = st.columns([2, 1, 1])
            nome_a = c1.text_input("Nome Arma", value=p_arma["nome"], key=f"nome_{idx}")
            attiva_a = c2.checkbox("Attiva", value=p_arma["attiva"], key=f"att_{idx}")
            comp_a = c3.checkbox("Companion", value=p_arma["companion"], key=f"comp_{idx}", help="Le armi Companion non beneficiano di buff agli attacchi o al Hit (eccetto All-out Attack)")

            s1, s2, s3, s4, s5 = st.columns(5)
            idx_atk = opzioni_dadi.index(p_arma["atk"]) if p_arma["atk"] in opzioni_dadi else 1
            idx_dmg = opzioni_dadi.index(p_arma["dmg"]) if p_arma["dmg"] in opzioni_dadi else 0

            atk_a = s1.selectbox("Attacks", opzioni_dadi, index=idx_atk, key=f"atk_{idx}")
            hit_a = s2.selectbox("Hit (X+)", [2, 3, 4, 5, 6], index=p_arma["hit"]-2, key=f"hit_{idx}")
            wnd_a = s3.selectbox("Wound (X+)", [2, 3, 4, 5, 6], index=p_arma["wnd"]-2, key=f"wnd_{idx}")
            rend_a = s4.number_input("Rend", 0, 5, value=p_arma["rend"], key=f"rend_{idx}")
            dmg_a = s5.selectbox("Damage", opzioni_dadi, index=idx_dmg, key=f"dmg_{idx}")

            ab1, ab2, ab3 = st.columns(3)
            opz_crit = ["Nessuno", "Crit (Mortal)", "Crit (Auto-wound)", "Crit (2 Hits)"]
            opz_anti = ["Nessuno", "HERO", "INFANTRY", "CAVALRY", "MONSTER", "WAR MACHINE"]
            crit_a = ab1.selectbox("Abilità Critico", opz_crit, index=opz_crit.index(p_arma["crit_type"]), key=f"crit_{idx}")
            anti_a = ab2.selectbox("Anti-X (+1 Rend)", opz_anti, index=opz_anti.index(p_arma["anti_target"]), key=f"anti_{idx}")
            ranged_a = ab3.checkbox("Arma da Tiro (Ranged)", value=p_arma["ranged"], key=f"rng_{idx}")

            ch1, ch2 = st.columns(2)
            chrg_dmg_a = ch1.checkbox("Charge (+1 Damage)", value=p_arma["charge_dmg"], key=f"cdmg_{idx}")
            anti_chrg_a = ch2.checkbox("Anti-Charge (+1 Rend)", value=p_arma["anti_charge"], key=f"achrg_{idx}")

            armi_configurate.append({
                "nome": nome_a, "attiva": attiva_a, "ranged": ranged_a,
                "atk": atk_a, "hit": hit_a, "wnd": wnd_a, "rend": rend_a, "dmg": dmg_a,
                "crit_type": crit_a, "anti_target": anti_a,
                "charge_dmg": chrg_dmg_a, "anti_charge": anti_chrg_a, "companion": comp_a
            })

with col_difesa:
    st.subheader("🛡️ Profilo Bersaglio & Terreno")
    with st.container(border=True):
        d1, d2, d3 = st.columns(3)
        save_b = d1.selectbox("Save Bersaglio", [2, 3, 4, 5, 6, 7], index=2, format_func=lambda x: f"{x}+" if x < 7 else "Nessuno (-)")
        ward_b = d2.selectbox("Ward Bersaglio", [7, 6, 5, 4], index=0, format_func=lambda x: f"{x}+" if x < 7 else "Nessuno (-)")
        salute_b = d3.number_input("Salute Totale Bersaglio", min_value=1, max_value=100, value=10, help="Somma della caratteristica Health di tutti i modelli del bersaglio")

        keywords_b = st.multiselect("Keywords del Bersaglio (Attiva i bonus Anti-X)", ["INFANTRY", "HERO", "CAVALRY", "MONSTER", "WAR MACHINE"], default=["INFANTRY"])

        st.markdown("**Condizioni Difensive e Terreni (GHB 2024-25):**")
        t1, t2 = st.columns(2)
        cover_b = t1.checkbox("🌲 Bersaglio in Cover (+1 Save)", value=False, help="Garantito da Area Terrain, Obstacles, Obscuring e Places of Power")
        aod_b = t2.checkbox("🛡️ Comando: All-out Defence (+1 Save)", value=False)
        obscuring_b = t1.checkbox("🌫️ Terreno Obscuring (-1 Hit al tiro)", value=False)
        bersaglio_carica = t2.checkbox("⚡ Il Bersaglio ha Caricato", value=False, help="Attiva l'eventuale Anti-charge (+1 Rend) delle tue armi")

        debuff_ward = st.checkbox("💀 Debuff: -1 al tiro Ward (es. Vitiating Vapours)", value=False, help="Come l'abilità passiva del Corpse Cart di Veremord's Shamblers")

bersaglio_dict = {
    "save": save_b, "ward": ward_b, "salute": salute_b, "keywords": keywords_b,
    "cover": cover_b, "aod": aod_b, "obscuring": obscuring_b,
    "bersaglio_ha_caricato": bersaglio_carica,
    "mod_ward_penalita": 1 if debuff_ward else 0
}
mod_globali["bersaglio_ha_caricato"] = bersaglio_carica

# ==========================================
# ESECUZIONE CALCOLI E SIMULAZIONE
# ==========================================
risultati_armi = [calcola_arma_analitico(a, mod_globali, bersaglio_dict) for a in armi_configurate]

danno_atteso_armi = sum(r["danno_netto"] for r in risultati_armi)
ward_eff = bersaglio_dict["ward"] + bersaglio_dict["mod_ward_penalita"]
moltiplicatore_ward = 1.0 if (bersaglio_dict["ward"] >= 7 or ward_eff > 6) else 1.0 - ((7 - max(2, ward_eff)) / 6.0)
danno_extra_atteso = (media_dado(mortal_extra) if mortal_extra != "0" else 0.0) * moltiplicatore_ward

danno_totale_atteso = danno_atteso_armi + danno_extra_atteso

# Esegui Monte Carlo (10.000 iterazioni)
campioni_mc = simula_monte_carlo(armi_configurate, mod_globali, bersaglio_dict, n_sim=10000)
prob_uccisione = np.mean(campioni_mc >= salute_b) * 100.0
dev_std = np.std(campioni_mc)
roi_punti = (danno_totale_atteso / punti_unita) * 100.0

st.divider()

# ==========================================
# METRICHE PRINCIPALI IN EVIDENZA
# ==========================================
m1, m2, m3, m4 = st.columns(4)
m1.metric("💥 Danno Medio Atteso E[D]", f"{danno_totale_atteso:.2f} ferite", f"± {dev_std:.1f} (Deviazione Std)")
m2.metric("☠️ Probabilità Wipeout (Kill)", f"{prob_uccisione:.1f}%", f"vs {salute_b} Salute Totale")
m3.metric("⚖️ Efficienza per 100 Punti", f"{roi_punti:.2f} Danni", f"Costo: {punti_unita} pt")
m4.metric("🎲 Attacchi Totali Lanciati", f"{sum(r['attacchi'] for r in risultati_armi):.0f} dadi")

# ==========================================
# TABS DI ANALISI AVANZATA
# ==========================================
tab1, tab2, tab3 = st.tabs([
    "📊 Analisi Funnel & Armi",
    "🎲 Distribuzione Monte Carlo (Stile MATLAB)",
    "🧠 Consigliere Tattico & Heatmap Bersagli"
])

with tab1:
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.subheader("Ripartizione Danni per Arma")
        righe_armi = []
        for a, r in zip(armi_configurate, risultati_armi):
            if a["attiva"]:
                righe_armi.append({
                    "Arma": a["nome"],
                    "Attacchi": round(r["attacchi"], 1),
                    "Hits Totali": round(r["hits"], 2),
                    "Wounds (con Auto)": round(r["wounds"], 2),
                    "Save Falliti": round(r["unsaved"], 2),
                    "Mortali da Crit": round(r["mortal"], 2),
                    "Danno Netto": round(r["danno_netto"], 2)
                })
        df_armi = pd.DataFrame(righe_armi)
        st.dataframe(df_armi, use_container_width=True, hide_index=True)

    with col_t2:
        st.subheader("Funnel di Conversione Dadi")
        df_funnel = pd.DataFrame({
            "Fase": ["1. Attacchi", "2. Colpi (Hits)", "3. Ferite (Wounds)", "4. Save Falliti", "5. Danno Netto Finale"],
            "Valore": [
                sum(r["attacchi"] for r in risultati_armi),
                sum(r["hits"] for r in risultati_armi),
                sum(r["wounds"] for r in risultati_armi),
                sum(r["unsaved"] for r in risultati_armi),
                danno_totale_atteso
            ]
        })
        st.bar_chart(df_funnel.set_index("Fase"))

with tab2:
    st.subheader("Curva di Probabilità Cumulativa: Probabilità di infliggere ALMENO X Danni")
    st.caption("Calcolata su N = 10.000 simulazioni stocastiche Monte Carlo.")
    
    max_danno_grafico = int(np.percentile(campioni_mc, 99.5)) + 2
    asse_x = np.arange(1, max(10, max_danno_grafico))
    prob_almeno_x = [np.mean(campioni_mc >= x) * 100.0 for x in asse_x]
    
    df_mc = pd.DataFrame({
        "Danni Minimi (X)": asse_x,
        "Probabilità (%)": prob_almeno_x
    }).set_index("Danni Minimi (X)")
    
    st.line_chart(df_mc)
    
    p1, p2, p3 = st.columns(3)
    p1.info(f"**Caso Sfortunato (25° Percentile):** Farai almeno **{int(np.percentile(campioni_mc, 25))} danni** nel 75% delle partite.")
    p2.success(f"**Mediana (50° Percentile):** Farai almeno **{int(np.percentile(campioni_mc, 50))} danni** nella metà dei casi.")
    p3.warning(f"**Spike Fortunato (90° Percentile):** Hai il 10% di possibilità di esplodere facendo **{int(np.percentile(campioni_mc, 90))}+ danni**!")

with tab3:
    st.subheader("🧠 Ottimizzatore Scelte Tattiche (What-If Engine)")
    
    # Calcola scenari alternativi istantanei
    mod_aoa = mod_globali.copy()
    mod_aoa["all_out_attack"] = True
    mod_aoa["mod_hit"] = mod_hit_extra + 1
    danno_con_aoa = sum(calcola_arma_analitico(a, mod_aoa, bersaglio_dict)["danno_netto"] for a in armi_configurate) + danno_extra_atteso

    mod_wnd_plus = mod_globali.copy()
    mod_wnd_plus["mod_wnd"] = mod_wnd_extra + 1
    danno_con_wnd = sum(calcola_arma_analitico(a, mod_wnd_plus, bersaglio_dict)["danno_netto"] for a in armi_configurate) + danno_extra_atteso

    bers_aod = bersaglio_dict.copy()
    bers_aod["aod"] = True
    danno_vs_aod = sum(calcola_arma_analitico(a, mod_globali, bers_aod)["danno_netto"] for a in armi_configurate) + danno_extra_atteso

    c_w1, c_w2, c_w3 = st.columns(3)
    diff_aoa = danno_con_aoa - danno_totale_atteso
    diff_wnd = danno_con_wnd - danno_totale_atteso
    diff_aod = danno_vs_aod - danno_totale_atteso

    c_w1.metric("Se usi All-out Attack (+1 Hit)", f"{danno_con_aoa:.2f} Danni", f"+{diff_aoa:.2f} ferite")
    c_w2.metric("Se ottieni +1 to Wound", f"{danno_con_wnd:.2f} Danni", f"+{diff_wnd:.2f} ferite")
    c_w3.metric("Se il nemico usa All-out Defence", f"{danno_vs_aod:.2f} Danni", f"{diff_aod:.2f} ferite", delta_color="inverse")

    st.divider()
    st.subheader("🎯 Matrice Target Priority: Danno Atteso contro ogni combinazione di Save e Ward")
    st.caption("Usa questa tabella per capire a colpo d'occhio contro quale tipo di unità nemica la tua unità rende al massimo.")

    saves_lista = [2, 3, 4, 5, 6, 7]
    wards_lista = [7, 6, 5, 4]
    matrice_dati = {}

    for w_val in wards_lista:
        col_nome = f"Ward {w_val}+" if w_val < 7 else "Nessun Ward"
        valori_col = []
        for s_val in saves_lista:
            b_temp = bersaglio_dict.copy()
            b_temp["save"] = s_val
            b_temp["ward"] = w_val
            b_temp["mod_ward_penalita"] = 0
            d_temp = sum(calcola_arma_analitico(a, mod_globali, b_temp)["danno_netto"] for a in armi_configurate)
            valori_col.append(round(d_temp, 2))
        matrice_dati[col_nome] = valori_col

    df_matrice = pd.DataFrame(matrice_dati, index=[f"Save {s}+" if s < 7 else "No Save (-)" for s in saves_lista])
    st.dataframe(df_matrice.style.background_gradient(cmap="YlOrRd"), use_container_width=True)