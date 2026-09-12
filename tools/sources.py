# -*- coding: utf-8 -*-
"""Catalogo das provas: arquivo, gabarito, dialeto e numero de alternativas."""

SRC = r"C:\Users\rapha\OneDrive\Área de Trabalho\COOTEC"

# dialeto: "num" = questao inicia com "01."; "questao" = inicia com "QUESTAO 01"
PROVAS = {
    2008: dict(prova="VESTIBULINHO prova2008-bauru-guara.pdf",         gab="VEST gabarito2008-bauru-guara.pdf", dialeto="num",     alts=5),
    2009: dict(prova="VESTIBULINHO prova2009-bauru-guara.pdf",         gab="VEST gabarito2009-bauru-guara.pdf", dialeto="num",     alts=5),
    2010: dict(prova="VESTIBULINHO prova2010-bauru-guara.pdf",         gab="VEST gabarito2010-bauru-guara.pdf", dialeto="num",     alts=5),
    2011: dict(prova="VESTIBULINHO prova2011.pdf",                     gab="VEST gabarito2011.pdf",             dialeto="num",     alts=4),
    2012: dict(prova="VESTIBULINHO+2012+ProvaConhecimentosGerais.pdf", gab="VEST+2012+Gabarito.pdf",            dialeto="num",     alts=4),
    2013: dict(prova="2013.pdf",                                       gab="gabarito 2013.pdf",                 dialeto="num",     alts=4),
    2014: dict(prova="Prova objetiva 2014.pdf",                        gab="Gabarito 2014.pdf",                 dialeto="questao", alts=4),
    2015: dict(prova="Prova objetiva 2015.pdf",                        gab="Gabarito2015.pdf",                  dialeto="questao", alts=4),
    2016: dict(prova="2016.pdf",                                       gab="gabarito 2016.pdf",                 dialeto="questao", alts=4),
    2019: dict(prova="2019.pdf",                                       gab="gabarito 2019.pdf",                 dialeto="questao", alts=4),
    2020: dict(prova="2020.pdf",                                       gab="gabarito 2020.pdf",                 dialeto="questao", alts=4),
    2021: dict(prova="2021.pdf",                                       gab="gabarito 2021.pdf",                 dialeto="questao", alts=4),
    2022: dict(prova="2022.pdf",                                       gab="gabarito 2022.pdf",                 dialeto="questao", alts=4),
}

MATERIA_CANON = {
    "MATEMATICA": "Matemática",
    "LINGUA PORTUGUESA": "Língua Portuguesa",
    "PORTUGUES": "Língua Portuguesa",
    "CIENCIAS": "Ciências",
    "CIENCIAS HUMANAS": "Ciências Humanas",
    "CIENCIAS NATURAIS": "Ciências Naturais",
    "CIENCIAS DA NATUREZA": "Ciências Naturais",
    "HISTORIA": "História",
    "GEOGRAFIA": "Geografia",
    "INGLES": "Inglês",
    "LINGUA INGLESA": "Inglês",
}
