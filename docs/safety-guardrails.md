# Safety Guardrails

HomePilot personas must follow strict safety guidelines to ensure that interactions remain appropriate and within bounds.  Although the personas in this repository provide only stub functionality, the following principles should be considered when extending them:

* **Respect privacy and confidentiality** – Personas should not request or expose sensitive personal information.
* **Avoid harmful advice** – Personas that provide health, fitness or educational guidance must clearly state that they are not replacements for professional advice and should avoid making unsafe recommendations.
* **Content moderation** – Generated content should be filtered to avoid offensive, hateful or otherwise inappropriate language.  This applies particularly to creative personas like Creator Muse and Storyteller.
* **Non‑diagnostic health** – The General Doctor persona provides general wellness information only and does not diagnose conditions or prescribe treatments.

Safety guardrails can be encoded in system prompts, tool wrappers and validation scripts to ensure that personas behave responsibly.