# Annotation guide - taxonomy v1.1

You are labelling web pages scraped from pharmaceutical (AstraZeneca-family) websites and from external sites they link to. For each item assign ONE page **type** and ONE primary **audience**. Use only the fields shown (URL + extracted text) - do not browse the web.

## Page types (what the page *is for*, not what disease/product it mentions)

- **Homepage / Hub** - Site or section front page whose main job is routing to other sections.
- **Gateway / Selector** - Interstitial that asks who you are or which country/language you want (HCP confirmation, 'choose country').
- **Login / Registration** - Sign-in, register, forgot-password, consent-to-access pages.
- **Contact / Locations** - How to reach the company or a team; office/location lists; 'request a call'.
- **Legal & Compliance** - Privacy statement, cookie policy, terms of use / terms of purchase, legal notice, disclaimers, regulatory disclosures (transfers of value, political contributions, grant disclosures), accessibility statement.
- **Form / Request** - A page whose purpose is submitting something: enquiry/medical-information request form, event registration form, access request, survey.
- **Safety Reporting** - Adverse-event / product-quality-complaint reporting and pharmacovigilance instructions.
- **About the Company** - Who the company is: strategy, leadership, governance, history, locations-in-country overviews, foundations.
- **Investor Relations** - Financial results, annual reports, share price, shareholder info, regulatory announcements.
- **Careers** - Jobs, early talent, working-here content, application process.
- **News & Media** - Press releases, media statements, newsroom, press-kit, image/broadcast library.
- **Article / Story** - Editorial feature, blog post, interview, podcast or video story (not a press release).
- **Sustainability** - Environment, ESG, code of ethics, health-equity programmes, community investment, sustainability reports.
- **Product Information** - A specific medicine/brand: indications, dosing, administration, efficacy summary, brand resources.
- **Prescribing Information** - Formal product documents: SmPC, PI, package leaflet, patient information leaflet, label.
- **Disease & Therapy Area** - Disease education or therapy-area overview (what a disease is, diagnosis, symptoms, treatment landscape).
- **Clinical Evidence** - Clinical trial results, congress abstract/poster/slides, journal article, guideline or health-technology assessment.
- **Medical Education & Events** - Courses, webinars, congress/event listings, training for professionals, podcasts for education.
- **Patient Support** - Material that supports living with a condition: patient stories, tips, side-effect self-care, programmes, services.
- **R&D & Science** - Research strategy, pipeline, platforms/technologies, science explainers, clinical-trial recruitment info.
- **Listing / Library** - An index or search/list page that mainly links to many items (congress library, document list, news archive).
- **Utility / Error** - 404/empty/loading/viewer shell, redirects, placeholders - no real content.
- **Other** - None of the above; use sparingly and record why.

## Audiences (who the page is *written for*)

- **Healthcare Professional** - Doctors, nurses, pharmacists, specialists; clinical/technical language, 'intended for HCPs', prescribing, dosing, trial data.
- **Patient / Caregiver** - People with a condition or looking after someone with one; lay language about living with disease, symptoms, treatment experience.
- **General Public** - Anyone: corporate story, science explainers, sustainability, community; no gating.
- **Investor** - Shareholders and analysts: results, reports, dividends, governance, share data.
- **Media** - Journalists: press releases, media contacts, image/broadcast library.
- **Job Seeker** - Prospective employees: vacancies, early talent, application process. (No intranet/employee-only content exists in the sample scans.)
- **Business Partner** - Suppliers, collaborators, licensing/BD counterparts, researchers seeking funding or data access.
- **Unclear** - Page carries no audience signal (error shells, bare viewers, empty pages).

## Decision rules (apply in order)
1. **Function over topic.** A page about a cancer drug can be Product Information, Clinical Evidence, Patient Support or Prescribing Information - pick by what the reader does with it.
2. **Documents (PDF)** are typed by the kind of document: annual/quarterly report, results presentation -> Investor Relations; SmPC/EPAR/leaflet/PI -> Prescribing Information; poster/abstract/slides/paper -> Clinical Evidence; code of ethics, sustainability report -> Sustainability; transfers-of-value / political-contribution / grant disclosures, terms of purchase -> Legal & Compliance; patient brochure -> Patient Support; press release -> News & Media.
3. **Congress libraries**: the page listing many posters for one congress -> Listing / Library; a single poster/abstract viewer page -> Clinical Evidence.
4. **Gate/login pages** that show a login box or 'access restricted to HCPs' (e.g. login.html?requesturl=...) -> Login / Registration, audience = the audience the gate declares.
5. **External-domain pages** are labelled the same way, by function: journal article / PubMed / ClinicalTrials.gov -> Clinical Evidence; health-charity or CDC-style disease explainer -> Disease & Therapy Area; regulator product information -> Prescribing Information; the front page of an unrelated organisation -> Homepage / Hub; a news/magazine article -> Article / Story.
6. **Audience: explicit declaration wins.** 'Intended for healthcare professionals only' (any language) => Healthcare Professional. Otherwise infer from register: dosing, trial endpoints, prescribing => HCP; 'you/your' lay language about living with a condition => Patient / Caregiver; corporate story, science explainer, sustainability => General Public; results/shareholders => Investor; press releases / newsroom / image library => Media; vacancies => Job Seeker; suppliers, licensing, research-funding => Business Partner.
7. **Unclear / Utility** only when there is genuinely no content (error page, bare viewer shell, empty text). Never use it just because the text is in a language you find hard.
8. **Other** (type) only if no type fits; add `note: "NEW:<suggested type>"` so the taxonomy can grow.
9. Be decisive but honest: give `conf` 3 = certain, 2 = probable, 1 = guess.
