# Listing copy (Kleinanzeigen style)

ReLoop writes copy in the style of Kleinanzeigen listings. It does not integrate with Kleinanzeigen and does not publish anything. Write the German version first (`listing_title`, `listing_description`), then an English version with the same content (`listing_translations.en`).

## Principles

- Write concise, natural German: factual, friendly and neutral. Use no sales hype, no keyword stuffing, no emoji walls and no ALL CAPS.
- Include only supported facts: identity, brand and model where known, quantity, whether the offer is a single item, individual units or a bundle, physical condition, user-reported function, known defects, and included and missing accessories.
- Attribute function to what the user reported: "Getestet und funktionsfähig" only if the user said they tested it. Otherwise leave function out, or say "nicht getestet" if the user said so.
- Do not present unresolved guesses as facts. Leave uncertain specifications out. Qualify one only when it is genuinely useful and true, for example "Laut Typenschild eines Geräts: Modell 24MK430H".
- Never invent or add: an asking price, "VB" or negotiation terms, pickup or shipping, the reason for selling (use it only if the user gave one), warranty or return terms, private-seller status, legal disclaimers such as "Privatverkauf, keine Garantie", or claims like "wie neu", "top Zustand" or "neuwertig".
- Keep serial numbers, personal data and precise locations out unless the user explicitly asks to include them.
- If there is too little supported information for a meaningful listing, set the listing fields to `null` and say why in the summary.

## Title

Use the pattern `[Menge ×] [Marke] [Modell] [Artikeltyp] [wichtigstes Merkmal] [– Hinweis auf Defekt]`.

- Leave out any part that is unknown.
- Keep it short and scannable. Aiming for about 60 characters or fewer is a style choice, not a verified platform limit.
- Put a known defect or "für Bastler" in the title when the item does not work.

Examples:
- `24 × LG Computermonitore (Büroauflösung)`
- `2 × JBL Bluetooth-Lautsprecher – 1 funktionsfähig, 1 defekt`
- `WLAN-Router mit 4 Antennen`

## Description structure (German)

Leave out any line that has no supported content:

```
<Ein Satz: Was wird angeboten, wie viele, einzeln oder als Paket.>

Zustand: <Wortlaut aus Tabelle unten; konkrete sichtbare Mängel>
Funktion: <nur vom Nutzer bestätigte Angaben>
Lieferumfang: <bestätigtes Zubehör>
Nicht enthalten: <bestätigt fehlendes Zubehör>
Details: <belegte Merkmale, z. B. Farbe, Größe laut Typenschild>
```

## Condition wording

| Value | German | English |
| --- | --- | --- |
| `new_sealed` | Neu und originalverpackt (OVP, Siegel intakt) | New, factory-sealed |
| `unused_open_box` | Unbenutzt, Verpackung geöffnet | Unused, open box |
| `light_wear` | Gebraucht mit leichten Gebrauchsspuren | Used, light signs of wear |
| `moderate_wear` | Gebraucht mit deutlichen Gebrauchsspuren | Used, clearly visible signs of wear |
| `heavy_wear` | Stark gebraucht, starke Gebrauchsspuren | Heavily used, significant wear |
| `damaged` | Beschädigt (siehe Mängel) | Damaged (see defects) |
| `mixed` | Zustand unterschiedlich, siehe Einzelangaben | Condition varies, see unit details |
| `null` | Leave condition out, or "Gebraucht" if use is evident | Leave condition out, or "Used" |

## Function wording

| Value | German | English |
| --- | --- | --- |
| `working` | Getestet und funktionsfähig | Tested and working |
| `partially_working` | Teilweise funktionsfähig: <was nicht geht> | Partly working: <what fails> |
| `not_working` | Defekt: <Symptom, falls bekannt> – für Bastler oder als Ersatzteilspender | Not working: <symptom if known>, for repair or parts |
| `untested` | Nicht getestet | Not tested |
| `mixed` | Per unit, for example "1 Gerät funktionsfähig, 1 Gerät defekt" | Per unit |
| `null` | Leave it out | Leave it out |

## Category suggestion

Give a human-readable path in `suggested_category`, for example `Elektronik > Monitore` or `Haus & Garten > Küche`. It is a suggestion for the user to pick in the marketplace. Never output official category IDs or claim the path matches the marketplace's current tree exactly.

## English version

Translate the German listing faithfully: the same facts and caveats, with nothing added or removed. Use plain British or international English.
