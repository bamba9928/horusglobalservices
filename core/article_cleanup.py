"""Nettoyage des titres des articles issus d'anciens copier-coller.

Constat (2026-10) : les articles utilisaient des <h1> pour tout et n'importe quoi :
titre de l'article repete dans le corps, titres de sections, phrases d'introduction, et meme
des titres VIDES servant d'espacement. Or la page affiche deja le titre de l'article en <h1> :
un corps d'article ne doit contenir que des <h2>/<h3>... Une fois la mise en forme (plugin
Typography de Tailwind) activee, ces <h1> deviennent geants.

Regles, volontairement prudentes et deterministes :
  1. titre (h1-h4) vide                                   -> supprime
  2. premier titre = <h1> identique au titre de l'article  -> supprime (doublon de la page)
  3. autre <h1> qui est une phrase (long ou ponctue)       -> <p>
  4. autre <h1>                                            -> <h2>
  5. paragraphe vide (&nbsp;, <br>) servant d'espaceur      -> supprime (le plugin Typography gere
     deja les marges : ils creent de grands blancs)
Les <h2>/<h3>/<h4>, les paragraphes non vides et le texte ne sont jamais modifies. Idempotent.
"""
import re
from collections import Counter
from html import unescape

HEADING = re.compile(r"<(h[1-4])(\b[^>]*)>(.*?)</\1>", re.S | re.I)
EMPTY_PARAGRAPH = re.compile(r"<p\b[^>]*>(?:\s|&nbsp;|\xa0|<br\s*/?>)*</p>\s*", re.I)
MAX_TITLE_LENGTH = 90
SENTENCE_END = (".", ":", ";", ",", "…", "!", "?")


def plain_text(inner_html):
    text = unescape(re.sub(r"<[^>]+>", " ", inner_html)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _comparable(text):
    return re.sub(r"\W+", "", text.casefold())


def clean_article_html(html, title):
    """Retourne (html_nettoye, Counter des modifications)."""
    changes = Counter()
    state = {"first_heading_seen": False}

    def replace(match):
        tag, attributes, inner = match.group(1).lower(), match.group(2), match.group(3)
        text = plain_text(inner)

        if not text and "<img" not in inner.lower():
            changes["titre vide supprimé"] += 1
            return ""

        is_first = not state["first_heading_seen"]
        state["first_heading_seen"] = True
        if tag != "h1":
            return match.group(0)

        if is_first and _comparable(text) == _comparable(title):
            changes["titre en double supprimé"] += 1
            return ""
        if len(text) > MAX_TITLE_LENGTH or text.endswith(SENTENCE_END):
            changes["h1 → paragraphe (phrase)"] += 1
            return f"<p{attributes}>{inner}</p>"
        changes["h1 → h2 (titre de section)"] += 1
        return f"<h2{attributes}>{inner}</h2>"

    html = HEADING.sub(replace, html)
    html, spacers = EMPTY_PARAGRAPH.subn("", html)
    if spacers:
        changes["paragraphe vide supprimé"] += spacers
    return html, changes
