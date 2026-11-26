"""Gera as artes do README (assets/*.svg) com a fonte Bricolage Grotesque embutida.

Uso:
    python ferramentas/gerar_svgs.py <caminho do BricolageGrotesque[opsz,wdth,wght].ttf>

A fonte vem do Google Fonts (github.com/google/fonts, ofl/bricolagegrotesque, licença OFL).
Cada SVG leva só as letras que usa, recortadas e embutidas em WOFF2.
Dependências: pip install fonttools brotli
"""
import base64
import io
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

RAIZ = Path(__file__).resolve().parent.parent
ASSETS = RAIZ / "assets"

# Paleta
BG0, BG, CARD, LINHA = "#0B1D26", "#0F2530", "#12303D", "#25485A"
TEXTO, APAGADO = "#EEF5F3", "#9BB8B8"
TEAL, OURO, CEU, VIOLETA, CORAL = "#5FD8C1", "#E8C88A", "#6CC4FF", "#B69CFF", "#FF9E80"

# Eixo óptico por peso: texto pequeno legível, título com corte de display
OPSZ = {400: 18, 500: 18, 700: 72, 800: 96}


class Fonte:
    def __init__(self, caminho):
        self.caminho = caminho
        self.cache = {}

    def inst(self, peso):
        if peso not in self.cache:
            f = TTFont(self.caminho)
            self.cache[peso] = instancer.instantiateVariableFont(
                f, {"wght": peso, "opsz": OPSZ[peso], "wdth": 100})
        return self.cache[peso]

    def largura(self, texto, tam, peso, ls=0.0):
        f = self.inst(peso)
        cmap, hm, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
        falta = {c for c in texto if ord(c) not in cmap}
        assert not falta, f"fonte sem glifo para {falta!r}"
        return sum(hm[cmap[ord(c)]][0] for c in texto) * tam / upm + ls * len(texto)

    def woff2(self, peso, chars):
        buf = io.BytesIO()
        self.inst(peso).save(buf)
        buf.seek(0)
        ft = TTFont(buf)
        op = subset.Options()
        op.flavor = "woff2"
        op.layout_features = ["kern", "liga", "calt"]
        op.name_IDs = [1, 2]
        op.hinting = False
        sub = subset.Subsetter(op)
        sub.populate(text=chars)
        sub.subset(ft)
        out = io.BytesIO()
        ft.flavor = "woff2"
        ft.save(out)
        return base64.b64encode(out.getvalue()).decode()


F: Fonte = None  # definida no main


def n(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


class SVG:
    def __init__(self, w, h, titulo):
        self.w, self.h, self.titulo = w, h, titulo
        self.defs, self.corpo, self.css = [], [], []
        self.chars = defaultdict(set)
        self.kf = {}

    def t(self, x, y, texto, tam, peso=400, fill=TEXTO, anc="start", ls=0, cls="", style=""):
        self.chars[peso].update(texto)
        c = f' class="{cls}"' if cls else ""
        st = f' style="{style}"' if style else ""
        return (f'<text x="{n(x)}" y="{n(y)}" font-size="{tam}" font-weight="{peso}" fill="{fill}" '
                f'text-anchor="{anc}" letter-spacing="{ls}"{c}{st}>{escape(texto)}</text>')

    def add(self, *p):
        self.corpo.extend(p)

    def d(self, *p):
        self.defs.extend(p)

    def brilho_borda(self, x, y, w, h, rx, grad, atraso=0.0, dur=7.0, comp=150):
        """Traço de luz que percorre a borda de um retângulo arredondado."""
        per = 2 * (w + h) - (8 - 2 * math.pi) * rx
        nome = f"bb{int(per)}"
        if nome not in self.kf:
            self.kf[nome] = f"@keyframes {nome}{{to{{stroke-dashoffset:-{n(per)}}}}}"
        return (f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" rx="{rx}" fill="none" '
                f'stroke="url(#{grad})" stroke-width="2" stroke-linecap="round" '
                f'stroke-dasharray="{comp} {n(per - comp)}" '
                f'style="animation:{nome} {dur}s linear {atraso}s infinite"/>')

    def render(self):
        faces = "".join(
            f"@font-face{{font-family:'BG';font-weight:{p};src:url(data:font/woff2;base64,"
            f"{F.woff2(p, ''.join(sorted(ch)))}) format('woff2')}}"
            for p, ch in sorted(self.chars.items()))
        css = (faces + "text{font-family:'BG','Segoe UI',Helvetica,Arial,sans-serif}"
               + "".join(self.css) + "".join(self.kf.values())
               + "@media (prefers-reduced-motion:reduce){*{animation:none!important}}")
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(self.titulo)}">'
                f"<title>{escape(self.titulo)}</title><style>{css}</style>"
                f"<defs>{''.join(self.defs)}</defs>{''.join(self.corpo)}</svg>")


# ---------- peças comuns ----------
CSS_BASE = (
    ".pop{transform-box:fill-box;transform-origin:center;animation:pop .5s cubic-bezier(.3,1.4,.5,1) both}"
    "@keyframes pop{from{opacity:0;transform:scale(.3)}}"
    ".up{animation:up .7s ease-out both}"
    "@keyframes up{from{opacity:0;transform:translateY(16px)}}"
    ".pulso{transform-box:fill-box;transform-origin:center;animation:pulso 2.6s ease-out infinite}"
    "@keyframes pulso{0%{opacity:.7;transform:scale(1)}100%{opacity:0;transform:scale(2.6)}}"
    ".deriva1{animation:deriva1 18s ease-in-out infinite alternate}"
    "@keyframes deriva1{to{transform:translate(-140px,70px) scale(1.15)}}"
    ".deriva2{animation:deriva2 22s ease-in-out infinite alternate}"
    "@keyframes deriva2{to{transform:translate(160px,-60px) scale(1.2)}}"
    ".deriva3{animation:deriva3 26s ease-in-out infinite alternate}"
    "@keyframes deriva3{to{transform:translate(-90px,90px) scale(.9)}}"
)


def defs_base(s, w, h, rx=22):
    s.d(f'<clipPath id="moldura"><rect width="{w}" height="{h}" rx="{rx}"/></clipPath>',
        '<pattern id="pontos" width="26" height="26" patternUnits="userSpaceOnUse">'
        '<circle cx="2" cy="2" r="1.1" fill="#FFFFFF" fill-opacity=".07"/></pattern>')
    for nome, cor in (("Teal", TEAL), ("Violeta", VIOLETA), ("Ouro", OURO), ("Ceu", CEU), ("Coral", CORAL)):
        s.d(f'<radialGradient id="r{nome}"><stop offset="0" stop-color="{cor}" stop-opacity=".30"/>'
            f'<stop offset="1" stop-color="{cor}" stop-opacity="0"/></radialGradient>')
    s.d(f'<linearGradient id="gBorda" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{TEAL}"/><stop offset=".5" stop-color="{VIOLETA}"/>'
        f'<stop offset="1" stop-color="{OURO}"/></linearGradient>')
    s.css.append(CSS_BASE)


def fundo(s, w, h, bolhas, rx=22):
    """Fundo escuro com bolhas de luz que derivam e grade de pontos."""
    p = [f'<rect width="{w}" height="{h}" fill="{BG0}"/>']
    for i, (cx, cy, r, cor) in enumerate(bolhas):
        p.append(f'<circle class="deriva{i % 3 + 1}" cx="{cx}" cy="{cy}" r="{r}" fill="url(#r{cor})"/>')
    p.append(f'<rect width="{w}" height="{h}" fill="url(#pontos)"/>')
    return p


def moldura(w, h, rx=22):
    return (f'<rect x=".75" y=".75" width="{w - 1.5}" height="{h - 1.5}" rx="{rx}" fill="none" '
            f'stroke="url(#gBorda)" stroke-opacity=".55" stroke-width="1.5"/>')


def pilula(s, x, y, texto, cor, tam=17, peso=500, ponto=True, pulso=False, fill_txt=None, atraso=None):
    h = tam + 17
    tw = F.largura(texto, tam, peso)
    pad = 16
    w = tw + pad * 2 + (18 if ponto else 0)
    cls = ' class="up"' if atraso is not None else ""
    st = f' style="animation-delay:{atraso}s"' if atraso is not None else ""
    p = [f'<g{cls}{st}>',
         f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{h}" rx="{h / 2}" fill="#FFFFFF" '
         f'fill-opacity=".05" stroke="{cor}" stroke-opacity=".45"/>']
    tx = x + pad
    if ponto:
        cy = y + h / 2
        if pulso:
            p.append(f'<circle class="pulso" cx="{n(tx + 4)}" cy="{n(cy)}" r="4.5" fill="{cor}"/>')
        p.append(f'<circle cx="{n(tx + 4)}" cy="{n(cy)}" r="4.5" fill="{cor}"/>')
        tx += 18
    p.append(s.t(tx, y + h / 2 + tam * 0.36, texto, tam, peso, fill_txt or TEXTO))
    p.append("</g>")
    return p, w


def quebra(texto, tam, peso, maxw):
    linhas, atual = [], ""
    for palavra in texto.split():
        tent = (atual + " " + palavra).strip()
        if F.largura(tent, tam, peso) <= maxw:
            atual = tent
        else:
            linhas.append(atual)
            atual = palavra
    linhas.append(atual)
    return linhas


# ---------- header ----------
def header():
    W, H = 1280, 420
    s = SVG(W, H, "Gustavo Pelissari, Assistente de Dados e Tecnologia no Grupo Bononi. "
                  "35 aplicações em produção ligadas a um login único.")
    defs_base(s, W, H)
    corpo = ['<g clip-path="url(#moldura)">']
    corpo += fundo(s, W, H, [(1080, 60, 380, "Teal"), (180, 460, 420, "Violeta"), (640, -80, 300, "Ouro")])

    # Selo de lugar
    p, _ = pilula(s, 72, 62, "Umuarama, Paraná", TEAL, tam=17, pulso=True, fill_txt=APAGADO, atraso=0.05)
    corpo += p

    # Nome com gradiente e brilho
    nome, tn, xn, yn = "Gustavo Pelissari", 78, 68, 176
    wn = F.largura(nome, tn, 800, -2.2)
    assert wn < 760, wn
    s.d(s_clip := f'<clipPath id="cNome">{s.t(xn, yn, nome, tn, 800, ls=-2.2)}</clipPath>')
    s.d(f'<linearGradient id="gNome" gradientUnits="userSpaceOnUse" x1="{xn}" y1="0" x2="{n(xn + wn)}" y2="0">'
        f'<stop offset="0" stop-color="{TEXTO}"/><stop offset=".42" stop-color="{TEXTO}"/>'
        f'<stop offset=".75" stop-color="{TEAL}"/><stop offset="1" stop-color="{OURO}"/></linearGradient>'
        '<linearGradient id="gBrilho" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#FFFFFF" stop-opacity="0"/>'
        '<stop offset=".5" stop-color="#FFFFFF" stop-opacity=".65"/>'
        '<stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>')
    s.css.append(f".brn{{animation:brn 7s ease-in-out 1.4s infinite}}"
                 f"@keyframes brn{{0%{{transform:translateX(0)}}40%,100%{{transform:translateX({n(wn + 320)}px)}}}}")
    corpo += ['<g clip-path="url(#cNome)" class="up" style="animation-delay:.15s">',
              f'<rect x="{xn - 6}" y="{yn - 80}" width="{n(wn + 20)}" height="104" fill="url(#gNome)"/>',
              f'<rect class="brn" x="{xn - 240}" y="{yn - 80}" width="150" height="104" fill="url(#gBrilho)" '
              f'transform="skewX(-18)"/></g>']

    # Cargo digitando
    cargo, tc, xc, yc = "Assistente de Dados e Tecnologia no Grupo Bononi", 27, 72, 228
    wc = F.largura(cargo, tc, 500)
    nch = len(cargo)
    s.d(f'<clipPath id="cCargo"><rect class="tp" x="{xc - 2}" y="{yc - 30}" width="{n(wc + 8)}" height="42"/></clipPath>')
    s.css.append(f".tp{{transform-box:fill-box;transform-origin:0 50%;animation:tp 2.6s steps({nch}) .6s both}}"
                 f"@keyframes tp{{from{{transform:scaleX(0)}}}}"
                 f".cr{{animation:cr 2.6s steps({nch}) .6s both,pisca 1.1s step-end 3.2s infinite}}"
                 f"@keyframes cr{{from{{transform:translateX(-{n(wc + 6)}px)}}}}"
                 f"@keyframes pisca{{50%{{opacity:0}}}}")
    corpo += [f'<g clip-path="url(#cCargo)">{s.t(xc, yc, cargo, tc, 500, TEAL)}</g>',
              f'<rect class="cr" x="{n(xc + wc + 6)}" y="{yc - 24}" width="3" height="30" rx="1.5" fill="{TEAL}"/>']

    # Descrição
    for i, (lin, y) in enumerate((("Desenvolvo e mantenho os sistemas que rodam a operação", 282),
                                  ("do Grupo Bononi e da Stonni, do ERP ao coletor da expedição.", 311))):
        corpo.append(f'<g class="up" style="animation-delay:{0.35 + i * 0.1}s">{s.t(72, y, lin, 20, 400, APAGADO)}</g>')

    # Chips
    x = 72
    for i, (txt, cor) in enumerate((("Arquitetura", TEAL), ("Banco de dados", CEU),
                                    ("Integrações", OURO), ("Deploy contínuo", VIOLETA))):
        p, w = pilula(s, x, 340, txt, cor, tam=16, atraso=0.9 + i * 0.12)
        corpo += p
        x += w + 10
    assert x < 820, x

    # Rede: 35 apps em volta do Hub
    cx, cy, R = 1010, 196, 138
    cores = [TEAL, CEU, TEAL, VIOLETA, TEAL, OURO, TEAL, CORAL]
    s.css.append(".gira{transform-box:fill-box;transform-origin:center;animation:gira 90s linear infinite}"
                 "@keyframes gira{to{transform:rotate(360deg)}}"
                 f".pk{{animation:pk 2.8s linear infinite}}@keyframes pk{{from{{stroke-dashoffset:12}}to{{stroke-dashoffset:-{R - 30}}}}}"
                 ".flu{animation:flu 3s linear infinite}@keyframes flu{to{stroke-dashoffset:-90}}")
    s.d(f'<radialGradient id="gHalo"><stop offset="0" stop-color="{TEAL}" stop-opacity=".18"/>'
        f'<stop offset="1" stop-color="{TEAL}" stop-opacity="0"/></radialGradient>'
        f'<linearGradient id="gHub" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{TEAL}"/>'
        f'<stop offset="1" stop-color="{CEU}"/></linearGradient>')
    corpo += [f'<circle cx="{cx}" cy="{cy}" r="{R + 60}" fill="url(#gHalo)"/>',
              f'<circle class="gira" cx="{cx}" cy="{cy}" r="{R + 32}" fill="none" stroke="{LINHA}" stroke-width="1.2" stroke-dasharray="2 8"/>',
              f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{LINHA}" stroke-width="1" stroke-dasharray="2 6"/>']
    nos = []
    for i in range(35):
        a = -math.pi / 2 + i * 2 * math.pi / 35
        nos.append((cx + R * math.cos(a), cy + R * math.sin(a), cores[i % len(cores)]))
    for x2, y2, _ in nos:
        corpo.append(f'<line x1="{cx}" y1="{cy}" x2="{n(x2)}" y2="{n(y2)}" stroke="{LINHA}" stroke-width="1"/>')
    for i in range(0, 35, 3):
        x2, y2, cor = nos[i]
        corpo.append(f'<line class="pk" style="animation-delay:{n(i * 0.21)}s" x1="{n(x2)}" y1="{n(y2)}" '
                     f'x2="{cx}" y2="{cy}" stroke="{cor}" stroke-width="2.4" stroke-linecap="round" '
                     f'stroke-dasharray="12 {R + 40}"/>')
    # ERP alimentando o Hub
    corpo += [f'<path d="M1214 56 L{cx} {cy}" stroke="{OURO}" stroke-width="1.8" stroke-dasharray="4 5" class="flu" fill="none"/>']
    for i, (x2, y2, cor) in enumerate(nos):
        corpo.append(f'<circle class="pop" style="animation-delay:{n(0.3 + i * 0.045)}s" cx="{n(x2)}" cy="{n(y2)}" r="6.5" fill="{cor}"/>')
    corpo += [f'<rect x="1190" y="41" width="48" height="30" rx="8" fill="{BG0}" stroke="{OURO}" stroke-width="1.6"/>',
              s.t(1214, 62, "ERP", 15, 700, OURO, "middle"),
              f'<circle class="pulso" cx="{cx}" cy="{cy}" r="40" fill="none" stroke="{TEAL}" stroke-width="2"/>',
              f'<circle class="pulso" style="animation-delay:1.3s" cx="{cx}" cy="{cy}" r="40" fill="none" stroke="{TEAL}" stroke-width="2"/>',
              f'<circle cx="{cx}" cy="{cy}" r="40" fill="url(#gHub)"/>',
              s.t(cx, cy + 8, "Hub", 22, 800, BG0, "middle"),
              s.t(cx, 394, "35 aplicações em produção, um login só", 18, 500, APAGADO, "middle")]
    corpo.append("</g>")
    corpo.append(moldura(W, H))
    s.add(*corpo)
    return s


# ---------- números ----------
def numeros():
    W, H = 1280, 200
    s = SVG(W, H, "35 aplicações internas em produção, 1 login único, 2 empresas atendidas "
                  "(Grupo Bononi e Stonni) e 0 entregas validadas só por build verde.")
    defs_base(s, W, H)
    itens = [("35", "aplicações internas", "em produção", TEAL, "Teal"),
             ("1", "login único ligando", "todas elas", CEU, "Ceu"),
             ("2", "empresas atendidas:", "Grupo Bononi e Stonni", VIOLETA, "Violeta"),
             ("0", "entregas validadas só", "por build verde", OURO, "Ouro")]
    gap, cw, ch = 20, (W - 60) / 4, 196
    s.d(f'<linearGradient id="gCard" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{CARD}"/>'
        f'<stop offset="1" stop-color="{BG0}"/></linearGradient>')
    for i, (num, l1, l2, cor, nome) in enumerate(itens):
        x, y = i * (cw + gap), 2
        s.d(f'<clipPath id="cc{i}"><rect x="{n(x)}" y="{y}" width="{n(cw)}" height="{ch}" rx="20"/></clipPath>',
            f'<linearGradient id="gn{i}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{TEXTO}"/>'
            f'<stop offset="1" stop-color="{cor}"/></linearGradient>',
            f'<linearGradient id="gb{i}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{cor}" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="{cor}"/></linearGradient>')
        s.add(f'<g class="up" style="animation-delay:{0.1 + i * 0.15}s">',
              f'<rect x="{n(x)}" y="{y}" width="{n(cw)}" height="{ch}" rx="20" fill="url(#gCard)" stroke="{LINHA}"/>',
              f'<g clip-path="url(#cc{i})"><circle class="deriva{i % 3 + 1}" cx="{n(x + cw - 20)}" cy="{y + 20}" r="120" fill="url(#r{nome})"/></g>',
              s.brilho_borda(x, y, cw, ch, 20, f"gb{i}", atraso=i * 1.1, dur=8),
              s.t(x + 30, y + 106, num, 88, 800, f"url(#gn{i})", ls=-3),
              s.t(x + 32, y + 144, l1, 18, 400, APAGADO),
              s.t(x + 32, y + 169, l2, 18, 500, TEXTO),
              "</g>")
    return s


# ---------- áreas ----------
ICONES = {
    "pacote": "M3 7.5 12 3l9 4.5v9L12 21l-9-4.5z M3 7.5l9 4.5 9-4.5 M12 12v9 M7.5 5.25l9 4.5",
    "sync": "M4 10a8 8 0 0 1 14.6-4.2 M20 3v4.5h-4.5 M20 14a8 8 0 0 1-14.6 4.2 M4 21v-4.5h4.5",
    "barras": "M3 21h18 M6 17v-5 M10.5 17V7 M15 17v-8 M19.5 17V4",
    "sacola": "M5 8h14l-1.2 12.1a1 1 0 0 1-1 .9H7.2a1 1 0 0 1-1-.9z M9 8V6.5a3 3 0 0 1 6 0V8",
    "servidor": "M4 4h16v6H4z M4 14h16v6H4z M8 7h.01 M8 17h.01",
}


def areas():
    W = 1280
    itens = [
        ("Operação", "pacote", TEAL,
         "Expedição com separação, conferência e romaneio direto no coletor Android, além de compras, "
         "cobrança, frete, RH, treinamento e loja física."),
        ("Integração de dados", "sync", CEU,
         "Replicação do ERP para a nuvem e integrações com Bling, marketplaces e transportadoras, "
         "incluindo cotação de frete e auditoria de CT-e."),
        ("Dashboards", "barras", OURO, "Painéis financeiros e comerciais construídos direto sobre SQL."),
        ("Canais de venda", "sacola", CORAL,
         "Loja própria com painel administrativo, portal do representante, CRM de atacado e portal "
         "da rede de assistência técnica da Stonni."),
        ("Infraestrutura", "servidor", VIOLETA,
         "Migrations, controle de acesso por módulo, Edge Functions, rotinas agendadas e deploy contínuo."),
    ]
    linhas_layout = [itens[:2], itens[2:]]
    gap, pad, tam, alt_l = 20, 30, 18, 25
    blocos, y = [], 2
    for fila in linhas_layout:
        cw = (W - gap * (len(fila) - 1)) / len(fila)
        quebras = [quebra(desc, tam, 400, cw - pad * 2) for *_, desc in fila]
        ch = 158 + alt_l * (max(len(q) for q in quebras) - 1) + 36
        for j, (item, q) in enumerate(zip(fila, quebras)):
            blocos.append((j * (cw + gap), y, cw, ch, item, q))
        y += ch + gap
    H = int(y - gap + 2)
    s = SVG(W, H, "Áreas no Grupo Bononi: operação, integração de dados, dashboards, canais de venda e infraestrutura.")
    defs_base(s, W, H)
    s.d(f'<linearGradient id="gCard" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{CARD}"/>'
        f'<stop offset="1" stop-color="{BG0}"/></linearGradient>')
    for i, (x, y, cw, ch, (titulo, ic, cor, _), q) in enumerate(blocos):
        s.d(f'<clipPath id="ca{i}"><rect x="{n(x)}" y="{y}" width="{n(cw)}" height="{ch}" rx="22"/></clipPath>',
            f'<linearGradient id="gba{i}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{cor}" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="{cor}"/></linearGradient>',
            f'<radialGradient id="ra{i}"><stop offset="0" stop-color="{cor}" stop-opacity=".22"/>'
            f'<stop offset="1" stop-color="{cor}" stop-opacity="0"/></radialGradient>')
        ix, iy = x + pad, y + pad
        corpo = [f'<g class="up" style="animation-delay:{0.1 + i * 0.13}s">',
                 f'<rect x="{n(x)}" y="{y}" width="{n(cw)}" height="{ch}" rx="22" fill="url(#gCard)" stroke="{LINHA}"/>',
                 f'<g clip-path="url(#ca{i})"><circle class="deriva{i % 3 + 1}" cx="{n(x + cw - 40)}" cy="{y + 10}" r="200" fill="url(#ra{i})"/>'
                 f'<rect x="{n(x)}" y="{y}" width="{n(cw)}" height="{ch}" fill="url(#pontos)"/></g>',
                 s.brilho_borda(x, y, cw, ch, 22, f"gba{i}", atraso=i * 1.3, dur=9, comp=180),
                 f'<rect x="{n(ix)}" y="{iy}" width="54" height="54" rx="15" fill="{cor}" fill-opacity=".13" stroke="{cor}" stroke-opacity=".45"/>',
                 f'<path transform="translate({n(ix + 12)} {iy + 12}) scale(1.25)" d="{ICONES[ic]}" fill="none" '
                 f'stroke="{cor}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
                 s.t(ix, y + 122, titulo, 27, 700, TEXTO, ls=-0.4)]
        for k, lin in enumerate(q):
            corpo.append(s.t(ix + 1, y + 158 + k * alt_l, lin, tam, 400, APAGADO))
        corpo.append("</g>")
        s.add(*corpo)
    return s


# ---------- projetos ----------
def projeto(arquivo, status, cor, nome_cor, titulo, linhas, chips, link=None, titulo_svg=""):
    W, H = 620, 340
    s = SVG(W, H, titulo_svg)
    defs_base(s, W, H)
    s.d(f'<linearGradient id="gT" gradientUnits="userSpaceOnUse" x1="40" y1="0" x2="{n(40 + F.largura(titulo, 40, 800, -1))}" y2="0">'
        f'<stop offset="0" stop-color="{TEXTO}"/><stop offset=".55" stop-color="{TEXTO}"/><stop offset="1" stop-color="{cor}"/></linearGradient>',
        f'<linearGradient id="gbp" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{cor}" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="{cor}"/></linearGradient>')
    corpo = ['<g clip-path="url(#moldura)">']
    corpo += fundo(s, W, H, [(600, 20, 300, nome_cor), (40, 380, 260, "Violeta")])
    p, _ = pilula(s, 40, 34, status, cor, tam=17, pulso=True, fill_txt=cor, atraso=0.05)
    corpo += p
    corpo.append(f'<g class="up" style="animation-delay:.15s">{s.t(40, 122, titulo, 40, 800, "url(#gT)", ls=-1)}</g>')
    for i, lin in enumerate(linhas):
        corpo.append(f'<g class="up" style="animation-delay:{0.25 + i * 0.08}s">{s.t(41, 164 + i * 28, lin, 19, 400, APAGADO)}</g>')
    corpo.append(f'<line x1="40" y1="254" x2="580" y2="254" stroke="{LINHA}"/>')
    x = 40
    for i, c in enumerate(chips):
        p, w = pilula(s, x, 274, c, LINHA, tam=15, ponto=False, atraso=0.5 + i * 0.1)
        corpo += p
        x += w + 6
    if link:
        wl = F.largura(link, 15, 500)
        assert x + 16 < 560 - wl, (x, wl)
        corpo += [s.t(558, 296, link, 15, 500, cor, "end"),
                  f'<path d="M565 293 l9 -9 M567 284 h7 v7" stroke="{cor}" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>']
    else:
        # barra de "em construção"
        s.d('<clipPath id="cTrilho"><rect x="440" y="287" width="140" height="8" rx="4"/></clipPath>')
        s.css.append(".carga{animation:carga 1.8s ease-in-out infinite}@keyframes carga{from{transform:translateX(-60px)}to{transform:translateX(140px)}}")
        corpo += [f'<rect x="440" y="287" width="140" height="8" rx="4" fill="{LINHA}"/>',
                  f'<g clip-path="url(#cTrilho)"><rect class="carga" x="440" y="287" width="60" height="8" rx="4" fill="{cor}"/></g>']
    corpo.append("</g>")
    corpo.append(s.brilho_borda(1, 1, W - 2, H - 2, 22, "gbp", dur=8, comp=200))
    corpo.append(moldura(W, H))
    s.add(*corpo)
    return arquivo, s


# ---------- stack ----------
def stack():
    secoes = json.loads((RAIZ / "ferramentas" / "stack.json").read_text(encoding="utf-8"))
    W, H = 1280, 632
    s = SVG(W, H, "Tecnologias usadas nas aplicações do Grupo Bononi: " + ", ".join(
        it["rotulo"] for sec in secoes for it in sec["itens"]) + ".")
    defs_base(s, W, H)
    cores = [TEAL, CEU, OURO, VIOLETA, CORAL]
    corpo = ['<g clip-path="url(#moldura)">']
    corpo += fundo(s, W, H, [(1150, 40, 360, "Teal"), (120, 640, 380, "Violeta"), (700, 330, 260, "Ouro")])
    k = 0
    for si, sec in enumerate(secoes):
        cor = cores[si]
        ys = 99 + 112 * si
        yi = 58 + 112 * si
        if si:
            corpo.append(f'<line x1="56" y1="{ys - 63}" x2="1224" y2="{ys - 63}" stroke="{LINHA}"/>')
        corpo += [f'<rect x="56" y="{ys - 21}" width="4" height="26" rx="2" fill="{cor}"/>',
                  s.t(72, ys, sec["nome"], 23, 700, cor)]
        for j, it in enumerate(sec["itens"]):
            x = 347 + 106 * j
            corpo.append(f'<g class="pop" style="animation-delay:{n(0.1 + k * 0.05)}s">')
            corpo.append(f'<rect x="{x - 12}" y="{yi - 12}" width="56" height="56" rx="15" fill="{cor}" '
                         f'fill-opacity=".12" stroke="{cor}" stroke-opacity=".4"/>')
            if "d" in it:
                corpo.append(f'<path transform="translate({x} {yi}) scale(1.3333)" d="{it["d"]}" fill="{cor}"/>')
            else:
                corpo.append(s.t(x + 16, yi + 22, it["sigla"], 16, 700, cor, "middle"))
            corpo.append(s.t(x + 16, yi + 72, it["rotulo"], 15, 500, APAGADO, "middle"))
            corpo.append("</g>")
            k += 1
    corpo.append("</g>")
    corpo.append(moldura(W, H))
    s.add(*corpo)
    return s


# ---------- rodapé ----------
def rodape():
    W, H = 1280, 170
    s = SVG(W, H, "Valeu pela visita! gustavopelissari.com.br")
    defs_base(s, W, H)
    s.d(f'<linearGradient id="gOnda" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{TEAL}"/>'
        f'<stop offset=".5" stop-color="{VIOLETA}"/><stop offset="1" stop-color="{OURO}"/></linearGradient>')
    wt = F.largura("Valeu pela visita!", 34, 800, -0.8)
    s.d(f'<linearGradient id="gTit" gradientUnits="userSpaceOnUse" x1="{n(640 - wt / 2)}" y1="0" x2="{n(640 + wt / 2)}" y2="0">'
        f'<stop offset="0" stop-color="{TEAL}"/><stop offset=".5" stop-color="{TEXTO}"/><stop offset="1" stop-color="{OURO}"/></linearGradient>')
    corpo = ['<g clip-path="url(#moldura)">']
    corpo += fundo(s, W, H, [(640, 200, 420, "Teal")])
    ondas = [(118, 10, 0.0, 0.18, 14), (128, 12, 1.6, 0.28, 10), (140, 8, 3.1, 0.45, 7)]
    for i, (base, amp, fase, op, dur) in enumerate(ondas):
        pts = " ".join(f"L{x} {n(base + amp * math.sin(2 * math.pi * x / 640 + fase))}" for x in range(0, 2561, 16))
        s.css.append(f".on{i}{{animation:on {dur}s linear infinite}}")
        corpo.append(f'<path class="on{i}" d="M0 {H} {pts} L2560 {H}Z" fill="url(#gOnda)" fill-opacity="{op}"/>')
    s.css.append("@keyframes on{to{transform:translateX(-1280px)}}")
    corpo += [s.t(640, 66, "Valeu pela visita!", 34, 800, "url(#gTit)", "middle", -0.8),
              s.t(640, 98, "gustavopelissari.com.br", 17, 500, APAGADO, "middle")]
    corpo.append("</g>")
    corpo.append(moldura(W, H))
    s.add(*corpo)
    return s


def main():
    global F
    F = Fonte(sys.argv[1])
    saidas = {"header.svg": header(), "numeros.svg": numeros(), "areas.svg": areas(),
              "stack.svg": stack(), "rodape.svg": rodape()}
    for arq, s in (
        projeto("projeto-otimizador.svg", "No ar", TEAL, "Teal", "Otimizador de Prompts",
                ["Transforma uma ideia em prompt pronto para IA.",
                 "Planos pagos, limite de uso por plano e extensão",
                 "de navegador para ChatGPT, Claude e Gemini."],
                ["Next.js", "Supabase", "Gemini"], link="otimizadordeprompts.com.br",
                titulo_svg="Otimizador de Prompts, no ar: transforma uma ideia em prompt pronto para IA."),
        projeto("projeto-gestao-financeira.svg", "Nova versão a caminho", OURO, "Ouro", "Gestão Financeira",
                ["Controle financeiro pessoal com lançamentos,",
                 "conciliação e dados separados por usuário, sendo",
                 "refeito para cálculos à prova de erro."],
                ["Supabase", "Docker", "Render"],
                titulo_svg="Gestão Financeira: controle financeiro pessoal, nova versão a caminho."),
    ):
        saidas[arq] = s
    for arq, s in saidas.items():
        txt = s.render()
        (ASSETS / arq).write_text(txt, encoding="utf-8", newline="\n")
        print(f"{arq:32} {s.w}x{s.h}  {len(txt.encode()) / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
