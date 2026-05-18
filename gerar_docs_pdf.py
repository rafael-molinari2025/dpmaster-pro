"""Gera PDF de documentação técnica extraindo docstrings de app_dp.py via AST."""

import ast
import os
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    Table, TableStyle, PageBreak
)

# ── Configurações ──────────────────────────────────────────────────────────────
FONTE_ALVO = os.path.join(os.path.dirname(__file__), "app_dp.py")
SAIDA_PDF  = os.path.join(os.path.dirname(__file__), "documentacao_tecnica.pdf")
SISTEMA    = "DPMaster Pro"
VERSAO     = "2.0.0"

# Seções na ordem em que aparecem no arquivo
SECAO_MAP = {
    "CONFIGURAÇÕES / LOGGING":  "Configurações e Logging",
    "SEGURANÇA":                "Segurança",
    "CRIPTOGRAFIA":             "Criptografia",
    "CARREGAR / SALVAR":        "Persistência de Dados",
    "eSocial FILA":             "Fila eSocial",
    "DOCUMENTOS":               "Documentos de Funcionários",
    "CÁLCULOS":                 "Cálculos Trabalhistas",
    "GERAÇÃO DE PDF":           "Geração de PDF (ReportLab)",
    "eSocial XML":              "Geração de XML eSocial",
    "UI / CSS":                 "Interface / CSS",
    "LOGIN / PERMISSÕES":       "Login e Permissões",
}

# ── Extração via AST ───────────────────────────────────────────────────────────
def extrair_funcoes(caminho: str) -> list[dict]:
    """Lê o arquivo Python e extrai nome, linha, docstring e seção de cada função."""
    with open(caminho, "r", encoding="utf-8") as f:
        source = f.read()
        linhas = source.splitlines()

    tree = ast.parse(source)
    funcoes = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node) or ""
            # Detectar seção: varre para trás a partir da linha da def
            secao = "Outros"
            for i in range(node.lineno - 2, max(node.lineno - 60, -1), -1):
                linha = linhas[i].strip()
                for chave, nome in SECAO_MAP.items():
                    if chave in linha:
                        secao = nome
                        break
                if secao != "Outros":
                    break

            # Montar assinatura simples
            args = [a.arg for a in node.args.args]
            sig = f"def {node.name}({', '.join(args)})"

            funcoes.append({
                "nome":   node.name,
                "linha":  node.lineno,
                "sig":    sig,
                "doc":    doc,
                "secao":  secao,
            })

    # Ordenar por linha
    funcoes.sort(key=lambda x: x["linha"])
    return funcoes


# ── Construção do PDF ──────────────────────────────────────────────────────────
COR_TITULO   = colors.HexColor("#0f172a")
COR_SECAO    = colors.HexColor("#1e3a5f")
COR_FUNC_BG  = colors.HexColor("#f1f5f9")
COR_SIG_BG   = colors.HexColor("#1e293b")
COR_LINHA    = colors.HexColor("#cbd5e1")
COR_DOC      = colors.HexColor("#334155")
COR_SEM_DOC  = colors.HexColor("#dc2626")


def estilos():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "Titulo", parent=base["Title"],
            fontSize=22, textColor=COR_TITULO,
            spaceAfter=4, alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        ),
        "subtitulo": ParagraphStyle(
            "Subtitulo", parent=base["Normal"],
            fontSize=10, textColor=colors.HexColor("#475569"),
            spaceAfter=2, alignment=TA_CENTER,
        ),
        "secao": ParagraphStyle(
            "Secao", parent=base["Normal"],
            fontSize=13, fontName="Helvetica-Bold",
            textColor=colors.white, spaceBefore=10, spaceAfter=2,
        ),
        "sig": ParagraphStyle(
            "Sig", parent=base["Code"],
            fontSize=8, fontName="Courier-Bold",
            textColor=colors.HexColor("#7dd3fc"),
            leftIndent=6, spaceBefore=0, spaceAfter=0,
        ),
        "linha": ParagraphStyle(
            "Linha", parent=base["Normal"],
            fontSize=7, textColor=colors.HexColor("#94a3b8"),
            leftIndent=6,
        ),
        "doc": ParagraphStyle(
            "Doc", parent=base["Normal"],
            fontSize=9, textColor=COR_DOC,
            leftIndent=8, rightIndent=8,
            spaceBefore=4, spaceAfter=4,
            leading=13,
        ),
        "sem_doc": ParagraphStyle(
            "SemDoc", parent=base["Normal"],
            fontSize=8, textColor=COR_SEM_DOC,
            leftIndent=8, italics=1,
        ),
        "rodape": ParagraphStyle(
            "Rodape", parent=base["Normal"],
            fontSize=7, textColor=colors.HexColor("#94a3b8"),
            alignment=TA_CENTER,
        ),
        "indice_secao": ParagraphStyle(
            "IndSecao", parent=base["Normal"],
            fontSize=10, fontName="Helvetica-Bold",
            textColor=COR_SECAO, spaceBefore=6,
        ),
        "indice_func": ParagraphStyle(
            "IndFunc", parent=base["Normal"],
            fontSize=8, textColor=colors.HexColor("#475569"),
            leftIndent=12,
        ),
        "stats": ParagraphStyle(
            "Stats", parent=base["Normal"],
            fontSize=9, textColor=colors.HexColor("#374151"),
            leftIndent=4,
        ),
    }


def cabecalho_pagina(canvas, doc):
    """Callback de página: cabeçalho e rodapé em todas as folhas."""
    largura, altura = A4
    canvas.saveState()
    # Linha topo
    canvas.setStrokeColor(COR_SECAO)
    canvas.setLineWidth(1.2)
    canvas.line(15*mm, altura - 12*mm, largura - 15*mm, altura - 12*mm)
    # Texto cabeçalho
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(COR_SECAO)
    canvas.drawString(15*mm, altura - 10*mm, f"{SISTEMA}  |  Documentação Técnica v{VERSAO}")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    canvas.drawRightString(largura - 15*mm, altura - 10*mm,
                           f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    # Rodapé
    canvas.setStrokeColor(COR_LINHA)
    canvas.setLineWidth(0.5)
    canvas.line(15*mm, 12*mm, largura - 15*mm, 12*mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    canvas.drawCentredString(largura / 2, 8*mm, f"Página {doc.page}")
    canvas.restoreState()


def gerar_pdf(funcoes: list[dict], saida: str):
    s = estilos()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=20*mm, bottomMargin=18*mm,
    )

    story = []

    # ── Capa ──────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 30*mm))
    story.append(Paragraph(f"🏢 {SISTEMA}", s["titulo"]))
    story.append(Paragraph("Documentação Técnica do Código-Fonte", s["subtitulo"]))
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="60%", thickness=2, color=COR_SECAO, hAlign="CENTER"))
    story.append(Spacer(1, 6*mm))

    total   = len(funcoes)
    com_doc = sum(1 for f in funcoes if f["doc"])
    sem_doc = total - com_doc
    secoes  = len({f["secao"] for f in funcoes})

    stats = [
        ["Arquivo analisado",    "app_dp.py"],
        ["Versão do sistema",    VERSAO],
        ["Total de funções",     str(total)],
        ["Com docstring",        str(com_doc)],
        ["Sem docstring",        str(sem_doc)],
        ["Seções documentadas",  str(secoes)],
        ["Data de geração",      datetime.now().strftime("%d/%m/%Y %H:%M")],
    ]
    tab = Table(
        [[Paragraph(f"<b>{r[0]}</b>", s["stats"]),
          Paragraph(r[1], s["stats"])] for r in stats],
        colWidths=[70*mm, 90*mm],
        hAlign="CENTER",
    )
    tab.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1),
         [colors.HexColor("#f1f5f9"), colors.HexColor("#ffffff")]),
        ("GRID", (0, 0), (-1, -1), 0.4, COR_LINHA),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(tab)
    story.append(PageBreak())

    # ── Índice ─────────────────────────────────────────────────────────────────
    story.append(Paragraph("Índice de Funções", ParagraphStyle(
        "TitIdx", parent=getSampleStyleSheet()["Title"],
        fontSize=16, textColor=COR_TITULO, alignment=TA_LEFT,
        spaceAfter=6, fontName="Helvetica-Bold",
    )))
    story.append(HRFlowable(width="100%", thickness=1, color=COR_LINHA))
    story.append(Spacer(1, 4*mm))

    secao_atual = None
    for f in funcoes:
        if f["secao"] != secao_atual:
            secao_atual = f["secao"]
            story.append(Paragraph(f["secao"], s["indice_secao"]))
        marcador = "✓" if f["doc"] else "✗"
        cor = "#166534" if f["doc"] else "#991b1b"
        story.append(Paragraph(
            f'<font color="{cor}">{marcador}</font>  '
            f'{f["nome"]}  '
            f'<font color="#94a3b8" size="7">linha {f["linha"]}</font>',
            s["indice_func"],
        ))

    story.append(PageBreak())

    # ── Conteúdo por seção ─────────────────────────────────────────────────────
    secao_atual = None
    for f in funcoes:
        if f["secao"] != secao_atual:
            secao_atual = f["secao"]
            # Cabeçalho de seção
            sec_tab = Table(
                [[Paragraph(f"  {secao_atual}", s["secao"])]],
                colWidths=[180*mm],
            )
            sec_tab.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), COR_SECAO),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("ROUNDEDCORNERS", [4]),
            ]))
            story.append(Spacer(1, 4*mm))
            story.append(sec_tab)
            story.append(Spacer(1, 3*mm))

        # Card da função
        sig_tab = Table(
            [[Paragraph(f["sig"], s["sig"]),
              Paragraph(f'<font size="7" color="#94a3b8">linha {f["linha"]}</font>',
                        ParagraphStyle("R", parent=getSampleStyleSheet()["Normal"],
                                       fontSize=7, textColor=colors.HexColor("#94a3b8"),
                                       alignment=1))]],
            colWidths=[140*mm, 38*mm],
        )
        sig_tab.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COR_SIG_BG),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (0, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROUNDEDCORNERS", [4]),
        ]))

        doc_texto = f["doc"].replace("\n", " ").strip() if f["doc"] else None
        doc_par = (
            Paragraph(doc_texto, s["doc"]) if doc_texto
            else Paragraph("⚠  Sem docstring.", s["sem_doc"])
        )

        card = Table(
            [[sig_tab], [doc_par]],
            colWidths=[180*mm],
        )
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COR_FUNC_BG),
            ("BACKGROUND", (0, 0), (-1, 0), COR_SIG_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, COR_LINHA),
            ("TOPPADDING", (0, 1), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))

        story.append(card)
        story.append(Spacer(1, 3*mm))

    # Construir com callback de página
    doc.build(story, onFirstPage=cabecalho_pagina, onLaterPages=cabecalho_pagina)

    # Salvar no disco
    with open(saida, "wb") as f:
        f.write(buf.getvalue())

    return saida


# ── Entrypoint ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Analisando {FONTE_ALVO} ...")
    funcoes = extrair_funcoes(FONTE_ALVO)
    print(f"  {len(funcoes)} funções encontradas.")
    print(f"Gerando PDF em {SAIDA_PDF} ...")
    gerar_pdf(funcoes, SAIDA_PDF)
    print("Concluído.")
