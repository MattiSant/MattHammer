import streamlit as st
import numpy as np
import pandas as pd
import json
import os
from core_engine import (
    calcola_arma_analitico,
    _push_su_github_file,
    ordina_unita_per_fazione_e_nome
)
from utils import (
    estrai_valore_keyword,
    estrai_livello_potere,
    estrai_intero_sicuro
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARMIES_DB_FILE = os.path.join(BASE_DIR, "armies_db.json")
FORMATIONS_DB_FILE = os.path.join(BASE_DIR, "formations.json")
TRAITS_DB_FILE = os.path.join(BASE_DIR, "heroic_traits_db.json")
ARTEFACTS_DB_FILE = os.path.join(BASE_DIR, "artefacts_db.json")

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
    ]
}

def costruisci_bersaglio_da_db(nome_unita, dati_u_db, rinforzata=False, bonus_extra=None):
    bonus_extra = bonus_extra or {}
    dif = dati_u_db.get("difesa", {})
    stat = dati_u_db.get("statistiche_cerchio", {})
    molt = 2 if rinforzata else 1

    sv = estrai_intero_sicuro(stat.get("save", dif.get("save", 4)), default=4)
    wd = estrai_intero_sicuro(stat.get("ward", dif.get("ward", 7)), default=7)
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
        "cover": False, "aod": False, "bonus_save_extra": int(bonus_extra.get("bonus_save", 0)),
        "obscuring": False, "bersaglio_ha_caricato": False,
        "mod_ward_penalita": 0, "blocca_ward": False, "mod_wnd_nerf": 0,
        "mod_hit_subito": int(bonus_extra.get("mod_hit_subito", 0)),
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
        "mod_hit": int(bonus_attaccante.get("mod_hit", 0)) + int(bersaglio_test.get("mod_hit_subito", 0)),
        "mod_wnd": int(bonus_attaccante.get("mod_wnd", 0)),
        "bonus_atk": int(bonus_attaccante.get("bonus_atk", 0)),
        "bonus_rend": int(bonus_attaccante.get("bonus_rend", 0)),
        "bonus_dmg": int(bonus_attaccante.get("bonus_dmg", 0)),
        "crit_on": 5 if bonus_attaccante.get("crit_on") == 5 else 6,
        "bersaglio_ha_caricato": bersaglio_test.get("bersaglio_ha_caricato", False)
    }

    danno_melee = 0.0
    danno_ranged = 0.0
    max_rend = 0
    attacchi_tot = 0.0

    for a in armi:
        if a.get("attiva", False) and str(a.get("hit", "---")) != "---":
            ris = calcola_arma_analitico(a, mod_glob, bersaglio_test)
            if a.get("ranged", False):
                danno_ranged += ris["danno_netto"]
            else:
                danno_melee += ris["danno_netto"]
            attacchi_tot += ris["attacchi"]
            r_val = estrai_intero_sicuro(a.get("rend", 0), default=0) + int(bonus_attaccante.get("bonus_rend", 0))
            if r_val > max_rend:
                max_rend = r_val

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
        /* Box Abilità Passive / Normali: bronzo satinato */
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
        /* Box Reazioni: cremisi regale e rubino */
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
    
    if "db_tratti_eroici_dict" not in st.session_state:
        st.session_state["db_tratti_eroici_dict"] = carica_db_supporto_dict(TRAITS_DB_FILE)
        st.session_state["db_tratti_eroici"] = list(st.session_state["db_tratti_eroici_dict"].keys())

    if "db_artefatti_dict" not in st.session_state:
        st.session_state["db_artefatti_dict"] = carica_db_supporto_dict(ARTEFACTS_DB_FILE)
        st.session_state["db_artefatti"] = list(st.session_state["db_artefatti_dict"].keys())

    db_tratti_eroici = st.session_state["db_tratti_eroici"]
    db_artefatti = st.session_state["db_artefatti"]

    if "sdg_nome_armata" not in st.session_state:
        st.session_state["sdg_nome_armata"] = "Armata Path to Glory"
    if "sdg_fazione_armata" not in st.session_state:
        st.session_state["sdg_fazione_armata"] = "Nighthaunt"
    if "sdg_formazione_scelta" not in st.session_state:
        st.session_state["sdg_formazione_scelta"] = "Death Stalkers"

    opzioni_db = ordina_unita_per_fazione_e_nome(st.session_state["db_unita"])

    # ==========================================
    # CARICAMENTO ARMATA ESISTENTE
    # ==========================================
    armate_salvate = list(st.session_state["archivio_armate"].keys())
    if armate_salvate:
        with st.expander("📂 Carica un'Armata dal tuo Archivio", expanded=False):
            c_load1, c_load2 = st.columns([3, 1])
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
                    st.rerun()

    # ==========================================
    # SEZIONE 1: GENERALITÀ DELL'ARMATA E FORMAZIONE
    # ==========================================
    st.markdown('<div class="section-header">Configurazione Schieramento e Formazione</div>', unsafe_allow_html=True)
    st.caption("Definisci le generalità dell'esercito, il formato della battaglia e la Formazione tattica associata con i relativi bonus.")

    with st.container(border=True):
        st.markdown('<div class="subsection-title">Generalità dell\'Esercito</div>', unsafe_allow_html=True)
        
        col_f1, col_f2, col_f3, col_f4 = st.columns([1.5, 1.2, 1.3, 1])
        st.session_state["sdg_nome_armata"] = col_f1.text_input("Nome della Lista", value=st.session_state["sdg_nome_armata"])
        
        lista_fazioni_disp = ["Nighthaunt", "Blades of Khorne", "Orruk Kruleboyz", "Sylvaneth", "Grande Alleanza / Altro"]
        idx_faz = lista_fazioni_disp.index(st.session_state["sdg_fazione_armata"]) if st.session_state["sdg_fazione_armata"] in lista_fazioni_disp else 0
        st.session_state["sdg_fazione_armata"] = col_f2.selectbox("Fazione", lista_fazioni_disp, index=idx_faz)

        formato_scelto = col_f3.selectbox(
            "Formato Battaglia",
            ["Vanguard (1000 pt)", "Strike Force (1500 pt)", "Battlehost (2000 pt)", "Personalizzato (Custom)"],
            index=0
        )

        if "720" in formato_scelto:
            limite_punti = 720
        elif "600" in formato_scelto:
            limite_punti = 600
        elif "1000" in formato_scelto:
            limite_punti = 1000
        elif "1500" in formato_scelto:
            limite_punti = 1500
        elif "2000" in formato_scelto:
            limite_punti = 2000
        else:
            limite_punti = col_f4.number_input("Punti Custom", min_value=100, max_value=5000, value=720, step=10)

        st.markdown("---")
        st.markdown('<div class="subsection-title">Formazione di Battaglia (Battle Formation)</div>', unsafe_allow_html=True)
        st.caption("Formazione ufficiale associata all'armata. Regole, fasi d'attivazione e modificatori numerici sono pre-impostati da database.")

        fazioni_disponibili_db = st.session_state["archivio_formazioni"]
        formazioni_fazione = fazioni_disponibili_db.get(st.session_state["sdg_fazione_armata"], {
            "Formazione Standard": {
                "fase_attivazione": "Nessuna", "monouso": False, "tipo_effetto": "Nessuno", "valore_modificatore": "0", "descrizione": "Nessuna abilità speciale attiva."
            }
        })

        lista_nomi_formazioni = list(formazioni_fazione.keys()) if isinstance(formazioni_fazione, dict) else ["Formazione Standard"]
        idx_form = lista_nomi_formazioni.index(st.session_state["sdg_formazione_scelta"]) if st.session_state["sdg_formazione_scelta"] in lista_nomi_formazioni else 0
        
        formazione_selezionata = st.selectbox("Nome Formazione", lista_nomi_formazioni, index=idx_form)
        st.session_state["sdg_formazione_scelta"] = formazione_selezionata

        dati_form = formazioni_fazione.get(formazione_selezionata, {
            "fase_attivazione": "Hero Phase", "monouso": False, "tipo_effetto": "Nessuno", "valore_modificatore": "0", "descrizione": "Descrizione non disponibile."
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
        # 1. Pulisce tutte le chiavi dei widget di Streamlit legate ai reggimenti
        chiavi_da_eliminare = [
            k for k in st.session_state.keys()
            if k.startswith("reg_lead_") or k.startswith("reg_trait_") or k.startswith("reg_art_") or k.startswith("fol_")
        ]
        for k in chiavi_da_eliminare:
            del st.session_state[k]

        # 2. Resetta la struttura dati del Reggimento #1
        st.session_state["sdg_reggimenti"] = [{
            "leader": "--- Scegli Eroe Leader ---",
            "is_generale": True,
            "rinforzato": False,
            "tratto_eroico": "Nessuno",
            "artefatto": "Nessuno",
            "seguito": []
        }]
        st.session_state["sdg_ausiliari"] = []
        
        # 3. Incrementa la versione per costringere Streamlit a ricreare i widget da zero
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

            lc1, lc2 = st.columns([2.5, 1.5])
            lista_scelta_leader = ["--- Scegli Eroe Leader ---"] + eroi_db_filtrati
            idx_lead = lista_scelta_leader.index(reg["leader"]) if reg["leader"] in lista_scelta_leader else 0
            
            # Selectbox Leader con chiave dinamica di versione
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
            idx_tratto = db_tratti_eroici.index(reg.get("tratto_eroico", "Nessuno")) if reg.get("tratto_eroico", "Nessuno") in db_tratti_eroici else 0
            
            # Selectbox Tratto Eroico con chiave dinamica di versione
            reg["tratto_eroico"] = tc1.selectbox(
                "Tratto Eroico (Heroic Trait)", 
                db_tratti_eroici, 
                index=idx_tratto, 
                key=f"reg_trait_{r_idx}_v{st.session_state['sdg_roster_version']}"
            )

            idx_art = db_artefatti.index(reg.get("artefatto", "Nessuno")) if reg.get("artefatto", "Nessuno") in db_artefatti else 0
            
            # Selectbox Artefatto con chiave dinamica di versione
            reg["artefatto"] = tc2.selectbox(
                "Artefatto di Potere", 
                db_artefatti, 
                index=idx_art, 
                key=f"reg_art_{r_idx}_v{st.session_state['sdg_roster_version']}"
            )

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
                pt_tratto = st.session_state["db_tratti_eroici_dict"].get(reg.get("tratto_eroico", "Nessuno"), {}).get("punti", 0)
                pt_artefatto = st.session_state["db_artefatti_dict"].get(reg.get("artefatto", "Nessuno"), {}).get("punti", 0)
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
                        is_reaz = ab.get("reazione", False)
                        classe_box = "ability-box-reaction" if is_reaz else "ability-box"
                        reaz_txt = "🔴 Reaction: " if is_reaz else "🟢 "
                        fasi_txt = ", ".join(ab.get("fasi", ["Generica"]))
                        st.markdown(f"""
                        <div class="{classe_box}">
                            <small style="color: #d8c29d;"><b>[{fasi_txt}]</b></small><br>
                            <b>{reaz_txt}{ab.get('nome', 'Abilità')}</b>: {ab.get('descrizione', '')}
                        </div>
                        """, unsafe_allow_html=True)

            st.markdown("---")
            max_seguito = 4 if reg.get("is_generale", False) else 3
            st.markdown(f"**Seguito ({len(reg['seguito'])} / {max_seguito} slot occupati):**")

            sc_add1, sc_add2 = st.columns([3, 1])
            unita_seg_sel = sc_add1.selectbox(
                "Aggiungi unità di seguito:", 
                ["--- Scegli unità ---"] + opzioni_db, 
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
                
                fc1, fc2, fc3 = st.columns([3, 1.5, 0.6])
                fc1.markdown(f"• **{fol['nome']}** ({estrai_intero_sicuro(d_fol_db.get('n_modelli', 1))*molt} mod. — `{estrai_intero_sicuro(d_fol_db.get('punti', 0))*molt} pt`)")
                
                if puo_rinf:
                    fol["rinforzata"] = fc2.checkbox("Rinforzata (x2)", value=fol.get("rinforzata", False), key=f"fol_rinf_{r_idx}_{f_idx}")
                else:
                    fc2.caption("Non rinforzabile")
                    fol["rinforzata"] = False

                if fc3.button("✖", key=f"del_fol_{r_idx}_{f_idx}"):
                    seguito_da_rimuovere.append(f_idx)

                # --- INTERFACCIA EQUIPAGGIAMENTO EROI NEL SEGUITO ---
                kw_fol = [str(k).upper() for k in d_fol_db.get("keywords", [])]
                if "HERO" in kw_fol:
                    st.markdown("<div style='margin-top:-5px; margin-bottom:10px; padding-left:15px;'><small style='color:#d4af37;'>✨ <i>Eroe (Può equipaggiare Tratti e Artefatti)</i></small></div>", unsafe_allow_html=True)
                    tf_col1, tf_col2 = st.columns(2)
                    
                    idx_t_f = db_tratti_eroici.index(fol.get("tratto_eroico", "Nessuno")) if fol.get("tratto_eroico", "Nessuno") in db_tratti_eroici else 0
                    fol["tratto_eroico"] = tf_col1.selectbox("Tratto Eroico", db_tratti_eroici, index=idx_t_f, key=f"fol_trait_{r_idx}_{f_idx}_v{st.session_state['sdg_roster_version']}")
                    
                    idx_a_f = db_artefatti.index(fol.get("artefatto", "Nessuno")) if fol.get("artefatto", "Nessuno") in db_artefatti else 0
                    fol["artefatto"] = tf_col2.selectbox("Artefatto", db_artefatti, index=idx_a_f, key=f"fol_art_{r_idx}_{f_idx}_v{st.session_state['sdg_roster_version']}")

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
        mod_t = st.session_state["db_tratti_eroici_dict"].get(nome_tratto, {}).get("modificatori", {})
        mod_a = st.session_state["db_artefatti_dict"].get(nome_artefatto, {}).get("modificatori", {})
        for sorgente in (mod_t, mod_a):
            if isinstance(sorgente, dict):
                for k, v in sorgente.items():
                    if not isinstance(v, (int, float)):
                        continue
                    if k in ["ward_nativo", "crit_on"]:
                        b[k] = min(b.get(k, 7), int(v))
                    else:
                        b[k] = b.get(k, 0) + int(v)
        pt_t = estrai_intero_sicuro(st.session_state["db_tratti_eroici_dict"].get(nome_tratto, {}).get("punti", 0))
        pt_a = estrai_intero_sicuro(st.session_state["db_artefatti_dict"].get(nome_artefatto, {}).get("punti", 0))
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
            oc_u = estrai_intero_sicuro(d_u.get("statistiche_cerchio", {}).get("controllo", 2), default=2) + int(bonus_lead.get("bonus_controllo", 0))

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
        "🩺 Check-Up Strategico & Rendimento Unità",
        "⚔️ Confronto Armate & Comparatore d'Ingaggio",
        "📜 Salvataggio & Pergamena Torneo"
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
                st.markdown("#### Avvertimenti dello Stratega e Sinergie")
                consigli_speciali = []
                if any("Knight of Shrouds" in u["chiave_db"] for u in unita_totali_schierate) and any("Guardian of Souls" in u["chiave_db"] for u in unita_totali_schierate):
                    consigli_speciali.append("✨ **Sinergia Warlord & Supporto:** Il *Knight of Shrouds* attiva immediatamente una fanteria amica con *Infantry Overseer* e si cura con *Stolen Hours*, mentre il *Guardian of Souls* dà +1 Wound.")
                if any("Spirit Hosts" in u["chiave_db"] for u in unita_totali_schierate):
                    consigli_speciali.append("🛡️ **Ancoraggio Difensivo (Spirit Hosts):** *Drawn to War* fornisce **Ward (4+)** agli eroi di fanteria Nighthaunt entro 3\".")
                if any("Scriptor Mortis" in u["chiave_db"] for u in unita_totali_schierate):
                    consigli_speciali.append("⚖️ **Anti-Tank (Scriptor Mortis):** Condanna il bersaglio corazzato nemico per conferire *Crit (Mortal)* alle unità Nighthaunt.")
                if max_rend_armata < 2:
                    consigli_speciali.append("⚠️ **Penetrazione Armatura Limitata:** Il Rend massimo nativo è basso. Sfrutta formazioni o debuff al Save contro bersagli con Save 2+/3+.")
                if livello_magico_tot == 0 and livello_preti_tot == 0:
                    consigli_speciali.append("⚠️ **Assenza di Supporto Arcano:** Nessun Mago o Prete in lista (nessun Unbind/Banish disponibile).")
                if not consigli_speciali:
                    consigli_speciali.append("✅ **Bilanciamento Solido:** La lista copre bene i ruoli offensivi e di controllo mappa.")
                for cs in consigli_speciali:
                    st.markdown(f"- {cs}")

    # ==========================================
    # TAB 2: MATRICE MATCH-UP E COMPARATORE DIRETTO (B vs A)
    # ==========================================
    with tab_matchup:
        st.markdown('<div class="subsection-title">1. Schieramento dell\'Armata Nemica</div>', unsafe_allow_html=True)
        st.caption("Importa un'armata avversaria preconfigurata, carica un roster salvato o componi i nemici manualmente.")

        with st.container(border=True):
            im1, im2 = st.columns([2.5, 1])
            opzioni_import_nemici = ["--- Scegli armata nemica ---"] + list(ARMATE_NEMICHE_NOTE.keys()) + [f"[Archivio] {k}" for k in armate_salvate]
            scelta_armata_nota = im1.selectbox("Importa Armata Avversaria:", opzioni_import_nemici)
            if im2.button("📥 Importa Nemici", type="primary", use_container_width=True):
                if scelta_armata_nota in ARMATE_NEMICHE_NOTE:
                    st.session_state["sdg_nemici_matchup"] = [
                        dict(x) for x in ARMATE_NEMICHE_NOTE[scelta_armata_nota]
                        if x["nome"] in st.session_state["db_unita"]
                    ]
                    st.toast(f"Armata '{scelta_armata_nota}' importata!", icon="✅")
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
                    st.toast(f"Roster '{k_arch}' importato come avversario!", icon="✅")
                    st.rerun()

            st.markdown("---")
            mc1, mc2, mc3 = st.columns([2.5, 1, 1])
            nemico_sel = mc1.selectbox("Aggiungi singola unità nemica:", ["--- Scegli unità nemica dal DB ---"] + opzioni_db, key="sel_enemy_mu")
            nemico_rinf = mc2.checkbox("Rinforzata (x2)", value=False, key="chk_enemy_rinf")
            if mc3.button("➕ Aggiungi Nemico", use_container_width=True):
                if nemico_sel != "--- Scegli unità nemica dal DB ---":
                    st.session_state["sdg_nemici_matchup"].append({"nome": nemico_sel, "rinforzata": nemico_rinf})
                    st.rerun()

            if st.session_state["sdg_nemici_matchup"]:
                nem_str_list = [f"{i+1}. {n['nome']}" + (" (x2)" if n["rinforzata"] else "") for i, n in enumerate(st.session_state["sdg_nemici_matchup"])]
                st.markdown("**Forze Avversarie in Campo:** " + " | ".join(nem_str_list))
                if st.button("🗑️ Svuota Armata Nemica"):
                    st.session_state["sdg_nemici_matchup"] = []
                    st.rerun()

        if len(unita_totali_schierate) > 0 and len(st.session_state["sdg_nemici_matchup"]) > 0:
            # Costruzione profili completi dei nemici
            nemici_elaborati = []
            for n_idx, nem_item in enumerate(st.session_state["sdg_nemici_matchup"]):
                d_nem = st.session_state["db_unita"].get(nem_item["nome"], {})
                if not d_nem:
                    continue
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
                    # Danno che la mia unità infligge al nemico (% vita tolta)
                    ris_att = calcola_output_unita_su_bersaglio(d_mia, mia_u["rinforzata"], nem["profilo_difensivo"], mia_u["bonus_unita"], ha_caricato=True)
                    perc_inflitta = min(100.0, (ris_att["danno_totale"] / float(nem["profilo_difensivo"]["salute"])) * 100.0)
                    col_att.append(round(perc_inflitta, 1))

                    # Danno che il nemico infligge alla mia unità se la attacca a pieno organico (% mia vita persa)
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
            st.markdown('<div class="subsection-title">4. Simulatore di Duello & Convenienza d\'Ingaggio (Tua Unità B vs Nemico A)</div>', unsafe_allow_html=True)
            st.caption("Analisi completa di scambio: calcola i modelli nemici uccisi nel primo impatto, il contrattacco dei modelli superstiti e il guadagno/perdita in Punti.")

            with st.container(border=True):
                duel_c1, duel_c2 = st.columns(2)
                scelta_mia_idx = duel_c1.selectbox(
                    "Scegli la Tua Unità (Unità B):",
                    range(len(unita_totali_schierate)),
                    format_func=lambda i: f"{unita_totali_schierate[i]['etichetta']} ({unita_totali_schierate[i]['punti']} pt | {unita_totali_schierate[i]['salute']} PF)",
                    key="duel_sel_mia"
                )
                scelta_nem_idx = duel_c2.selectbox(
                    "Scegli il Bersaglio Nemico (Unità A):",
                    range(len(nemici_elaborati)),
                    format_func=lambda i: f"{nemici_elaborati[i]['etichetta']} ({nemici_elaborati[i]['profilo_difensivo']['punti']} pt | {nemici_elaborati[i]['profilo_difensivo']['salute']} PF)",
                    key="duel_sel_nem"
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

                # Preparazione profili con opzioni attive
                bonus_miei_duello = dict(mia_sel["bonus_unita"])
                if mia_aoa:
                    bonus_miei_duello["mod_hit"] = bonus_miei_duello.get("mod_hit", 0) + 1

                prof_dif_nem_duello = dict(nem_sel["profilo_difensivo"])
                prof_dif_nem_duello["aod"] = nem_aod

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

                # Contrattacco dei soli modelli superstiti nemici (solo armi da mischia in fase di combattimento)
                out_contrattacco_nem = calcola_output_unita_su_bersaglio(
                    d_nem_db, nem_sel["rinforzata"], prof_dif_mio_duello,
                    ha_caricato=False, n_modelli_override=modelli_nem_superstiti
                )
                danno_subito_contrattacco = out_contrattacco_nem["danno_melee"]
                hp_per_mod_mio = prof_dif_mio_duello["salute_per_modello"]
                miei_modelli_persi = min(prof_dif_mio_duello["n_modelli"], int(danno_subito_contrattacco // hp_per_mod_mio))

                # Calcolo Valore Punti Neutralizzati vs Punti Persi
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
                k2.metric("Modelli Nemici Uccisi", f"{modelli_nem_uccisi} / {prof_dif_nem_duello['n_modelli']} mod.", f"{modelli_nem_superstiti} superstiti")
                k3.metric("Danno Subito al Contrattacco", f"{danno_subito_contrattacco:.1f} / {mia_sel['salute']} PF", f"-{miei_modelli_persi} tuoi modelli")
                k4.metric("Bilancio Scambio Punti", f"{bilancio_netto_pt:+.0f} pt", f"Guadagni {pt_nem_neutralizzati:.0f}pt | Perdi {pt_miei_persi:.0f}pt")

                # Verdetto Intelligente d'Ingaggio
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
            if st.button("💾 Salva Armata nell'Archivio", type="primary"):
                chiave_armata = f"{st.session_state['sdg_fazione_armata']}: {st.session_state['sdg_nome_armata']}"
                st.session_state["archivio_armate"][chiave_armata] = {
                    "nome": st.session_state["sdg_nome_armata"],
                    "fazione": st.session_state["sdg_fazione_armata"],
                    "formazione": st.session_state["sdg_formazione_scelta"],
                    "limite_punti": limite_punti,
                    "punti_totali": punti_totali,
                    "reggimenti": st.session_state["sdg_reggimenti"],
                    "ausiliari": st.session_state["sdg_ausiliari"]
                }
                salva_archivio_armate(st.session_state["archivio_armate"])
                st.toast(f"Armata '{chiave_armata}' salvata con successo!")
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
                pt_t = st.session_state["db_tratti_eroici_dict"].get(nome_t, {}).get("punti", 0)
                pt_a = st.session_state["db_artefatti_dict"].get(nome_a, {}).get("punti", 0)
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
                    pt_t_f = st.session_state["db_tratti_eroici_dict"].get(nome_t_f, {}).get("punti", 0)
                    pt_a_f = st.session_state["db_artefatti_dict"].get(nome_a_f, {}).get("punti", 0)
                    pt_f_base = estrai_intero_sicuro(d_f.get('punti', 0)) * molt
                    pt_f_tot = pt_f_base + pt_t_f + pt_a_f
                    
                    linee_export.append(f"  • Seguito: {fol['nome']}{rinf_str} ({pt_f_tot} pt)")
                    if nome_t_f != "Nessuno":
                        linee_export.append(f"    - Tratto: {nome_t_f} ({pt_t_f} pt)")
                    if nome_a_f != "Nessuno":
                        linee_export.append(f"    - Artefatto: {nome_a_f} ({pt_a_f} pt)")

            testo_completo_export = "\n".join(linee_export)
            st.text_area("Pergamena dell'Esercito:", value=testo_completo_export, height=300)