"""Versioned taxonomy. Type and Audience are independent axes (deck slide 8).

v1 was drafted from the URL-structure survey of the 10 sample scans and is checked
against embedding clusters in scripts/03_cluster.py. Versioning matters: a gold label
is only valid for the taxonomy version it was written against.
"""
VERSION = "v1.1"   # v1.1: + Form / Request, Legal & Compliance (added after cluster review)

PAGE_TYPES = {
    "Homepage / Hub":            "Site or section front page whose main job is routing to other sections.",
    "Gateway / Selector":        "Interstitial that asks who you are or which country/language you want (HCP confirmation, 'choose country').",
    "Login / Registration":      "Sign-in, register, forgot-password, consent-to-access pages.",
    "Contact / Locations":       "How to reach the company or a team; office/location lists; 'request a call'.",
    "Legal & Compliance":        "Privacy statement, cookie policy, terms of use / terms of purchase, legal notice, disclaimers, regulatory disclosures (transfers of value, political contributions, grant disclosures), accessibility statement.",
    "Form / Request":            "A page whose purpose is submitting something: enquiry/medical-information request form, event registration form, access request, survey.",
    "Safety Reporting":          "Adverse-event / product-quality-complaint reporting and pharmacovigilance instructions.",
    "About the Company":         "Who the company is: strategy, leadership, governance, history, locations-in-country overviews, foundations.",
    "Investor Relations":        "Financial results, annual reports, share price, shareholder info, regulatory announcements.",
    "Careers":                   "Jobs, early talent, working-here content, application process.",
    "News & Media":              "Press releases, media statements, newsroom, press-kit, image/broadcast library.",
    "Article / Story":           "Editorial feature, blog post, interview, podcast or video story (not a press release).",
    "Sustainability":            "Environment, ESG, code of ethics, health-equity programmes, community investment, sustainability reports.",
    "Product Information":       "A specific medicine/brand: indications, dosing, administration, efficacy summary, brand resources.",
    "Prescribing Information":   "Formal product documents: SmPC, PI, package leaflet, patient information leaflet, label.",
    "Disease & Therapy Area":    "Disease education or therapy-area overview (what a disease is, diagnosis, symptoms, treatment landscape).",
    "Clinical Evidence":         "Clinical trial results, congress abstract/poster/slides, journal article, guideline or health-technology assessment.",
    "Medical Education & Events":"Courses, webinars, congress/event listings, training for professionals, podcasts for education.",
    "Patient Support":           "Material that supports living with a condition: patient stories, tips, side-effect self-care, programmes, services.",
    "R&D & Science":             "Research strategy, pipeline, platforms/technologies, science explainers, clinical-trial recruitment info.",
    "Listing / Library":         "An index or search/list page that mainly links to many items (congress library, document list, news archive).",
    "Utility / Error":           "404/empty/loading/viewer shell, redirects, placeholders - no real content.",
    "Other":                     "None of the above; use sparingly and record why.",
}

AUDIENCES = {
    "Healthcare Professional": "Doctors, nurses, pharmacists, specialists; clinical/technical language, 'intended for HCPs', prescribing, dosing, trial data.",
    "Patient / Caregiver":     "People with a condition or looking after someone with one; lay language about living with disease, symptoms, treatment experience.",
    "General Public":          "Anyone: corporate story, science explainers, sustainability, community; no gating.",
    "Investor":                "Shareholders and analysts: results, reports, dividends, governance, share data.",
    "Media":                   "Journalists: press releases, media contacts, image/broadcast library.",
    "Job Seeker":              "Prospective employees: vacancies, early talent, application process. (No intranet/employee-only content exists in the sample scans.)",
    "Business Partner":        "Suppliers, collaborators, licensing/BD counterparts, researchers seeking funding or data access.",
    "Unclear":                 "Page carries no audience signal (error shells, bare viewers, empty pages).",
}

TYPES = list(PAGE_TYPES)
AUD = list(AUDIENCES)
