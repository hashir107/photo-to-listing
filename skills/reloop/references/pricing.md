# Price suggestions

ReLoop can suggest a price range for the Kleinanzeigen "Preis" field, but only when the user wants one. A suggestion is only as good as its basis, so every price states where it came from. The user decides the final price and the Preistyp (Festpreis or VB).

## 0. Opt-in (`price_status`)

Do not estimate a price by default. Track the user's choice in `price_status`:

| `price_status` | When | `price_estimate` | Preis row in section B |
| --- | --- | --- | --- |
| `offered` | Default when the item type is known and the user has not chosen yet. Ask once, at the end of section C: **Preisvorschlag?** Vergleichsanzeigen mit Preisen einfügen, die Websuche erlauben, oder den Preis selbst festlegen? | `null` | "noch kein Vorschlag (siehe Frage unten)" |
| `estimated` | The user pasted comparable prices, allowed web search, asked for an estimate, or already did one of these in the first message | the estimate (sections 1–5) | the price with its basis |
| `declined` | The user says they will set the price themselves, e.g. "mache ich selbst" or "I'll add it myself" | `null` | "selbst festlegen" |
| `not_applicable` | No price is possible yet: item type unknown, nothing inspectable, or a regulated item (section 5) | `null` | "kein Vorschlag" and the reason |

Rules:
- The offer is not one of the three clarification questions, and it never displaces them.
- A pricing choice persists across turns. After `declined`, never offer or estimate again unless the user asks.
- If the user ignores the offer, leave it `offered` and keep the one-line offer. Do not escalate or nag.
- **Web search allowed** means the user agreed to a lookup. Only search if the host can, and follow the rules in section 6. If nothing usable is found or the host cannot browse, say so and give the labelled `model_knowledge` range.
- When the status moves from `offered` to `estimated`, mention it in the change bullets.

## 1. Basis, in order of preference

Use the first basis that is available. You may mention a lower-ranked basis as a cross-check, but `basis` names the one the numbers come from.

| `basis` | When | Evidence required | How to compute |
| --- | --- | --- | --- |
| `user_comparables` | The user pasted prices of comparable listings, for example "Ähnliche Anzeigen: 45 €, 50 €, 60 €" or a screenshot | `user_statement` evidence quoting the prices | Take the median. Adjust for differences in condition, function, accessories and quantity, and say how |
| `reference_new_price` | Web search is available and the item is identified well enough (brand + model, or a precise product type) | `external_reference` evidence with the real URL you opened (manufacturer, retailer or price-comparison page) and the price seen there | Multiply the current new price by the depreciation band (section 2), then apply the adjustments |
| `model_knowledge` | No comparables and no usable source | `inference` evidence with `certainty: "tentative"` that explains the reasoning in one line | Give a cautious range from general knowledge of used prices. In the table, label it **"ungeprüft (Modellwissen)"** and suggest checking comparable listings |

Never present a `model_knowledge` price as researched. Never cite a source you did not open.

## 2. Depreciation bands (`reference_new_price`)

These are **heuristic** starting points for second-hand consumer goods, not market data. Use the user's comparables over them whenever you have both.

| Condition / function | Share of the current new price |
| --- | --- |
| `new_sealed` | 70–85 % |
| `unused_open_box` | 60–75 % |
| `light_wear`, working | 40–60 % |
| `moderate_wear`, working | 30–45 % |
| `heavy_wear`, working | 15–30 % |
| `not_working` / for parts | 5–20 % |
| function `untested` or unknown | the condition band, minus another 20–30 % of it |

Adjustments:
- **Age:** if the model is several generations old or no longer sold, use the lower half of the band. If no current new price exists, use the successor's price only with an explicit note.
- **Missing accessories** such as the power supply, remote or stand lower the price. Original packaging slightly raises it.
- **Brand or model unknown:** widen the range and say why. If even the product type is too vague to price, give no price.

## 3. Quantity and lots

- `scope: "per_unit"` when several identical units may be sold separately, or when the sale configuration is unknown. `scope: "lot"` when the user sells everything together. `scope: "single_item"` for one item.
- For lots, also give `lot_total_suggested`, which is the per-unit price × quantity minus a bulk discount of about 15–30 %. State the discount in `assumptions`.
- Keep the table and the JSON consistent. Any price shown in the Preis row, including a lot total, must also be in `price_estimate`. If you mention a lot total, set `lot_total_suggested` to that number.
- A cited page that shows no current new price (discontinued model, no offers) is still useful evidence. Cite it, then fall back to `model_knowledge` and say why.
- Units with different function (for example 1 working, 1 defective) are priced separately. Mention the defective unit's parts value in `assumptions`.

## 4. Rounding and range

- Round to 5 € below 100 €, and to 10 € above.
- Keep `low ≤ suggested ≤ high`. Make the range wider when the basis is weaker (model_knowledge, unknown model, untested).
- Currency is always EUR.

## 5. When to give no price (`price_estimate: null`)

- `item_type` is unknown, for example unrelated objects or a conflict not yet resolved.
- No photo could be inspected and the user gave too little detail.
- The item may be regulated or unsafe to resell, such as medicines, weapons or recalled products. Say so instead.

In the table, write "kein Vorschlag" with the reason, and ask the one question that would unlock a price.

## 6. Never

- Never fetch, scrape or automate access to Kleinanzeigen, eBay or other marketplace pages. Ask the user to paste comparable prices instead; they can check listings themselves in a few seconds.
- Never upload the user's photos to search or price services without explicit permission.
- Never invent URLs, retailers, comparable listings or "average market prices".
- Never put the price in the title or description.
- Never claim certainty: a price is a suggestion, and the market decides.
