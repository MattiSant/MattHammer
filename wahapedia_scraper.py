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


class _WahapediaHTMLParser(HTMLParser):
    """
    Parser HTML nativo (zero dipendenze esterne) progettato per leggere
    le Warscroll di Wahapedia AoS 4e: estrae testo strutturato, righe di tabelle
    delle armi e statistiche del cerchio (Move, Health, Save, Control).
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
        self.stats_classes = {}
        self.active_stat_key = None

    def handle_starttag(self, tag, attrs):
        tag_l = tag.lower()
        if tag_l in self.ignore_tags:
            self.ignore_depth += 1
            return
        if self.ignore_depth > 0:
            return

        attr_dict = dict(attrs)
        cls_str = attr_dict.get("class", "").lower()

        if "wsmove" in cls_str:
            self.active_stat_key = "movimento"
        elif "wswounds" in cls_str or "wshealth" in cls_str:
            self.active_stat_key = "salute"
        elif "wssave" in cls_str:
            self.active_stat_key = "save"
        elif "wscontrol" in cls_str or "wsbravery" in cls_str:
            self.active_stat_key = "controllo"
        elif "wsheader" in cls_str or "wstitle" in cls_str:
            self.active_stat_key = "nome"

        if tag_l == "tr":
            self.in_tr = True
            self.current_row = []
        elif tag_l in ("td", "th") and self.in_tr:
            self.in_td = True
            self.current_cell = []
        elif tag_l in ("br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4"):
            self.text_chunks.append("\n")

    def handle_endtag(self, tag):
        tag_l = tag.lower()
        if tag_l in self.ignore_tags and self.ignore_depth > 0:
            self.ignore_depth -= 1
            return
        if self.ignore_depth > 0:
            return

        self.active_stat_key = None

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
        elif tag_l in ("div", "p", "li", "h1", "h2", "h3"):
            self.text_chunks.append("\n")

    def handle_data(self, data):
        if self.ignore_depth > 0:
            return
        if self.active_stat_key and data.strip():
            if self.active_stat_key not in self.stats_classes:
                self.stats_classes[self.active_stat_key] = data.strip()
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


def _parsa_riga_arma(nome_arma, gittata, atk, hit_str, wnd_str, rnd_str, dmg, abilita_str):
    nome_pulito = re.sub(r"\s+", " ", nome_arma).strip(" ,-\t\n")
    if not nome_pulito or nome_pulito.lower() in ["ranged weapons", "melee weapons", "weapon", "weapons"]:
        return None

    ranged = True if (gittata and gittata.strip() not in ["-", "---", "Melee", ""]) else False
    range_val = gittata.strip() if ranged else "Melee"

    atk_val = str(atk).strip().upper().replace(" ", "")
    hit_val = estrai_intero_sicuro(hit_str, default=4)
    wnd_val = estrai_intero_sicuro(wnd_str, default=4)
    rend_val = 0 if str(rnd_str).strip() in ["-", "---", "0", ""] else estrai_intero_sicuro(rnd_str, default=0)
    dmg_val = str(dmg).strip().upper().replace(" ", "")

    ab_up = (abilita_str or "").upper()

    crit = "Nessuno"
    if "CRIT (MORTAL)" in ab_up:
        crit = "Crit (Mortal)"
    elif "CRIT (AUTO-WOUND)" in ab_up:
        crit = "Crit (Auto-wound)"
    elif "CRIT (2 HITS)" in ab_up:
        crit = "Crit (2 Hits)"

    anti = "Nessuno"
    anti_charge_flag = False
    if "ANTI-CHARGE" in ab_up:
        anti = "CHARGE"
        anti_charge_flag = True
    elif "ANTI-HERO" in ab_up:
        anti = "HERO"
    elif "ANTI-INFANTRY" in ab_up:
        anti = "INFANTRY"
    elif "ANTI-MONSTER" in ab_up:
        anti = "MONSTER"
    elif "ANTI-CAVALRY" in ab_up:
        anti = "CAVALRY"
    elif "ANTI-WAR MACHINE" in ab_up:
        anti = "WAR MACHINE"
    elif "ANTI-BEAST" in ab_up:
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


def estrai_armi_da_testo_o_html(testo_grezzo, righe_tabella_html=None):
    armi = []

    if righe_tabella_html:
        for celle in righe_tabella_html:
            if len(celle) >= 6:
                if len(celle) >= 7 and re.match(r"^[2-6]\+$", celle[3]) and re.match(r"^[2-6]\+$", celle[4]):
                    ab_str = celle[7] if len(celle) >= 8 else ""
                    arma = _parsa_riga_arma(celle[0], celle[1], celle[2], celle[3], celle[4], celle[5], celle[6], ab_str)
                    if arma:
                        armi.append(arma)
                elif re.match(r"^[2-6]\+$", celle[2]) and re.match(r"^[2-6]\+$", celle[3]):
                    ab_str = celle[6] if len(celle) >= 7 else ""
                    arma = _parsa_riga_arma(celle[0], None, celle[1], celle[2], celle[3], celle[4], celle[5], ab_str)
                    if arma:
                        armi.append(arma)

    if armi:
        return armi

    pattern_riga = re.compile(
        r"^(?:(.*?)\s+)?"
        r"(?:(\d+\")\s+)?"
        r"(\d+|[1-9]?D[36](?:\+\d+)?)\s+"
        r"([2-6]\+)\s+"
        r"([2-6]\+)\s+"
        r"(\-|---|0|\d+)\s+"
        r"(\d+|[1-9]?D[36](?:\+\d+)?)"
        r"(?:\s+(.*))?$",
        re.IGNORECASE
    )

    linee = [re.sub(r"\s+", " ", l.replace("\t", " ")).strip() for l in testo_grezzo.split("\n") if l.strip()]
    buffer_nome = ""

    for l in linee:
        if any(l.upper().startswith(h) for h in ["RANGED WEAPONS", "MELEE WEAPONS", "WEAPON ", "RNG ATK", "ATK HIT"]):
            buffer_nome = ""
            continue

        m = pattern_riga.match(l)
        if m:
            prefisso_nome = (m.group(1) or "").strip()
            gittata = m.group(2)
            atk = m.group(3)
            hit = m.group(4)
            wnd = m.group(5)
            rnd = m.group(6)
            dmg = m.group(7)
            coda_abilita = m.group(8) or ""

            nome_completo = prefisso_nome if prefisso_nome else buffer_nome
            ab_combinata = f"{nome_completo} {coda_abilita}"
            for tag in [
                "Crit (Auto-wound)", "Crit (Mortal)", "Crit (2 Hits)", "Shoot in Combat",
                "Anti-HERO (+1 Rend)", "Anti-INFANTRY (+1 Rend)", "Anti-MONSTER (+1 Rend)",
                "Anti-CAVALRY (+1 Rend)", "Anti-WAR MACHINE (+1 Rend)", "Anti-BEAST (+1 Rend)",
                "Anti-charge (+1 Rend)", "Charge (+1 Damage)", "Companion"
            ]:
                nome_completo = re.sub(re.escape(tag), "", nome_completo, flags=re.IGNORECASE)

            arma = _parsa_riga_arma(nome_completo, gittata, atk, hit, wnd, rnd, dmg, ab_combinata)
            if arma:
                armi.append(arma)
            buffer_nome = ""
        else:
            if len(l) < 45 and not any(k in l.lower() for k in ["declare:", "effect:", "keywords", "phase", "passive"]):
                buffer_nome = l

    return armi


def estrai_abilita_multiple_da_testo(testo_grezzo):
    abilita_trovate = []
    nomi_visti = set()

    linee = [l.strip() for l in testo_grezzo.split("\n") if l.strip()]
    pattern_header_fase = re.compile(
        r"^(?:Passive|Once Per (?:Turn|Battle).*|Any .* Phase|Your .* Phase|Enemy .* Phase|Deployment Phase|Start of .*|End of .*|Reaction:.*)$",
        re.IGNORECASE
    )

    indici_inizio = [i for i, l in enumerate(linee) if pattern_header_fase.match(l)]
    for idx_pos, start_i in enumerate(indici_inizio):
        end_i = indici_inizio[idx_pos + 1] if idx_pos + 1 < len(indici_inizio) else min(len(linee), start_i + 15)
        blocco_linee = []
        for l_sub in linee[start_i:end_i]:
            if l_sub.upper().startswith("KEYWORDS") or l_sub.upper().startswith("UNIT SIZE"):
                break
            blocco_linee.append(l_sub)
        blocco_txt = "\n".join(blocco_linee)
        if "effect:" in blocco_txt.lower() or "effetto:" in blocco_txt.lower():
            ab_parsed = analizza_abilita_warscroll(blocco_txt)
            if ab_parsed and ab_parsed["nome"].lower() not in nomi_visti:
                nomi_visti.add(ab_parsed["nome"].lower())
                abilita_trovate.append(ab_parsed)

    return abilita_trovate


def analizza_warscroll_completa(testo_grezzo, parser_html=None, fazione_default="Nighthaunt", nome_default=""):
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

    righe_html = None
    if parser_html is not None:
        righe_html = parser_html.rows
        sc = parser_html.stats_classes
        if "nome" in sc:
            risultato["nome"] = sc["nome"].title()
        if "movimento" in sc:
            mv = sc["movimento"]
            risultato["movimento"] = mv if '"' in mv else f'{mv}"'
        if "salute" in sc:
            risultato["salute"] = max(1, estrai_intero_sicuro(sc["salute"], 2))
        if "save" in sc:
            sv = sc["save"]
            risultato["save"] = sv if ("+" in sv or sv == "-") else f"{sv}+"
        if "controllo" in sc:
            risultato["controllo"] = max(0, estrai_intero_sicuro(sc["controllo"], 1))

    m_mov_txt = re.search(r"(?:Move|Movimento)\s*[:\-]?\s*(\d+\")", testo_grezzo, re.I)
    if m_mov_txt:
        risultato["movimento"] = m_mov_txt.group(1)

    m_hp_txt = re.search(r"(?:Health|Wounds|Salute)\s*[:\-]?\s*(\d{1,2})\b", testo_grezzo, re.I)
    if m_hp_txt:
        risultato["salute"] = max(1, int(m_hp_txt.group(1)))

    m_sv_txt = re.search(r"(?:Save|Salvezza)\s*[:\-]?\s*([2-6]\+|\-)", testo_grezzo, re.I)
    if m_sv_txt:
        risultato["save"] = m_sv_txt.group(1)

    m_oc_txt = re.search(r"(?:Control|Controllo)\s*[:\-]?\s*(\d{1,2})\b", testo_grezzo, re.I)
    if m_oc_txt:
        risultato["controllo"] = int(m_oc_txt.group(1))

    m_base = re.search(r"(\d+(?:\s*x\s*\d+)?\s*mm)", testo_grezzo, re.I)
    if m_base:
        risultato["basetta"] = m_base.group(1).replace(" ", "")

    m_pts = re.search(r"(?:Points|Punti|Cost)\s*[:\-]?\s*(\d{2,4})|(\d{2,3})\s*(?:pts|pt\b)", testo_grezzo, re.I)
    if m_pts:
        pt_v = int(m_pts.group(1) or m_pts.group(2))
        if 40 <= pt_v <= 2000:
            risultato["punti"] = pt_v

    m_size = re.search(r"(?:Unit\s*Size|Modelli)\s*[:\-]?\s*(\d{1,2})", testo_grezzo, re.I)
    if m_size:
        risultato["n_modelli"] = max(1, int(m_size.group(1)))

    m_kw = re.search(r"KEYWORDS\s*[:\n\t ]\s*([^\n]+)", testo_grezzo, re.I)
    if m_kw:
        blocco_kw = m_kw.group(1).strip()
        kws = [k.strip() for k in re.split(r"[,|•]", blocco_kw) if k.strip()]
        risultato["keywords"] = kws

    kw_upper_str = " , ".join(risultato["keywords"]).upper() + " " + testo_grezzo[-400:].upper()
    m_ward_kw = re.search(r"WARD\s*\(([456]\+)\)", kw_upper_str)
    if m_ward_kw:
        risultato["ward"] = m_ward_kw.group(1)
    if "CHAMPION" in kw_upper_str:
        risultato["campione"] = True
    if "HERO" in kw_upper_str and "Unit Size" not in testo_grezzo:
        risultato["n_modelli"] = 1
        risultato["puo_rinforzare"] = False
    if "UNIQUE" in kw_upper_str or "cannot be reinforced" in testo_grezzo.lower():
        risultato["puo_rinforzare"] = False

    risultato["armi"] = estrai_armi_da_testo_o_html(testo_grezzo, righe_tabella_html=righe_html)
    risultato["abilita"] = estrai_abilita_multiple_da_testo(testo_grezzo)

    return risultato


def scarica_warscroll_da_wahapedia(url_o_testo, fazione="Nighthaunt", nome_unita=""):
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