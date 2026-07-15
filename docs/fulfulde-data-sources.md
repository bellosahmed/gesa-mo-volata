# Fulfulde / Fulani data sources — audit & citations

Sources provided by the project owner and audited on **2026-07-15** for fine-tuning the local
model (Qwen2.5-1.5B) to understand and produce Fulfulde. Every source we use is cited here;
licenses are recorded before any data touches training.

## Usable now (downloaded / verified accessible)

### 1. Kallaama speech dataset — ★ primary training corpus
- **Paper:** Gauthier, E., Ndiaye, A., Guissé, A. (2024). *Kallaama: A Transcribed Speech Dataset
  about Agriculture in the Three Most Widely Spoken Languages in Senegal.*
  https://arxiv.org/html/2404.01991v1
- **Data:** https://github.com/gauthelo/kallaama-speech-dataset — **License: CC-BY-4.0**
- **What we verified:** `data/text_corpora/pulaar.txt` = **742,024 words / 37,643 lines** of
  Latin-script Pulaar (Senegal Fulfulde, ISO `fuc`); plus 220 checked transcription files
  (`data/transcriptions/checked/transcriptions-fuc/`, 6,352 utterances) of **agriculture radio
  programmes** ("ndema e ngaynaaka" — farming and herding). Domain-matched to Gesa Mo Volata.
- **Use:** continued-pretraining / LoRA text corpus; agriculture transcripts for domain phrasing.

### 2. The `guizme` Hugging Face profile (https://huggingface.co/guizme)
Audited at the owner's request — all datasets previewed via the datasets-server API:

| Dataset | Rows | Content | License |
|---|---|---|---|
| `guizme/adlam_francais` | 1,195 | **French ↔ Pulaar parallel pairs** (Pulaar in ADLaM script; transliterable to Latin) | MIT |
| `guizme/pulaar_corpus` | 379 | Latin-script Pulaar sentences (from PDFs, e.g. *Ndimaagu*) | CC-BY-4.0 |
| `guizme/Pulaar` | 160 | Voice clips + Latin-script Pulaar transcriptions | **CC0-1.0** |
| `guizme/adlam_fulfulde` | 51 | Voice clips + ADLaM-script transcriptions (Winden Jangen ADLaM, Conakry) | CC-BY-4.0 |
| `guizme/fall` | 7 | ff→fr/en translated clips (Macina/Fuuta accents) | — |
| `guizme/fulfulde` | — | not accessible via API (404) | — |

- **Use:** `adlam_francais` (transliterated) + `pulaar_corpus` + `Pulaar` transcriptions join the
  training mix; the parallel pairs are the seed for instruction-style translation examples.
  Voice data noted for a future speech interface (out of scope for the text agent).

### 3. Ajami HTR dataset (Zenodo)
- Yousuf, O. et al. (2025). *A Handwritten Text Recognition Dataset for Ajami Manuscripts in
  Fulfulde and Hausa.* https://zenodo.org/records/15691686 (DOI 10.5281/zenodo.15691686) —
  **License: CC-BY-4.0**, direct download (16.8 GB).
- Publication record: https://uu.diva-portal.org/smash/record.jsf?pid=diva2%3A2048357&dswid=-7345
- 5 Fulfulde + 24 Hausa manuscripts, 400 pages, 6,132 lines (images + transcriptions).
- **Use:** not used — handwritten Ajami-script images; wrong modality/orthography for our text model.

## Gated or credentialed (owner action needed to obtain)

### 4. Adamawa Fulfulde–French Parallel Corpus of Narratives 1.2 (Mozilla Data Collective)
- https://mozilladatacollective.com/datasets/cml5asbhf009sme079y6sa9hm — License NOODL-1.0,
  **"Request Access" required**. 1,977 parallel Fulfulde–French lines.
- **Would be valuable** (parallel text → instruction pairs). Owner must request access.

### 5. Adamawa Fulfulde TTS dataset (Mozilla Data Collective)
- https://mozilladatacollective.com/datasets/cmp0f3tib02a4mp07ch5tr808 — License NOODL-1.0,
  **"Request Access" required**. 1,303 read-speech recordings + transcriptions (~3.5 h).

### 6. Fulani–English pair dataset (Kaggle)
- https://www.kaggle.com/datasets/michaelanietie/fulani-english-pair-dataset — requires Kaggle
  login/API credentials (none on this machine). Parallel pairs would be directly useful for
  instruction tuning if the owner downloads it.

## Reference-only (no training data)

### 7. CLLD Meta — Western Niger Fulfulde (`west2454`, ISO `fuh`)
- https://meta.clld.org/languages/west2454 — linguistic metadata (Glottolog/CLDF), CC-BY-4.0.
  Useful for dialect identification (our targets: `fuc` Pulaar / `fuh`–`fub` eastern variants).

### 8. SADiLaR / CLARIN VLO — Fulfulde first-language acquisition videos
- https://vlo.clarin.eu/record/https_58__47__47_hdl.handle.net_47_20.500.12185_47_533_64_format_61_cmdi
  (HDL 20.500.12185/533, Ibrahima Abdoul Hayou Cissé, Mali, 2010) — **CC BY-NC-SA 3.0**.
- Child-caregiver interaction videos. **Not used:** wrong modality and the NonCommercial
  clause is incompatible with challenge distribution.

## Licensing note

Training uses only **CC-BY-4.0** sources (Kallaama). Attribution is given here and must be
repeated in REPORT.md if a fine-tuned model ships. NOODL/NC-licensed sources are excluded
unless access terms are cleared by the owner.

## Dialect caveat

Kallaama is **Pulaar (fuc, Senegal)**. Fulfulde varieties (Pulaar, Maasina, Adamawa…) differ
noticeably; a model tuned on Pulaar serves Senegambian users best. Record the target variety
in `metadata.json` `language_scope` accordingly (currently `ff`, the macrolanguage code).
