"""Tier 1 - rules / keyword evidence. Microseconds per page, fully explainable.

Each rule = (regex, weight) applied to one of four fields:
  u  URL path tokens        t  title / first heading
  h  raw page head (nav, banner, gate text - where audiences are *declared*)
  b  cleaned body
Scores are summed per label; the winner's margin over the runner-up becomes confidence.
Lexicons are generic multilingual concepts (EN/ES/PT/NL/FR/SV/NO/DA/FI/JA), not site specific.
"""
import math
import re
from dataclasses import dataclass, field

from .preprocess import PageFeatures

R = lambda p: re.compile(p, re.I)

_CUE = (r"intended|directed|aimed|designed|reserved|restricted|exclusively|solely|only for|"
        r"dirigid[ao]s?|destinad[ao]s?|orientad[ao]s?|exclusivamente|[uú]nicamente|solo para|apenas|"
        r"uitsluitend|bestemd|uniquement|exclusivement|destin[eé]e?s?|enbart|endast|kun for|kun til|vain|"
        r"のみ|限定|専用|向けの")
_ONLY = r"only|exclusively|solely|exclusivamente|[uú]nicamente|solamente|apenas|uitsluitend|uniquement|exclusivement|enbart|endast|のみ|限定|専用"
_HCP_NOUN = (r"health ?care professionals?|HCPs?|medical professionals|prescribers|profesionales? (sanitarios?|facultados?|de la salud)|"
             r"profesional facultado|profissionais de sa[uú]de|zorgprofessionals?|zorgverleners|professionnels? de (la )?sant[eé]|"
             r"h[äa]lso- och sjukv[åa]rd|sjukvårdspersonal|helsepersonell|sundhedspersonale|terveydenhuollon ammattilai\\w*|"
             r"医療関係者|医療従事者|医師")
_PAT_NOUN = r"patients?|pacientes?|patiënten|patients|patienter|pasienter|患者さん|患者様|ご家族"

# ---------------------------------------------------------------- page type
TYPE_RULES = {
    "Legal & Compliance": [
        ("u", R(r"privacy|privacidad|privacidade|cookie|legal|terms|terminos|condiciones|aviso-legal|disclaimer|"
                r"integritet|personvern|tietosuoja|datenschutz|accessib|accesibilidad|modern-slavery|"
                r"プライバシー|個人情報|利用規約|サイトのご利用"), 3.0),
        ("t", R(r"privacy|cookie|terms (of|and)|legal notice|aviso legal|disclaimer|política de privacidad|"
                r"integritetspolicy|personvern|プライバシー|ご利用条件|個人情報"), 3.0),
        ("b", R(r"personal data|datos personales|dados pessoais|persoonsgegevens|données personnelles|"
                r"data controller|responsable del tratamiento|cookies? (policy|settings)"), 1.0),
    ],
    "Form / Request": [
        ("u", R(r"form(?!at)|formulario|formul[aá]rio|formulier|inscripci|inscri[cç][aã]o|registration-form|request|solicitud|"
                r"pedido|aanvraag|survey|encuesta|forms\.office|amp-form|apply-form|フォーム"), 3.0),
        ("t", R(r"^(request|solicitud|formulario|inscripci[oó]n|registration form|enquiry form|contact form|"
                r"formulier|フォーム)|request a (call|follow.?up|meeting|sample)|submit (a|your)"), 3.0),
        ("b", R(r"\*\s*required|campos? obligatorios|required fields?|submit\b|enviar\b|verzenden"), 1.0),
    ],
    "Safety Reporting": [
        ("u", R(r"adverse|reacciones-adversas|reportar|farmacovigil|pharmacovigil|biverkning|bivirkning|"
                r"sideeffect-report|report-?(an)?-?(ae|event)|safety-report|副作用報告"), 3.0),
        ("t", R(r"report(ing)? (an )?adverse|adverse (event|reaction|drug)|notificaci[oó]n de (reacciones|acontecimientos)|"
                r"notifica[cç][aã]o de acontecimentos|biverkningsrapport|有害事象"), 3.0),
        ("b", R(r"report (an )?(adverse|side effect)|yellow card|reportar (un )?(efecto|evento) adverso|medwatch"), 1.5),
    ],
    "Login / Registration": [
        ("u", R(r"login|log-in|signin|sign-in|register|registr|prelogin|inloggen|acceder|iniciar-sesion|"
                r"connexion|se-connecter|logga-in|forgot|reset-password|user/"), 3.0),
        ("t", R(r"^(log ?in|sign ?in|register|registro|acceder|inicia sesi[oó]n|inloggen|se connecter|"
                r"create (an )?account|ログイン|会員登録)"), 3.0),
        ("b", R(r"forgot (your )?password|olvidaste tu contrase|password|contrase[ñn]a|wachtwoord|mot de passe"), 1.0),
    ],
    "Contact / Locations": [
        ("u", R(r"contact|contacta|contacto|contacte|kontakt|contactez|neem-contact|yhteystiedot|our-locations|"
                r"locations|ubicaciones|お問い合わせ|お問合せ|inquiry"), 3.0),
        ("t", R(r"^(contact|contacta|contacto|kontakt|neem contact|contactez|get in touch|お問い合わせ)"), 3.0),
        ("b", R(r"(tel[eé]fono|phone|telefoon|t[eé]l[eé]phone)[:\s]+[\+\d(]"), 0.7),
    ],
    "Gateway / Selector": [
        ("u", R(r"choose-country|select-country|country-selector|region|elige-pais|escolha-o-pais|"
                r"gateway|interstitial|prelogin|exit"), 3.0),
        ("t", R(r"choose (a |your )?(country|region)|select (a |your )?country|country selector|"
                r"i am a healthcare|elige tu pa[ií]s"), 3.0),
        ("h", R(r"(are you a|i am a|soy un|sou um|ben je een|[eê]tes-vous un) (healthcare|health care|profesional|"
                r"profissional|zorgverlener|professionnel)"), 2.5),
    ],
    "Investor Relations": [
        ("u", R(r"investor|inversor|investidor|investeerder|investisseur|aktieägare|sijoittaj|annual-report|"
                r"quarterly|results|earnings|shareholder|share-price|dividend|stock-exchange|sec-filings|"
                r"IR/|投資家|株主"), 3.0),
        ("t", R(r"investor|annual report|full.?year (and|&) q\d|q[1-4] (and|&)? ?(h[12]|\d{4})|\b(h1|h2|fy|9m|q[1-4]) ?\d{0,4} results|"
                r"results announcement|dividend|share(holder)?|stock exchange announcement|capital markets"), 3.0),
        ("b", R(r"\b(EPS|earnings per share|total revenue|core operating profit|dividend|guidance|shareholders?)\b"), 1.0),
    ],
    "Careers": [
        ("u", R(r"career|jobs?\b|vacanc|talent|recruit|trabaja|empleo|carreira|carri[eè]re|vacature|"
                r"karriär|ura|採用|求人|apply"), 3.0),
        ("t", R(r"career|join (us|our)|early talent|vacanc|job (search|opening)|work with us|trabaja con nosotros|"
                r"採用情報|求人"), 3.0),
        ("b", R(r"search jobs|apply now|job alerts|talent network|application process"), 1.5),
    ],
    "News & Media": [
        ("u", R(r"press|media-centre|media|news|noticias|notas-prensa|nieuws|actualit|nyheter|nyheder|uutiset|"
                r"prensa|imprensa|ニュース|プレス|newsroom|statements?"), 2.5),
        ("t", R(r"press release|media (statement|release)|nota de prensa|comunicado|persbericht|communiqu[eé]|"
                r"pressmeddelande|statement on|ニュースリリース"), 3.0),
        ("b", R(r"for media (enquiries|inquiries)|about astrazeneca\s*$|london,? uk|cambridge,? uk|wilmington,? de"), 1.2),
    ],
    "Article / Story": [
        ("u", R(r"stories|story|blog|article|articulo|artikel|podcast|insight|topics|what-science-can-do|"
                r"personified|historias|perspectives|magazine"), 2.0),
        ("b", R(r"(listen|watch) (now|the)|read (more|the full)|min read|share this (article|story)"), 0.8),
    ],
    "Sustainability": [
        ("u", R(r"sustainab|sostenib|sustentab|duurzaam|hållbar|bærekraft|environment|climate|esg|ethics|"
                r"compliance|health-equity|nature|responsible|corporate-transparency|transparen|community|"
                r"foundation|fundacion|サステナ"), 3.0),
        ("t", R(r"sustainab|climate|net.?zero|ethics|health equity|biodiversity|environment|esg|responsible business"), 2.5),
    ],
    "Prescribing Information": [
        ("u", R(r"prescribing-?information|smpc|ficha-tecnica|resumo-das-caracter|spc\b|package-leaflet|"
                r"prospecto|folheto|bipacksedel|bijsluiter|notice|product-?information|label|添付文書|"
                r"fachinformation|felleskatalogen|\bpi\b"), 3.0),
        ("t", R(r"prescribing information|summary of product characteristics|smpc|ficha t[eé]cnica|"
                r"folheto informativo|package leaflet|prospecto|bipacksedel|添付文書"), 3.0),
        ("b", R(r"indications and usage|posology and method|posolog[ií]a y forma|contraindications?|"
                r"boxed warning|special warnings and precautions|marketing authori[sz]ation holder"), 1.2),
    ],
    "Clinical Evidence": [
        ("u", R(r"congress|pdf-?viewer|pptviewer|study|studies|trial|clinical|estudio|ensayo|publication|abstract|"
                r"poster|pubmed|nejm|lancet|doi\.org|fulltext|article/|guideline|guia|guideline|臨床|試験|"
                r"estudo|studie|data(?!set)"), 1.6),        # not "dataset(s)": a data catalogue is not clinical evidence
        ("t", R(r"phase [123i]+|randomi[sz]ed|double.?blind|efficacy and safety|versus|placebo|post hoc|meta-analysis|"
                r"real.?world|overall survival|NCT\d{8}|et al\b|abstract"), 2.5),
        ("b", R(r"(primary|secondary) endpoint|hazard ratio|confidence interval|\bHR\b[ =]|\bCI\b|"
                r"patients (were|was) randomi|intention.to.treat|progression.free survival|\bp ?[<=] ?0\.\d+"), 2.0),
    ],
    "Medical Education & Events": [
        ("u", R(r"course|curso|cursos|webinar|event|evento|congres|masterclass|education|educaci|formaci|"
                r"training|e-?learning|opleiding|utbildning|seminar|symposium|learning|講演|セミナー|研修"), 2.5),
        ("t", R(r"webinar|masterclass|course|curso|congress|congreso|symposium|training|workshop|"
                r"e-?learning|seminario|セミナー|講座"), 2.5),
    ],
    "Patient Support": [
        ("u", R(r"patient-?support|patient-?resources|pacientes|patient|support|apoyo|stories|testimon|experience|"
                r"体験談|tips|recipe|self-?care|living-with|vivre|leven-met|live-with|aftercare|"
                r"caregiver|cuidador|sideeffect|side_effect|副作用|生活"), 2.2),
        ("t", R(r"living with|tips for|ask your doctor|questions to ask|talk to your (doctor|healthcare)|"
                r"体験談|副作用.{0,6}対策|セルフケア|vivre avec|leven met|patient (story|stories|support)"), 2.5),
        ("b", R(r"you may (feel|experience)|your (doctor|nurse)|talk to your|ask your doctor|"
                r"お医者さん|主治医|ご自身|患者さん(へ|の)"), 1.0),
    ],
    "Disease & Therapy Area": [
        ("u", R(r"therapy-?areas?|therapeutic|areas-terapeuticas|disease|disease-education|patolog|pathology|"
                r"oncolog|cardio|respirat|diabet|nephro|renal|asthma|asma|copd|cancer|c[aá]ncer|ziektedomeinen|"
                r"domaines|terapiomraden|sjukdom|疾患|がん|癌"), 2.2),
        ("t", R(r"what is|qu[eé] es|o que [eé]|what you need to know|symptoms|diagnosis|treatment options|"
                r"about (asthma|copd|cancer|diabetes|kidney)|とは|について"), 2.0),
    ],
    "Product Information": [
        ("u", R(r"medicines?|medicamentos?|medicijnen|m[eé]dicaments|l[aä]kemedel|products?|productos?|produtos|"
                r"brand|dosing|dosage|dosering|administra|toediening|how-to-use|imfinzi|tagrisso|lynparza|"
                r"enhertu|calquence|farxiga|forxiga|symbicort|trixeo|breztri|fasenra|saphnelo|tezspire|lokelma|"
                r"wainzua|truqap|koselugo|ultomiris|soliris|airsupra|fluenz|beyfortus|evusheld|tagrisso|薬"), 2.2),
        ("b", R(r"recommended dose|dosing schedule|dose modification|how to (administer|use|inject)|"
                r"mechanism of action|indicated for|is indicated in"), 1.5),
    ],
    "R&D & Science": [
        ("u", R(r"r-d|research|investigaci|pipeline|science|technolog|platform|genomic|ai-|innovation|"
                r"clinical-trials?|ensayos-clinicos|治験|forskning"), 2.0),
        ("t", R(r"pipeline|our science|research and development|r&d|platform|technology|genomics|治験"), 2.0),
    ],
    "About the Company": [
        ("u", R(r"about|who-we-are|our-company|nuestra-?compania|quienes|sobre|over-ons|a-propos|om-oss|om-os|"
                r"tietoa|leadership|board|governance|strategy|history|our-people|corporate|company|会社概要|企業"), 2.2),
        ("t", R(r"^about\b|who we are|our (company|strategy|leadership|history|story|people)|"
                r"qui[eé]nes somos|nuestra compa[ñn][ií]a|sobre nosotros|over ons|om oss|company profile"), 2.5),
    ],
    "Listing / Library": [
        ("u", R(r"library|biblioteca|archive|archivo|listing|search|buscar|results\b|list\b|index|overview|"
                r"congress-library|resources?\b|recursos|downloads?"), 1.5),
        ("b", R(r"(showing|mostrando)\s+\d+|page \d+ of|load more|cargar m[aá]s|filter(s| by)|sort by|"
                r"\d+ results?"), 1.2),
    ],
    "Utility / Error": [
        ("t", R(r"^(404|page not found|p[aá]gina no encontrada|error|access denied|forbidden|not found|"
                r"loading|opening document|redirect)"), 3.5),
        ("u", R(r"404|error|not-found|redirect|print"), 2.0),
    ],
}

# ---------------------------------------------------------------- audience
AUD_RULES = {
    "Healthcare Professional": [
        # declared gating language - the strongest, almost free, signal (deck slide 10).
        # A bare 'Healthcare professionals' is usually a nav label, so a *cue word* must accompany the audience noun.
        ("h", R(r"(" + _CUE + r").{0,90}?(" + _HCP_NOUN + r")|(" + _HCP_NOUN + r").{0,45}?(" + _ONLY + r")"), 4.0),
        ("u", R(r"hcp|healthcare-professional|profesional|professional|medical-?information|medicalinformation|"
                r"prescrib|dosing|clinical|congress|zorgprofessional"), 1.8),
        ("b", R(r"\b(dosing|posology|contraindications?|adverse reactions|pharmacokinetics|hazard ratio|"
                r"progression.free survival|randomi[sz]ed|prescribing information|summary of product characteristics|"
                r"phase (II|III|3|2)|mg/kg|ESMO|ASCO|ERS|ADA|EASD|ESC)\b"), 1.4),
    ],
    "Patient / Caregiver": [
        ("h", R(r"(" + _CUE + r").{0,60}?(" + _PAT_NOUN + r")|if you (are|have been) (a )?patient"), 3.0),
        ("u", R(r"patients?|pacientes?|patiënt|体験談|living-with|vivre|support|caregiver|cuidador|"
                r"side_?effect|副作用"), 1.8),
        ("b", R(r"\b(you|your|usted|tu|vos|あなた|ご自身)\b.{0,60}\b(doctor|nurse|treatment|symptoms|médico|síntomas|"
                r"主治医|治療|症状)\b|患者さん|ご家族|talk to your doctor|ask your doctor|consult your doctor"), 1.5),
    ],
    "Investor": [
        ("u", R(r"investor|inversor|investidor|annual-report|results|earnings|shareholder|dividend|stock-exchange|"
                r"sec-filings|share-price|quarterly|IR\b"), 3.0),
        ("t", R(r"investor|annual report|results|dividend|shareholder|stock exchange"), 2.5),
        ("b", R(r"\b(shareholders?|investors?|analysts?|dividend|earnings|guidance|webcast)\b"), 1.2),
    ],
    "Media": [
        ("u", R(r"press|media|prensa|imprensa|persbericht|pressmeddelande|newsroom|image-and-broadcast|プレス"), 2.5),
        ("b", R(r"for (media|press) (enquiries|inquiries|contact)|media relations|press office|journalists"), 2.0),
    ],
    "Job Seeker": [
        ("u", R(r"career|jobs?\b|vacanc|talent|recruit|trabaja|empleo|carreira|vacature|karriär|採用|求人"), 3.5),
        ("b", R(r"apply now|search jobs|job alerts|talent network|your application|early talent"), 2.0),
    ],
    "Business Partner": [
        ("u", R(r"partner|supplier|procurement|licens|collaborat|business-development|proveedor|fornecedor|leverancier|"
                r"alliance|open-innovation|funding|grants?|investigator-sponsored|iis\b|externally-sponsored"), 3.0),
        ("b", R(r"suppliers?|procurement|business development|licensing|investigator.sponsored|grant (application|request)"), 1.5),
    ],
    "General Public": [
        ("u", R(r"sustainab|about|who-we-are|our-company|what-science-can-do|stories|news|media-centre|history|"
                r"community|foundation|fundacion|hållbar|duurzaam|nuestracompania|company"), 1.5),
        ("b", R(r"we are a (global|science-led)|our mission|our purpose|our ambition|science can do"), 1.2),
    ],
}


def _anchor_url_rules():
    """URL rules must start at a token boundary: 'form' must not fire inside 'medicalinformation'."""
    for table in (TYPE_RULES, AUD_RULES):
        for label, rs in table.items():
            table[label] = [(f, re.compile(r"(?<![a-z])(?:" + rx.pattern + ")", re.I) if f == "u" else rx, w)
                            for f, rx, w in rs]


_anchor_url_rules()


@dataclass
class RuleResult:
    label: str
    confidence: float
    scores: dict = field(default_factory=dict)
    evidence: list = field(default_factory=list)


def _fields(f: PageFeatures) -> dict:
    return dict(u=" ".join(f.url_toks) + " " + f.url.lower(), t=f.title, h=f.head, b=f.body[:3000])


def _score(f: PageFeatures, rules: dict) -> tuple[dict, dict]:
    F = _fields(f)
    scores, ev = {}, {}
    for label, rs in rules.items():
        s = 0.0
        for fld, rx, w in rs:
            m = rx.search(F[fld])
            if m:
                s += w
                ev.setdefault(label, []).append(f"{fld}:{m.group(0)[:40]!r}")
        if s:
            scores[label] = s
    return scores, ev


def _conf(scores: dict) -> tuple[str, float]:
    if not scores:
        return "", 0.0
    top = sorted(scores.items(), key=lambda kv: -kv[1])
    best, s1 = top[0]
    s2 = top[1][1] if len(top) > 1 else 0.0
    # confidence grows with absolute evidence and with the margin over the runner-up
    strength = 1 - math.exp(-s1 / 3.0)
    margin = (s1 - s2) / (s1 + 1e-9)
    return best, round(0.15 + 0.85 * strength * (0.35 + 0.65 * margin), 3)


def apply_type_postrules(f: PageFeatures, scores: dict) -> dict:
    """Structural cues that are not keyword-shaped."""
    if f.n_body < 40 and not f.is_pdf:
        scores["Utility / Error"] = scores.get("Utility / Error", 0) + 3.0
    if f.shape.get("is_root") and f.depth <= 1:
        scores["Homepage / Hub"] = scores.get("Homepage / Hub", 0) + 4.0
    elif not f.is_pdf and f.shape.get("n_seg", 9) <= 1 and not f.shape.get("has_query"):
        scores["Homepage / Hub"] = scores.get("Homepage / Hub", 0) + 2.0   # section front pages: /oncology.html
    if f.is_pdf and f.pdf_pages and f.pdf_pages > 60:
        scores["Investor Relations"] = scores.get("Investor Relations", 0) + 0.3
    return scores


def classify_type(f: PageFeatures) -> RuleResult:
    sc, ev = _score(f, TYPE_RULES)
    sc = apply_type_postrules(f, sc)
    lab, c = _conf(sc)
    return RuleResult(lab, c, sc, ev.get(lab, []))


def classify_audience(f: PageFeatures) -> RuleResult:
    sc, ev = _score(f, AUD_RULES)
    # site-level context: if most pages on this host carry an explicit audience declaration, so does this one
    if f.host_decl_hcp >= 0.4:
        sc["Healthcare Professional"] = sc.get("Healthcare Professional", 0) + 3.5
        ev.setdefault("Healthcare Professional", []).append(f"host:{f.host_decl_hcp:.0%} of pages declare HCP-only")
    if f.host_decl_pat >= 0.4:
        sc["Patient / Caregiver"] = sc.get("Patient / Caregiver", 0) + 2.5
    lab, c = _conf(sc)
    return RuleResult(lab, c, sc, ev.get(lab, []))


def declared_audience(f: PageFeatures) -> str:
    """Only the explicit self-declaration ('intended for HCPs only'), kept separate from
    content-based audience so the two can be compared for mismatch findings (deck slide 12)."""
    hits = [rx for fld, rx, w in AUD_RULES["Healthcare Professional"] if fld == "h"]
    if any(rx.search(f.head) for rx in hits):
        return "Healthcare Professional"
    if f.host_decl_hcp >= 0.4:
        return "Healthcare Professional"
    for fld, rx, w in AUD_RULES["Patient / Caregiver"]:
        if fld == "h" and rx.search(f.head):
            return "Patient / Caregiver"
    return ""
