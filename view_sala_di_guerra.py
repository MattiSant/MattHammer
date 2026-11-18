import streamlit as st
import numpy as np
import pandas as pd
import json
import os
from core_engine import (
    calcola_arma_analitico,
    _push_su_github_file,
    ordina_unita_per_fazione_e_nome,
    ordina_supporti_per_fazione_e_nome
)
from utils import (
    estrai_valore_keyword,
    estrai_livello_potere,
    estrai_intero_sicuro,
    filtra_unita_per_fazione,
    filtra_supporti_per_fazione,
    render_card_abilita_wahapedia,
    mostra_toast_rapido
)
from ability_parser import applica_abilita_attive_a_mod_globali

# Usa percorsi assoluti per evitare scritture in cartelle errate al riavvio
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARMIES_DB_FILE = os.path.join(BASE_DIR, "armies_db.json")
FORMATIONS_DB_FILE = os.path.join(BASE_DIR, "formations.json")
TRAITS_DB_FILE = os.path.join(BASE_DIR, "heroic_traits_db.json")
ARTEFACTS_DB_FILE = os.path.join(BASE_DIR, "artefacts_db.json")

# ==========================================
# GESTIONE ARCHIVI JSON E SUPPORTO
# ==========================================
def carica_archivio_armate():
    if os.path.exists(ARMIES_DB_FILE):
        try:
            with open(ARMIES_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def salva_archivio_armate(armate_dict):
    successo, messaggio = _push_su_github_file(ARMIES_DB_FILE, armate_dict, "Aggiornamento Roster Armata")
    if not successo:
        st.warning(messaggio)
    return True

def carica_formazioni_db():
    if os.path.exists(FORMATIONS_DB_FILE):
        try:
            with open(FORMATIONS_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def carica_db_supporto_dict(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                dati = json.load(f)
                if isinstance(dati, dict) and "Generali" not in dati:
                    return dati
        except Exception:
            pass
    return {"Nessuno": {"punti": 0, "modificatori": {}}}

ARMATE_NEMICHE_NOTE = {
    "Khorne: Eroi d'Assalto (450pt)": [
        {"nome": "Blades of Khorne: Bloodsecrator", "rinforzata": False},
        {"nome": "Blades of Khorne: Deathbringer", "rinforzata": False},
        {"nome": "Blades of Khorne: Mighty Lord of Khorne", "rinforzata": False},
        {"nome": "Blades of Khorne: Slaughterpriest", "rinforzata": False}
    ],
    "Orruk Kruleboyz: Orda & Boss (410pt)": [
        {"nome": "Orruk Kruleboyz: Gutrippaz", "rinforzata": True},
        {"nome": "Orruk Kruleboyz: Hobgrot Slittaboss", "rinforzata": False},
        {"nome": "Orruk Kruleboyz: Killaboss on Great Gnashtoof", "rinforzata": False}
    ],
    "Sylvaneth: Bosco & Kurnoth (610pt)": [
        {"nome": "Sylvaneth: Branchwych", "rinforzata": False},
        {"nome": "Sylvaneth: Dryads", "rinforzata": True},
        {"nome": "Sylvaneth: Kurnoth Hunters With Greatswords", "rinforzata": False},
        {"nome": "Sylvaneth: Grove Guardian", "rinforzata": False}
    ],
    "Nighthaunt: Corte Spettrale (700pt)": [
        {"nome": "Nighthaunt: Knight of Shrouds", "rinforzata": False},
        {"nome": "Nighthaunt: Guardian of Souls", "rinforzata": False},
        {"nome": "Nighthaunt: Bladegheist Revenants", "rinforzata": False},
        {"nome": "Nighthaunt: Grimghast Reapers", "rinforzata": False},
        {"nome": "Nighthaunt: Spirit Hosts", "rinforzata": False}
    ]
}

# ==========================================
# FUNZIONI DI CALCOLO E SUPPORTO TATTICO
# ==========================================
def costruisci_bersaglio_da_db(nome_unita, dati_u_db, rinforzata=False, bonus_extra=None):
    bonus_extra = bonus_extra or {}
    dif = dati_u_db.get("difesa", {})
    stat = dati_u_db.get("statistiche_cerchio", {})
    molt = 2 if rinforzata else 1

    sv = estrai_intero_sicuro(stat.get("save", dif.get("save", 4)), default=4)
    wd = estrai_intero_sicuro(stat.get("ward", dif.get("ward", 7)), default=7)
    
    # Estrae eventuali bonus difensivi passivi dalle abilità della Warscroll stessa
    bonus_ab_dif = {}
    for ab_u in dati_u_db.get("abilita", []):
        for k_m, v_m in ab_u.get("modificatori", {}).items():
            if k_m == "ward_nativo" and isinstance(v_m, (int, float)):
                wd = min(wd, int(v_m))
            elif k_m in ["bonus_save", "mod_hit_subito", "mod_wnd_nerf"] and isinstance(v_m, (int, float)):
                bonus_ab_dif[k_m] = bonus_ab_dif.get(k_m, 0) + int(v_m)

    if "ward_nativo" in bonus_extra:
        wd = min(wd, int(bonus_extra["ward_nativo"]))

    n_mod = max(1, estrai_intero_sicuro(dati_u_db.get("n_modelli", 1), default=1)) * molt
    sal_mod = max(1, estrai_intero_sicuro(stat.get("salute", dif.get("salute_per_modello", 1)), default=1))
    hp_tot = max(1, n_mod * sal_mod + int(bonus_extra.get("bonus_salute", 0)))
    pt_tot = estrai_intero_sicuro(dati_u_db.get("punti", 0)) * molt + int(bonus_extra.get("punti_equip", 0))

    kw = [str(k).upper() for k in dati_u_db.get("keywords", ["INFANTRY"])]
    is_etereo = (
        "nighthaunt" in nome_unita.lower()
        or "nighthaunt" in dati_u_db.get("fazione", "").lower()
        or any(k in ["NIGHTHAUNT", "ETHEREAL", "ETHEREO", "SPIRIT"] for k in kw)
    )

    return {
        "nome": nome_unita,
        "save": sv, "ward": wd, "salute": hp_tot, "salute_per_modello": sal_mod,
        "n_modelli": n_mod, "punti": pt_tot, "keywords": kw,
        "cover": False, "aod": False, "bonus_save_extra": int(bonus_extra.get("bonus_save", 0)) + int(bonus_ab_dif.get("bonus_save", 0)),
        "obscuring": False, "bersaglio_ha_caricato": False,
        "mod_ward_penalita": 0, "blocca_ward": False, "mod_wnd_nerf": int(bonus_ab_dif.get("mod_wnd_nerf", 0)),
        "mod_hit_subito": int(bonus_extra.get("mod_hit_subito", 0)) + int(bonus_ab_dif.get("mod_hit_subito", 0)),
        "immune_rend": is_etereo
    }

def calcola_output_unita_su_bersaglio(dati_unita_db, rinforzata, bersaglio_test, bonus_attaccante=None, ha_caricato=True, n_modelli_override=None):
    bonus_attaccante = bonus_attaccante or {}
    armi = dati_unita_db.get("armi", [])
    n_mod_base = max(1, estrai_intero_sicuro(dati_unita_db.get("n_modelli", 1), default=1))
    n_mod = n_modelli_override if n_modelli_override is not None else (n_mod_base * (2 if rinforzata else 1))
    
    if n_mod <= 0:
        return {"danno_melee": 0.0, "danno_ranged": 0.0, "danno_totale": 0.0, "max_rend": 0, "attacchi_tot": 0.0}

    campione = bool(dati_unita_db.get("campione", False))
    mod_glob = {
        "n_modelli": n_mod,
        "campione": campione,
        "ha_caricato": ha_caricato,
        "all_out_attack": False,
        "mod_hit": int(bonus_attaccante.get("mod_hit", 0)),
        "mod_wnd": int(bonus_attaccante.get("mod_wnd", 0)),
        "bonus_atk": int(bonus_attaccante.get("bonus_atk", 0)),
        "bonus_rend": int(bonus_attaccante.get("bonus_rend", 0)),
        "bonus_dmg": int(bonus_attaccante.get("bonus_dmg", 0)),
        "crit_on": 5 if bonus_attaccante.get("crit_on") == 5 else 6,
        "bersaglio_ha_caricato": bersaglio_test.get("bersaglio_ha_caricato", False)
    }

    # Applica automaticamente le abilità Warscroll dell'unità (rispettando ha_caricato e il bersaglio)
    mod_glob = applica_abilita_attive_a_mod_globali(dati_unita_db.get("abilita", []), mod_glob, bersaglio=bersaglio_test)

    danno_melee = 0.0
    danno_ranged = 0.0
    max_rend = 0
    attacchi_tot = 0.0

    for a in armi:
        if a.get("attiva", False) and str(a.get("hit", "---")) != "---":
            arma_eval = dict(a)
            if "crit_override" in mod_glob and not arma_eval.get("companion", False):
                arma_eval["crit_type"] = mod_glob["crit_override"]
            ris = calcola_arma_analitico(arma_eval, mod_glob, bersaglio_test)
            if a.get("ranged", False):
                danno_ranged += ris["danno_netto"]
            else:
                danno_melee += ris["danno_netto"]
            attacchi_tot += ris["attacchi"]
            b_rnd_arma = 0 if a.get("companion", False) else (
                int(mod_glob.get("bonus_rend", 0)) + (int(mod_glob.get("bonus_rend_ranged", 0)) if a.get("ranged", False) else int(mod_glob.get("bonus_rend_melee", 0)))
            )
            r_val = estrai_intero_sicuro(a.get("rend", 0), default=0) + b_rnd_arma
            if r_val > max_rend:
                max_rend = r_val

    # Aggiunge eventuali Danni Mortali Extra generati da abilità (es. impatto in carica) ridotti dal Ward bersaglio
    ward_b = bersaglio_test.get("ward", 7)
    molt_ward = 0.0 if bersaglio_test.get("blocca_ward", False) else (1.0 if ward_b >= 7 else 1.0 - ((7 - max(2, ward_b)) / 6.0))
    mortali_ab = float(mod_glob.get("mortal_extra_fisso", 0.0)) + float(mod_glob.get("mortal_ab_analitico", 0.0))
    n_d_ab = int(mod_glob.get("mortal_extra_dadi", 0))
    if n_d_ab > 0:
        t_d_ab = int(mod_glob.get("mortal_extra_tipo", 6))
        soglia_ab = str(mod_glob.get("mortal_extra_soglia", "Nessuna (Somma)"))
        if soglia_ab.startswith("Nessuna"):
            mortali_ab += n_d_ab * (2.0 if t_d_ab == 3 else 3.5)
        else:
            mortali_ab += n_d_ab * max(0.0, (t_d_ab - int(soglia_ab[0]) + 1) / float(t_d_ab))
    
    danno_melee += (mortali_ab * molt_ward)

    return {
        "danno_melee": danno_melee,
        "danno_ranged": danno_ranged,
        "danno_totale": danno_melee + danno_ranged,
        "max_rend": max_rend,
        "attacchi_tot": attacchi_tot
    }


# ==========================================
# VISTA PRINCIPALE: SALA DI GUERRA
# ==========================================
def render_sala_di_guerra():
    st.markdown("""
    <style>
        .section-header {
            font-family: 'Cinzel Decorative', serif !important;
            font-size: 1.85rem !important;
            color: #f7d57f !important;
            letter-spacing: 1.8px !important;
            text-transform: uppercase;
            border-bottom: 2px solid #8c6d46 !important;
            padding-bottom: 6px;
            margin-top: 15px;
            margin-bottom: 6px;
            text-shadow: 0 3px 10px rgba(0,0,0,0.85), 0 0 12px rgba(212, 175, 55, 0.25);
        }
        .subsection-title {
            font-family: 'Cinzel', serif !important;
            font-size: 1.25rem !important;
            color: #e6c665 !important;
            font-weight: 700 !important;
            letter-spacing: 0.8px !important;
            border-bottom: 1px dashed rgba(230, 198, 101, 0.45);
            padding-bottom: 4px;
            margin-bottom: 8px;
        }
        div[data-testid="stContainer"] .subsection-title {
            color: #5a3c1e !important;
            border-bottom: 1px dashed rgba(90, 60, 30, 0.4);
        }
        .warscroll-box {
            background: linear-gradient(135deg, #22180f 0%, #120d08 100%);
            border: 2px solid #8c6d46;
            border-top: 3px solid #d4af37;
            border-radius: 4px 12px 4px 12px;
            padding: 14px 16px;
            margin-top: 8px;
            margin-bottom: 12px;
            color: #f4ecd8;
            box-shadow: 0 6px 18px rgba(0,0,0,0.7), inset 0 0 25px rgba(212, 175, 55, 0.08);
        }
        .ability-box {
            background: linear-gradient(90deg, rgba(50, 32, 18, 0.75) 0%, rgba(32, 20, 11, 0.6) 100%);
            border-left: 4px solid #d4af37;
            border: 1px solid #6b4d2a;
            border-left-width: 4px;
            padding: 9px 13px;
            margin: 7px 0;
            border-radius: 3px 8px 8px 3px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.4);
        }
        .ability-box-reaction {
            background: linear-gradient(90deg, rgba(65, 20, 20, 0.8) 0%, rgba(40, 12, 12, 0.6) 100%);
            border-left: 4px solid #e74c3c;
            border: 1px solid #852a20;
            border-left-width: 4px;
            padding: 9px 13px;
            margin: 7px 0;
            border-radius: 3px 8px 8px 3px;
            box-shadow: 0 2px 8px rgba(192, 57, 43, 0.25);
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("MattHammer — Sala di Guerra")
    st.caption("Costruttore d'armata avanzato per Reggimenti (AoS 4e), gestione formazioni e simulatore di Match-Up.")

    # Inizializzazione Session State
    if "archivio_formazioni" not in st.session_state:
        st.session_state["archivio_formazioni"] = carica_formazioni_db()
    if "archivio_armate" not in st.session_state:
        st.session_state["archivio_armate"] = carica_archivio_armate()
    if "sdg_roster_version" not in st.session_state:
        st.session_state["sdg_roster_version"] = 0
    if "sdg_reggimenti" not in st.session_state or not isinstance(st.session_state["sdg_reggimenti"], list) or len(st.session_state["sdg_reggimenti"]) == 0:
        st.session_state["sdg_reggimenti"] = [
            {
                "leader": "--- Scegli Eroe Leader ---",
                "is_generale": True,
                "rinforzato": False,
                "tratto_eroico": "Nessuno",
                "artefatto": "Nessuno",
                "seguito": []
            }
        ]
    if "sdg_ausiliari" not in st.session_state:
        st.session_state["sdg_ausiliari"] = []
    if "sdg_nemici_matchup" not in st.session_state:
        st.session_state["sdg_nemici_matchup"] = []
    
    st.session_state["tratti_disp_lead_dict"] = carica_db_supporto_dict(TRAITS_DB_FILE)
    st.session_state["tratti_disp_lead"] = ordina_supporti_per_fazione_e_nome(st.session_state["tratti_disp_lead_dict"])

    st.session_state["art_disp_lead_dict"] = carica_db_supporto_dict(ARTEFACTS_DB_FILE)
    st.session_state["art_disp_lead"] = ordina_supporti_per_fazione_e_nome(st.session_state["art_disp_lead_dict"])

    tratti_disp_lead = st.session_state["tratti_disp_lead"]
    art_disp_lead = st.session_state["art_disp_lead"]

    if "sdg_nome_armata" not in st.session_state:
        st.session_state["sdg_nome_armata"] = ""
    if "sdg_fazione_armata" not in st.session_state:
        st.session_state["sdg_fazione_armata"] = "--- Seleziona Fazione ---"
    if "sdg_formazione_scelta" not in st.session_state:
        st.session_state["sdg_formazione_scelta"] = "--- Seleziona Formazione ---"

    opzioni_db = ordina_unita_per_fazione_e_nome(st.session_state["db_unita"])

    # ==========================================
    # CARICAMENTO ARMATA ESISTENTE
    # ==========================================
    armate_salvate = list(st.session_state["archivio_armate"].keys())
    if armate_salvate:
        with st.expander("📂 Carica un'Armata dal tuo Archivio", expanded=False):
            c_load1, c_load2, c_load3 = st.columns([2.5, 1, 1])
            armata_da_caricare = c_load1.selectbox("Seleziona Armata:", ["--- Scegli Armata ---"] + armate_salvate)
            if c_load2.button("📥 Carica Armata", type="primary", use_container_width=True):
                if armata_da_caricare != "--- Scegli Armata ---":
                    dati_armata = st.session_state["archivio_armate"][armata_da_caricare]
                    st.session_state["sdg_nome_armata"] = dati_armata.get("nome", "Armata Caricata")
                    st.session_state["sdg_fazione_armata"] = dati_armata.get("fazione", "Nighthaunt")
                    st.session_state["sdg_formazione_scelta"] = dati_armata.get("formazione", "Formazione Standard")
                    st.session_state["sdg_reggimenti"] = dati_armata.get("reggimenti", [])
                    st.session_state["sdg_ausiliari"] = dati_armata.get("ausiliari", [])
                    st.session_state["sdg_roster_version"] += 1
                    st.session_state["sdg_limite_custom"] = dati_armata.get("limite_punti", 720)
                    st.session_state["sdg_formato_scelto"] = "Personalizzato (Custom)" if dati_armata.get("limite_punti") not in [1000, 1500] else (
                        "Vanguard (1000 pt)" if dati_armata.get("limite_punti") == 1000 else "Strike Force (1500 pt)"
                    )
                    mostra_toast_rapido(f"Armata '{armata_da_caricare}' caricata!", "✅")
                    st.rerun()
            if c_load3.button("🗑️ Elimina", use_container_width=True):
                if armata_da_caricare != "--- Scegli Armata ---":
                    del st.session_state["archivio_armate"][armata_da_caricare]
                    salva_archivio_armate(st.session_state["archivio_armate"])
                    mostra_toast_rapido(f"Armata '{armata_da_caricare}' eliminata dall'archivio!", icon="🗑️")
                    st.rerun()

    # ==========================================
    # SEZIONE 1: GENERALITÀ DELL'ARMATA E FORMAZIONE
    # ==========================================
    st.markdown('<div class="section-header">Configurazione Schieramento e Formazione</div>', unsafe_allow_html=True)
    st.caption("Definisci le generalità dell'esercito, il formato della battaglia e la Formazione tattica associata con i relativi bonus.")

    with st.container(border=True):
        st.markdown('<div class="subsection-title">Generalità dell\'Esercito</div>', unsafe_allow_html=True)
        
        col_f1, col_f2, col_f3, col_f4 = st.columns([1.5, 1.2, 1.3, 1])
        st.session_state["sdg_nome_armata"] = col_f1.text_input(
            "Nome della Lista",
            value=st.session_state["sdg_nome_armata"],
            placeholder="Inserisci il nome della tua armata...",
            key=f"inp_nome_armata_v{st.session_state['sdg_roster_version']}"
        )

        lista_fazioni_disp = [
            "--- Seleziona Fazione ---",
            "Blades of Khorne", "Cities of Sigmar", "Daughters of Khaine",
            "Disciples of Tzeentch", "Flesh-eater Courts", "Fyreslayers",
            "Gloomspite Gitz", "Hedonites of Slaanesh", "Idoneth Deepkin",
            "Kharadron Overlords", "Lumineth Realm-lords", "Maggotkin of Nurgle",
            "Nighthaunt", "Ogor Mawtribes", "Orruk Kruleboyz", "Orruk Warclans",
            "Ossiarch Bonereapers", "Seraphon", "Skaven", "Slaves to Darkness",
            "Sons of Behemat", "Soulblight Gravelords", "Stormcast Eternals",
            "Sylvaneth", "Grande Alleanza / Altro"
        ]
        idx_faz = lista_fazioni_disp.index(st.session_state["sdg_fazione_armata"]) if st.session_state["sdg_fazione_armata"] in lista_fazioni_disp else 0
        st.session_state["sdg_fazione_armata"] = col_f2.selectbox("Fazione", lista_fazioni_disp, index=idx_faz)

        opzioni_formato = ["Vanguard (1000 pt)", "Strike Force (1500 pt)", "Personalizzato (Custom)"]
        fmt_default = st.session_state.get("sdg_formato_scelto", "Vanguard (1000 pt)")
        idx_fmt = opzioni_formato.index(fmt_default) if fmt_default in opzioni_formato else 0
        formato_scelto = col_f3.selectbox("Formato Battaglia", opzioni_formato, index=idx_fmt)
        st.session_state["sdg_formato_scelto"] = formato_scelto

        if "1000" in formato_scelto:
            limite_punti = 1000
        elif "1500" in formato_scelto:
            limite_punti = 1500
        else:
            val_custom = int(st.session_state.get("sdg_limite_custom", 720))
            limite_punti = col_f4.number_input("Punti Custom", min_value=100, max_value=5000, value=val_custom, step=10)
            st.session_state["sdg_limite_custom"] = limite_punti
        st.markdown("---")
        st.markdown('<div class="subsection-title">Formazione di Battaglia (Battle Formation)</div>', unsafe_allow_html=True)
        st.caption("Formazione ufficiale associata all'armata. Regole, fasi d'attivazione e modificatori numerici sono pre-impostati da database.")

        fazioni_disponibili_db = st.session_state["archivio_formazioni"]
        
        formazioni_fazione = fazioni_disponibili_db.get(st.session_state["sdg_fazione_armata"], {})
        lista_nomi_formazioni = ["--- Seleziona Formazione ---"] + (list(formazioni_fazione.keys()) if isinstance(formazioni_fazione, dict) else [])
        
        idx_form = lista_nomi_formazioni.index(st.session_state["sdg_formazione_scelta"]) if st.session_state["sdg_formazione_scelta"] in lista_nomi_formazioni else 0
        
        formazione_selezionata = st.selectbox("Nome Formazione", lista_nomi_formazioni, index=idx_form)
        st.session_state["sdg_formazione_scelta"] = formazione_selezionata

        dati_form = formazioni_fazione.get(formazione_selezionata, {
            "fase_attivazione": "Passiva", "monouso": False, "modificatori": {}, "descrizione": "Descrizione non disponibile."
        })

        mod_formazione_attiva = dati_form.get("modificatori", {})
        mod_form_str = ", ".join([f"{k}: +{v}" if isinstance(v, int) and v > 0 else f"{k}: {v}" for k, v in mod_formazione_attiva.items()]) if mod_formazione_attiva else "Nessun modificatore diretto"

        fc1, fc2, fc3 = st.columns([1.2, 1, 1.8])
        with fc1:
            st.markdown(f"**Modificatori Attivi:**\n`{mod_form_str}`")
        with fc2:
            st.markdown(f"**Fase di Attivazione:**\n`{dati_form.get('fase_attivazione', 'Nessuna')}`")
            is_monouso_str = "Sì (Once per Battle)" if dati_form.get('monouso', False) else "No (Ricorrente / Passiva)"
            st.markdown(f"**Monouso:** `{is_monouso_str}`")
        with fc3:
            st.markdown("**Regola & Descrizione Ufficiale:**")
            st.info(dati_form.get('descrizione', 'Nessun dettaglio inserito.'))

    # ==========================================
    # SEZIONE 2: COMPOSIZIONE REGGIMENTI
    # ==========================================
    st.markdown('<div class="section-header">Composizione Reggimenti</div>', unsafe_allow_html=True)
    st.caption("Il Reggimento #1 è guidato dal Generale d'Armata. I leader devono possedere la keyword HERO.")

    col_btn_reg1, col_btn_reg2 = st.columns([1, 3])
    if col_btn_reg1.button("➕ Aggiungi Reggimento", type="primary", use_container_width=True):
        st.session_state["sdg_reggimenti"].append({
            "leader": "--- Scegli Eroe Leader ---",
            "is_generale": False,
            "rinforzato": False,
            "tratto_eroico": "Nessuno",
            "artefatto": "Nessuno",
            "seguito": []
        })
        st.rerun()

    if col_btn_reg2.button("Svuota Roster Completo"):
        chiavi_da_eliminare = [
            k for k in st.session_state.keys()
            if k.startswith("reg_lead_") or k.startswith("reg_trait_") or k.startswith("reg_art_") or k.startswith("fol_")
        ]
        for k in chiavi_da_eliminare:
            del st.session_state[k]

        st.session_state["sdg_reggimenti"] = [{
            "leader": "--- Scegli Eroe Leader ---",
            "is_generale": True,
            "rinforzato": False,
            "tratto_eroico": "Nessuno",
            "artefatto": "Nessuno",
            "seguito": []
        }]
        st.session_state["sdg_ausiliari"] = []
        st.session_state["sdg_roster_version"] += 1
        st.rerun()

    eroi_db_filtrati = []
    for k_unita in opzioni_db:
        dati_u_temp = st.session_state["db_unita"].get(k_unita, {})
        keywords_u = [str(kw).upper() for kw in dati_u_temp.get("keywords", ["HERO"])]
        if "HERO" in keywords_u or not dati_u_temp.get("keywords"): 
            eroi_db_filtrati.append(k_unita)

    if not eroi_db_filtrati:
        eroi_db_filtrati = opzioni_db

    reggimenti_da_rimuovere = []

    for r_idx, reg in enumerate(st.session_state["sdg_reggimenti"]):
        if r_idx == 0:
            reg["is_generale"] = True

        with st.container(border=True):
            head_c1, head_c2 = st.columns([4, 1])
            etichetta_gen = " — ★ GENERALE D'ARMATA (Reggimento Principale)" if reg.get("is_generale", False) else f" — Reggimento #{r_idx+1}"
            head_c1.markdown(f'<div class="subsection-title">{etichetta_gen}</div>', unsafe_allow_html=True)
            
            if r_idx > 0:
                if head_c2.button("🗑️ Rimuovi", key=f"del_reg_{r_idx}", use_container_width=True):
                    reggimenti_da_rimuovere.append(r_idx)

            f_reg_col1, lc1, lc2 = st.columns([1.2, 2.2, 1.3])
            with f_reg_col1:
                eroi_reg_filtrati = filtra_unita_per_fazione(
                    st.session_state["db_unita"], eroi_db_filtrati, f"reg_eroi_{r_idx}",
                    label_fazione="Fazione Leader", default_fazione=st.session_state["sdg_fazione_armata"]
                )
            
            lista_scelta_leader = ["--- Scegli Eroe Leader ---"] + list(eroi_reg_filtrati)
            if reg["leader"] != "--- Scegli Eroe Leader ---" and reg["leader"] not in lista_scelta_leader:
                lista_scelta_leader.append(reg["leader"])

            idx_lead = lista_scelta_leader.index(reg["leader"]) if reg["leader"] in lista_scelta_leader else 0
            reg["leader"] = lc1.selectbox(
                "Leader (Solo Eroi)", 
                lista_scelta_leader, 
                index=idx_lead, 
                key=f"reg_lead_{r_idx}_v{st.session_state['sdg_roster_version']}"
            )

            ruolo_magico_str = "Nessun Potere Arcano"
            if reg["leader"] in st.session_state["db_unita"]:
                dati_l_db = st.session_state["db_unita"][reg["leader"]]
                kw_l = dati_l_db.get("keywords", [])
                lvl_w = estrai_livello_potere(kw_l, "Wizard")
                lvl_p = estrai_livello_potere(kw_l, "Priest")
                
                pezzi_ruolo = []
                if lvl_w > 0: pezzi_ruolo.append(f"🔮 Mago ({lvl_w})")
                if lvl_p > 0: pezzi_ruolo.append(f"✨ Prete ({lvl_p})")
                if pezzi_ruolo:
                    ruolo_magico_str = " | ".join(pezzi_ruolo)

            lc2.markdown(f"**Ruolo Magico/Religioso:**\n`{ruolo_magico_str}`")

            tc1, tc2 = st.columns(2)
            with tc1:
                tratti_disp_lead = filtra_supporti_per_fazione(st.session_state["tratti_disp_lead_dict"], st.session_state["tratti_disp_lead"], f"tr_lead_{r_idx}", st.session_state["sdg_fazione_armata"])
                if reg.get("tratto_eroico", "Nessuno") not in tratti_disp_lead:
                    tratti_disp_lead.append(reg["tratto_eroico"])
                

            with tc2:
                art_disp_lead = filtra_supporti_per_fazione(st.session_state["art_disp_lead_dict"], st.session_state["art_disp_lead"], f"ar_lead_{r_idx}", st.session_state["sdg_fazione_armata"])
                if reg.get("artefatto", "Nessuno") not in art_disp_lead:
                    art_disp_lead.append(reg["artefatto"])
                
            
            idx_tratto = tratti_disp_lead.index(reg.get("tratto_eroico", "Nessuno")) if reg.get("tratto_eroico", "Nessuno") in tratti_disp_lead else 0
            reg["tratto_eroico"] = tc1.selectbox(
                "Tratto Eroico (Heroic Trait)", 
                tratti_disp_lead, 
                index=idx_tratto, 
                key=f"reg_trait_{r_idx}_v{st.session_state['sdg_roster_version']}"
            )

            idx_art = art_disp_lead.index(reg.get("artefatto", "Nessuno")) if reg.get("artefatto", "Nessuno") in art_disp_lead else 0
            reg["artefatto"] = tc2.selectbox(
                "Artefatto di Potere", 
                art_disp_lead, 
                index=idx_art, 
                key=f"reg_art_{r_idx}_v{st.session_state['sdg_roster_version']}"
            )

            if reg.get("tratto_eroico", "Nessuno") != "Nessuno":
                desc_tr = st.session_state["tratti_disp_lead_dict"].get(reg["tratto_eroico"], {}).get("descrizione", "")
                st.caption(f"✨ **{reg['tratto_eroico']}:** {desc_tr}")
            if reg.get("artefatto", "Nessuno") != "Nessuno":
                desc_ar = st.session_state["art_disp_lead_dict"].get(reg["artefatto"], {}).get("descrizione", "")
                st.caption(f"🏺 **{reg['artefatto']}:** {desc_ar}")

            if reg["leader"] in st.session_state["db_unita"]:
                d_lead = st.session_state["db_unita"][reg["leader"]]
                stat_c = d_lead.get("statistiche_cerchio", {})
                dif_lead = d_lead.get("difesa", {})
                
                mov_val = stat_c.get("movimento", "6\"")
                oc_val = stat_c.get("controllo", 2)
                sv_val = stat_c.get("save", f"{dif_lead.get('save', 5)}+")
                hp_val = stat_c.get("salute", dif_lead.get("salute_per_modello", 5))
                wd_val = stat_c.get("ward", f"{dif_lead.get('ward', 5)}+")

                pt_lead_base = d_lead.get('punti', 0)
                pt_tratto = st.session_state["tratti_disp_lead_dict"].get(reg.get("tratto_eroico", "Nessuno"), {}).get("punti", 0)
                pt_artefatto = st.session_state["art_disp_lead_dict"].get(reg.get("artefatto", "Nessuno"), {}).get("punti", 0)
                pt_lead_totale = pt_lead_base + pt_tratto + pt_artefatto
                
                str_punti = f"{pt_lead_totale} pt"
                if pt_tratto > 0 or pt_artefatto > 0:
                    str_punti += f" <small style='color:#a8977a;'>(Base {pt_lead_base} + Equip {pt_tratto + pt_artefatto})</small>"

                st.markdown(f"""
                <div class="warscroll-box">
                    <strong style="color: #f5d680;">📜 Sunto Warscroll — {reg['leader']}</strong><br>
                    <b>Punti:</b> {str_punti} | <b>Basetta:</b> {d_lead.get('dimensione_basetta', 'Standard')} | <b>Movimento:</b> {mov_val} | <b>Controllo (OC):</b> {oc_val} | <b>Save:</b> {sv_val} | <b>Salute:</b> {hp_val} | <b>Ward:</b> {wd_val}
                </div>
                """, unsafe_allow_html=True)

                abilita_leader = d_lead.get("abilita", [])
                if abilita_leader:
                    st.markdown("**Abilità della Warscroll:**")
                    for ab in abilita_leader:
                        st.markdown(render_card_abilita_wahapedia(ab), unsafe_allow_html=True)

            st.markdown("---")
            max_seguito = 4 if reg.get("is_generale", False) else 3
            st.markdown(f"**Seguito ({len(reg['seguito'])} / {max_seguito} slot occupati):**")

            sc_f, sc_add1, sc_add2 = st.columns([1.2, 2.2, 0.9])
            with sc_f:
                opzioni_seg_filtrate = filtra_unita_per_fazione(
                    st.session_state["db_unita"], opzioni_db, f"seg_u_{r_idx}",
                    label_fazione="Fazione Seguito", default_fazione=st.session_state["sdg_fazione_armata"]
                )
            unita_seg_sel = sc_add1.selectbox(
                "Aggiungi unità di seguito:", 
                ["--- Scegli unità ---"] + opzioni_seg_filtrate, 
                key=f"sel_add_seg_{r_idx}_v{st.session_state['sdg_roster_version']}"
            )
  
            if sc_add2.button("➕ Aggiungi", key=f"btn_add_seg_{r_idx}", use_container_width=True):
                if unita_seg_sel != "--- Scegli unità ---":
                    if len(reg["seguito"]) < max_seguito:
                        reg["seguito"].append({
                            "nome": unita_seg_sel,
                            "rinforzata": False,
                            "tratto_eroico": "Nessuno",
                            "artefatto": "Nessuno"
                        })
                        st.rerun()
                    else:
                        st.warning("Limite slot seguito raggiunto per questo reggimento.")

            seguito_da_rimuovere = []
            for f_idx, fol in enumerate(reg["seguito"]):
                d_fol_db = st.session_state["db_unita"].get(fol["nome"], {})
                puo_rinf = d_fol_db.get("può_essere_rinforzata", True)
                molt = 2 if fol.get("rinforzata", False) else 1
                
                pt_t_fol = st.session_state["tratti_disp_lead_dict"].get(fol.get("tratto_eroico", "Nessuno"), {}).get("punti", 0)
                pt_a_fol = st.session_state["art_disp_lead_dict"].get(fol.get("artefatto", "Nessuno"), {}).get("punti", 0)
                pt_fol_visivo = estrai_intero_sicuro(d_fol_db.get('punti', 0)) * molt + pt_t_fol + pt_a_fol

                fc1, fc2, fc3 = st.columns([3, 1.5, 0.6])
                fc1.markdown(f"• **{fol['nome']}** ({estrai_intero_sicuro(d_fol_db.get('n_modelli', 1))*molt} mod. — `{pt_fol_visivo} pt`)")
                
                if puo_rinf:
                    fol["rinforzata"] = fc2.checkbox("Rinforzata (x2)", value=fol.get("rinforzata", False), key=f"fol_rinf_{r_idx}_{f_idx}")
                else:
                    fc2.caption("Non rinforzabile")
                    fol["rinforzata"] = False

                if fc3.button("✖", key=f"del_fol_{r_idx}_{f_idx}"):
                    seguito_da_rimuovere.append(f_idx)

                kw_fol = [str(k).upper() for k in d_fol_db.get("keywords", [])]
                if "HERO" in kw_fol:
                    st.markdown("<div style='margin-top:-5px; margin-bottom:10px; padding-left:15px;'><small style='color:#d4af37;'>✨ <i>Eroe nel Seguito (Può equipaggiare Tratti e Artefatti)</i></small></div>", unsafe_allow_html=True)
                    tf_col1, tf_col2 = st.columns(2)
                    
                    opz_t_fol = list(tratti_disp_lead)
                    if fol.get("tratto_eroico", "Nessuno") not in opz_t_fol:
                        opz_t_fol.append(fol["tratto_eroico"])
                    idx_t_f = opz_t_fol.index(fol.get("tratto_eroico", "Nessuno"))
                    fol["tratto_eroico"] = tf_col1.selectbox("Tratto Eroico", opz_t_fol, index=idx_t_f, key=f"fol_trait_{r_idx}_{f_idx}_v{st.session_state['sdg_roster_version']}")
                    
                    opz_a_fol = list(art_disp_lead)
                    if fol.get("artefatto", "Nessuno") not in opz_a_fol:
                        opz_a_fol.append(fol["artefatto"])
                    idx_a_f = opz_a_fol.index(fol.get("artefatto", "Nessuno"))
                    fol["artefatto"] = tf_col2.selectbox("Artefatto", opz_a_fol, index=idx_a_f, key=f"fol_art_{r_idx}_{f_idx}_v{st.session_state['sdg_roster_version']}")

                    if fol.get("tratto_eroico", "Nessuno") != "Nessuno":
                        st.caption(f"✨ **{fol['tratto_eroico']}:** {st.session_state['tratti_disp_lead_dict'].get(fol['tratto_eroico'], {}).get('descrizione', '')}")
                    if fol.get("artefatto", "Nessuno") != "Nessuno":
                        st.caption(f"🏺 **{fol['artefatto']}:** {st.session_state['art_disp_lead_dict'].get(fol['artefatto'], {}).get('descrizione', '')}")

                stat_cf = d_fol_db.get("statistiche_cerchio", {})             
                dif_f = d_fol_db.get("difesa", {})
                m_f = stat_cf.get("movimento", "6\"")
                oc_f = stat_cf.get("controllo", 1)
                s_f = stat_cf.get("save", f"{dif_f.get('save', 6)}+")
                w_f = stat_cf.get("ward", f"{dif_f.get('ward', 5)}+")
                
                st.markdown(f"""
                <div style="font-size: 0.88rem; background: rgba(0,0,0,0.25); border-left: 2px solid #8c6d46; padding: 5px 8px; border-radius: 4px; margin-bottom: 6px;">
                    Move: <b>{m_f}</b> | OC Base: <b>{oc_f}</b> | Save: <b>{s_f}</b> | Ward: <b>{w_f}</b> | Basetta: <b>{d_fol_db.get('dimensione_basetta', 'Standard')}</b>
                </div>
                """, unsafe_allow_html=True)

            if seguito_da_rimuovere:
                for idx_f_del in sorted(seguito_da_rimuovere, reverse=True):
                    reg["seguito"].pop(idx_f_del)
                st.rerun()

    if reggimenti_da_rimuovere:
        for idx_r_del in sorted(reggimenti_da_rimuovere, reverse=True):
            st.session_state["sdg_reggimenti"].pop(idx_r_del)
        st.rerun()

    # ==========================================
    # AGGREGAZIONE DATI DELL'ARMATA (CON BONUS FORMAZIONE/TRATTI/ARTEFATTI)
    # ==========================================
    bersaglio_medio_riferimento = {
        "save": 4, "ward": 7, "salute": 20, "keywords": ["INFANTRY"],
        "cover": False, "aod": False, "bonus_save_extra": 0,
        "obscuring": False, "bersaglio_ha_caricato": False,
        "mod_ward_penalita": 0, "blocca_ward": False, "mod_wnd_nerf": 0, "mod_hit_subito": 0
    }

    def combina_bonus_unita(mod_form, nome_tratto, nome_artefatto):
        b = dict(mod_form) if isinstance(mod_form, dict) else {}
        mod_t = st.session_state["tratti_disp_lead_dict"].get(nome_tratto, {}).get("modificatori", {})
        mod_a = st.session_state["art_disp_lead_dict"].get(nome_artefatto, {}).get("modificatori", {})
        for sorgente in (mod_t, mod_a):
            if isinstance(sorgente, dict):
                for k, v in sorgente.items():
                    if not isinstance(v, (int, float)):
                        continue
                    if k in ["ward_nativo", "crit_on"]:
                        b[k] = min(b.get(k, 7), int(v))
                    else:
                        b[k] = b.get(k, 0) + int(v)
        pt_t = estrai_intero_sicuro(st.session_state["tratti_disp_lead_dict"].get(nome_tratto, {}).get("punti", 0))
        pt_a = estrai_intero_sicuro(st.session_state["art_disp_lead_dict"].get(nome_artefatto, {}).get("punti", 0))
        b["punti_equip"] = pt_t + pt_a
        return b

    unita_totali_schierate = []
    punti_totali = 0
    ferite_totali_armata = 0
    modelli_totali_armata = 0
    oc_totale_armata = 0
    livello_magico_tot = 0
    livello_preti_tot = 0
    danno_melee_armata = 0.0
    danno_tiro_armata = 0.0
    max_rend_armata = 0
    n_unita_screen_economiche = 0
    ha_generale = False
    n_eroi = 0

    for r_idx, reg in enumerate(st.session_state["sdg_reggimenti"]):
        if reg.get("is_generale", False) and reg["leader"] in st.session_state["db_unita"]:
            ha_generale = True

        if reg["leader"] in st.session_state["db_unita"]:
            n_eroi += 1
            d_u = st.session_state["db_unita"][reg["leader"]]
            bonus_lead = combina_bonus_unita(mod_formazione_attiva, reg.get("tratto_eroico", "Nessuno"), reg.get("artefatto", "Nessuno"))
            profilo_dif_lead = costruisci_bersaglio_da_db(reg["leader"], d_u, False, bonus_lead)
            
            pt_u = profilo_dif_lead["punti"]
            n_mod_u = profilo_dif_lead["n_modelli"]
            hp_u = profilo_dif_lead["salute"]
            oc_u = (estrai_intero_sicuro(d_u.get("statistiche_cerchio", {}).get("controllo", 2), default=2) + int(bonus_lead.get("bonus_controllo", 0))) * n_mod_u

            kw_u = d_u.get("keywords", [])
            livello_magico_tot += estrai_livello_potere(kw_u, "Wizard")
            livello_preti_tot += estrai_livello_potere(kw_u, "Priest")

            perf = calcola_output_unita_su_bersaglio(d_u, False, bersaglio_medio_riferimento, bonus_lead)
            punti_totali += pt_u
            ferite_totali_armata += hp_u
            modelli_totali_armata += n_mod_u
            oc_totale_armata += oc_u
            danno_melee_armata += perf["danno_melee"]
            danno_tiro_armata += perf["danno_ranged"]
            if perf["max_rend"] > max_rend_armata:
                max_rend_armata = perf["max_rend"]

            unita_totali_schierate.append({
                "etichetta": f"[Reg.{r_idx+1} Leader] {reg['leader']}",
                "chiave_db": reg["leader"],
                "rinforzata": False,
                "punti": pt_u,
                "salute": hp_u,
                "oc": oc_u,
                "danno_medio": perf["danno_totale"],
                "bonus_unita": bonus_lead,
                "profilo_difensivo": profilo_dif_lead
            })

        for fol in reg["seguito"]:
            if fol["nome"] in st.session_state["db_unita"]:
                d_f = st.session_state["db_unita"][fol["nome"]]
                rinf = bool(fol.get("rinforzata", False))
                bonus_fol = combina_bonus_unita(mod_formazione_attiva, fol.get("tratto_eroico", "Nessuno"), fol.get("artefatto", "Nessuno"))
                profilo_dif_fol = costruisci_bersaglio_da_db(fol["nome"], d_f, rinf, bonus_fol)

                pt_f = profilo_dif_fol["punti"]
                n_mod_f = profilo_dif_fol["n_modelli"]
                hp_f = profilo_dif_fol["salute"]
                oc_f = (estrai_intero_sicuro(d_f.get("statistiche_cerchio", {}).get("controllo", 1), default=1) + int(bonus_fol.get("bonus_controllo", 0))) * n_mod_f

                kw_f = d_f.get("keywords", [])
                livello_magico_tot += estrai_livello_potere(kw_f, "Wizard")
                livello_preti_tot += estrai_livello_potere(kw_f, "Priest")

                if pt_f <= 130 and n_mod_f >= 5:
                    n_unita_screen_economiche += 1

                perf_f = calcola_output_unita_su_bersaglio(d_f, rinf, bersaglio_medio_riferimento, bonus_fol)
                punti_totali += pt_f
                ferite_totali_armata += hp_f
                modelli_totali_armata += n_mod_f
                oc_totale_armata += oc_f
                danno_melee_armata += perf_f["danno_melee"]
                danno_tiro_armata += perf_f["danno_ranged"]
                if perf_f["max_rend"] > max_rend_armata:
                    max_rend_armata = perf_f["max_rend"]

                unita_totali_schierate.append({
                    "etichetta": f"[Reg.{r_idx+1}] {fol['nome']}" + (" (x2)" if rinf else ""),
                    "chiave_db": fol["nome"],
                    "rinforzata": rinf,
                    "punti": pt_f,
                    "salute": hp_f,
                    "oc": oc_f,
                    "danno_medio": perf_f["danno_totale"],
                    "bonus_unita": bonus_fol,
                    "profilo_difensivo": profilo_dif_fol
                })

    # ==========================================
    # SEZIONE 3: CRUSCOTTO E DIAGNOSI
    # ==========================================
    st.markdown('<div class="section-header">Cruscotto Tattico e Diagnosi della Lista</div>', unsafe_allow_html=True)
    st.caption("Verifica dei punti, controllo dei vincoli 4e, analisi delle sinergie e Comparatore d'Ingaggio.")

    with st.container(border=True):
        st.markdown('<div class="subsection-title">Controllo Punti e Regolamento</div>', unsafe_allow_html=True)
        perc_punti = min(1.0, punti_totali / float(limite_punti)) if limite_punti > 0 else 0.0
        st.progress(perc_punti, text=f"Punti Spesi: {punti_totali} / {limite_punti} pt ({(punti_totali/float(limite_punti))*100:.1f}%)")

        v1, v2, v3 = st.columns(3)

        n_tratti_attivi = sum(
            (1 if r.get("tratto_eroico", "Nessuno") != "Nessuno" else 0) +
            sum(1 for f in r.get("seguito", []) if f.get("tratto_eroico", "Nessuno") != "Nessuno")
            for r in st.session_state["sdg_reggimenti"]
        )
        n_artefatti_attivi = sum(
            (1 if r.get("artefatto", "Nessuno") != "Nessuno" else 0) +
            sum(1 for f in r.get("seguito", []) if f.get("artefatto", "Nessuno") != "Nessuno")
            for r in st.session_state["sdg_reggimenti"]
        )

        if n_tratti_attivi > 1 or n_artefatti_attivi > 1:
            st.warning(f"⚠️ **Nota Regolamento Matched Play:** Hai equipaggiato **{n_tratti_attivi} Tratti Eroici** e **{n_artefatti_attivi} Artefatti** (il limite standard da torneo è 1 Tratto e 1 Artefatto per armata).")
        
        if 0 < punti_totali <= limite_punti:
            v1.success(f"Punti in Regola ({punti_totali}/{limite_punti})")
        elif punti_totali > limite_punti:
            v1.error(f"Sforamento di +{punti_totali - limite_punti} pt!")
        else:
            v1.warning("Nessuna unità inserita")

        if ha_generale:
            v2.success("Generale Designato: Sì")
        else:
            v2.error("Manca il Generale!")

        n_reg_attivi = len(st.session_state["sdg_reggimenti"])
        v3.success(f"Reggimenti (Drops): {n_reg_attivi}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pool Ferite Armata", f"{ferite_totali_armata} PF", f"{modelli_totali_armata} Modelli")
    m2.metric("Danno Medio (vs Save 4+)", f"{(danno_melee_armata + danno_tiro_armata):.1f} Danni", f"Mischia: {danno_melee_armata:.1f} | Tiro: {danno_tiro_armata:.1f}")
    m3.metric("Potere Arcano", f"{livello_magico_tot} Cast / Unbind", f"{livello_preti_tot} Preghiere")
    m4.metric("Controllo Mappa (OC)", f"{oc_totale_armata} Punti OC", f"{len(unita_totali_schierate)} Unità")

    tab_diag, tab_matchup, tab_export = st.tabs([
        "Check-Up Strategico & Rendimento Unità",
        "Confronto Armate & Comparatore d'Ingaggio",
        "Salvataggio & Pergamena Torneo"
    ])

    with tab_diag:
        st.markdown('<div class="subsection-title">Rendimento Individuale delle Unità Schierate</div>', unsafe_allow_html=True)
        st.caption("Analisi di efficienza (Danno e Salute per 100 punti) di ogni unità della tua lista contro un bersaglio standard (Save 4+).")
        
        if len(unita_totali_schierate) == 0:
            st.info("Inserisci unità nei reggimenti per visualizzare la diagnosi strategica.")
        else:
            righe_rendimento = []
            for u in unita_totali_schierate:
                roi_u = (u["danno_medio"] / float(u["punti"])) * 100.0 if u["punti"] > 0 else 0.0
                hp_100 = (u["salute"] / float(u["punti"])) * 100.0 if u["punti"] > 0 else 0.0
                righe_rendimento.append({
                    "Unità": u["etichetta"],
                    "Punti": u["punti"],
                    "Salute (PF)": u["salute"],
                    "OC": u["oc"],
                    "Danno Medio (vs 4+)": round(u["danno_medio"], 2),
                    "ROI Danno / 100pt": round(roi_u, 2),
                    "PF / 100pt": round(hp_100, 1)
                })
            st.dataframe(pd.DataFrame(righe_rendimento), use_container_width=True, hide_index=True)

            with st.container(border=True):
                st.markdown("#### Avvertimenti dello Stratega e Sinergie (Analisi Keywords)")
                consigli_speciali = []

                # 1. Raccolta Keywords, Ruoli e Abilità di tutte le unità schierate
                all_kw = set()
                n_infantry = 0
                n_cavalry = 0
                n_monster = 0
                n_fly = 0
                n_ward_nativo = 0
                eroi_schierati = []
                truppe_schierate = []

                for u in unita_totali_schierate:
                    d_db = st.session_state["db_unita"].get(u["chiave_db"], {})
                    # Normalizza keywords (gestisce anche stringhe unite come "INFANTRY CHAOS")
                    kws_raw = d_db.get("keywords", [])
                    kws = set()
                    for k in kws_raw:
                        for token in str(k).upper().replace(",", " ").split():
                            kws.add(token)
                        kws.add(str(k).upper().strip())
                    all_kw.update(kws)

                    is_hero = "HERO" in kws
                    if is_hero:
                        eroi_schierati.append((u["etichetta"], d_db, kws))
                    else:
                        truppe_schierate.append((u["etichetta"], d_db, kws))

                    if "INFANTRY" in kws and not is_hero:
                        n_infantry += 1
                    if "CAVALRY" in kws:
                        n_cavalry += 1
                    if "MONSTER" in kws:
                        n_monster += 1
                    if "FLY" in kws:
                        n_fly += 1
                    if u["profilo_difensivo"]["ward"] <= 6 or any("WARD" in k for k in kws):
                        n_ward_nativo += 1

                # 2. Analisi Sinergie Automatiche dalle Abilità delle Warscrolls in campo
                for u in unita_totali_schierate:
                    d_db = st.session_state["db_unita"].get(u["chiave_db"], {})
                    nome_breve = u["chiave_db"].split(": ")[-1]
                    for ab in d_db.get("abilita", []):
                        desc_up = ab.get("descrizione", "").upper()
                        nome_ab = ab.get("nome", "Abilità")

                        # Sinergie verso INFANTRY amica
                        if "FRIENDLY" in desc_up and "INFANTRY" in desc_up:
                            if n_infantry > 0:
                                consigli_speciali.append(f"**Sinergia Keyword [INFANTRY] ({nome_breve} — *{nome_ab}*):** Quest'abilità potenzia o supporta le tue **{n_infantry} unità di Fanteria** in lista. Mantienile entro il raggio dell'aura.")
                            else:
                                consigli_speciali.append(f"**Sinergia Inutilizzata ({nome_breve} — *{nome_ab}*):** Quest'abilità richiede unità amiche **INFANTRY** (non-Eroe), ma non ne hai schierate nella lista!")

                        # Sinergie specifiche BLOODBOUND (Blades of Khorne)
                        if "BLOODBOUND" in desc_up and "FRIENDLY" in desc_up:
                            if "STRIKE-FIRST" in desc_up:
                                eroi_bb = [e[0] for e in eroi_schierati if "BLOODBOUND" in e[2] and nome_breve not in e[0]]
                                if eroi_bb:
                                    consigli_speciali.append(f"**Combo Strike-First ({nome_breve} — *{nome_ab}*):** Puoi conferire *Strike-First* a un altro Eroe **BLOODBOUND** in lista ({', '.join(eroi_bb)}). Falli caricare insieme!")
                                else:
                                    consigli_speciali.append(f"**Bersaglio Mancante ({nome_breve} — *{nome_ab}*):** Richiede un altro **BLOODBOUND INFANTRY HERO** entro 12\" per attivare *Strike-First*, ma non hai altri eroi compatibili.")
                            elif "+1" in desc_up or "ADD 1" in desc_up:
                                consigli_speciali.append(f"**Moltiplicatore di Forza [BLOODBOUND] ({nome_breve} — *{nome_ab}*):** Potenzia gli attacchi o i tiri per ferire delle tue unità con keyword **BLOODBOUND**.")

                        # Sinergie Anti-Cura / Blocco Rally
                        if "CANNOT BE HEALED" in desc_up:
                            consigli_speciali.append(f"**Blocco Rigenerazione ({nome_breve} — *{nome_ab}*):** Impedisce cure e resurrezioni nemiche in mischia. Mandalo contro bersagli che si rigenerano o evocano modelli.")

                # 3. Analisi Tattica per Keywords di Fazione e Struttura Armata
                if "NIGHTHAUNT" in all_kw:
                    if n_fly == len(unita_totali_schierate):
                        consigli_speciali.append("**Armata Spettrale Volante [FLY + ETHEREAL]:** Tutte le tue unità ignorano il Rend nemico e scavalcano schermi e terreni. Usa la mobilità per isolare i supporti avversari.")
                    if any("Spirit Hosts" in u["chiave_db"] for u in unita_totali_schierate) and len(eroi_schierati) > 0:
                        consigli_speciali.append("**Scudo Corporale [INFANTRY HERO]:** Gli *Spirit Hosts* forniscono **Ward (4+)** ai tuoi Eroi di fanteria Nighthaunt entro il raggio di combattimento.")

                if "BLADES OF KHORNE" in all_kw or "KHORNE" in all_kw:
                    if len(eroi_schierati) >= 3 and len(truppe_schierate) == 0:
                        consigli_speciali.append("**Assetto Herohammer [SOLO HERO]:** Hai schierato esclusivamente Eroi. Alto output offensivo, ma **basso Controllo Mappa (OC)** e vulnerabilità alle cariche di orda: sfrutta i terreni per non farti circondare.")
                    if any("PRIEST" in k for k in all_kw):
                        consigli_speciali.append("**Sinergia Rituale [PRIEST]:** Hai Sacerdoti in campo per accumulare punti rituali e contrastare la magia nemica.")

                if "KRULEBOYZ" in all_kw:
                    unita_crit_mortal = [u["etichetta"] for u in unita_totali_schierate if any(a.get("crit_type") == "Crit (Mortal)" for a in st.session_state["db_unita"].get(u["chiave_db"], {}).get("armi", []))]
                    if unita_crit_mortal:
                        consigli_speciali.append(f"**Veleno Mortale [CRIT (MORTAL)]:** Le unità {', '.join(unita_crit_mortal)} infliggono Danni Mortali sui colpi critici. Ideali per abbattere nemici con Save 2+/3+.")

                if "SYLVANETH" in all_kw:
                    if "MONSTER" in all_kw:
                        consigli_speciali.append("**Presenza Boschiva [MONSTER]:** Hai unità **MONSTER** in lista in grado di usare le abilità *Rampage* e assorbire le cariche centrali.")

                # 4. Check-up Globale dei Ruoli (Mobilità, Magia, Rend, Resilienza)
                if n_cavalry == 0 and n_fly == 0:
                    consigli_speciali.append("**Bassa Mobilità Tattica (Nessun [CAVALRY] o [FLY]):** L'armata si muove interamente a piedi. Rischi di subire l'iniziativa sugli obiettivi laterali; tieni da parte 1 CP per *At the Double* (Corsa +6\").")

                if n_ward_nativo == 0:
                    consigli_speciali.append("**Vulnerabilità ai Danni Mortali (Nessun [WARD]):** Nessuna unità possiede un tiro Ward attivo. Fai estrema attenzione a magie, preghiere e armi con *Crit (Mortal)*.")

                if max_rend_armata < 2:
                    consigli_speciali.append("**Penetrazione Armatura Limitata (Rend < 2):** Contro bersagli corazzati (Save 2+/3+) farai fatica a passare l'armatura. Sfrutta i bonus di Formazione o le armi con *Crit (Mortal)*.")

                if livello_magico_tot == 0 and livello_preti_tot == 0:
                    consigli_speciali.append("**Assenza di [WIZARD] e [PRIEST]:** Non hai modo di dissipare incantesimi (*Unbind*) o bandire manifestazioni nemiche, a meno di abilità speciali o artefatti.")

                # Rimuove eventuali duplicati mantenendo l'ordine
                consigli_unici = list(dict.fromkeys(consigli_speciali))
                for cs in consigli_unici:
                    st.markdown(f"- {cs}")

    # ==========================================
    # TAB 2: MATRICE MATCH-UP E COMPARATORE DIRETTO (B vs A)
    # ==========================================
    with tab_matchup:
        st.markdown('<div class="subsection-title">1. Schieramento dell\'Armata Nemica</div>', unsafe_allow_html=True)
        st.caption("Scegli un'armata preconfigurata, un'intera fazione dal DB o aggiungi singole unità nemiche.")

        with st.container(border=True):
            im1, im2 = st.columns([2.5, 1])
            opzioni_import_nemici = (
                ["--- Scegli armata o fazione nemica ---"]
                + list(ARMATE_NEMICHE_NOTE.keys())
                + ["[Fazione DB] Nighthaunt", "[Fazione DB] Blades of Khorne", "[Fazione DB] Orruk Kruleboyz", "[Fazione DB] Sylvaneth"]
                + [f"[Archivio] {k}" for k in armate_salvate]
            )
            scelta_armata_nota = im1.selectbox("Importa Schieramento Avversario:", opzioni_import_nemici, key="sel_preset_nemico")
            if im2.button("📥 Sostituisci e Importa Nemici", type="primary", use_container_width=True):
                if scelta_armata_nota in ARMATE_NEMICHE_NOTE:
                    st.session_state["sdg_nemici_matchup"] = [
                        dict(x) for x in ARMATE_NEMICHE_NOTE[scelta_armata_nota]
                        if x["nome"] in st.session_state["db_unita"]
                    ]
                    mostra_toast_rapido(f"Armata nemica '{scelta_armata_nota}' caricata!", "✅")
                    st.rerun()
                elif scelta_armata_nota.startswith("[Fazione DB] "):
                    faz_target = scelta_armata_nota.replace("[Fazione DB] ", "").strip()
                    st.session_state["sdg_nemici_matchup"] = [
                        {"nome": k_u, "rinforzata": False}
                        for k_u in opzioni_db
                        if st.session_state["db_unita"].get(k_u, {}).get("fazione") == faz_target or k_u.startswith(f"{faz_target}:")
                    ]
                    mostra_toast_rapido(f"Tutte le unità {faz_target} caricate come nemici!", "✅")
                    st.rerun()
                elif scelta_armata_nota.startswith("[Archivio] "):
                    k_arch = scelta_armata_nota.replace("[Archivio] ", "")
                    dati_arc_nem = st.session_state["archivio_armate"].get(k_arch, {})
                    nemici_estratti = []
                    for r_nem in dati_arc_nem.get("reggimenti", []):
                        if r_nem.get("leader") in st.session_state["db_unita"]:
                            nemici_estratti.append({"nome": r_nem["leader"], "rinforzata": False})
                        for f_nem in r_nem.get("seguito", []):
                            if f_nem.get("nome") in st.session_state["db_unita"]:
                                nemici_estratti.append({"nome": f_nem["nome"], "rinforzata": bool(f_nem.get("rinforzata", False))})
                    st.session_state["sdg_nemici_matchup"] = nemici_estratti
                    mostra_toast_rapido(f"Roster '{k_arch}' importato come avversario!", "✅")
                    st.rerun()

            st.markdown("---")
            mc0, mc1, mc2, mc3 = st.columns([1.2, 2.0, 0.9, 0.9])
            with mc0:
                opzioni_nem_filtrate = filtra_unita_per_fazione(st.session_state["db_unita"], opzioni_db, "mu_enemy", label_fazione="Filtra Fazione Nemico")
            nemico_sel = mc1.selectbox("Aggiungi singola unità nemica:", ["--- Scegli unità nemica dal DB ---"] + opzioni_nem_filtrate, key="sel_enemy_mu")
            nemico_rinf = mc2.checkbox("Rinforzata (x2)", value=False, key="chk_enemy_rinf")
            if mc3.button("➕ Aggiungi Nemico", use_container_width=True):
                if nemico_sel != "--- Scegli unità nemica dal DB ---":
                    st.session_state["sdg_nemici_matchup"].append({"nome": nemico_sel, "rinforzata": nemico_rinf})
                    st.rerun()

            if st.session_state["sdg_nemici_matchup"]:
                nem_str_list = [f"{i+1}. {n['nome']}" + (" (x2)" if n["rinforzata"] else "") for i, n in enumerate(st.session_state["sdg_nemici_matchup"])]
                st.markdown("**🔴 Forze Avversarie Attualmente in Campo:** " + " | ".join(nem_str_list))
                if st.button("🗑️ Svuota Armata Nemica"):
                    st.session_state["sdg_nemici_matchup"] = []
                    st.rerun()

        nemici_validi = [
            n for n in st.session_state["sdg_nemici_matchup"]
            if n.get("nome") in st.session_state["db_unita"]
        ]

        if len(unita_totali_schierate) > 0 and len(nemici_validi) > 0:
            nemici_elaborati = []
            for n_idx, nem_item in enumerate(nemici_validi):
                d_nem = st.session_state["db_unita"][nem_item["nome"]]
                rinf_n = bool(nem_item.get("rinforzata", False))
                prof_dif_n = costruisci_bersaglio_da_db(nem_item["nome"], d_nem, rinf_n)
                perf_n_base = calcola_output_unita_su_bersaglio(d_nem, rinf_n, bersaglio_medio_riferimento)
                nemici_elaborati.append({
                    "etichetta": f"[Nem.{n_idx+1}] {nem_item['nome']}" + (" (x2)" if rinf_n else ""),
                    "chiave_db": nem_item["nome"],
                    "dati_db": d_nem,
                    "rinforzata": rinf_n,
                    "profilo_difensivo": prof_dif_n,
                    "danno_medio": perf_n_base["danno_totale"]
                })

            # --- RIEPILOGO FRONTE A FRONTE DELLE DUE ARMATE ---
            st.markdown('<div class="subsection-title">2. Bilancio Complessivo tra le Due Armate</div>', unsafe_allow_html=True)
            pt_nem_tot = sum(n["profilo_difensivo"]["punti"] for n in nemici_elaborati)
            hp_nem_tot = sum(n["profilo_difensivo"]["salute"] for n in nemici_elaborati)
            dmg_nem_tot = sum(n["danno_medio"] for n in nemici_elaborati)
            dmg_mio_tot = danno_melee_armata + danno_tiro_armata

            ca1, ca2, ca3 = st.columns(3)
            ca1.metric("Punti Schierati (Tu vs Nemico)", f"{punti_totali} vs {pt_nem_tot} pt", f"{punti_totali - pt_nem_tot:+d} pt")
            ca2.metric("Pool Ferite (Tu vs Nemico)", f"{ferite_totali_armata} vs {hp_nem_tot} PF", f"{ferite_totali_armata - hp_nem_tot:+d} PF")
            ca3.metric("Danno Medio vs Save 4+", f"{dmg_mio_tot:.1f} vs {dmg_nem_tot:.1f}", f"{dmg_mio_tot - dmg_nem_tot:+.1f} Danni")

            # --- MATRICE OFFENSIVA E DIFENSIVA ---
            st.markdown('<div class="subsection-title">3. Matrici Incrociate (Attacco & Rischio Contrattacco)</div>', unsafe_allow_html=True)
            matrice_attacco = {}
            matrice_rischio = {}

            for nem in nemici_elaborati:
                col_att = []
                col_ris = []
                for mia_u in unita_totali_schierate:
                    d_mia = st.session_state["db_unita"][mia_u["chiave_db"]]
                    ris_att = calcola_output_unita_su_bersaglio(d_mia, mia_u["rinforzata"], nem["profilo_difensivo"], mia_u["bonus_unita"], ha_caricato=True)
                    perc_inflitta = min(100.0, (ris_att["danno_totale"] / float(nem["profilo_difensivo"]["salute"])) * 100.0)
                    col_att.append(round(perc_inflitta, 1))

                    ris_sub = calcola_output_unita_su_bersaglio(nem["dati_db"], nem["rinforzata"], mia_u["profilo_difensivo"], ha_caricato=True)
                    perc_subita = min(100.0, (ris_sub["danno_totale"] / float(mia_u["salute"])) * 100.0)
                    col_ris.append(round(perc_subita, 1))

                matrice_attacco[nem["etichetta"]] = col_att
                matrice_rischio[nem["etichetta"]] = col_ris

            c_mat1, c_mat2 = st.columns(2)
            with c_mat1:
                st.markdown("**🗡️ % Salute Nemica Rimossa (Tu Carichi)**")
                df_att = pd.DataFrame(matrice_attacco, index=[u["etichetta"] for u in unita_totali_schierate])
                st.dataframe(df_att.style.background_gradient(cmap="YlGn", vmin=0, vmax=100).format("{:.1f}%"), use_container_width=True)
            with c_mat2:
                st.markdown("**🛡️ % Tua Salute Persa (Se il Nemico Carica Te)**")
                df_ris = pd.DataFrame(matrice_rischio, index=[u["etichetta"] for u in unita_totali_schierate])
                st.dataframe(df_ris.style.background_gradient(cmap="OrRd", vmin=0, vmax=100).format("{:.1f}%"), use_container_width=True)

            # --- COMPARATORE DETTAGLIATO D'INGAGGIO 1v1 (VALE LA PENA INGAGGIARE?) ---
            st.markdown("---")
            st.markdown('<div class="subsection-title">4. Simulatore di Duello & Convenienza d\'Ingaggio</div>', unsafe_allow_html=True)
            st.caption("Analisi completa di scambio: calcola i modelli nemici uccisi nel primo impatto, il contrattacco dei modelli superstiti e il rapporto tra punti neutralizzati e punti persi.")

            with st.container(border=True):
                duel_c1, duel_c2 = st.columns(2)
                hash_mie = len(unita_totali_schierate)
                hash_nem = len(nemici_elaborati)

                scelta_mia_idx = duel_c1.selectbox(
                    "Scegli la Tua Unità Attaccante:",
                    range(len(unita_totali_schierate)),
                    format_func=lambda i: f"{unita_totali_schierate[i]['etichetta']} ({unita_totali_schierate[i]['punti']} pt | {unita_totali_schierate[i]['salute']} PF)",
                    key=f"duel_sel_mia_{hash_mie}"
                )
                scelta_nem_idx = duel_c2.selectbox(
                    "Scegli l'Unità Bersaglio Nemica:",
                    range(len(nemici_elaborati)),
                    format_func=lambda i: f"{nemici_elaborati[i]['etichetta']} ({nemici_elaborati[i]['profilo_difensivo']['punti']} pt | {nemici_elaborati[i]['profilo_difensivo']['salute']} PF)",
                    key=f"duel_sel_nem_{hash_nem}"
                )

                opt_c1, opt_c2, opt_c3, opt_c4 = st.columns(4)
                mia_carica = opt_c1.checkbox("Tua Unità ha Caricato", value=True, key="duel_mia_chg")
                mia_aoa = opt_c2.checkbox("Tu usi All-out Attack (+1 Hit)", value=False, key="duel_mia_aoa")
                nem_aod = opt_c3.checkbox("Nemico usa All-out Defence (+1 Save)", value=False, key="duel_nem_aod")
                mia_aod = opt_c4.checkbox("Tu usi All-out Defence (+1 Save)", value=False, key="duel_mia_aod")
                
                mia_sel = unita_totali_schierate[scelta_mia_idx]
                nem_sel = nemici_elaborati[scelta_nem_idx]
                d_mia_db = st.session_state["db_unita"][mia_sel["chiave_db"]]
                d_nem_db = nem_sel["dati_db"]

                bonus_miei_duello = dict(mia_sel["bonus_unita"])
                if mia_aoa:
                    bonus_miei_duello["mod_hit"] = bonus_miei_duello.get("mod_hit", 0) + 1

                prof_dif_nem_duello = dict(nem_sel["profilo_difensivo"])
                prof_dif_nem_duello["aod"] = nem_aod
                prof_dif_nem_duello["bersaglio_ha_caricato"] = (not mia_carica)

                prof_dif_mio_duello = dict(mia_sel["profilo_difensivo"])
                prof_dif_mio_duello["aod"] = mia_aod
                prof_dif_mio_duello["bersaglio_ha_caricato"] = mia_carica

                # --- SCENARIO A: TU ATTACCHI PER PRIMO, I SUPERSTITI NEMICI CONTRATTACCANO ---
                out_mio_1 = calcola_output_unita_su_bersaglio(d_mia_db, mia_sel["rinforzata"], prof_dif_nem_duello, bonus_miei_duello, ha_caricato=mia_carica)
                danno_mio_inflitto = out_mio_1["danno_totale"]
                
                hp_per_mod_nem = prof_dif_nem_duello["salute_per_modello"]
                modelli_nem_uccisi = min(prof_dif_nem_duello["n_modelli"], int(danno_mio_inflitto // hp_per_mod_nem))
                modelli_nem_superstiti = max(0, prof_dif_nem_duello["n_modelli"] - modelli_nem_uccisi)
                if danno_mio_inflitto >= prof_dif_nem_duello["salute"]:
                    modelli_nem_superstiti = 0

                out_contrattacco_nem = calcola_output_unita_su_bersaglio(
                    d_nem_db, nem_sel["rinforzata"], prof_dif_mio_duello,
                    ha_caricato=False, n_modelli_override=modelli_nem_superstiti
                )
                danno_subito_contrattacco = out_contrattacco_nem["danno_melee"]
                hp_per_mod_mio = prof_dif_mio_duello["salute_per_modello"]
                miei_modelli_persi = min(prof_dif_mio_duello["n_modelli"], int(danno_subito_contrattacco // hp_per_mod_mio))

                perc_nem_rimossa = min(1.0, danno_mio_inflitto / float(prof_dif_nem_duello["salute"]))
                perc_mia_persa = min(1.0, danno_subito_contrattacco / float(prof_dif_mio_duello["salute"]))
                pt_nem_neutralizzati = prof_dif_nem_duello["punti"] * perc_nem_rimossa
                pt_miei_persi = mia_sel["punti"] * perc_mia_persa
                bilancio_netto_pt = pt_nem_neutralizzati - pt_miei_persi

                # --- SCENARIO B: IL NEMICO TI CARICA E COLPISCE PER PRIMO ---
                out_nem_carica = calcola_output_unita_su_bersaglio(d_nem_db, nem_sel["rinforzata"], prof_dif_mio_duello, ha_caricato=True)
                danno_nem_se_carica = out_nem_carica["danno_totale"]
                perc_mia_persa_se_caricato = min(1.0, danno_nem_se_carica / float(prof_dif_mio_duello["salute"]))

                st.markdown("---")
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Tuo Danno Inflitto", f"{danno_mio_inflitto:.1f} / {prof_dif_nem_duello['salute']} PF", f"{perc_nem_rimossa*100:.0f}% vita nemica")
                if prof_dif_nem_duello["n_modelli"] == 1:
                    hp_restanti_eroe = max(0.0, float(prof_dif_nem_duello["salute"]) - danno_mio_inflitto)
                    k2.metric("Stato Bersaglio Singolo", f"{hp_restanti_eroe:.1f} PF rimasti", "Eliminato!" if hp_restanti_eroe == 0 else "Ancora attivo")
                else:
                    k2.metric("Modelli Nemici Uccisi", f"{modelli_nem_uccisi} / {prof_dif_nem_duello['n_modelli']} mod.", f"{modelli_nem_superstiti} superstiti")
                k3.metric("Danno Subito al Contrattacco", f"{danno_subito_contrattacco:.1f} / {mia_sel['salute']} PF", f"-{miei_modelli_persi} tuoi modelli")
                k4.metric(
                    "Convenienza Scambio (Punti)", 
                    f"{bilancio_netto_pt:+.0f} pt netti", 
                    f"Neutralizzi {pt_nem_neutralizzati:.0f}pt | Perdi {pt_miei_persi:.0f}pt",
                    help="Differenza tra il valore in punti di vita che togli al nemico e il valore in punti di vita che perdi tu nel suo contrattacco. Se è positivo (+), lo scambio è a tuo favore."
                )

                if modelli_nem_superstiti == 0:
                    st.success(f"🟢 **INGAGGIO PERFETTO (Wipeout al Primo Colpo):** Spazzi via completamente **{nem_sel['etichetta']}** prima che possa contrattaccare! Subisci **0 danni** di risposta e neutralizzi **{prof_dif_nem_duello['punti']} pt** nemici.")
                elif bilancio_netto_pt >= 25 and perc_mia_persa < 0.65:
                    st.success(f"🟢 **INGAGGIO CONSIGLIATO (Scambio Positivo: {bilancio_netto_pt:+.0f} pt):** Uccidi **{modelli_nem_uccisi} modelli** nemici riducendo la loro risposta a **{danno_subito_contrattacco:.1f} danni**. Esci dallo scontro in netto vantaggio economico e di sopravvivenza.")
                elif bilancio_netto_pt >= -15 and perc_mia_persa < 0.75:
                    st.info(f"🟡 **INGAGGIO DI LOGORAMENTO EQUILIBRATO ({bilancio_netto_pt:+.0f} pt):** Lo scontro è bilanciato. Togli il **{perc_nem_rimossa*100:.0f}%** di vita al nemico e subisci il **{perc_mia_persa*100:.0f}%** al contrattacco. Ingaggia se ti serve contendere l'obiettivo o se hai un supporto/buff aggiuntivo.")
                else:
                    st.error(f"🔴 **SCONSIGLIATO DA SOLO (Scambio Negativo: {bilancio_netto_pt:+.0f} pt):** Anche colpendo per primo, lasceresti in vita **{modelli_nem_superstiti} modelli** nemici che ti infliggerebbero **{danno_subito_contrattacco:.1f} danni** ({perc_mia_persa*100:.0f}% della tua salute). Non caricare frontalmente senza prima indebolire il bersaglio con magie, tiro o una carica combinata!")

                if perc_mia_persa_se_caricato >= 0.80:
                    st.warning(f"⚠️ **Attenzione al Posizionamento (Minaccia di Carica Nemica):** Se è **{nem_sel['etichetta']}** a caricare te per primo, infligge **{danno_nem_se_carica:.1f} danni** ({perc_mia_persa_se_caricato*100:.0f}% della tua vita) rischiando di distruggerti prima che tu possa combattere! Mantieni la distanza di sicurezza o usa uno schermo.")
        else:
            st.info("Schiera almeno un'unità nella tua armata e importa (o aggiungi) almeno un'unità nemica per attivare le Matrici e il Simulatore di Duello.")

    # ==========================================
    # TAB 3: SALVATAGGIO E ESPORTAZIONE
    # ==========================================
    with tab_export:
        st.markdown('<div class="subsection-title">Salvataggio & Esportazione Torneo</div>', unsafe_allow_html=True)
        st.caption("Salva l'armata nell'archivio JSON o copia il testo formattato per i tornei Path to Glory.")

        with st.container(border=True):
            if "conferma_sovrascrittura_armata" not in st.session_state:
                st.session_state["conferma_sovrascrittura_armata"] = False

            nome_lista_pulito = st.session_state['sdg_nome_armata'].strip()
            chiave_armata = f"{st.session_state['sdg_fazione_armata']}: {nome_lista_pulito}"
            payload_armata = {
                "nome": nome_lista_pulito,
                "fazione": st.session_state["sdg_fazione_armata"],
                "formazione": st.session_state["sdg_formazione_scelta"],
                "limite_punti": limite_punti,
                "punti_totali": punti_totali,
                "reggimenti": st.session_state["sdg_reggimenti"],
                "ausiliari": st.session_state["sdg_ausiliari"]
            }

            if st.button("💾 Salva Armata nell'Archivio", type="primary"):
                if chiave_armata in st.session_state["archivio_armate"]:
                    st.session_state["conferma_sovrascrittura_armata"] = True
                else:
                    st.session_state["archivio_armate"][chiave_armata] = payload_armata
                    salva_archivio_armate(st.session_state["archivio_armate"])
                    st.session_state["conferma_sovrascrittura_armata"] = False
                    mostra_toast_rapido(f"Armata '{chiave_armata}' salvata con successo!", "✅")
                    st.rerun()

            if st.session_state.get("conferma_sovrascrittura_armata", False):
                st.warning(f"⚠️ Esiste già un'armata salvata con il nome **'{chiave_armata}'**. Vuoi sovrascriverla o salvarla come una nuova lista?")
                col_ov1, col_ov2, col_ov3 = st.columns(3)
                
                if col_ov1.button("🔄 Sovrascrivi Esistente", type="primary", use_container_width=True):
                    st.session_state["archivio_armate"][chiave_armata] = payload_armata
                    salva_archivio_armate(st.session_state["archivio_armate"])
                    st.session_state["conferma_sovrascrittura_armata"] = False
                    mostra_toast_rapido(f"Armata '{chiave_armata}' sovrascritta con successo!", icon="✅")
                    st.rerun()
                    
                if col_ov2.button("✨ Crea Copia con Nuovo Nome", use_container_width=True):
                    contatore = 2
                    while f"{chiave_armata} ({contatore})" in st.session_state["archivio_armate"]:
                        contatore += 1
                    nuovo_nome = f"{nome_lista_pulito} ({contatore})"
                    nuova_chiave = f"{st.session_state['sdg_fazione_armata']}: {nuovo_nome}"
                    payload_armata["nome"] = nuovo_nome
                    st.session_state["sdg_nome_armata"] = nuovo_nome
                    st.session_state["archivio_armate"][nuova_chiave] = payload_armata
                    salva_archivio_armate(st.session_state["archivio_armate"])
                    st.session_state["conferma_sovrascrittura_armata"] = False
                    st.session_state["sdg_roster_version"] += 1
                    mostra_toast_rapido(f"Creata nuova lista '{nuova_chiave}'!", "✅")
                    st.rerun()
                    
                if col_ov3.button("✖ Annulla", use_container_width=True):
                    st.session_state["conferma_sovrascrittura_armata"] = False
                    st.rerun()

            linee_export = [
                f"=== {st.session_state['sdg_nome_armata'].upper()} ===",
                f"Fazione: {st.session_state['sdg_fazione_armata']} | Formazione: {st.session_state['sdg_formazione_scelta']}",
                f"Punti Totali: {punti_totali} / {limite_punti} pt | Reggimenti: {len(st.session_state['sdg_reggimenti'])}",
                f"Ferite Totali: {ferite_totali_armata} PF | Controllo: {oc_totale_armata} OC",
                "-" * 55
            ]

            for r_i, reg in enumerate(st.session_state["sdg_reggimenti"]):
                gen_tag = " [GENERALE]" if reg.get("is_generale", False) else ""
                d_l = st.session_state["db_unita"].get(reg["leader"], {})
                
                nome_t = reg.get("tratto_eroico", "Nessuno")
                nome_a = reg.get("artefatto", "Nessuno")
                pt_t = st.session_state["tratti_disp_lead_dict"].get(nome_t, {}).get("punti", 0)
                pt_a = st.session_state["art_disp_lead_dict"].get(nome_a, {}).get("punti", 0)
                pt_l_tot = estrai_intero_sicuro(d_l.get('punti', 0)) + pt_t + pt_a
                
                linee_export.append(f"\nREGGIMENTO {r_i+1}:")
                linee_export.append(f"  • Leader: {reg['leader']}{gen_tag} ({pt_l_tot} pt)")
                if nome_t != "Nessuno":
                    linee_export.append(f"    - Tratto: {nome_t} ({pt_t} pt)")
                if nome_a != "Nessuno":
                    linee_export.append(f"    - Artefatto: {nome_a} ({pt_a} pt)")
                
                for fol in reg["seguito"]:
                    d_f = st.session_state["db_unita"].get(fol["nome"], {})
                    molt = 2 if fol.get("rinforzata", False) else 1
                    rinf_str = " [Rinforzata]" if fol.get("rinforzata", False) else ""
                    
                    nome_t_f = fol.get("tratto_eroico", "Nessuno")
                    nome_a_f = fol.get("artefatto", "Nessuno")
                    pt_t_f = st.session_state["tratti_disp_lead_dict"].get(nome_t_f, {}).get("punti", 0)
                    pt_a_f = st.session_state["art_disp_lead_dict"].get(nome_a_f, {}).get("punti", 0)
                    pt_f_base = estrai_intero_sicuro(d_f.get('punti', 0)) * molt
                    pt_f_tot = pt_f_base + pt_t_f + pt_a_f
                    
                    linee_export.append(f"  • Seguito: {fol['nome']}{rinf_str} ({pt_f_tot} pt)")
                    if nome_t_f != "Nessuno":
                        linee_export.append(f"    - Tratto: {nome_t_f} ({pt_t_f} pt)")
                    if nome_a_f != "Nessuno":
                        linee_export.append(f"    - Artefatto: {nome_a_f} ({pt_a_f} pt)")

            testo_completo_export = "\n".join(linee_export)
            st.text_area("Pergamena dell'Esercito:", value=testo_completo_export, height=300)

            st.download_button(
                label="📜 Scarica Pergamena Torneo (.txt)",
                data=testo_completo_export,
                file_name=f"{st.session_state['sdg_nome_armata'].replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True
            )