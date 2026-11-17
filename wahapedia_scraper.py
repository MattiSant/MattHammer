import re
import requests
from html.parser import HTMLParser
from ability_parser import analizza_abilita_warscroll
from utils import estrai_intero_sicuro

FAZIONI_SLUG_WAHAPEDIA = {
    "Nighthaunt": "nighthaunt",
    "Blades of Khorne": "blades-of-khorne",
    "Orruk Kruleboyz": "orruk-warclans",
    "Orruk Warclans": "orruk-warclans",
    "Sylvaneth": "sylvaneth",
    "Stormcast Eternals": "stormcast-eternals",
    "Skaven": "skaven",
    "Slaves to Darkness": "slaves-to-darkness",
    "Soulblight Gravelords": "soulblight-gravelords",
    "Ossiarch Bonereapers": "ossiarch-bonereapers",
    "Flesh-eater Courts": "flesh-eater-courts",
    "Gloomspite Gitz": "gloomspite-gitz",
    "Seraphon": "seraphon",
    "Cities of Sigmar": "cities-of-sigmar",
    "Daughters of Khaine": "daughters-of-khaine",
    "Lumineth Realm-lords": "lumineth-realm-lords",
    "Idoneth Deepkin": "idoneth-deepkin",
    "Kharadron Overlords": "kharadron-overlords",
    "Fyreslayers": "fyreslayers",
    "Maggotkin of Nurgle": "maggotkin-of-nurgle",
    "Disciples of Tzeentch": "disciples-of-tzeentch",
    "Hedonites of Slaanesh": "hedonites-of-slaanesh",
    "Ogor Mawtribes": "ogor-mawtribes",
    "Sons of Behemat": "sons-of-behemat"
}

# Mappa inversa da slug minuscolo di Wahapedia al nome esatto usato nell'app
SLUG_TO_FAZIONE = {v.lower(): k for k, v in FAZIONI_SLUG_WAHAPEDIA.items()}
SLUG_TO_FAZIONE["orruk-warclans"] = "Orruk Kruleboyz"  # o "Orruk Warclans" in base alla tua preferenza

def estrai_fazione_da_url_o_testo(url_o_testo, default_fazione="Nighthaunt"):
    """
    Riconosce automaticamente la fazione:
    1) Dall'URL Wahapedia: https://wahapedia.ru/aos4/factions/<slug-fazione>/<unita>
    2) Dal banner testuale: •<FAZIONE> WARSCROLL•
    """
    txt = (url_o_testo or "").strip()
    
    # 1. Estrazione diretta dal link di Wahapedia
    m_url = re.search(r"/aos4/factions/([^/\s\?#]+)", txt, flags=re.IGNORECASE)
    if m_url:
        slug = m_url.group(1).strip().lower()
        if slug in SLUG_TO_FAZIONE:
            return SLUG_TO_FAZIONE[slug]
        for k_app, v_slug in FAZIONI_SLUG_WAHAPEDIA.items():
            if v_slug.lower() == slug or k_app.lower().replace(" ", "-") == slug:
                return k_app

    # 2. Fallback: estrazione dal banner •FAZIONE WARSCROLL• se è stato incollato il testo
    m_ban = re.search(r"•\s*([^•\n]+?)\s+WARSCROLL\s*•", txt, flags=re.IGNORECASE)
    if m_ban:
        faz_ban = m_ban.group(1).strip().lower()
        for k_app in FAZIONI_SLUG_WAHAPEDIA.keys():
            if k_app.lower() in faz_ban or faz_ban in k_app.lower():
                return k_app

    return default_fazione

ABILITA_CORE_DA_IGNORARE = {
    "fly", "retreat", "charge", "fight", "shoot", "normal move", "run",
    "guarded hero", "ward", "companion", "crit (mortal)", "crit (auto-wound)",
    "crit (2 hits)", "shoot in combat", "anti-charge", "obscuring", "cover",
    "in combat", "combat range", "visibility", "coherency", "mortal damage",
    "wound roll", "hit roll", "save roll", "ward save", "rally", "all-out attack",
    "all-out defence", "redeploy", "forward to victory", "counter-charge",
    "magical intervention", "counter-magic", "power through", "pile-in", "pile in",
    "auto-wound", "beast", "champion", "musician", "standard bearer", "priest", "wizard"
}


def _normalizza_trattini(testo):
    """Converte tutti i trattini Unicode (es. non-breaking hyphen \u2011 di Wahapedia) in '-' standard."""
    if not testo:
        return ""
    return re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2212‐‑‒–—]", "-", str(testo))


class _WahapediaHTMLParser(HTMLParser):
    """
    Parser HTML nativo per Wahapedia AoS 4e:
    - NON ignora <span class="tooltip"> o <a class="tooltip">, perché lì dentro Wahapedia
      scrive 'Crit (Auto-wound)', 'Anti-X (+1 Rend)', 'Companion', ecc.!
    - Ignora invece solo i <div> nascosti di template tooltip in fondo alla pagina
      (style='display:none', id='tooltip_content...', class='tooltip_templates').
    """
    def __init__(self):
        super().__init__()
        self.ignore_tags = {"script", "style", "nav", "footer", "noscript"}
        self.ignore_depth = 0
        self.in_tr = False
        self.in_td = False
        self.in_title = False
        self.page_title = ""
        self.current_row = []
        self.current_cell = []
        self.rows = []
        self.text_chunks = []

    def handle_starttag(self, tag, attrs):
        tag_l = tag.lower()
        if self.ignore_depth > 0:
            self.ignore_depth += 1
            return

        if tag_l == "title":
            self.in_title = True
            return

        attr_dict = {k.lower(): (v or "").lower() for k, v in attrs}
        cls_s = attr_dict.get("class", "")
        id_s = attr_dict.get("id", "")
        style_s = attr_dict.get("style", "").replace(" ", "")

        # Ignora solo contenitori <div> nascosti o template popup, MAI <span> o <a>!
        is_hidden_div = tag_l == "div" and (
            "tooltip_templates" in cls_s
            or "tooltip_content" in id_s
            or "tooltip" in id_s
            or "d_mob" in cls_s.split()
            or "nav" in cls_s.split()
        )
        if (
            tag_l in self.ignore_tags
            or "display:none" in style_s
            or "visibility:hidden" in style_s
            or is_hidden_div
        ):
            self.ignore_depth = 1
            return

        if tag_l == "tr":
            self.in_tr = True
            self.current_row = []
            self.text_chunks.append("\n")
        elif tag_l in ("td", "th") and self.in_tr:
            self.in_td = True
            self.current_cell = []
            self.text_chunks.append(" ")
        elif tag_l in ("br", "p", "div", "li", "h1", "h2", "h3", "h4", "table"):
            if self.in_td:
                self.current_cell.append(" | ")
            self.text_chunks.append("\n")
        elif tag_l in ("span", "b", "strong", "i", "a"):
            self.text_chunks.append(" ")

    def handle_endtag(self, tag):
        tag_l = tag.lower()
        if tag_l == "title":
            self.in_title = False
            return
        if self.ignore_depth > 0:
            self.ignore_depth -= 1
            return

        if tag_l in ("td", "th") and self.in_td:
            cell_txt = _normalizza_trattini(re.sub(r"\s+", " ", "".join(self.current_cell)).strip())
            self.current_row.append(cell_txt)
            self.in_td = False
            self.text_chunks.append(" ")
        elif tag_l == "tr" and self.in_tr:
            if any(self.current_row):
                self.rows.append(self.current_row)
            self.in_tr = False
            self.text_chunks.append("\n")
        elif tag_l in ("div", "p", "li", "h1", "h2", "h3", "h4", "table") and not self.in_td:
            self.text_chunks.append("\n")

    def handle_data(self, data):
        if self.in_title:
            self.page_title += data
            return
        if self.ignore_depth == 0:
            if self.in_td:
                self.current_cell.append(data)
            self.text_chunks.append(data)

    def get_clean_text(self):
        raw = _normalizza_trattini("".join(self.text_chunks))
        linee = [re.sub(r"[ \t]+", " ", l).strip() for l in raw.split("\n")]
        return "\n".join([l for l in linee if l])


def costruisci_url_wahapedia(fazione, nome_unita):
    slug_fazione = FAZIONI_SLUG_WAHAPEDIA.get(fazione, fazione.lower().replace(" ", "-"))
    parole_pic = {"of", "on", "with", "the", "and", "in", "to", "for", "a"}
    tokens = re.split(r"[\s\-]+", nome_unita.strip())
    slug_tokens = []
    for i, t in enumerate(tokens):
        t_clean = re.sub(r"[^a-zA-Z0-9']", "", t)
        if i > 0 and t_clean.lower() in parole_pic:
            slug_tokens.append(t_clean.lower())
        else:
            slug_tokens.append(t_clean.capitalize())
    slug_unita = "-".join(slug_tokens)
    return f"https://wahapedia.ru/aos4/factions/{slug_fazione}/{slug_unita}"


def _estrai_nome_unita_sicuro(corpo_ws, page_title="", nome_fallback=""):
    """
    Estrae il nome dell'unità con triplo controllo:
    1) Dal testo subito dopo '•... WARSCROLL•' e prima di 'Damage calculator' / 'RANGED WEAPONS' / 'MELEE WEAPONS'
    2) Dal tag <title> della pagina Wahapedia (es. 'Knight of Shrouds — Nighthaunt [Age of Sigmar...]')
    3) Dall'URL o nome_fallback.
    """
    # 1. Cerca tra l'inizio di corpo_ws (subito dopo •WARSCROLL•) e 'Damage calculator' o 'WEAPONS'
    m_prima_dc = re.search(
        r"^\s*([^\n•]{2,65}?)(?:\s+Damage\s+calculator|\s*\n\s*Damage\s+calculator|\s*\n\s*(?:RANGED|MELEE)\s+WEAPONS)",
        corpo_ws.strip(),
        flags=re.IGNORECASE | re.DOTALL
    )
    if m_prima_dc:
        candidato = re.sub(r"\s+", " ", m_prima_dc.group(1)).strip(" .•-\n\t")
        if 2 <= len(candidato) <= 55 and not any(k in candidato.upper() for k in ["WARSCROLL", "WEAPONS", "MOVE", "BATTLE PROFILE"]):
            return candidato

    # 2. Dal <title> della pagina HTML (es. "Guardian of Souls — Nighthaunt...")
    if page_title:
        t_norm = _normalizza_trattini(page_title)
        if "-" in t_norm:
            cand_t = t_norm.split("-")[0].strip()
            if 2 <= len(cand_t) <= 55 and "warscrolls" not in cand_t.lower():
                return cand_t

    return nome_fallback.strip() or "Unità Importata"


def _estrai_statistiche_cerchio(testo_pre, testo_corpo):
    combinato = testo_pre + "\n" + testo_corpo[:400]
    pattern_ruota = re.compile(
        r"\b(\d{1,2}\"|2D6\"|3D6\"|D6\")\s*"
        r"(\d{1,2})\.?\s*"
        r"([2-6]\+|\-)\.?\s*"
        r"(\d{1,2}|\-)\.?"
        r"(?:\s*([456]\+))?",
        re.MULTILINE
    )
    matches = list(pattern_ruota.finditer(combinato))
    if matches:
        m = matches[-1]
        return {
            "movimento": m.group(1),
            "salute": max(1, int(m.group(2))),
            "save": m.group(3),
            "controllo": int(m.group(4)) if m.group(4).isdigit() else 1,
            "ward": m.group(5) if m.group(5) else None
        }
    return None


def _pulisci_nome_arma(nome_grezzo):
    txt = _normalizza_trattini(nome_grezzo).strip()
    if "[" in txt:
        prima_parte = txt.split("[")[0].strip()
        linee_p = [l.strip(" ,-\t•.") for l in prima_parte.split("\n") if l.strip(" ,-\t•.")]
        if linee_p:
            txt = linee_p[-1]
    else:
        linee_p = [l.strip(" ,-\t•.") for l in txt.split("\n") if l.strip(" ,-\t•.")]
        if linee_p:
            txt = linee_p[-1]

    # Rimuove qualsiasi tag abilità dal nome dell'arma
    txt = re.sub(r"Crit\s*\([^\)]+\)", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"Anti-[A-Za-z\s]+(?:\(\+1\s*Rend\))?", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"Charge\s*\(\+1\s*Damage\)", "", txt, flags=re.IGNORECASE)
    for tag in ["Shoot in Combat", "Companion", "Damage calculator", "(+1 Rend)"]:
        txt = re.sub(re.escape(tag), "", txt, flags=re.IGNORECASE)

    txt = re.sub(r"\s+", " ", txt).strip(" ,-\t\n•.[]")

    parti_punto = [p.strip() for p in txt.split(".") if p.strip()]
    if len(parti_punto) >= 2 and parti_punto[0].lower() == parti_punto[1].lower():
        txt = parti_punto[0]

    parole = txt.split()
    n_p = len(parole)
    if n_p >= 2 and n_p % 2 == 0:
        meta = n_p // 2
        if " ".join(parole[:meta]).lower() == " ".join(parole[meta:]).lower():
            txt = " ".join(parole[:meta])

    return txt.strip(" ,-\t\n•.[]")


def _parsa_riga_arma(nome_arma_grezzo, gittata, atk, hit_str, wnd_str, rnd_str, dmg, abilita_extra=""):
    nome_arma_norm = _normalizza_trattini(nome_arma_grezzo)
    abilita_extra_norm = _normalizza_trattini(abilita_extra)

    nome_pulito = _pulisci_nome_arma(nome_arma_norm)
    if not nome_pulito or nome_pulito.lower() in [
        "ranged weapons", "melee weapons", "weapon", "weapons", "view conditions", "damage calculator", "atk", "rng"
    ]:
        return None

    ranged = True if (gittata and gittata.strip() not in ["-", "---", "Melee", ""]) else False
    range_val = gittata.strip() if ranged else "Melee"

    atk_val = str(atk).strip().upper().replace(" ", "").rstrip(".")
    hit_val = estrai_intero_sicuro(hit_str, default=4)
    wnd_val = estrai_intero_sicuro(wnd_str, default=4)
    rnd_clean = str(rnd_str).strip().rstrip(".")
    rend_val = 0 if rnd_clean in ["-", "–", "---", "0", ""] else estrai_intero_sicuro(rnd_clean, default=0)
    dmg_val = str(dmg).strip().upper().replace(" ", "").rstrip(".")

    # Cerca i tag abilità con regex flessibili (così cattura Crit (Auto-wound), Anti-X, Charge (+1 Damage), Companion)
    ab_up = f"{nome_arma_norm} {abilita_extra_norm}".upper()

    crit = "Nessuno"
    if re.search(r"CRIT\s*\(\s*MORTAL\s*\)", ab_up):
        crit = "Crit (Mortal)"
    elif re.search(r"CRIT\s*\(\s*AUTO\s*[\-\s]?\s*WOUND\s*\)", ab_up):
        crit = "Crit (Auto-wound)"
    elif re.search(r"CRIT\s*\(\s*2\s*HITS\s*\)", ab_up):
        crit = "Crit (2 Hits)"

    anti = "Nessuno"
    anti_charge_flag = False
    if re.search(r"ANTI\s*[\-\s]\s*CHARGE", ab_up):
        anti = "CHARGE"
        anti_charge_flag = True
    elif re.search(r"ANTI\s*[\-\s]\s*HERO", ab_up):
        anti = "HERO"
    elif re.search(r"ANTI\s*[\-\s]\s*INFANTRY", ab_up):
        anti = "INFANTRY"
    elif re.search(r"ANTI\s*[\-\s]\s*MONSTER", ab_up):
        anti = "MONSTER"
    elif re.search(r"ANTI\s*[\-\s]\s*CAVALRY", ab_up):
        anti = "CAVALRY"
    elif re.search(r"ANTI\s*[\-\s]\s*WAR\s*MACHINE", ab_up):
        anti = "WAR MACHINE"
    elif re.search(r"ANTI\s*[\-\s]\s*BEAST", ab_up):
        anti = "BEAST"

    charge_dmg_flag = bool(re.search(r"CHARGE\s*\(\s*\+1\s*DAMAGE\s*\)", ab_up))
    companion_flag = "COMPANION" in ab_up

    return {
        "nome": nome_pulito,
        "attiva": True,
        "ranged": ranged,
        "range": range_val,
        "atk": atk_val,
        "hit": hit_val,
        "wnd": wnd_val,
        "rend": rend_val,
        "dmg": dmg_val,
        "crit_type": crit,
        "anti_target": anti,
        "charge_dmg": charge_dmg_flag,
        "anti_charge": anti_charge_flag,
        "companion": companion_flag
    }


def estrai_armi_da_testo_o_html(corpo_ws, righe_tabella_html=None):
    """
    Estrae tutte le armi gestendo anche la struttura a 2 righe di Wahapedia:
    - Riga 1 (colspan): 'Sword of Stolen Hours [Crit (Auto-wound)]'
    - Riga 2 (numeri):  ['5', '4+', '3+', '1', '2'] oppure ['Sword of Stolen Hours...', '5', '4+', '3+', '1', '2']
    """
    armi = []
    nomi_armi_visti = set()

    if righe_tabella_html:
        ultimo_header_arma = ""
        for celle in righe_tabella_html:
            celle_pulite = [_normalizza_trattini(c).strip() for c in celle if c.strip()]
            if not celle_pulite:
                continue

            # Se è la riga 1 con solo il Nome Arma + [Abilità] (1 o 2 celle senza statistiche X+)
            if len(celle_pulite) <= 2 and not any(re.match(r"^[2-6]\+$", c) for c in celle_pulite):
                testo_c = " ".join(celle_pulite)
                if not any(h in testo_c.upper() for h in ["WEAPONS", "DAMAGE CALCULATOR", "VIEW CONDITIONS"]):
                    ultimo_header_arma = testo_c
                continue

            # Caso Ranged o Melee con 5, 6, 7 o 8 celle
            # Cerchiamo la coppia adiacente (Hit, Wnd) nel formato [2-6]+
            idx_hit = -1
            for i in range(len(celle_pulite) - 2):
                if re.match(r"^[2-6]\+$", celle_pulite[i]) and re.match(r"^[2-6]\+$", celle_pulite[i + 1]):
                    idx_hit = i
                    break

            if idx_hit >= 1 and idx_hit + 3 < len(celle_pulite):
                atk_c = celle_pulite[idx_hit - 1]
                hit_c = celle_pulite[idx_hit]
                wnd_c = celle_pulite[idx_hit + 1]
                rnd_c = celle_pulite[idx_hit + 2]
                dmg_c = celle_pulite[idx_hit + 3]
                ab_dopo = " ".join(celle_pulite[idx_hit + 4:]) if idx_hit + 4 < len(celle_pulite) else ""

                gittata_c = None
                nome_cella = ""
                if idx_hit >= 2 and re.match(r"^\d{1,2}\"$", celle_pulite[idx_hit - 2]):
                    gittata_c = celle_pulite[idx_hit - 2]
                    nome_cella = " ".join(celle_pulite[:idx_hit - 2])
                else:
                    nome_cella = " ".join(celle_pulite[:idx_hit - 1])

                nome_combinato = f"{ultimo_header_arma} {nome_cella}".strip() if ultimo_header_arma else nome_cella
                arma = _parsa_riga_arma(nome_combinato, gittata_c, atk_c, hit_c, wnd_c, rnd_c, dmg_c, ab_dopo)
                if arma and (arma["nome"].lower(), arma["ranged"]) not in nomi_armi_visti:
                    nomi_armi_visti.add((arma["nome"].lower(), arma["ranged"]))
                    armi.append(arma)
                ultimo_header_arma = ""

    if armi:
        return armi

    # Fallback multi-linea universale sul testo del corpo warscroll
    testo_sezione = _normalizza_trattini(corpo_ws)
    for marker_fine in ["BATTLE PROFILE", "View conditions"]:
        if marker_fine in testo_sezione:
            testo_sezione = testo_sezione.split(marker_fine)[0]
            break

    testo_pulito = re.sub(
        r"\b(?:RANGED\s+WEAPONS|MELEE\s+WEAPONS|Damage\s+calculator)\b"
        r"(?:[\s,]+(?:Rng|Atk|Hit|Wnd|Rnd|Dmg|Ability))*",
        "\n",
        testo_sezione,
        flags=re.IGNORECASE
    )

    pattern_arma_ml = re.compile(
        r"([^\n]+(?:\n[^\n]+)?)\s+"
        r"(?:(\d{1,2}\")[\s,]+)?"
        r"(\d+|[1-9]?D[36](?:\+\d+)?)[\s,]+"
        r"([2-6]\+)[\s,]+"
        r"([2-6]\+)[\s,]+"
        r"(\-|–|---|0|[1-5])[\s,]+"
        r"(\d+|[1-9]?D[36](?:\+\d+)?)\b",
        re.IGNORECASE
    )

    for m in pattern_arma_ml.finditer(testo_pulito):
        blocco_nome = m.group(1).strip()
        gittata = m.group(2)
        atk = m.group(3)
        hit = m.group(4)
        wnd = m.group(5)
        rnd = m.group(6)
        dmg = m.group(7)

        arma = _parsa_riga_arma(blocco_nome, gittata, atk, hit, wnd, rnd, dmg)
        if arma and (arma["nome"].lower(), arma["ranged"]) not in nomi_armi_visti:
            nomi_armi_visti.add((arma["nome"].lower(), arma["ranged"]))
            armi.append(arma)

    return armi


def estrai_abilita_multiple_da_testo(corpo_ws):
    abilita_trovate = []
    nomi_visti = set()

    testo_ab = corpo_ws.split("BATTLE PROFILE", 1)[1] if "BATTLE PROFILE" in corpo_ws else corpo_ws

    linee = [l.strip() for l in testo_ab.split("\n") if l.strip()]
    pattern_header_fase = re.compile(
        r"^(?:Passive|Once Per (?:Turn|Battle).*|Any .* Phase|Your .* Phase|Enemy .* Phase|Deployment Phase|Start of .*|End of .*|Reaction:.*)$",
        re.IGNORECASE
    )

    indici_inizio = [i for i, l in enumerate(linee) if pattern_header_fase.match(l)]
    for idx_pos, start_i in enumerate(indici_inizio):
        end_i = indici_inizio[idx_pos + 1] if idx_pos + 1 < len(indici_inizio) else min(len(linee), start_i + 12)
        blocco_linee = []
        for l_sub in linee[start_i:end_i]:
            if l_sub.upper().startswith(("KEYWORDS", "UNIT SIZE:", "POINTS:", "BASE SIZE:", "CAN BE REINFORCED:", "REGIMENT OPTIONS:", "NOTES:")):
                continue
            if "keyword is used in the following" in l_sub.lower():
                break
            blocco_linee.append(l_sub)

        blocco_txt = "\n".join(blocco_linee)
        if "effect:" in blocco_txt.lower() or "effetto:" in blocco_txt.lower():
            ab_parsed = analizza_abilita_warscroll(blocco_txt)
            if ab_parsed:
                nome_low = ab_parsed["nome"].strip().lower()
                if nome_low in ABILITA_CORE_DA_IGNORARE or any(
                    nome_low.startswith(core_k + ":") or nome_low == core_k
                    for core_k in ABILITA_CORE_DA_IGNORARE
                ):
                    continue
                if nome_low not in nomi_visti:
                    nomi_visti.add(nome_low)
                    abilita_trovate.append(ab_parsed)

    return abilita_trovate


def _isola_sezioni_warscroll(testo_intero):
    m_ws = list(re.finditer(r"•[^•\n]*WARSCROLL•", testo_intero, flags=re.IGNORECASE))
    if m_ws:
        idx_inizio_stats = max(0, m_ws[0].start() - 1500)
        idx_inizio_corpo = m_ws[0].end()
        testo_pre_header = testo_intero[idx_inizio_stats:idx_inizio_corpo]
        resto = testo_intero[idx_inizio_corpo:]
    else:
        testo_pre_header = testo_intero[:1200]
        resto = testo_intero

    # Taglia subito via la coda dei riferimenti di fine pagina ("The X keyword is used in...")
    m_footer_kw = re.search(r"The\s+[A-Z\s\-]+\s+keyword\s+is\s+used\s+in", resto)
    if m_footer_kw:
        resto = resto[:m_footer_kw.start()]

    matches_kw = list(re.finditer(r"\bKEYWORDS\b", resto))
    corpo_ws = resto
    coda_kw = ""

    # Scorre i blocchi KEYWORDS dal fondo per trovare la barra principale della Warscroll
    # (che contiene sempre almeno una Grande Alleanza, la Fazione o un Ruolo unità)
    marker_unita = [
        "ORDER", "CHAOS", "DEATH", "DESTRUCTION",
        "HERO", "INFANTRY", "CAVALRY", "MONSTER", "WAR MACHINE", "BEAST", "MANIFESTATION"
    ]
    for m_k in reversed(matches_kw):
        finestra = resto[m_k.end():m_k.end() + 260]
        if any(mk in finestra.upper() for mk in marker_unita):
            corpo_ws = resto[:m_k.start()]
            coda_kw = finestra
            break

    return testo_pre_header, corpo_ws, coda_kw


def analizza_warscroll_completa(testo_intero, parser_html=None, fazione_default="Nighthaunt", nome_default=""):
    testo_intero = _normalizza_trattini(testo_intero)
    risultato = {
        "fazione": fazione_default,
        "nome": nome_default or "Unità Importata",
        "punti": 100,
        "n_modelli": 1,
        "basetta": "32mm",
        "puo_rinforzare": True,
        "campione": False,
        "movimento": '6"',
        "salute": 2,
        "save": "4+",
        "controllo": 1,
        "ward": "7+",
        "armi": [],
        "abilita": [],
        "keywords": []
    }

    testo_pre, corpo_ws, coda_kw = _isola_sezioni_warscroll(testo_intero)
    titolo_pag = parser_html.page_title if parser_html is not None else ""
    risultato["nome"] = _estrai_nome_unita_sicuro(corpo_ws, page_title=titolo_pag, nome_fallback=nome_default)

    stats_ruota = _estrai_statistiche_cerchio(testo_pre, corpo_ws)
    if stats_ruota:
        risultato["movimento"] = stats_ruota["movimento"]
        risultato["salute"] = stats_ruota["salute"]
        risultato["save"] = stats_ruota["save"]
        risultato["controllo"] = stats_ruota["controllo"]
        if stats_ruota["ward"]:
            risultato["ward"] = stats_ruota["ward"]
    else:
        m_mov = re.search(r"(?:Move|Movimento)\s*[:\-]?\s*(\d+\")", testo_intero, re.I)
        if m_mov:
            risultato["movimento"] = m_mov.group(1)
        m_hp = re.search(r"(?:Health|Wounds|Salute)\s*[:\-]?\s*(\d{1,2})\b", testo_intero, re.I)
        if m_hp:
            risultato["salute"] = max(1, int(m_hp.group(1)))
        m_sv = re.search(r"(?:Save|Salvezza)\s*[:\-]?\s*([2-6]\+|\-)", testo_intero, re.I)
        if m_sv:
            risultato["save"] = m_sv.group(1)
        m_oc = re.search(r"(?:Control|Controllo)\s*[:\-]?\s*(\d{1,2})\b", testo_intero, re.I)
        if m_oc:
            risultato["controllo"] = int(m_oc.group(1))

    m_size = re.search(r"(?:Unit\s*Size|Modelli)\s*[:\-]?\s*(\d{1,2})", corpo_ws, re.I)
    if m_size:
        risultato["n_modelli"] = max(1, int(m_size.group(1)))

    m_pts = re.search(r"(?:Points|Punti|Cost)\s*[:\-]?\s*(\d{2,4})|(\d{2,3})\s*(?:pts|pt\b)", corpo_ws, re.I)
    if m_pts:
        pt_v = int(m_pts.group(1) or m_pts.group(2))
        if 40 <= pt_v <= 2000:
            risultato["punti"] = pt_v

    m_base = re.search(r"Base\s*size\s*:\s*([^\n\.]+?mm)|(\d+(?:\s*[x×]\s*\d+)?\s*mm)", corpo_ws, re.I)
    if m_base:
        b_raw = (m_base.group(1) or m_base.group(2)).replace("×", "x")
        risultato["basetta"] = re.sub(r"\s+", "", b_raw)

    m_reinf = re.search(r"Can\s+be\s+reinforced\s*:\s*(Yes|No)", corpo_ws, re.I)
    if m_reinf:
        risultato["puo_rinforzare"] = (m_reinf.group(1).lower() == "yes")

    if coda_kw:
        linee_kw = []
        for l_k in [l.strip() for l in coda_kw.split("\n") if l.strip()]:
            if any(stop_w in l_k.lower() for stop_w in [
                "keyword is used", "when a unit", "declare:", "effect:", "passive",
                "phase", "roll a dice", "if an attack", "a model is", "soaring above",
                "each time", "pick a", "target"
            ]):
                break
            linee_kw.append(l_k)
            if len(linee_kw) >= 2:  # Le unità AoS 4e hanno sempre 2 righe di keywords in fondo
                break

        # Unisce le due righe con una virgola e divide su virgola, pipe (|) o bullet (•)
        blocco_kw_unito = ", ".join(linee_kw)
        kws_grezze = re.split(r"[,|•\n]+", blocco_kw_unito)
        parole_ab_escluse = {"keywords", "keyword", "spell", "prayer", "rampage", "core", "unlimited", "summon"}
        kws_pulite = []
        for k in kws_grezze:
            # Rimuove la parola KEYWORDS se rimasta attaccata all'inizio
            k_clean = re.sub(r"^\s*keywords?\s*[:\-]?\s*", "", k, flags=re.IGNORECASE).strip(" .•-\t")
            if k_clean and k_clean.lower() not in parole_ab_escluse and len(k_clean) < 35:
                if k_clean.upper() not in [x.upper() for x in kws_pulite]:
                    kws_pulite.append(k_clean)
        risultato["keywords"] = kws_pulite

    kw_upper_str = " , ".join(risultato["keywords"]).upper()
    m_ward_kw = re.search(r"WARD\s*\(([456]\+)\)", kw_upper_str)
    if m_ward_kw:
        risultato["ward"] = m_ward_kw.group(1)
    if "CHAMPION" in kw_upper_str:
        risultato["campione"] = True
    if "HERO" in kw_upper_str and not m_size:
        risultato["n_modelli"] = 1
        risultato["puo_rinforzare"] = False
    if "UNIQUE" in kw_upper_str:
        risultato["puo_rinforzare"] = False

    righe_html = parser_html.rows if parser_html is not None else None
    risultato["armi"] = estrai_armi_da_testo_o_html(corpo_ws, righe_tabella_html=righe_html)
    risultato["abilita"] = estrai_abilita_multiple_da_testo(corpo_ws)

    for ab in risultato["abilita"]:
        w_ab = ab.get("modificatori", {}).get("ward_nativo")
        if w_ab in [4, 5, 6] and risultato["ward"] == "7+":
            risultato["ward"] = f"{w_ab}+"

    return risultato


def converti_warscroll_in_record_db(dati_w, fazione):
    """Converte il dizionario estratto da Wahapedia nel formato esatto di units_db.json."""
    s_int = estrai_intero_sicuro(dati_w.get("save", "4+"), default=7)
    w_int = estrai_intero_sicuro(dati_w.get("ward", "7+"), default=7)
    return {
        "fazione": fazione,
        "n_modelli": dati_w["n_modelli"],
        "dimensione_basetta": dati_w["basetta"],
        "può_essere_rinforzata": dati_w["puo_rinforzare"],
        "campione": dati_w["campione"],
        "punti": dati_w["punti"],
        "statistiche_cerchio": {
            "movimento": dati_w["movimento"],
            "controllo": dati_w["controllo"],
            "save": dati_w["save"],
            "salute": dati_w["salute"],
            "ward": dati_w["ward"]
        },
        "difesa": {
            "salute_per_modello": dati_w["salute"],
            "save": s_int,
            "ward": w_int
        },
        "armi": dati_w["armi"],
        "abilita": dati_w["abilita"],
        "keywords": dati_w["keywords"]
    }


def scarica_warscroll_da_wahapedia(url_o_testo, fazione="Nighthaunt", nome_unita=""):
    fazione = estrai_fazione_da_url_o_testo(url_o_testo, default_fazione=fazione)
    inp = (url_o_testo or "").strip()
    if not inp and nome_unita.strip():
        inp = costruisci_url_wahapedia(fazione, nome_unita)

    if not inp:
        return None, "Inserisci un URL di Wahapedia, un Nome Unità oppure incolla il testo della Warscroll.", False

    if inp.startswith("http://") or inp.startswith("https://"):
        # Se è un URL, il fallback del nome viene SEMPRE preso dallo slug dell'URL (mai dal vecchio nome in sessione!)
        nome_da_url = inp.rstrip("/").split("/")[-1].replace(".html", "").replace("-", " ")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,it;q=0.8"
        }
        try:
            resp = requests.get(inp, headers=headers, timeout=12)
            if resp.status_code == 200:
                parser = _WahapediaHTMLParser()
                parser.feed(resp.text)
                testo_pagina = parser.get_clean_text()
                dati = analizza_warscroll_completa(testo_pagina, parser_html=parser, fazione_default=fazione, nome_default=nome_da_url)
                return dati, f"Warscroll '{dati['nome']}' scaricata ({len(dati['armi'])} armi, {len(dati['abilita'])} abilità)!", True
            elif resp.status_code in [403, 503]:
                return None, "Wahapedia ha protetto la pagina con Cloudflare (403). Apri la pagina nel browser, premi CTRL+A e CTRL+C e incolla tutto il testo nel box qui sotto!", False
            else:
                return None, f"Pagina non trovata su Wahapedia (HTTP {resp.status_code}). Verifica l'URL: {inp}", False
        except Exception as e:
            return None, f"Errore di rete durante il collegamento a Wahapedia: {e}", False

    dati = analizza_warscroll_completa(inp, parser_html=None, fazione_default=fazione, nome_default=nome_unita or "Unità Wahapedia")
    return dati, f"Warscroll '{dati['nome']}' analizzata: {len(dati['armi'])} armi e {len(dati['abilita'])} abilità estratte!", True


def sincronizza_fazione_da_wahapedia(fazione, db_unita_attuale, testo_collated_opzionale=""):
    if testo_collated_opzionale:
        fazione = estrai_fazione_da_url_o_testo(testo_collated_opzionale, default_fazione=fazione)
    """
    Aggiorna automaticamente in blocco tutte le unità della fazione desiderata e compila il dizionario del DB:
    1) Prova prima a scaricare la pagina riepilogativa di tutte le Warscrolls della fazione:
       https://wahapedia.ru/aos4/factions/{slug_fazione}/warscrolls.html
       (oppure analizza il testo incollato se fornito in 'testo_collated_opzionale').
    2) Inoltre, aggiorna via URL individuale eventuali unità di quella fazione già presenti in db_unita_attuale.
    Restituisce: (n_unita_aggiornate, elenco_nomi_aggiornati, messaggio_stato, successo_bool)
    """
    slug_fazione = FAZIONI_SLUG_WAHAPEDIA.get(fazione, fazione.lower().replace(" ", "-"))
    url_warscrolls_fazione = f"https://wahapedia.ru/aos4/factions/{slug_fazione}/warscrolls.html"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    testo_sorgente = (testo_collated_opzionale or "").strip()
    if not testo_sorgente or testo_sorgente.startswith("http"):
        url_target = testo_sorgente if testo_sorgente.startswith("http") else url_warscrolls_fazione
        try:
            resp = requests.get(url_target, headers=headers, timeout=15)
            if resp.status_code == 200:
                p_all = _WahapediaHTMLParser()
                p_all.feed(resp.text)
                testo_sorgente = p_all.get_clean_text()
            elif resp.status_code in [403, 503]:
                return 0, [], f"Cloudflare (403) ha bloccato il download massivo da {url_target}. Apri {url_warscrolls_fazione} nel browser, premi CTRL+A / CTRL+C e incolla tutto nel box per aggiornare l'intera fazione in un click!", False
        except Exception as e:
            return 0, [], f"Errore di rete durante la sincronizzazione fazione: {e}", False

    unita_aggiornate = []

    # Divide la pagina 'warscrolls.html' in blocchi, uno per ogni '•... WARSCROLL•'
    matches_ws = list(re.finditer(r"•[^•\n]*WARSCROLL•", testo_sorgente, flags=re.IGNORECASE))
    if matches_ws:
        for i, m_w in enumerate(matches_ws):
            start_chunk = max(0, m_w.start() - 400)
            end_chunk = matches_ws[i + 1].start() - 120 if i + 1 < len(matches_ws) else len(testo_sorgente)
            chunk_unita = testo_sorgente[start_chunk:end_chunk]

            # Passiamo None come parser_html così usa l'estrattore multi-linea universale sul singolo blocco
            dati_u = analizza_warscroll_completa(chunk_unita, parser_html=None, fazione_default=fazione)
            nome_u = dati_u["nome"].strip()
            if nome_u and nome_u != "Unità Importata" and (dati_u["armi"] or dati_u["abilita"]):
                chiave_db = f"{fazione}: {nome_u}"
                db_unita_attuale[chiave_db] = converti_warscroll_in_record_db(dati_u, fazione)
                unita_aggiornate.append(nome_u)

    # Se non era una pagina multipla ma non abbiamo ancora aggiornato le unità esistenti nel DB,
    # prova ad aggiornare singolarmente le unità della fazione già presenti nel database
    if not unita_aggiornate:
        chiavi_fazione = [
            k for k, v in db_unita_attuale.items()
            if k != "--- Seleziona o Resetta ---" and (v.get("fazione") == fazione or k.startswith(f"{fazione}:"))
        ]
        for k_u in chiavi_fazione:
            nome_solo = k_u.split(": ")[-1] if ": " in k_u else k_u
            dati_sing, _, ok_s = scarica_warscroll_da_wahapedia("", fazione=fazione, nome_unita=nome_solo)
            if ok_s and dati_sing and (dati_sing["armi"] or dati_sing["abilita"]):
                db_unita_attuale[k_u] = converti_warscroll_in_record_db(dati_sing, fazione)
                unita_aggiornate.append(nome_solo)

    if unita_aggiornate:
        return len(unita_aggiornate), unita_aggiornate, f"Sincronizzate e aggiornate {len(unita_aggiornate)} unità per la fazione {fazione}!", True
    return 0, [], f"Nessuna Warscroll trovata per {fazione}. Verifica la connessione o incolla il testo di {url_warscrolls_fazione}.", False

