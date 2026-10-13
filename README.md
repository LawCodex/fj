# LawCodex — Fiji (`fj`)

Legislation of the Republic of Fiji as plain Markdown, from the official **Laws of Fiji** website
of the Office of the Attorney-General (<https://www.laws.gov.fj>), which publishes the consolidated
*Revised Edition of the Laws of Fiji* (principal Acts and their subsidiary legislation), kept up to
date by the Office of the Attorney-General.

Part of [LawCodex](https://github.com/LawCodex): the legislation of every country as Markdown in git.

Retrieved: **2026-10-13**.

## Contents

| Category | Directory | Files |
|---|---|---:|
| Constitution of the Republic of Fiji (2013) — English and iTaukei | `constitution/` | 2 |
| Consolidated principal Acts | `acts/` | 381 |
| Subsidiary legislation (regulations, rules, orders, notices…), grouped by parent Act | `subsidiary/<parent act>/` | 914 (under 194 Acts) |
| **Total** | | **1,297** |

Every Act listed under *Consolidated Laws* (390 titles) was retrieved; 9 of them (town proclamations
and a declaration under the Health and Safety at Work Act) have no text on the site.

## What is NOT covered

- *Laws as Published* (the as-made annual Acts, 2014 onwards, PDF) and *Omitted/Repealed Laws*
  (PDF): not included, since the consolidated texts incorporate in-force amendments.
- The Hindi translation of the Constitution: its PDF uses legacy font encoding and extracts as
  garbage, so it was skipped. The Constitution files are text extracted from the official PDFs
  (English is the authoritative text; the iTaukei text is the official translation); the table
  of contents is dropped and headings (`## CHAPTER`, `### Part`, `#### N. heading`) are rebuilt.
- Images (forms in schedules) are not reproduced: they appear as `[image: <file name>]`.

## Structure

```
constitution/constitution-2013-en.md, constitution-2013-fj.md
acts/<slug of title>.md                       acts/crimes-act-2009.md
subsidiary/<parent act slug>/<slug>.md        subsidiary/surveyors-act-1969/surveyors-regulations-2021.md
```

Each Act file contains the long title, the *Table of Amendments*, then the provisions in the order
shown by the laws.gov.fj viewer: `## PART …`, `### DIVISION …` / `### s N heading` (section depth
follows the official table of contents; `[XXX N]` loose-leaf paragraph numbers are dropped).
Notes, history notes and footnotes are kept. Front matter: `identifier` (Laws of Fiji internal id),
`last_amended` (the site's "last updated" date for the consolidation), `source` (viewer page) and
`source_api`.

## Sources and licence

- Official source: Office of the Attorney-General of Fiji — <https://www.laws.gov.fj>. The site is
  a single-page application backed by a public JSON API (`/api/get_all_acts`, `/api/get_act_by_id/<id>`,
  `/api/retrieve_html/<LegalId>`, `/api/retrieve_constitution`), which is what `scripts/fj_fetch.py`
  uses (≈50,000 requests, 3 in parallel, identifying User-Agent, cached). No robots.txt is published;
  the site's Disclaimer describes it as "providing information free of charge for the benefit of the
  public" and does not restrict automated access.
- The texts are official legislation of Fiji, reproduced verbatim as public legal information. This
  is not an official version: the Office of the Attorney-General disclaims liability for the online
  texts; consult laws.gov.fj or the printed Revised Edition for authoritative texts.

## Regenerate

```sh
python3 scripts/fj_fetch.py   ../_raw/fj          # JSON API, cached in ../_raw/fj/api
python3 scripts/fj_convert.py ../_raw/fj .
```
