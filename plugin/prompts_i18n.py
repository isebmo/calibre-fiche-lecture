#!/usr/bin/env python
"""Prompts intégrés, par langue de fiche. Variables : {title} {authors} {language} {index} {total}
{chapter_title} {text} {part} {parts} {summaries}.

Le jeu français est identique aux prompts des versions 0.2.x (réponses en cache conservées).
"""

# --- Français -----------------------------------------------------------------
SYSTEM_PROMPT = (
    "Tu es un critique littéraire et un rédacteur expert de fiches de lecture. "
    "Tu écris en {language}, de manière claire, précise et fidèle au texte fourni. "
    "Tu n'inventes jamais d'éléments absents du texte. Tu réponds en Markdown."
)

CHAPTER_PROMPT = """Livre : « {title} » de {authors}.
Voici le texte intégral de la section {index}/{total}, intitulée « {chapter_title} ».

Rédige un résumé détaillé de cette section (environ 200 à 400 mots selon sa longueur et sa densité) :
- les événements ou idées principales, dans l'ordre où ils apparaissent ;
- les personnages, notions ou arguments clés qui apparaissent ou évoluent ;
- si c'est pertinent, une ou deux citations courtes et marquantes (entre guillemets).

Contraintes : pas de titre de niveau 1 ou 2, pas d'introduction ni de conclusion générale sur le livre.
Commence directement par le résumé.

--- DÉBUT DU TEXTE ---
{text}
--- FIN DU TEXTE ---"""

PART_PROMPT = """Livre : « {title} » de {authors}.
La section « {chapter_title} » ({index}/{total}) est longue et a été découpée.
Voici la partie {part}/{parts} de cette section.

Prends des notes de synthèse détaillées sur cette partie (événements ou idées, personnages ou notions, citations marquantes).

--- DÉBUT DU TEXTE ---
{text}
--- FIN DU TEXTE ---"""

MERGE_PROMPT = """Livre : « {title} » de {authors}.
Voici les notes successives prises sur les différentes parties de la section « {chapter_title} » ({index}/{total}).

Fusionne-les en un résumé unique, cohérent et détaillé de la section (environ 300 à 500 mots),
en respectant l'ordre du texte. Pas de titre de niveau 1 ou 2.

{text}"""

INTRO_PROMPT = """Livre : « {title} » de {authors}.
Voici les résumés de toutes les sections du livre, dans l'ordre :

{summaries}

À partir de ces résumés, rédige l'INTRODUCTION d'une fiche de lecture, avec les rubriques suivantes
(titres de niveau 3, « ### ») :
### Présentation de l'œuvre
(auteur, genre, sujet, contexte si on peut le déduire)
### Résumé d'ensemble
(300 à 500 mots, vue globale de l'intrigue ou de la thèse)
### Thèmes principaux
### Personnages ou notions clés

N'ajoute pas de titre de niveau 1 ou 2."""

CRITIQUE_PROMPT = """Livre : « {title} » de {authors}.
Voici les résumés de toutes les sections du livre, dans l'ordre :

{summaries}

Rédige la partie ANALYSE CRITIQUE de la fiche de lecture, avec les rubriques suivantes
(titres de niveau 3, « ### ») :
### Points forts
### Limites et faiblesses
### Style et construction
### Portée et actualité
### Public visé
### Appréciation finale
(avis argumenté et nuancé)

N'ajoute pas de titre de niveau 1 ou 2."""

FR = {
    'system_prompt': SYSTEM_PROMPT, 'chapter_prompt': CHAPTER_PROMPT, 'part_prompt': PART_PROMPT,
    'merge_prompt': MERGE_PROMPT, 'intro_prompt': INTRO_PROMPT, 'critique_prompt': CRITIQUE_PROMPT,
}

# --- English ------------------------------------------------------------------
EN = {
    'system_prompt': (
        "You are a literary critic and an expert writer of reading notes. "
        "You write in {language}, clearly, precisely and faithfully to the text provided. "
        "You never invent anything that is not in the text. You answer in Markdown."
    ),
    'chapter_prompt': """Book: “{title}” by {authors}.
Here is the full text of section {index}/{total}, titled “{chapter_title}”.

Write a detailed summary of this section (about 200 to 400 words depending on its length and density):
- the main events or ideas, in the order in which they appear;
- the key characters, notions or arguments that appear or develop;
- where relevant, one or two short, striking quotations (in quotation marks).

Constraints: no level 1 or level 2 headings, no introduction or general conclusion about the book.
Start the summary directly.

--- BEGINNING OF TEXT ---
{text}
--- END OF TEXT ---""",
    'part_prompt': """Book: “{title}” by {authors}.
The section “{chapter_title}” ({index}/{total}) is long and has been split.
Here is part {part}/{parts} of this section.

Take detailed summary notes on this part (events or ideas, characters or notions, striking quotations).

--- BEGINNING OF TEXT ---
{text}
--- END OF TEXT ---""",
    'merge_prompt': """Book: “{title}” by {authors}.
Here are the successive notes taken on the different parts of the section “{chapter_title}” ({index}/{total}).

Merge them into a single, coherent and detailed summary of the section (about 300 to 500 words),
following the order of the text. No level 1 or level 2 headings.

{text}""",
    'intro_prompt': """Book: “{title}” by {authors}.
Here are the summaries of all the sections of the book, in order:

{summaries}

Based on these summaries, write the INTRODUCTION of a set of reading notes, with the following sections
(level 3 headings, “###”):
### About the work
(author, genre, subject, context if it can be inferred)
### Overall summary
(300 to 500 words, an overview of the plot or the argument)
### Main themes
### Key characters or concepts

Do not add any level 1 or level 2 headings.""",
    'critique_prompt': """Book: “{title}” by {authors}.
Here are the summaries of all the sections of the book, in order:

{summaries}

Write the CRITICAL ANALYSIS part of the reading notes, with the following sections
(level 3 headings, “###”):
### Strengths
### Limitations and weaknesses
### Style and structure
### Scope and relevance today
### Intended audience
### Final assessment
(a reasoned and nuanced opinion)

Do not add any level 1 or level 2 headings.""",
}

# --- Español ------------------------------------------------------------------
ES = {
    'system_prompt': (
        "Eres un crítico literario y un redactor experto en fichas de lectura. "
        "Escribes en {language}, de forma clara, precisa y fiel al texto proporcionado. "
        "Nunca inventas elementos que no estén en el texto. Respondes en Markdown."
    ),
    'chapter_prompt': """Libro: «{title}», de {authors}.
Este es el texto íntegro de la sección {index}/{total}, titulada «{chapter_title}».

Redacta un resumen detallado de esta sección (entre 200 y 400 palabras aproximadamente, según su extensión y densidad):
- los acontecimientos o ideas principales, en el orden en que aparecen;
- los personajes, conceptos o argumentos clave que aparecen o evolucionan;
- si procede, una o dos citas breves y destacadas (entre comillas).

Restricciones: sin títulos de nivel 1 o 2, sin introducción ni conclusión general sobre el libro.
Empieza directamente con el resumen.

--- INICIO DEL TEXTO ---
{text}
--- FIN DEL TEXTO ---""",
    'part_prompt': """Libro: «{title}», de {authors}.
La sección «{chapter_title}» ({index}/{total}) es larga y se ha dividido.
Esta es la parte {part}/{parts} de la sección.

Toma notas de síntesis detalladas sobre esta parte (acontecimientos o ideas, personajes o conceptos, citas destacadas).

--- INICIO DEL TEXTO ---
{text}
--- FIN DEL TEXTO ---""",
    'merge_prompt': """Libro: «{title}», de {authors}.
Estas son las notas sucesivas tomadas sobre las distintas partes de la sección «{chapter_title}» ({index}/{total}).

Fusiónalas en un único resumen coherente y detallado de la sección (entre 300 y 500 palabras aproximadamente),
respetando el orden del texto. Sin títulos de nivel 1 o 2.

{text}""",
    'intro_prompt': """Libro: «{title}», de {authors}.
Estos son los resúmenes de todas las secciones del libro, en orden:

{summaries}

A partir de estos resúmenes, redacta la INTRODUCCIÓN de una ficha de lectura, con los siguientes apartados
(títulos de nivel 3, «###»):
### Presentación de la obra
(autor, género, tema, contexto si se puede deducir)
### Resumen general
(de 300 a 500 palabras, visión global de la trama o de la tesis)
### Temas principales
### Personajes o conceptos clave

No añadas títulos de nivel 1 o 2.""",
    'critique_prompt': """Libro: «{title}», de {authors}.
Estos son los resúmenes de todas las secciones del libro, en orden:

{summaries}

Redacta la parte de ANÁLISIS CRÍTICO de la ficha de lectura, con los siguientes apartados
(títulos de nivel 3, «###»):
### Puntos fuertes
### Límites y debilidades
### Estilo y estructura
### Alcance y actualidad
### Público destinatario
### Valoración final
(opinión argumentada y matizada)

No añadas títulos de nivel 1 o 2.""",
}

# --- Deutsch ------------------------------------------------------------------
DE = {
    'system_prompt': (
        "Du bist Literaturkritiker und ein erfahrener Verfasser von Buchzusammenfassungen. "
        "Du schreibst auf {language}, klar, präzise und getreu dem vorgelegten Text. "
        "Du erfindest niemals Dinge, die nicht im Text stehen. Du antwortest in Markdown."
    ),
    'chapter_prompt': """Buch: „{title}“ von {authors}.
Hier ist der vollständige Text des Abschnitts {index}/{total} mit dem Titel „{chapter_title}“.

Verfasse eine ausführliche Zusammenfassung dieses Abschnitts (etwa 200 bis 400 Wörter, je nach Länge und Dichte):
- die wichtigsten Ereignisse oder Gedanken in der Reihenfolge, in der sie vorkommen;
- die zentralen Figuren, Begriffe oder Argumente, die auftreten oder sich entwickeln;
- falls sinnvoll, ein oder zwei kurze, prägnante Zitate (in Anführungszeichen).

Vorgaben: keine Überschriften der Ebene 1 oder 2, keine Einleitung und kein allgemeines Fazit zum Buch.
Beginne direkt mit der Zusammenfassung.

--- TEXTANFANG ---
{text}
--- TEXTENDE ---""",
    'part_prompt': """Buch: „{title}“ von {authors}.
Der Abschnitt „{chapter_title}“ ({index}/{total}) ist lang und wurde aufgeteilt.
Hier ist Teil {part}/{parts} dieses Abschnitts.

Mache ausführliche zusammenfassende Notizen zu diesem Teil (Ereignisse oder Gedanken, Figuren oder Begriffe, prägnante Zitate).

--- TEXTANFANG ---
{text}
--- TEXTENDE ---""",
    'merge_prompt': """Buch: „{title}“ von {authors}.
Hier sind die nacheinander erstellten Notizen zu den verschiedenen Teilen des Abschnitts „{chapter_title}“ ({index}/{total}).

Füge sie zu einer einzigen, zusammenhängenden und ausführlichen Zusammenfassung des Abschnitts zusammen (etwa 300 bis 500 Wörter)
und halte dich an die Reihenfolge des Textes. Keine Überschriften der Ebene 1 oder 2.

{text}""",
    'intro_prompt': """Buch: „{title}“ von {authors}.
Hier sind die Zusammenfassungen aller Abschnitte des Buches, in der richtigen Reihenfolge:

{summaries}

Verfasse auf Grundlage dieser Zusammenfassungen die EINLEITUNG einer Buchzusammenfassung mit folgenden Rubriken
(Überschriften der Ebene 3, „###“):
### Vorstellung des Werks
(Autor, Gattung, Thema, Kontext, sofern ableitbar)
### Gesamtzusammenfassung
(300 bis 500 Wörter, Gesamtüberblick über Handlung oder These)
### Hauptthemen
### Zentrale Figuren oder Begriffe

Füge keine Überschriften der Ebene 1 oder 2 hinzu.""",
    'critique_prompt': """Buch: „{title}“ von {authors}.
Hier sind die Zusammenfassungen aller Abschnitte des Buches, in der richtigen Reihenfolge:

{summaries}

Verfasse den Teil KRITISCHE ANALYSE der Buchzusammenfassung mit folgenden Rubriken
(Überschriften der Ebene 3, „###“):
### Stärken
### Grenzen und Schwächen
### Stil und Aufbau
### Bedeutung und Aktualität
### Zielgruppe
### Gesamturteil
(begründete und differenzierte Einschätzung)

Füge keine Überschriften der Ebene 1 oder 2 hinzu.""",
}

# --- Italiano -----------------------------------------------------------------
IT = {
    'system_prompt': (
        "Sei un critico letterario e un redattore esperto di schede di lettura. "
        "Scrivi in {language}, in modo chiaro, preciso e fedele al testo fornito. "
        "Non inventi mai elementi assenti dal testo. Rispondi in Markdown."
    ),
    'chapter_prompt': """Libro: «{title}» di {authors}.
Ecco il testo integrale della sezione {index}/{total}, intitolata «{chapter_title}».

Scrivi un riassunto dettagliato di questa sezione (circa 200-400 parole a seconda della lunghezza e della densità):
- gli eventi o le idee principali, nell'ordine in cui compaiono;
- i personaggi, i concetti o gli argomenti chiave che compaiono o si sviluppano;
- se pertinente, una o due citazioni brevi e significative (tra virgolette).

Vincoli: nessun titolo di livello 1 o 2, nessuna introduzione o conclusione generale sul libro.
Inizia direttamente con il riassunto.

--- INIZIO DEL TESTO ---
{text}
--- FINE DEL TESTO ---""",
    'part_prompt': """Libro: «{title}» di {authors}.
La sezione «{chapter_title}» ({index}/{total}) è lunga ed è stata suddivisa.
Ecco la parte {part}/{parts} di questa sezione.

Prendi appunti di sintesi dettagliati su questa parte (eventi o idee, personaggi o concetti, citazioni significative).

--- INIZIO DEL TESTO ---
{text}
--- FINE DEL TESTO ---""",
    'merge_prompt': """Libro: «{title}» di {authors}.
Ecco gli appunti presi in successione sulle diverse parti della sezione «{chapter_title}» ({index}/{total}).

Uniscili in un unico riassunto coerente e dettagliato della sezione (circa 300-500 parole),
rispettando l'ordine del testo. Nessun titolo di livello 1 o 2.

{text}""",
    'intro_prompt': """Libro: «{title}» di {authors}.
Ecco i riassunti di tutte le sezioni del libro, in ordine:

{summaries}

Sulla base di questi riassunti, scrivi l'INTRODUZIONE di una scheda di lettura, con le seguenti rubriche
(titoli di livello 3, «###»):
### Presentazione dell'opera
(autore, genere, argomento, contesto se deducibile)
### Riassunto complessivo
(300-500 parole, visione d'insieme della trama o della tesi)
### Temi principali
### Personaggi o concetti chiave

Non aggiungere titoli di livello 1 o 2.""",
    'critique_prompt': """Libro: «{title}» di {authors}.
Ecco i riassunti di tutte le sezioni del libro, in ordine:

{summaries}

Scrivi la parte di ANALISI CRITICA della scheda di lettura, con le seguenti rubriche
(titoli di livello 3, «###»):
### Punti di forza
### Limiti e debolezze
### Stile e struttura
### Portata e attualità
### Pubblico di riferimento
### Giudizio finale
(opinione argomentata e sfumata)

Non aggiungere titoli di livello 1 o 2.""",
}

# --- Português ----------------------------------------------------------------
PT = {
    'system_prompt': (
        "És um crítico literário e um redator especialista em fichas de leitura. "
        "Escreves em {language}, de forma clara, precisa e fiel ao texto fornecido. "
        "Nunca inventas elementos que não estejam no texto. Respondes em Markdown."
    ),
    'chapter_prompt': """Livro: «{title}», de {authors}.
Eis o texto integral da secção {index}/{total}, intitulada «{chapter_title}».

Redige um resumo detalhado desta secção (cerca de 200 a 400 palavras, consoante a extensão e a densidade):
- os acontecimentos ou ideias principais, pela ordem em que aparecem;
- as personagens, noções ou argumentos-chave que surgem ou evoluem;
- se for pertinente, uma ou duas citações curtas e marcantes (entre aspas).

Restrições: sem títulos de nível 1 ou 2, sem introdução nem conclusão geral sobre o livro.
Começa diretamente pelo resumo.

--- INÍCIO DO TEXTO ---
{text}
--- FIM DO TEXTO ---""",
    'part_prompt': """Livro: «{title}», de {authors}.
A secção «{chapter_title}» ({index}/{total}) é longa e foi dividida.
Eis a parte {part}/{parts} desta secção.

Toma notas de síntese detalhadas sobre esta parte (acontecimentos ou ideias, personagens ou noções, citações marcantes).

--- INÍCIO DO TEXTO ---
{text}
--- FIM DO TEXTO ---""",
    'merge_prompt': """Livro: «{title}», de {authors}.
Eis as notas sucessivas tiradas sobre as diferentes partes da secção «{chapter_title}» ({index}/{total}).

Funde-as num único resumo coerente e detalhado da secção (cerca de 300 a 500 palavras),
respeitando a ordem do texto. Sem títulos de nível 1 ou 2.

{text}""",
    'intro_prompt': """Livro: «{title}», de {authors}.
Eis os resumos de todas as secções do livro, por ordem:

{summaries}

Com base nestes resumos, redige a INTRODUÇÃO de uma ficha de leitura, com as seguintes rubricas
(títulos de nível 3, «###»):
### Apresentação da obra
(autor, género, tema, contexto se for possível deduzi-lo)
### Resumo geral
(300 a 500 palavras, visão global do enredo ou da tese)
### Temas principais
### Personagens ou noções-chave

Não acrescentes títulos de nível 1 ou 2.""",
    'critique_prompt': """Livro: «{title}», de {authors}.
Eis os resumos de todas as secções do livro, por ordem:

{summaries}

Redige a parte de ANÁLISE CRÍTICA da ficha de leitura, com as seguintes rubricas
(títulos de nível 3, «###»):
### Pontos fortes
### Limites e fragilidades
### Estilo e construção
### Alcance e atualidade
### Público-alvo
### Apreciação final
(opinião fundamentada e matizada)

Não acrescentes títulos de nível 1 ou 2.""",
}

PROMPTS = {'fr': FR, 'en': EN, 'es': ES, 'de': DE, 'it': IT, 'pt': PT}
