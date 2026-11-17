import re
import requests
from html.parser import HTMLParser
from ability_parser import analizza_abilita_warscroll
from utils import estrai_intero_sicuro

FAZIONI_SLUG_WAHAPEDIA = {
    "Nighthaunt": "nighthaunt",
    "Blades of Khorne": "blades-of-khorne",
    "Orruk Kruleboyz": "orruk-warclans",
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

# Regole base / Keyword nei tooltip di Wahapedia che NON sono abilità specifiche dell'unità
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


class _WahapediaHTMLParser(HTMLParser):
    """
    Parser HTML nativo che:
    1) Scarta script, stili, menu e soprattutto i contenitori nascosti di tooltip
       (quelli che compaiono passandoci sopra col cursore per 'in combat', 'Fly', 'Retreat', ecc.).
    2) Raccoglie le righe delle tabelle (<tr>/<td>) mantenendo unito il testo di ogni cella.
    3) Produce il testo pulito della pagina per estrarre Statistiche, Battle Profile, Armi, Abilità e Keywords.
    """
    def __init__(self):
        super().__init__()
        self.ignore_tags = {"script", "style", "nav", "footer", "noscript"}
        self.ignore_depth = 0
        self.in_tr = False
        self.in_td = False
        self.current_row = []
        self.current_cell = []
        self.rows = []
        self.text_chunks = []

    def handle_starttag(self, tag, attrs):
        tag_l = tag.lower()
        if self.ignore_depth > 0:
            self.ignore_depth += 1
            return

        attr_dict = {k.lower(): (v or "").lower() for k, v in attrs}
        cls_s = attr_dict.get("class", "")
        id_s = attr_dict.get("id", "")
        style_s = attr_dict.get("style", "").replace(" ", "")

        # Ignora contenitori di tooltip in sovraimpressione, menu o blocchi duplicati mobile (d_mob)
        if (
            tag_l in self.ignore_tags
            or "display:none" in style_s
            or "visibility:hidden" in style_s
            or "tooltip" in id_s
            or "tooltip" in cls_s
            or "tippy" in cls_s
            or "d_mob" in cls_s.split()
            or "nav" in cls_s.split()
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
            if not self.in_td:
                self.text_chunks.append("\n")
            else:
                self.text_chunks.append(" ")
        elif tag_l in ("span", "b", "strong", "i", "a"):
            self.text_chunks.append(" ")

    def handle_endtag(self, tag):
        tag_l = tag.lower()
        if self.ignore_depth > 0:
            self.ignore_depth -= 1
            return

        if tag_l in ("td", "th") and self.in_td:
            cell_txt = re.sub(r"\s+", " ", "".join(self.current_cell)).strip()
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
        if self.ignore_depth == 0:
            if self.in_td:
                self.current_cell.append(data)
            self.text_chunks.append(data)

    def get_clean_text(self):
        raw = "".join(self.text_chunks)
        linee = [re.sub(r"[ \t]+", " ", l).strip() for l in raw.split("\n")]
        return "\n".join([l for l in linee if l])


def costruisci_url_wahapedia(fazione, nome_unita):
    """
    Genera automaticamente l'URL di Wahapedia AoS 4e a partire da Fazione e Nome Unità.
    Esempio: ('Nighthaunt', 'Black Coach') -> 'https://wahapedia.ru/aos4/factions/nighthaunt/Black-Coach'
    """
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


def _isola_sezioni_warscroll(testo_intero):
    """
    Divide il testo della pagina di Wahapedia in 3 blocchi precisi:
    1) testo_pre_header: i 1500 caratteri prima di '•... WARSCROLL•' (dove si trovano la ruota delle
       statistiche Move/Health/Save/Control/Ward seguita dal paragrafo di Lore).
    2) corpo_ws: solo il corpo della Warscroll (Armi, Battle Profile e Abilità dell'unità).
    3) coda_kw: le sole righe della barra KEYWORDS finale della Warscroll, tagliando via
       tutti i popup/tooltip che Wahapedia accoda in fondo alla pagina!
    """
    m_ws = list(re.finditer(r"•[^•\n]*WARSCROLL•", testo_intero, flags=re.IGNORECASE))
    if m_ws:
        idx_inizio_stats = max(0, m_ws[0].start() - 1500)
        idx_inizio_corpo = m_ws[0].end()
        testo_pre_header = testo_intero[idx_inizio_stats:idx_inizio_corpo]
        resto = testo_intero[idx_inizio_corpo:]
    else:
        testo_pre_header = testo_intero[:1200]
        resto = testo_intero

    # Cerca la barra KEYWORDS finale dell'unità (ignorando eventuali mini-tag KEYWORDS: SPELL / PRAYER / CORE)
    matches_kw = list(re.finditer(r"\bKEYWORDS\b", resto))
    corpo_ws = resto
    coda_kw = ""

    for m_k in matches_kw:
        finestra_dopo = resto[m_k.end():m_k.end() + 220]
        prima_riga_kw = finestra_dopo.strip().split("\n")[0].upper() if finestra_dopo.strip() else ""
        if any(w in prima_riga_kw for w in ["CORE", "SPELL", "PRAYER", "RAMPAGE", "UNLIMITED"]) and not any(
            u_kw in finestra_dopo.upper() for u_kw in [
                "HERO", "INFANTRY", "CAVALRY", "MONSTER", "WAR MACHINE", "BEAST",
                "ORDER", "CHAOS", "DEATH", "DESTRUCTION"
            ]
        ):
            continue
        corpo_ws = resto[:m_k.start()]
        coda_kw = resto[m_k.end():m_k.end() + 300]
        break

    return testo_pre_header, corpo_ws, coda_kw


def _estrai_statistiche_cerchio(testo_pre, testo_corpo):
    """
    Estrae Move, Health, Save, Control e Ward dalla ruota delle caratteristiche di Wahapedia AoS 4e.
    Su Wahapedia i numeri compaiono prima del testo di lore nel formato:
    10" 12 4+ 5. 5+  oppure  8" 5 5+ 2 5+  (sia sulla stessa riga sia su righe separate).
    """
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
    """
    Pulisce il nome dell'arma rimuovendo:
    - Le abilità tra parentesi quadre (es. "[Crit (Auto-wound)]")
    - Eventuali righe precedenti (es. il nome dell'unità se precede la prima arma)
    - Eventuali duplicazioni desktop/mobile (es. "Warblade Warblade")
    """
    txt = nome_grezzo.strip()
    if "[" in txt:
        prima_parte = txt.split("[")[0].strip()
        linee_p = [l.strip(" ,-\t•.") for l in prima_parte.split("\n") if l.strip(" ,-\t•.")]
        if linee_p:
            txt = linee_p[-1]
    else:
        linee_p = [l.strip(" ,-\t•.") for l in txt.split("\n") if l.strip(" ,-\t•.")]
        if linee_p:
            txt = linee_p[-1]

    for tag in [
        "Crit (Auto-wound)", "Crit (Mortal)", "Crit (2 Hits)", "Shoot in Combat",
        "Anti-HERO (+1 Rend)", "Anti-INFANTRY (+1 Rend)", "Anti-MONSTER (+1 Rend)",
        "Anti-CAVALRY (+1 Rend)", "Anti-WAR MACHINE (+1 Rend)", "Anti-BEAST (+1 Rend)",
        "Anti-charge (+1 Rend)", "Charge (+1 Damage)", "Companion", "Damage calculator",
        "Anti-HERO", "Anti-INFANTRY", "Anti-MONSTER", "Anti-CAVALRY",
        "Anti-WAR MACHINE", "Anti-BEAST", "Anti-charge"
    ]:
        txt = re.sub(re.escape(tag), "", txt, flags=re.IGNORECASE)

    txt = re.sub(r"\(\+1\s*Rend\)", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\s+", " ", txt).strip(" ,-\t\n•.")

    parti_punto = [p.strip() for p in txt.split(".") if p.strip()]
    if len(parti_punto) >= 2 and parti_punto[0].lower() == parti_punto[1].lower():
        txt = parti_punto[0]

    parole = txt.split()
    n_p = len(parole)
    if n_p >= 2 and n_p % 2 == 0:
        meta = n_p // 2
        if " ".join(parole[:meta]).lower() == " ".join(parole[meta:]).lower():
            txt = " ".join(parole[:meta])

    return txt.strip(" ,-\t\n•.")


def _parsa_riga_arma(nome_arma_grezzo, gittata, atk, hit_str, wnd_str, rnd_str, dmg, abilita_extra=""):
    """
    Converte i campi grezzi di una riga arma di Wahapedia nel dizionario arma di MattHammer.
    Nota: su Wahapedia le abilità dell'arma sono scritte dentro la prima cella (nome_arma_grezzo)!
    """
    nome_pulito = _pulisci_nome_arma(nome_arma_grezzo)
    if not nome_pulito or nome_pulito.lower() in [
        "ranged weapons", "melee weapons", "weapon", "weapons", "view conditions", "damage calculator"
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

    ab_up = f"{nome_arma_grezzo} {abilita_extra}".upper()

    crit = "Nessuno"
    if "CRIT (MORTAL)" in ab_up:
        crit = "Crit (Mortal)"
    elif "CRIT (AUTO-WOUND)" in ab_up:
        crit = "Crit (Auto-wound)"
    elif "CRIT (2 HITS)" in ab_up:
        crit = "Crit (2 Hits)"

    anti = "Nessuno"
    anti_charge_flag = False
    if "ANTI-CHARGE" in ab_up or "ANTI‐CHARGE" in ab_up:
        anti = "CHARGE"
        anti_charge_flag = True
    elif "ANTI-HERO" in ab_up or "ANTI‐HERO" in ab_up:
        anti = "HERO"
    elif "ANTI-INFANTRY" in ab_up or "ANTI‐INFANTRY" in ab_up:
        anti = "INFANTRY"
    elif "ANTI-MONSTER" in ab_up or "ANTI‐MONSTER" in ab_up:
        anti = "MONSTER"
    elif "ANTI-CAVALRY" in ab_up or "ANTI‐CAVALRY" in ab_up:
        anti = "CAVALRY"
    elif "ANTI-WAR MACHINE" in ab_up or "ANTI‐WAR MACHINE" in ab_up:
        anti = "WAR MACHINE"
    elif "ANTI-BEAST" in ab_up or "ANTI‐BEAST" in ab_up:
        anti = "BEAST"

    charge_dmg_flag = bool(re.search(r"CHARGE\s*\(\+1\s*DAMAGE\)", ab_up))
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
    Estrae tutte le armi della Warscroll:
    1) Prima controlla le righe `<tr>` estratte dal parser HTML (se Wahapedia usa `<table>`).
    2) Altrimenti usa il parser universale multi-linea (che funziona anche quando Wahapedia
       usa layout `<div>` con ogni valore su una riga diversa o quando si incolla il testo!).
    """
    armi = []
    nomi_armi_visti = set()

    # 1. Estrazione da righe <tr> HTML
    if righe_tabella_html:
        for celle in righe_tabella_html:
            celle_pulite = [c.strip() for c in celle if c.strip()]
            if len(celle_pulite) >= 6:
                if len(celle_pulite) >= 7 and re.match(r"^[2-6]\+$", celle_pulite[3]) and re.match(r"^[2-6]\+$", celle_pulite[4]):
                    ab_extra = celle_pulite[7] if len(celle_pulite) >= 8 else ""
                    arma = _parsa_riga_arma(
                        celle_pulite[0], celle_pulite[1], celle_pulite[2],
                        celle_pulite[3], celle_pulite[4], celle_pulite[5], celle_pulite[6], ab_extra
                    )
                    if arma and (arma["nome"].lower(), arma["ranged"]) not in nomi_armi_visti:
                        nomi_armi_visti.add((arma["nome"].lower(), arma["ranged"]))
                        armi.append(arma)
                elif re.match(r"^[2-6]\+$", celle_pulite[2]) and re.match(r"^[2-6]\+$", celle_pulite[3]):
                    ab_extra = celle_pulite[6] if len(celle_pulite) >= 7 else ""
                    arma = _parsa_riga_arma(
                        celle_pulite[0], None, celle_pulite[1],
                        celle_pulite[2], celle_pulite[3], celle_pulite[4], celle_pulite[5], ab_extra
                    )
                    if arma and (arma["nome"].lower(), arma["ranged"]) not in nomi_armi_visti:
                        nomi_armi_visti.add((arma["nome"].lower(), arma["ranged"]))
                        armi.append(arma)

    if armi:
        return armi

    # 2. Estrazione universale multi-linea (supporta sia layout <div> su righe separate sia testo incollato)
    testo_sezione = corpo_ws
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
    """
    Estrae SOLO le vere abilità della Warscroll (contenute in corpo_ws, quindi PRIMA della barra KEYWORDS),
    scartando qualsiasi regola base o tooltip ("Fly", "Retreat", "Charge", "in combat", ecc.).
    """
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


def analizza_warscroll_completa(testo_intero, parser_html=None, fazione_default="Nighthaunt", nome_default=""):
    """
    Estrae l'intera Warscroll (Statistiche Cerchio, Punti, Modelli, Basetta, Armi, Abilità, Keywords)
    isolando rigorosamente il corpo della Warscroll dai tooltip di Wahapedia.
    """
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

    # 1. Separa Pre-Header (Ruota Statistiche), Corpo Warscroll e Barra Keywords (tagliando via tutti i tooltip finali)
    testo_pre, corpo_ws, coda_kw = _isola_sezioni_warscroll(testo_intero)

    # 2. Nome Unità (prima riga subito dopo •... WARSCROLL•)
    linee_corpo = [l.strip() for l in corpo_ws.split("\n") if l.strip()]
    if linee_corpo and len(linee_corpo[0]) < 55 and not any(
        k in linee_corpo[0].upper() for k in ["WEAPONS", "DAMAGE CALCULATOR", "MOVE", "BATTLE PROFILE"]
    ):
        risultato["nome"] = linee_corpo[0].title()

    # 3. Estrazione Statistiche Difensive e Movimento dalla Ruota (es. 10" 12 4+ 5. 5+)
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

    # 4. Estrazione BATTLE PROFILE (Unit Size, Points, Base size, Can be reinforced)
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

    # 5. Estrazione Keywords dell'Unità (solo le righe della barra KEYWORDS, prima dei tooltip!)
    if coda_kw:
        linee_kw = []
        for l_k in [l.strip() for l in coda_kw.split("\n") if l.strip()][:3]:
            if any(stop_w in l_k.lower() for stop_w in [
                "keyword is used", "when a unit", "declare:", "effect:", "passive",
                "phase", "roll a dice", "if an attack", "a model is", "soaring above"
            ]):
                break
            linee_kw.append(l_k)
        blocco_kw_unito = ", ".join(linee_kw)
        kws = [k.strip(" .•") for k in re.split(r"[,|•]", blocco_kw_unito) if k.strip(" .•")]
        risultato["keywords"] = kws

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

    # 6. Estrazione Armi e Abilità
    righe_html = parser_html.rows if parser_html is not None else None
    risultato["armi"] = estrai_armi_da_testo_o_html(corpo_ws, righe_tabella_html=righe_html)
    risultato["abilita"] = estrai_abilita_multiple_da_testo(corpo_ws)

    # 7. Se una delle abilità passive dell'unità conferisce un Ward nativo (es. Dryads), aggiorna se necessario
    for ab in risultato["abilita"]:
        w_ab = ab.get("modificatori", {}).get("ward_nativo")
        if w_ab in [4, 5, 6] and risultato["ward"] == "7+":
            risultato["ward"] = f"{w_ab}+"

    return risultato


def scarica_warscroll_da_wahapedia(url_o_testo, fazione="Nighthaunt", nome_unita=""):
    """
    Funzione principale (Zero dipendenze esterne):
    - Se 'url_o_testo' è un URL (o se viene fornito solo il nome unità), scarica la pagina da Wahapedia.
    - Se Wahapedia blocca la richiesta (es. Cloudflare 403) o se l'utente ha incollato direttamente
      il testo della pagina (CTRL+A / CTRL+C da Wahapedia), analizza direttamente il testo!
    Restituisce: (dati_warscroll_dict, messaggio_stato, successo_bool)
    """
    inp = (url_o_testo or "").strip()
    if not inp and nome_unita.strip():
        inp = costruisci_url_wahapedia(fazione, nome_unita)

    if not inp:
        return None, "Inserisci un URL di Wahapedia, un Nome Unità oppure incolla il testo della Warscroll.", False

    if inp.startswith("http://") or inp.startswith("https://"):
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
                nome_fallback = nome_unita or inp.rstrip("/").split("/")[-1].replace("-", " ")
                dati = analizza_warscroll_completa(testo_pagina, parser_html=parser, fazione_default=fazione, nome_default=nome_fallback)
                return dati, f"Warscroll '{dati['nome']}' scaricata da Wahapedia ({len(dati['armi'])} armi, {len(dati['abilita'])} abilità)!", True
            elif resp.status_code in [403, 503]:
                return None, "Wahapedia ha protetto la pagina con Cloudflare (403). Apri la pagina nel browser, premi CTRL+A e CTRL+C e incolla tutto il testo nel box qui sotto!", False
            else:
                return None, f"Pagina non trovata su Wahapedia (HTTP {resp.status_code}). Verifica l'URL: {inp}", False
        except Exception as e:
            return None, f"Errore di rete durante il collegamento a Wahapedia: {e}", False

    dati = analizza_warscroll_completa(inp, parser_html=None, fazione_default=fazione, nome_default=nome_unita or "Unità Wahapedia")
    return dati, f"Warscroll analizzata con successo: {len(dati['armi'])} armi e {len(dati['abilita'])} abilità estratte!", True