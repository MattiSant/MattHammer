import streamlit as st
import numpy as np
import json
import os
import re
import base64
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "units_db.json")

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

def applica_stile_globale():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700;900&family=Cinzel:wght@600;700;800&family=Crimson+Pro:ital,wght@0,400;0,600;0,700;1,400&display=swap');

        /* Sfondo generale con trama impercettibile a pergamena scura e cenere */
        .stApp {
            background-color: #120e0a;
            background-image: 
                radial-gradient(circle at 50% 12%, rgba(58, 41, 24, 0.55) 0%, rgba(18, 14, 10, 0.95) 75%),
                radial-gradient(2px 2px at 20% 30%, rgba(212, 175, 55, 0.15), transparent),
                radial-gradient(1.5px 1.5px at 80% 40%, rgba(255, 140, 30, 0.15), transparent);
            color: #f4ecd8;
            font-family: 'Crimson Pro', 'Georgia', serif;
            font-size: 1.05rem;
        }

        /* Scrollbar personalizzata a stile forgia/bronzo antico */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #140e09;
        }
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(180deg, #7c5e3c 0%, #3d2817 100%);
            border-radius: 4px;
            border: 1px solid rgba(212, 175, 55, 0.3);
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #b38b4d;
        }

        /* Sidebar: legno laccato scuro con finiture dorate */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #18120b 0%, #0d0906 100%);
            border-right: 2px solid #6b4e2d;
            box-shadow: 5px 0 20px rgba(0, 0, 0, 0.85);
            color: #e6dfcc;
        }
        [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stMarkdown {
            color: #e6dfcc !important;
            font-family: 'Crimson Pro', serif;
        }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            font-family: 'Cinzel', serif !important;
            letter-spacing: 1.2px;
            color: #d4af37 !important;
            border-bottom: 1px solid #5c4730;
            padding-bottom: 5px;
            text-shadow: 0 2px 6px rgba(0,0,0,0.8);
        }

        /* Riquadri / Container principali: Pergamena Imperiale con doppia bordura */
        div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] {
            background: linear-gradient(135deg, #f7f1e1 0%, #ede3cb 50%, #e2d4b3 100%) !important;
            border: 2px solid #6e5233 !important;
            outline: 1px solid rgba(212, 175, 55, 0.35);
            outline-offset: -5px;
            border-top: 4px solid #b38b4d !important;
            border-bottom: 4px solid #4a3520 !important;
            border-radius: 4px 14px 4px 14px !important;
            padding: 24px !important;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.75), inset 0 0 40px rgba(139, 101, 59, 0.22) !important;
            color: #241c11 !important;
            margin-bottom: 18px !important;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        div[data-testid="stContainer"]:hover {
            box-shadow: 0 14px 35px rgba(0, 0, 0, 0.85), inset 0 0 45px rgba(212, 175, 55, 0.15) !important;
        }

        div[data-testid="stContainer"] h1, 
        div[data-testid="stContainer"] h2, 
        div[data-testid="stContainer"] h3,
        div[data-testid="stContainer"] h4 {
            color: #382412 !important;
            font-family: 'Cinzel', serif !important;
            font-weight: 700 !important;
            letter-spacing: 0.8px !important;
            border-bottom: 1px solid rgba(140, 109, 70, 0.45);
            padding-bottom: 6px;
            margin-bottom: 10px;
        }
        div[data-testid="stContainer"] p, 
        div[data-testid="stContainer"] label,
        div[data-testid="stContainer"] span,
        div[data-testid="stContainer"] li {
            color: #2b2116 !important;
            font-family: 'Crimson Pro', serif !important;
            font-weight: 600;
        }
        [data-testid="stCaptionContainer"] p {
            font-family: 'Crimson Pro', serif !important;
            font-style: italic !important;
            font-size: 0.98rem !important;
            color: #b8a68a !important;
        }
        div[data-testid="stContainer"] [data-testid="stCaptionContainer"] p {
            color: #5a4631 !important;
        }

        /* Titoli di primo livello con luminescenza runica */
        h1 {
            color: #f7d57f !important;
            font-family: 'Cinzel Decorative', serif !important;
            font-weight: 700 !important;
            letter-spacing: 2.5px !important;
            text-shadow: 0 4px 10px rgba(0, 0, 0, 0.9), 0 0 20px rgba(212, 175, 55, 0.35);
            text-transform: uppercase;
        }
        h2, h3 {
            color: #ebd597 !important;
            font-family: 'Cinzel', serif !important;
            letter-spacing: 1.2px !important;
            text-shadow: 0 2px 6px rgba(0, 0, 0, 0.85);
        }

        /* Separatore dorato sfumato */
        hr {
            border: 0 !important;
            height: 2px !important;
            background: linear-gradient(90deg, rgba(18,14,10,0) 0%, rgba(212,175,55,0.85) 50%, rgba(18,14,10,0) 100%) !important;
            margin: 1.6rem 0 !important;
            box-shadow: 0 0 8px rgba(212, 175, 55, 0.3);
        }

        /* Expander stilizzati a sigillo */
        .streamlit-expanderHeader {
            background: linear-gradient(90deg, #e3d3ae 0%, #d4bf94 100%) !important;
            border: 1px solid #7c5e3c !important;
            border-left: 5px solid #a37535 !important;
            border-radius: 4px 10px 4px 10px !important;
            color: #241c11 !important;
            font-family: 'Cinzel', serif !important;
            font-weight: 700 !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.35);
            transition: all 0.25s ease;
        }
        .streamlit-expanderHeader:hover {
            border-left: 5px solid #d4af37 !important;
            box-shadow: 0 0 10px rgba(212, 175, 55, 0.45);
        }

        /* Campi di input e textarea */
        input, textarea, select {
            background-color: #22160d !important;
            color: #fdf6e2 !important;
            border: 1px solid #8c6d46 !important;
            border-radius: 4px !important;
            font-family: 'Crimson Pro', serif !important;
            box-shadow: inset 0 2px 5px rgba(0,0,0,0.7);
        }
        input:focus, textarea:focus {
            border-color: #d4af37 !important;
            box-shadow: 0 0 8px rgba(212, 175, 55, 0.5), inset 0 2px 5px rgba(0,0,0,0.8) !important;
        }

        div[data-baseweb="select"] > div {
            background-color: #22160d !important;
            color: #fdf6e2 !important;
            border: 1px solid #8c6d46 !important;
            border-radius: 4px !important;
        }
        div[data-baseweb="select"] span {
            color: #fdf6e2 !important;
            font-family: 'Crimson Pro', serif !important;
        }

        /* Pulsanti base */
        button[data-baseweb="button"] {
            background: linear-gradient(180deg, #382416 0%, #24160c 100%) !important;
            color: #fdf6e2 !important;
            border: 1px solid #8c6d46 !important;
            border-radius: 4px !important;
            font-family: 'Cinzel', serif !important;
            transition: all 0.25s ease;
        }
        button[data-baseweb="button"]:hover {
            border-color: #d4af37 !important;
            box-shadow: 0 0 10px rgba(212, 175, 55, 0.4);
            transform: translateY(-1px);
        }

        /* Schede / Tabs del grimorio */
        button[data-baseweb="tab"] {
            font-family: 'Cinzel', serif !important;
            font-weight: 700 !important;
            letter-spacing: 0.8px !important;
            color: #bda688 !important;
            background-color: #1a120b !important;
            border: 1px solid #4a3723 !important;
            border-bottom: none !important;
            border-radius: 6px 6px 0 0 !important;
            padding: 10px 18px !important;
            margin-right: 4px !important;
            transition: all 0.25s ease;
        }
        button[data-baseweb="tab"]:hover {
            color: #f7d57f !important;
            background-color: #291c12 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            background: linear-gradient(180deg, #3d2c1b 0%, #20150b 100%) !important;
            color: #f7d57f !important;
            border-top: 3px solid #d4af37 !important;
            box-shadow: 0 -3px 12px rgba(212, 175, 55, 0.25);
        }

        /* Riquadri metriche con gemme bronzate */
        div[data-testid="metric-container"] {
            background: linear-gradient(145deg, #281d13 0%, #17100a 100%);
            border: 2px solid #8c6d46;
            border-top: 3px solid #d4af37;
            padding: 16px;
            border-radius: 4px 12px 4px 12px;
            box-shadow: 0 8px 18px rgba(0,0,0,0.7), inset 0 0 20px rgba(212, 175, 55, 0.08);
            transition: transform 0.2s ease;
        }
        div[data-testid="metric-container"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 22px rgba(0,0,0,0.85), 0 0 12px rgba(212, 175, 55, 0.35);
        }
        div[data-testid="metric-container"] label {
            color: #d4af37 !important;
            font-family: 'Cinzel', serif !important;
            font-weight: 700 !important;
            letter-spacing: 0.6px;
        }
        div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
            color: #fdf6e2 !important;
            font-family: 'Cinzel', serif !important;
            font-weight: 700;
            text-shadow: 0 2px 8px rgba(0,0,0,0.8);
        }

        /* Pulsanti Primari (Oro fuso & Rame) */
        .stButton button[kind="primary"] {
            background: linear-gradient(135deg, #7a4f10 0%, #b38b4d 50%, #8a5a14 100%);
            color: #fffde6 !important;
            border: 1px solid #f0ca65;
            font-family: 'Cinzel', serif !important;
            font-weight: 700;
            letter-spacing: 0.9px;
            border-radius: 4px 10px 4px 10px;
            box-shadow: 0 5px 12px rgba(0,0,0,0.6), inset 0 0 10px rgba(255,255,255,0.2);
            transition: all 0.25s ease;
        }
        .stButton button[kind="primary"]:hover {
            background: linear-gradient(135deg, #9c6818 0%, #d4af37 50%, #b38b4d 100%);
            box-shadow: 0 0 18px rgba(212, 175, 55, 0.75), 0 6px 14px rgba(0,0,0,0.8);
            transform: translateY(-2px);
        }
    </style>
    """, unsafe_allow_html=True)

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

def _push_su_github_file(filepath, json_dati, messaggio_commit="Aggiornamento Database"):
    st.session_state["cloud_sincronizzato"] = False
    
    # 1. Salva sempre il file localmente (una sola volta)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(json_dati, f, indent=4, ensure_ascii=False)
        
    nome_file = os.path.basename(filepath)
    
    # 2. Controllo Secrets
    if "GITHUB_TOKEN" not in st.secrets or "GITHUB_REPO" not in st.secrets:
        msg = f"⚠️ Salvato solo in locale ({nome_file}): GITHUB_TOKEN o GITHUB_REPO mancanti in st.secrets!"
        st.session_state["last_sync_status"] = ("warning", msg)
        return False, msg

    token = str(st.secrets["GITHUB_TOKEN"]).strip()
    repo_raw = str(st.secrets["GITHUB_REPO"]).strip()
    repo = repo_raw.replace("https://github.com/", "").replace("http://github.com/", "")
    if repo.endswith(".git"):
        repo = repo[:-4]
    repo = repo.strip("/")

    url = f"https://api.github.com/repos/{repo}/contents/{nome_file}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "MattHammer-Streamlit-App"
    }
    
    sha = None
    branch_usato = "main"
    
    try:
        get_resp = requests.get(url, headers=headers, timeout=10)
        if get_resp.status_code == 200:
            sha = get_resp.json().get("sha")
        elif get_resp.status_code == 404:
            repo_check = requests.get(f"https://api.github.com/repos/{repo}", headers=headers, timeout=10)
            if repo_check.status_code != 200:
                err_msg = f"❌ Repo '{repo}' non trovato o Token non valido (HTTP {repo_check.status_code}): {repo_check.text}"
                st.session_state["last_sync_status"] = ("error", err_msg)
                return False, err_msg
            branch_usato = repo_check.json().get("default_branch", "main")
        else:
            err_msg = f"❌ Errore Lettura GitHub ({get_resp.status_code}) su {url}: {get_resp.text}"
            st.session_state["last_sync_status"] = ("error", err_msg)
            return False, err_msg
    except Exception as e:
        err_msg = f"❌ Eccezione connessione GitHub (GET): {e}"
        st.session_state["last_sync_status"] = ("error", err_msg)
        return False, err_msg
        
    contenuto_str = json.dumps(json_dati, indent=4, ensure_ascii=False)
    contenuto_b64 = base64.b64encode(contenuto_str.encode("utf-8")).decode("utf-8")
    
    payload = {
        "message": f"🤖 Auto-sync: {messaggio_commit} ({nome_file})",
        "content": contenuto_b64,
        "branch": branch_usato
    }
    if sha:
        payload["sha"] = sha
        
    try:
        put_resp = requests.put(url, headers=headers, json=payload, timeout=10)
        if put_resp.status_code in [200, 201]:
            ok_msg = f"✅ {nome_file} sincronizzato su GitHub ({repo})!"
            st.session_state["last_sync_status"] = ("success", ok_msg)
            return True, ok_msg
        else:
            err_msg = f"❌ Errore Scrittura GitHub ({put_resp.status_code}): {put_resp.text}"
            st.session_state["last_sync_status"] = ("error", err_msg)
            return False, err_msg
    except Exception as e:
        err_msg = f"❌ Eccezione connessione GitHub (PUT): {e}"
        st.session_state["last_sync_status"] = ("error", err_msg)
        return False, err_msg

def salva_nel_database(db_dict):
    return _push_su_github_file(DB_FILE, db_dict, "Aggiornamento Warscroll nel Grimorio")

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
    if not arma.get("attiva", False) or str(arma.get("hit")) == "---" or str(arma.get("wnd")) == "---" or str(arma.get("atk")) == "---" or str(arma.get("dmg")) == "---": 
        return {"attacchi": 0, "hits": 0, "wounds": 0, "unsaved": 0, "mortal": 0, "danno_netto": 0}

    is_comp = arma.get("companion", False)
    atk_per_modello = media_dado(arma["atk"])
    if not is_comp: atk_per_modello += mod_globali.get("bonus_atk", 0)
    
    atk_totali = atk_per_modello * mod_globali["n_modelli"]
    if mod_globali.get("campione", False) and not is_comp: atk_totali += 1

    # Hit Roll (Cap AoS 4e: -1 / +1)
    mod_hit_netto = mod_globali.get("mod_hit", 0)
    if is_comp and mod_hit_netto > 0 and not mod_globali.get("all_out_attack", False): mod_hit_netto = 0
    if bersaglio.get("obscuring", False) and arma.get("ranged", False): mod_hit_netto -= 1
    hit_target = np.clip(int(arma["hit"]) - np.clip(mod_hit_netto, -1, 1), 2, 6)

    soglia_crit = mod_globali.get("crit_on", 6)
    prob_crit = (7 - soglia_crit) / 6.0
    prob_hit_totale = (7 - hit_target) / 6.0
    prob_hit_normale = max(0.0, prob_hit_totale - prob_crit)

    danno_per_colpo = media_dado(arma["dmg"])
    if arma.get("charge_dmg", False) and mod_globali.get("ha_caricato", False): danno_per_colpo += 1
    if not is_comp: danno_per_colpo += mod_globali.get("bonus_dmg", 0)

    mortal_da_crit = 0.0
    auto_wounds = 0.0
    hits_che_devono_ferire = atk_totali * prob_hit_normale

    crit_t = mod_globali.get("crit_override", arma.get("crit_type", "Nessuno")) if not is_comp else arma.get("crit_type", "Nessuno")
    if crit_t == "Crit (Mortal)": mortal_da_crit = atk_totali * prob_crit * danno_per_colpo
    elif crit_t == "Crit (Auto-wound)": auto_wounds = atk_totali * prob_crit
    elif crit_t == "Crit (2 Hits)": hits_che_devono_ferire += atk_totali * prob_crit * 2.0
    else: hits_che_devono_ferire += atk_totali * prob_crit

    hits_totali_visivi = hits_che_devono_ferire + auto_wounds + (atk_totali * prob_crit if crit_t == "Crit (Mortal)" else 0)

    # Wound Roll (Cap AoS 4e: -1 / +1)
    mod_wnd_netto = 0 if (is_comp and mod_globali.get("mod_wnd", 0) > 0) else mod_globali.get("mod_wnd", 0)
    mod_wnd_netto += bersaglio.get("mod_wnd_nerf", 0)
    wnd_target = np.clip(int(arma["wnd"]) - np.clip(mod_wnd_netto, -1, 1), 2, 6)
    prob_wnd = (7 - wnd_target) / 6.0
    wounds_totali = (hits_che_devono_ferire * prob_wnd) + auto_wounds

    # Rend & Anti-X
    rend_effettivo = (0 if str(arma.get("rend", 0)) == "---" else int(arma.get("rend", 0))) + (mod_globali.get("bonus_rend", 0) if not is_comp else 0)
    anti_t = arma.get("anti_target", "Nessuno")
    kw_bers = [str(k).upper() for k in bersaglio.get("keywords", [])]
    
    if anti_t != "Nessuno" and anti_t != "CHARGE" and anti_t in kw_bers:
        rend_effettivo += 1
    if (arma.get("anti_charge", False) or anti_t == "CHARGE") and mod_globali.get("bersaglio_ha_caricato", False):
        rend_effettivo += 1
    if bersaglio.get("immune_rend", False):
        rend_effettivo = 0

    # Save Roll (Cap AoS 4e: max +1 positivo)
    if bersaglio["save"] >= 7: prob_save_fallito = 1.0
    else:
        bonus_save_positivo = min(1, (1 if bersaglio.get("cover", False) else 0) + (1 if bersaglio.get("aod", False) else 0) + bersaglio.get("bonus_save_extra", 0))
        save_target = bersaglio["save"] - bonus_save_positivo + rend_effettivo
        prob_save_fallito = 1.0 if save_target > 6 else 1.0 - ((7 - max(2, save_target)) / 6.0)

    colpi_non_salvati = wounds_totali * prob_save_fallito
    danni_normali_lordi = colpi_non_salvati * danno_per_colpo

    if bersaglio.get("blocca_ward", False): prob_ward_fallito = 1.0
    else:
        ward_effettivo = bersaglio["ward"] + bersaglio.get("mod_ward_penalita", 0)
        prob_ward_fallito = 1.0 if (bersaglio["ward"] >= 7 or ward_effettivo > 6) else 1.0 - ((7 - max(2, ward_effettivo)) / 6.0)
        
    danno_netto = (danni_normali_lordi + mortal_da_crit) * prob_ward_fallito
    return {"attacchi": atk_totali, "hits": hits_totali_visivi, "wounds": wounds_totali, "unsaved": colpi_non_salvati, "mortal": mortal_da_crit, "danno_netto": danno_netto}

def simula_monte_carlo(armi, mod_globali, bersaglio, n_sim=10000):
    danni_totali_sim = np.zeros(n_sim, dtype=float)
    ward_effettivo = bersaglio["ward"] + bersaglio.get("mod_ward_penalita", 0)
    ha_ward = (bersaglio["ward"] < 7) and (ward_effettivo <= 6) and (not bersaglio.get("blocca_ward", False))
    ward_target = max(2, ward_effettivo)
    kw_bers = [str(k).upper() for k in bersaglio.get("keywords", [])]

    for arma in armi:
        if not arma.get("attiva", False) or str(arma.get("hit")) == "---" or str(arma.get("wnd")) == "---" or str(arma.get("atk")) == "---" or str(arma.get("dmg")) == "---": continue
        is_comp = arma.get("companion", False)
        atk_base = tira_dado_mc(arma["atk"], n_sim)
        if not is_comp: atk_base = atk_base + mod_globali.get("bonus_atk", 0)
        atk_tot_array = np.maximum(0, atk_base * mod_globali["n_modelli"] + (1 if (mod_globali.get("campione", False) and not is_comp) else 0))

        max_atk = int(np.max(atk_tot_array))
        if max_atk <= 0: continue

        # Vettorizzazione con maschera per attacchi variabili (D6, 2D6, ecc.)
        tiri_hit = np.random.randint(1, 7, size=(n_sim, max_atk))
        if np.min(atk_tot_array) != max_atk:
            mask_validi = np.arange(max_atk)[None, :] < atk_tot_array[:, None]
            tiri_hit = np.where(mask_validi, tiri_hit, 0)

        mod_hit_netto = mod_globali.get("mod_hit", 0)
        if is_comp and mod_hit_netto > 0 and not mod_globali.get("all_out_attack", False): mod_hit_netto = 0
        if bersaglio.get("obscuring", False) and arma.get("ranged", False): mod_hit_netto -= 1
        hit_target = np.clip(int(arma["hit"]) - np.clip(mod_hit_netto, -1, 1), 2, 6)

        is_crit = tiri_hit >= mod_globali.get("crit_on", 6)
        is_normal_hit = (tiri_hit >= hit_target) & (~is_crit)
        n_crits = np.sum(is_crit, axis=1)
        n_norm_hits = np.sum(is_normal_hit, axis=1)

        mortal_wounds_sim = np.zeros(n_sim)
        auto_wounds_sim = np.zeros(n_sim)
        hits_to_wound = n_norm_hits.copy()
        bonus_dmg_fisso = (1 if (arma.get("charge_dmg", False) and mod_globali.get("ha_caricato", False)) else 0) + (mod_globali.get("bonus_dmg", 0) if not is_comp else 0)

        crit_t = arma.get("crit_type", "Nessuno")
        if crit_t == "Crit (Mortal)": mortal_wounds_sim = n_crits * (tira_dado_mc(arma["dmg"], n_sim) + bonus_dmg_fisso)
        elif crit_t == "Crit (Auto-wound)": auto_wounds_sim = n_crits
        elif crit_t == "Crit (2 Hits)": hits_to_wound += n_crits * 2
        else: hits_to_wound += n_crits

        mod_wnd_netto = 0 if (is_comp and mod_globali.get("mod_wnd", 0) > 0) else mod_globali.get("mod_wnd", 0)
        mod_wnd_netto += bersaglio.get("mod_wnd_nerf", 0)
        wnd_target = np.clip(int(arma["wnd"]) - np.clip(mod_wnd_netto, -1, 1), 2, 6)
        wounds_sim = np.random.binomial(hits_to_wound.astype(int), (7 - wnd_target) / 6.0) + auto_wounds_sim

        rend_eff = (0 if str(arma.get("rend", 0)) == "---" else int(arma.get("rend", 0))) + (mod_globali.get("bonus_rend", 0) if not is_comp else 0)
        anti_t = arma.get("anti_target", "Nessuno")
        if anti_t != "Nessuno" and anti_t != "CHARGE" and anti_t in kw_bers: rend_eff += 1
        if (arma.get("anti_charge", False) or anti_t == "CHARGE") and mod_globali.get("bersaglio_ha_caricato", False): rend_eff += 1
        if bersaglio.get("immune_rend", False): rend_eff = 0
        
        if bersaglio["save"] >= 7: prob_fail_save = 1.0
        else:
            bonus_save = min(1, (1 if bersaglio.get("cover", False) else 0) + (1 if bersaglio.get("aod", False) else 0) + bersaglio.get("bonus_save_extra", 0))
            save_t = bersaglio["save"] - bonus_save + rend_eff
            prob_fail_save = 1.0 if save_t > 6 else 1.0 - ((7 - max(2, save_t)) / 6.0)

        danni_totali_sim += (np.random.binomial(wounds_sim.astype(int), prob_fail_save) * (tira_dado_mc(arma["dmg"], n_sim) + bonus_dmg_fisso)) + mortal_wounds_sim

    mortal_extra_dadi = mod_globali.get("mortal_extra_dadi", 0)
    mortal_extra_tipo = mod_globali.get("mortal_extra_tipo", 6)
    mortal_extra_soglia = str(mod_globali.get("mortal_extra_soglia", "Nessuna (Somma)"))
    mortal_extra_fisso = mod_globali.get("mortal_extra_fisso", 0)

    danni_totali_sim += mortal_extra_fisso
    if mortal_extra_dadi > 0:
        if mortal_extra_soglia.startswith("Nessuna"):
            lanci_extra = np.random.randint(1, mortal_extra_tipo + 1, size=(mortal_extra_dadi, n_sim))
            danni_totali_sim += np.sum(lanci_extra, axis=0)
        else:
            target_val = int(mortal_extra_soglia[0])
            prob = max(0.0, (mortal_extra_tipo - target_val + 1) / float(mortal_extra_tipo))
            danni_totali_sim += np.random.binomial(mortal_extra_dadi, prob, n_sim)

    if ha_ward:
        parte_intera = np.floor(danni_totali_sim).astype(int)
        resto_prob = danni_totali_sim - parte_intera
        dadi_ward = parte_intera + (np.random.random(n_sim) < resto_prob).astype(int)
        danni_totali_sim = np.random.binomial(dadi_ward, 1.0 - ((7 - ward_target) / 6.0)).astype(float)
    return danni_totali_sim

def sincronizza_tutti_i_db():
    """
    Esegue il push su GitHub di tutti e 5 i database JSON contemporaneamente.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    archivi = [
        "units_db.json",
        "armies_db.json",
        "formations.json",
        "heroic_traits_db.json",
        "artefacts_db.json"
    ]
    
    errori = []
    for nome_f in archivi:
        path_completo = os.path.join(base_dir, nome_f)
        if os.path.exists(path_completo):
            try:
                with open(path_completo, "r", encoding="utf-8") as f:
                    dati = json.load(f)
                ok, msg = _push_su_github_file(path_completo, dati, f"Sync Completo ({nome_f})")
                if not ok:
                    errori.append(f"{nome_f}: {msg}")
            except Exception as e:
                errori.append(f"{nome_f}: {e}")

    if not errori:
        st.session_state["cloud_sincronizzato"] = True
        return True, "Tutti i database sono stati sincronizzati con successo!"
    else:
        st.session_state["cloud_sincronizzato"] = False
        return False, " | ".join(errori)

def ordina_unita_per_fazione_e_nome(db_unita):
    """
    Restituisce le chiavi delle unità ordinate prima per Fazione e poi alfabeticamente per Nome.
    Esclude la chiave di reset/placeholder.
    """
    chiavi = [k for k in db_unita.keys() if k != "--- Seleziona o Resetta ---"]
    
    def chiave_ordinamento(chiave):
        dati = db_unita.get(chiave, {})
        fazione = dati.get("fazione", "")
        # Se la fazione non è specificata nel record, prova a ricavarla dal prefisso "Fazione: Nome"
        if not fazione or fazione == "---":
            fazione = chiave.split(": ")[0] if ": " in chiave else "Generica"
        
        nome = chiave.split(": ")[-1] if ": " in chiave else chiave
        return (fazione.lower(), nome.lower())

    return sorted(chiavi, key=chiave_ordinamento)


def ordina_supporti_per_fazione_e_nome(db_supporti):
    """
    Ordina tratti o artefatti strutturati.
    Mette sempre 'Nessuno' al primo posto, poi 'Generale', poi le fazioni specifiche in ordine alfabetico,
    e all'interno di ogni fazione i nomi in ordine alfabetico.
    """
    chiavi = [k for k in db_supporti.keys() if k != "Nessuno"]
    
    def chiave_ordinamento(nome):
        dati = db_supporti.get(nome, {})
        fazione = dati.get("fazione", "Generale")
        # Assegna priorità: "Generale" per primo (0), le altre fazioni alfabetiche dopo (1)
        priorita = 0 if fazione.lower() == "generale" else 1
        return (priorita, fazione.lower(), nome.lower())

    ordinati = sorted(chiavi, key=chiave_ordinamento)
    
    # Se "Nessuno" esiste nel DB, lo rimettiamo sempre in testa
    if "Nessuno" in db_supporti:
        return ["Nessuno"] + ordinati
    return ordinati