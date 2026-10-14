# Deadline Rescue — Project Idea and Hackathon Brief

> **Working title:** Deadline Rescue  
> **Primary hackathon track:** Alexa+  
> **Chosen implementation route:** Self-hosted MCP server using Streamable HTTP, plus a web-based demo client  
> **Core promise:** Turn money-related deadlines hidden in messages and documents into evidence-backed, actionable tasks—and track them until completion.
> **Budget rule:** ₹0 out-of-pocket. Do not introduce paid APIs, paid hosting, paid plans, paid trials that later convert, or services whose use could unexpectedly generate a bill.

---

## 1. The idea in one paragraph

People receive important payment, renewal, expiry, and cancellation information through many disconnected channels: emails, SMS messages, PDF bills, policy documents, purchase receipts, and service-provider pages. A normal reminder app expects the person to already know the date, understand what it relates to, and know what action to take. **Deadline Rescue helps bridge that gap.** A user supplies or authorizes access to a source, the system identifies a possible obligation, shows the exact evidence and date it found, helps the user verify the next step, and creates a follow-up that stays open until completion is confirmed.

The first version will focus on **avoiding unwanted recurring charges and missed household payment or renewal deadlines**. It will not attempt to replace every calendar, banking, bill-payment, or personal-assistant feature.

## 2. Hackathon details from the supplied Devpost page

**Event:** Build, Ship, Shape: Amazon Developer Hackathon  
**Organizer:** Amazon  
**Event page:** https://amazonappdev2026.devpost.com/  
**Deadline shown in the supplied page capture:** October 24, 2026 at 12:30 a.m. India Standard Time (IST)  
**Format:** Online  
**Eligibility shown:** Participants must be above the legal age of majority in their country of residence; standard country/territory exceptions apply.  
**Prize pool described on the page:** $138,000 in cash, with additional AWS credits contributing to the advertised total prize value.

The hackathon asks participants to pick **one primary track** and submit a working demo. A project can also enter a mini-challenge, but each project can win no more than one primary-track prize and one mini-challenge prize.

### Primary tracks

| Track | What the supplied page asks for | Fit for this project |
|---|---|---|
| **Alexa+** | Build a self-hosted MCP server using MCP specification **2025-11-25 or later** over **Streamable HTTP**, or build an Agent Skill. The page also describes a simulated Alexa+ experience in a web app as an option for people new to MCP. | **Selected.** Deadline Rescue will expose its useful capabilities as real MCP tools and demonstrate them with a web-based MCP client. |
| **Fire TV** | Ship a demo-ready application on Fire OS or Vega OS. React Native, web technologies, Android/Kotlin/Java, or another framework is acceptable if it runs on the required platform. Priority areas include AI-enhanced viewing, sports, fitness, family entertainment, multimodal UX, and computer vision. | Not selected. The idea is not fundamentally a TV experience. |
| **Bee (Wearable AI)** | Connect to real data recorded and processed through a Bee device or an Apple Watch running Bee software, using Bee CLI, MCP, or Agent Skills. The demo must show the project using that data for a useful purpose. Priority areas include education, developer experience, and personal productivity. | Not selected; it requires actual Bee/Apple Watch data. |
| **Ring** | Build a new app or extend one using Ring APIs, SDKs, simulators, or devices. A physical Ring device is not required. Priority areas include access control, business systems, IoT home automation, accessibility, and caretaking. | Not selected. Deadline Rescue does not depend on doorbell or home-security events. |

### Alexa+ track constraints to remember

- The MCP implementation must use **specification version 2025-11-25 or later** and **Streamable HTTP**.
- The repository and demo should make it clear that the MCP server is actually running and that its tools are genuinely invoked.
- The web application will be a **demo client for our own self-hosted MCP server**. Do not claim that it is running inside an Amazon Echo or integrated with Amazon's live Alexa+ service unless that integration is actually available and has been tested.
- The supplied page says required track technology must be called by the implementation; merely mentioning MCP in the README is insufficient.

### Mini-challenges

**AWS Builder:** Use an AWS service or tool in the project—examples listed on the page include Amazon Bedrock, AgentCore, Strands SDK, SageMaker, and Kiro Crew—and document the integration. The page says Kiro Crew alone qualifies without a separate AWS runtime service. **This challenge is optional and is not part of the default plan. Under the strict ₹0 rule, do not add Bedrock, AgentCore, or another AWS component unless its required usage is verified to be available at no cost without risking a bill. Do not count promotional credits or a limited trial as a sustainable free dependency.**

**Open Source:** Ship an additional open-source project with a license, or make a contribution (branch, fork, or pull request) to a public repository during the hackathon window. A pull request does not have to be merged. The submission needs the relevant contribution/repository URLs, GitHub username, and an explanation of the work and why it matters.

These mini-challenges are optional. The primary goal is a finished Alexa+ entry; add a mini-challenge only if it does not jeopardize the core demo. For this project, **₹0 takes priority over entering a mini-challenge**. The Open Source mini-challenge may be a better fit than AWS Builder if its additional required work can be completed without purchasing anything.

### Submission requirements from the supplied page

- A project description explaining what it does and how it works.
- A GitHub repository containing the source code, assets, and instructions needed to run the project. It must be public with an open-source license, or private and shared with the listed reviewers and `testing@devpost.com` as required by the page.
- A **public English demo video under three minutes**, hosted on YouTube or Vimeo. Lead with the most compelling part; judges are not required to watch beyond the three-minute mark.
- Product feedback for every tool, API, or SDK used: purpose, what worked, what needs improvement, onboarding experience, and whether we would use it again.
- Selection of the primary track and any mini-challenge entries.
- If an existing project is used, an explanation of what was built or changed during the hackathon window. This project is intended to be new.
- Optional feature requests and friction-log entries. The page says friction logs can earn up to a **10% judging bonus**; logs should include task attempted, steps, expected vs. actual result, severity, workaround, and actionable suggestion.

### Prize overview shown on the page

The page lists these track and mini-challenge awards (prize eligibility and exact terms remain subject to the official rules):

| Prize category | Award amounts shown | Other listed recognition
|---|---|---|
| Fire TV track | 1st: $25,000 cash + $15,000 AWS credits; 2nd: $15,000 cash + $5,000 AWS credits; 3rd: $4,000 cash + $1,000 AWS credits | First-place winner gets a meeting with the Amazon Developer team and feature placement on Amazon Developer channels; the page also lists feature placement for the other places. |
| Alexa+ track | 1st: $25,000 cash + $15,000 AWS credits; 2nd: $15,000 cash + $5,000 AWS credits; 3rd: $4,000 cash + $1,000 AWS credits | First-place winner gets a meeting with the Amazon Developer team and feature placement on Amazon Developer channels; the page also lists feature placement for the other places. |
| Bee track | 1st: $12,000 cash; 2nd: $8,000 cash | First-place winner gets a meeting with the Amazon Developer team; winners may be featured on Amazon Developer channels as listed. |
| Ring track | 1st: $12,000 cash; 2nd: $8,000 cash | First-place winner gets a meeting with the Amazon Developer team; winners may be featured on Amazon Developer channels as listed. |
| AWS Builder mini-challenge | $5,000 cash + $5,000 AWS credits for the winner | Meeting with the Amazon Developer team and feature placement on Amazon Developer channels. |
| Open Source mini-challenge | $5,000 cash + $5,000 AWS credits for the winner | Meeting with the Amazon Developer team and feature placement on Amazon Developer channels. |

The supplied capture has a slightly inconsistent first-place label for the Fire TV award (“Fire Track”). Verify the current prize wording and conditions on Devpost before relying on the award details.

### Judging criteria shown on the page

1. **Tech implementation:** How well the project is built and how effectively it uses the required track technology.
2. **Design:** Whether the product experience is complete, coherent, and intuitive for the intended interaction model.
3. **Potential impact:** Whether it solves a credible customer need and could serve a broader audience.
4. **Quality of idea:** Whether it uses the tools creatively and demonstrates genuine understanding of the ecosystem and users.

**Important:** The event details above are taken from the supplied Devpost page capture. Re-check the live event page before submission in case rules, dates, or links change.

---

## 3. Detailed problem statement

### The problem

People often lose money or face avoidable inconvenience because financial and service-related obligations are **spread across multiple messages and providers**, while the person is expected to remember the date, interpret the terms, and complete the right action themselves.

Examples include:

- A free trial that becomes a paid subscription unless it is cancelled.
- An OTT plan that renews through autopay even though the person no longer watches it.
- An annual insurance premium due date hidden in a policy email or PDF.
- A broadband/Wi-Fi bill that is due before a service interruption or late fee.
- A prepaid mobile recharge whose validity is ending, or a postpaid bill with a due date.
- A DTH/cable TV renewal that the household still needs to make.
- Electricity, water, piped gas, or other recurring household bills.
- A vehicle-insurance renewal or other policy expiry that needs attention before the stated date.
- A software, cloud-storage, domain, or hosting subscription that renews annually.
- A purchase return window or refund-claim deadline that expires if the required step is not completed.
- A course fee or examination fee deadline.
- A credit-card payment or EMI due date, where a missed due date may have financial consequences.

The issue is not merely that users need more reminders. **They first need to discover and understand the obligation, then decide what to do, then make sure it was completed.** A conventional calendar reminder usually starts too late in the process: it assumes the user already found the date and created the event correctly.

### Who experiences this?

The first target users are people who manage several recurring payments and subscriptions, especially those who:

- Use different providers for mobile, broadband, OTT, insurance, utilities, and other services.
- Receive notices through email, SMS, messaging apps, receipts, and PDF documents.
- Have both monthly and annual commitments.
- Share responsibility for household payments, but do not have one reliable list of who owns each task.
- Want to avoid unwanted renewals, late fees, service interruption, or an expired return/claim window.

This is not limited to users of Alexa devices. The web client makes the workflow accessible for the hackathon demo, while the self-hosted MCP server demonstrates an agent-ready interface for these functions.

### The job to be done

> “Help me discover important money-related deadlines from the information I give you, prove where each date came from, tell me what I need to do next, and keep tracking it until it is resolved.”

### Why a basic reminder is not enough

A basic reminder stores a date the user has already identified. Deadline Rescue should add a few important capabilities:

1. **Discovery:** Find a possible deadline inside a source the user provides or authorizes the app to access.
2. **Evidence:** Show the exact message/document snippet that supports the date. Do not invent dates or silently treat an uncertain date as confirmed.
3. **Interpretation:** Explain whether the source appears to describe a payment due date, renewal date, plan-validity end date, cancellation deadline, or return/claim window.
4. **Next step:** Help the user find the relevant official instructions or prepare the next action.
5. **Follow-through:** Create a reminder and retain the task's state until completion is verified or the user confirms it.

The differentiator is **evidence-backed follow-through**, not another chat interface and not a generic calendar.

---

## 4. Examples and intended behaviour

All examples below are illustrative. They are not statements about any actual user's account, provider terms, fees, or policy coverage. The product must rely on the supplied source and, where appropriate, the provider's current official instructions.

| Example | What the user might say or provide | What Deadline Rescue should do |
|---|---|---|
| **Free trial renewal** | “I started a free trial. Tell me when it starts charging me.” The user uploads or forwards the confirmation email. | Extract the trial end/renewal date and any cancellation terms; show the source passage; ask the user to confirm the interpretation; offer a reminder before the stated date and prepare the official cancellation route. |
| **OTT autopay** | “I barely use this streaming service. Is it going to renew?” | Check the supplied receipt or subscription email for renewal information; distinguish a known renewal date from an estimate; present the official account/cancellation link if available; do not cancel anything automatically. |
| **Annual health-insurance premium** | “My health-insurance premium is due sometime this month. Can you find the exact date?” | Search user-provided policy or insurer correspondence; surface the premium due date and policy reference only as appropriate; show the exact evidence; point to the insurer's official payment channel. If the date is not present, ask the user to check the insurer rather than guessing. |
| **Vehicle insurance renewal** | “My car insurance expires next month. Remind me early enough to compare renewal options.” | Extract the stated expiry/renewal date; schedule configurable advance reminders; provide a checklist to review the policy and renewal options. Do not imply coverage or legal compliance beyond the sourced information. |
| **Home broadband/Wi-Fi bill** | “When is my Wi-Fi bill due, and have I already marked it paid?” | Find the bill due date and amount, if shown; compare with the app's own task status; clearly distinguish a user-marked payment from a provider-confirmed payment. |
| **Prepaid mobile recharge** | “My mobile plan is about to expire. Help me avoid losing service.” | Extract the stated validity-end date from the recharge confirmation or plan message; remind the user before expiry; link to the operator's official recharge page if available. Do not assume an expiry time if the source does not give one. |
| **Postpaid mobile bill** | “Check the postpaid bill I uploaded and add the due date.” | Capture amount, bill period, due date, and provider; show the source; create a follow-up; keep status as pending until the user records payment or evidence confirms it. |
| **DTH/cable renewal** | “Our TV subscription renews soon. Put it on my list.” | Extract the recharge/renewal date and provider; create a task and optionally an advance reminder; distinguish a fixed monthly bill from a plan-validity end date. |
| **Electricity bill** | “I don't want to miss the electricity bill. What does this notice say?” | Extract the due date and amount printed in the supplied bill; show the quoted line or page; prepare a reminder. Any late fee or disconnection language must be quoted or linked to the notice, not invented. |
| **Water or piped-gas bill** | “Add the due date from this bill and tell me what is still pending.” | Extract the obligation and source; create a task; let the user mark it complete or attach a receipt/confirmation. |
| **Annual software or cloud subscription** | “My storage or developer-tool plan renews yearly. Warn me before the next charge.” | Record the renewal date and source; generate a configurable reminder plan; include an official management/cancellation link if found. |
| **Domain or web-hosting renewal** | “My domain renews next month. Don't let me forget.” | Capture the renewal date and provider, remind in advance, and keep the task open until the user confirms renewal or cancellation. |
| **Credit-card bill** | “Extract the payment due date from this statement.” | Extract and cite the due date shown in the statement; create reminders if asked. Treat financial statements as sensitive and do not initiate payments or offer debt/investment advice. |
| **EMI or loan instalment** | “The bank sent me an instalment notice. Add the actual due date.” | Extract the date and amount only from the supplied notice; create a reminder; flag ambiguities. Never calculate or promise penalties unless they are supported by the source. |
| **Return window** | “I bought this online. Until when can I return it?” | Look for the order/return policy and date in the supplied receipt or official order page; cite the source and prepare the steps. If the return policy cannot be verified, say so. |
| **Refund or claim deadline** | “I need to submit this form before the deadline. Keep track of it.” | Extract the submission date, required documents, and official channel from the source; assemble a checklist and track missing items. Do not claim eligibility unless the source supports it. |
| **Course or exam fee** | “The college notice has a fee deadline. Add it and remind me before it closes.” | Extract the date and required step from the notice; show the cited text and create reminders. |
| **Household bill shared with another person** | “This broadband bill is my roommate's responsibility. Make a task and show who owns it.” | Create a task with an explicitly assigned owner; keep assignment separate from payment status; avoid messaging the other person unless a supported messaging integration and user approval are present. |

### Example: what a useful response looks like

**User:** “Check this trial confirmation. I don't want another surprise charge.”

**Deadline Rescue:**

> “The email says the trial renews on **20 October**. Evidence: ‘Your trial ends and your subscription renews on 20 October.’ I have not verified whether there is an exact cancellation cut-off time. Would you like me to create reminders for 17 October and 19 October and open the provider's cancellation instructions?”

The date and quoted passage above are an illustrative mock example. In the actual app, the response must quote the uploaded source, not a hard-coded example.

### Example: date uncertainty

**User:** “My annual insurance premium is due around the end of the month. Add it.”

**Deadline Rescue:**

> “I found a policy document, but the text I can access does not state the next premium due date. I won't create a confirmed due date from ‘around the end of the month.’ You can upload the renewal notice or check the insurer's official account page. I can create a separate task to verify the date in the meantime.”

This is intentional behaviour: uncertainty should be visible rather than hidden.

---

## 5. Product scope

### MVP scope

The MVP should be narrow enough to finish and reliable enough to demonstrate:

1. Let the user paste text or upload supported source documents such as an email export, text file, or PDF.
2. Identify candidate obligations: provider, obligation type, date, amount (if present), recurrence (if explicit), source location/snippet, and confidence/verification status.
3. Display the extracted item beside its source evidence.
4. Allow the user to confirm, correct, or reject the candidate.
5. Create an in-app task and configurable advance reminders. A downloadable calendar event (`.ics`) can be an optional convenience.
6. Prepare a next-step checklist or official-provider link when one can be reliably identified.
7. Track status: `needs_review`, `confirmed`, `upcoming`, `action_needed`, `completed`, `cancelled`, or `date_unverified`.
8. Maintain a clear tool-call log in the demo so judges can see the MCP server doing real work.

### Suggested initial categories

- Free-trial and OTT/subscription renewal.
- Annual insurance premium or policy-renewal date.
- Broadband/Wi-Fi bill.
- Mobile plan validity, recharge, or postpaid bill.
- DTH/cable renewal.
- Electricity, water, and piped-gas bills.

Credit-card payments, EMIs, taxes, formal claims, and other higher-stakes obligations can be represented in examples, but should be treated as later-stage categories. The first version should not need bank account access or perform financial transactions.

### Out of scope for the MVP

- Automatically paying bills or moving money.
- Automatically cancelling subscriptions or insurance policies.
- Logging in to arbitrary provider websites or bypassing authentication/CAPTCHA.
- Scraping private accounts without an authorized integration.
- Claiming a payment succeeded merely because the user clicked a button.
- Providing legal, tax, insurance, credit, investment, or other professional financial advice.
- Promising to prevent every late fee, charge, or service interruption.
- Building a universal replacement for a calendar, banking app, bill-payment app, or Alexa.

---

## 6. Main workflow

### Step 1 — Ingest a source

The user uploads a supported file or pastes/forwards relevant content into the app. The source is given an ID and a timestamp. A future version may support an explicitly authorized email connector, but the first version should work without invasive account integration.

### Step 2 — Extract candidate obligations

A parser and extraction pipeline identifies candidate dates and actions. Every candidate should have structured fields and a source reference. The model may help interpret text, but date parsing and schema validation should be handled by deterministic code wherever possible.

### Step 3 — Show evidence and ask for confirmation

The UI shows the candidate date next to the exact source snippet and its source title. The user can confirm it, edit it, or reject it. Low-confidence and contradictory dates require review. The app must not silently convert an ambiguous phrase into a confirmed deadline.

### Step 4 — Create a follow-up

After confirmation, the user selects how early to be reminded—for example, 7 days and 1 day before the deadline. These are defaults the user can change, not rules that apply to every obligation. Store reminders in the app; optionally export to a calendar file.

### Step 5 — Prepare a next action

Depending on the obligation, the app can show an official provider link, a document checklist, a cancellation checklist, or a simple “verify the latest amount/date” task. If an official source cannot be verified, the app should state that limitation.

### Step 6 — Track outcome

The obligation remains pending until the user marks it complete or supported evidence confirms the result. Keep a distinction between:

- reminder created;
- action prepared;
- user says the action was completed;
- provider confirmation or receipt available.

These are different states and must not be conflated.

---

## 7. Proposed MCP server tools

The tool names are working names and can be refined during implementation. All should be implemented as real handlers, not static demo responses.

| Tool | Purpose | Important behaviour |
|---|---|---|
| `ingest_source` | Add pasted text or supported document content to the user's source collection. | Return a source ID and metadata; avoid placing sensitive full content in logs. |
| `find_deadline_candidates` | Search source records and identify potential bills, renewals, validity dates, or cancellation windows. | Return candidate items with evidence spans and a review status, not unqualified assertions. |
| `get_deadline_evidence` | Retrieve the source snippet, source title, and extraction details for one candidate. | Evidence must correspond to the exact source record. |
| `confirm_or_correct_deadline` | Confirm, amend, or reject a candidate. | Preserve the original extraction and record the user's correction. |
| `create_follow_up` | Create an in-app reminder/task for a confirmed item. | Require a verified or user-confirmed date; make lead time configurable; return the saved task ID. |
| `prepare_next_step` | Build a checklist or surface an official link associated with the item. | Do not claim the external action was completed. |
| `update_deadline_status` | Update task status or attach completion evidence. | Distinguish user confirmation from external/provider verification. |
| `list_deadlines` | Show upcoming, overdue, unresolved, or completed obligations. | Support filtering by provider, category, due period, and status. |

**MVP recommendation:** implement the first six tools well, and add status/list tools if time permits. A small set of dependable tools is better than many shallow ones.

---

## 8. Suggested architecture and technology

### High-level architecture

```text
React web client
      |
      v
Application backend / agent host (Python + FastAPI)
      |                      \
      | MCP client             \ LLM tool-selection / response layer
      v                         \
Self-hosted MCP server  <--------
(Streamable HTTP; MCP spec 2025-11-25+)
      |
      v
Tool handlers --> source parser / date validation / reminder logic
      |
      v
SQLite database + local/demo source files
```

The architecture may be simplified if one backend process hosts both the UI API and MCP client, but the repository and demo must make the MCP server endpoint and real tool calls easy to identify.

### Candidate stack — strict ₹0 baseline

- **Frontend:** React + Vite; develop and run locally.
- **Backend and agent host:** Python + FastAPI; run locally.
- **MCP implementation:** Python MCP SDK implementing the required version and Streamable HTTP transport.
- **Storage:** SQLite, stored on the local machine.
- **Parsing:** free Python libraries for email/text parsing and PDF text extraction. Keep scanned PDFs/OCR out of scope unless a no-cost solution is tested.
- **Extraction and agent logic:** start with deterministic parsing, explicit rules, and source evidence. If an LLM materially improves messy-document interpretation, use either (a) a local model via Ollama or (b) a provider's genuinely free tier while staying inside its free limits and without enabling paid billing. Keep the model provider replaceable.
- **Local model caution:** local inference has no API bill, but uses disk, RAM, and CPU. Test a small model on the actual development machine before committing to it; do not assume a large model will run smoothly.
- **Calendar convenience:** generate a downloadable `.ics` file instead of depending on a paid calendar API.
- **Testing:** free local unit tests and end-to-end tests that prove the web client calls the MCP server and changes SQLite state.
- **Hosting/demo:** run both client and server locally and record the required public demo video. The supplied hackathon page requires a repository and demo video but does not list public app hosting as a submission requirement. Deploy only if a suitable free plan meets the ₹0 rule and cannot unexpectedly bill.

### Hard budget rules

1. **No Amazon Bedrock in the default implementation.** It uses model-dependent pricing, so it is excluded unless the user later confirms a specific no-charge path they are comfortable with. The AWS Builder mini-challenge is optional; do not add cloud services solely for the badge.
2. **No paid API keys or paid model tiers.** Never upgrade a free model/API plan. If the free plan is unavailable, rate-limited, or asks to enable paid billing, switch to local inference or the deterministic fallback.
3. **No paid hosting, database, storage, domains, or subscription upgrades.** Local-first is the reference setup.
4. **No reliance on promotional credits or expiring trials.** Treat these as temporary subsidies, not a ₹0 architecture.
5. **No surprise billing risk.** Before trying any external service, inspect its current pricing and account/billing settings. If a payment method or billable overage could create a charge, skip it unless the service has a clear no-charge mode that meets the user's rule.
6. **Graceful no-LLM mode:** the core app must still run with deterministic extraction and mock/sample source documents if no free LLM is available. The product should remain demonstrable without a paid dependency.

### Where AI should and should not be used

Use the model for messy-language interpretation, classifying obligation types, extracting candidate fields from context, and explaining next steps in plain language.

Use normal code for date parsing, validation, persistence, reminder scheduling, status transitions, and permission checks. Never let the model silently invent a due date, payment amount, provider action, or completion status.

---

## 9. Suggested data model

Each tracked obligation should contain fields similar to:

- `id`
- `provider_name`
- `category` (subscription, insurance, broadband, mobile, utility, DTH, return-window, etc.)
- `obligation_type` (payment due, renewal, trial ending, plan validity, cancellation deadline, return deadline, claim deadline)
- `candidate_date` and, where available, the date/time or time zone explicitly stated in the source
- `amount` and `currency`, only when provided by the source
- `source_id`, `source_title`, and `evidence_snippet` or source coordinates
- `extraction_confidence` and `verification_status`
- `recurrence` only when the source states or the user confirms it
- `next_step` and `official_url`, when reliably available
- `reminder_schedule`
- `status`
- `owner`, if the user explicitly assigns one
- `created_at`, `updated_at`, and a small audit trail for changes

Do not treat an expected recurring date as confirmed merely because the last date is known. For example, a monthly bill's next due date can change; label predictions as estimates until verified.

---

## 10. Trust, privacy, and safety requirements

Deadline Rescue depends on personal messages and financial documents, so trust is part of the product—not an optional polish item.

- **Show the source:** every extracted date should be traceable to a document/message or an explicitly identified official source.
- **Separate fact from inference:** label dates as `source-stated`, `user-confirmed`, `estimated`, or `unverified`.
- **No invented penalties:** only display late fees, interruption warnings, grace periods, or coverage implications when the source supports them.
- **No automatic financial actions:** payments, cancellations, renewals, and claim submissions require an explicit user action. The MVP should prepare the step, not silently execute it.
- **Minimize data:** store only what is needed to track the obligation. Avoid logging full statements, policy numbers, or payment credentials.
- **Use demo-safe data:** use synthetic/sample documents for the public video unless the user has explicit permission to show real data. Never expose real email addresses, phone numbers, account numbers, policy numbers, or card details.
- **Allow correction and deletion:** users should be able to correct a date, dismiss an extraction, and delete imported source records.
- **Distinguish states:** a reminder sent is not a payment; opening a cancellation page is not a cancellation; a user marking an item complete is not the same as provider verification.
- **Time zones:** store exact dates reliably, use the user's locale where appropriate, and never invent a cut-off time when only a date is provided.

---

## 11. Example demo scenarios

A good submission should have a small number of polished end-to-end scenarios using real server-side state, not only a large feature list.

### Scenario A — Stop an unwanted free-trial renewal

1. Upload a mock trial-confirmation email.
2. The system extracts the renewal date and displays the supporting sentence.
3. The user confirms the date.
4. The system creates reminders and provides the official cancellation route.
5. The user later marks the task cancelled or attaches a confirmation; the status changes accordingly.

### Scenario B — Track an annual insurance premium

1. Upload a sample policy/renewal notice.
2. Extract the stated due date and, if supplied, the premium amount.
3. Show the source evidence and explain what remains unverified.
4. Create an advance reminder and a “review official insurer payment options” task.
5. Do not claim the policy is renewed until the user records or supplies confirmation.

### Scenario C — Manage recurring household bills

1. Upload sample broadband, mobile, electricity, and DTH notices.
2. Show them in a single “Upcoming” list, grouped by due date and provider.
3. Demonstrate that bill due dates, prepaid validity dates, and subscription renewal dates are classified differently.
4. Filter by “due this week,” “needs verification,” or “completed.”

### Scenario D — Handle an uncertain date correctly

1. Provide a source that says “renewal is near the end of the month” but does not state a calendar date.
2. The system labels the date as unverified and asks the user to confirm it or provide a more precise source.
3. Show how the application refuses to create a false confirmed deadline.

### Three-minute video outline

- **0:00–0:20:** State the user problem and show a crowded mix of trial, insurance, broadband, and mobile notices.
- **0:20–1:10:** Upload a source; show the extracted deadline and exact evidence; confirm or correct it.
- **1:10–1:50:** Create a follow-up and show the saved task in the upcoming list.
- **1:50–2:25:** Demonstrate a second category, such as insurance or broadband, and show how the extraction differs.
- **2:25–2:50:** Show the live MCP server/tool-call log and the actual stored state change.
- **2:50–3:00:** Summarize impact and the focused MVP scope.

---

## 12. How we will evaluate whether it works

The product should be evaluated on correctness and follow-through, not on how fluent the chatbot sounds.

- **Date accuracy:** compare extracted candidate dates to known dates in a curated set of sample emails/bills.
- **Evidence accuracy:** every confirmed date must point to the exact relevant source snippet.
- **Uncertainty handling:** include deliberately ambiguous or conflicting examples and verify that the system requests review instead of guessing.
- **Category distinction:** test subscription renewal versus plan-validity end date versus bill due date versus cancellation deadline.
- **Tool execution:** demonstrate that tool calls read and write database records and that the UI reflects actual results.
- **Status correctness:** test that creating a reminder does not mark a bill paid, and opening a cancellation link does not mark a subscription cancelled.
- **Recovery:** test malformed documents, missing dates, duplicate sources, and database/tool errors.

A concrete test set could start with 20–30 synthetic source snippets spanning the listed categories, including clear dates, missing dates, date conflicts, and misleading text. Record expected outputs before testing. Do not advertise an accuracy percentage until it has been measured on that test set.

---

## 13. Risks and decisions to resolve

1. **Source integration:** The value improves when the app can access relevant records, but a first hackathon version should not depend on full Gmail, SMS, bank, or provider-account integrations. Start with user-supplied source files/text and consider a supported connector only after the core flow works.
2. **Real-world differentiation:** A reminder app or bill list by itself is not enough. The demo must visibly establish evidence, allow confirmation, prepare next steps, and track outcome.
3. **Official information:** External provider pages can change, move, require login, or be unavailable. If an official route cannot be verified, surface the limitation instead of fabricating instructions.
4. **Financial safety:** No payment execution or automatic cancellation in the MVP. Use confirmation and evidence boundaries throughout the UI.
5. **Recurring obligations:** Monthly or annual recurrence should be user-confirmed or source-supported. Do not infer every future due date from one old bill.
6. **MCP compliance:** Verify the implemented specification version, Streamable HTTP endpoint, tool schemas, and live calls against the hackathon's requirement before recording the submission video.
7. **Track representation:** The self-hosted MCP server and custom web client demonstrate the project's MCP tools. Unless a permitted live Alexa+ integration is actually available and tested, describe the project accurately as an Alexa+-track MCP implementation/demo, not as a product already running inside Alexa+.

---

## 14. Product positioning

### One-line pitch

**Deadline Rescue turns scattered bill, subscription, insurance, and renewal notices into evidence-backed tasks—and follows each one through to a verified outcome.**

### Short project description

Deadline Rescue is a conversational personal-deadline agent built for the Alexa+ hackathon track. It uses a self-hosted MCP server to find candidate obligations in user-provided messages and documents, extract dates with source evidence, help users verify what is due, create reminders, prepare next steps, and track completion. Its first focus is free-trial renewals and everyday household commitments such as OTT autopay, annual insurance premiums, broadband bills, mobile recharges, and utilities. It does not pay bills or cancel services automatically, and it never treats an unverified date as fact.

### What we want judges to remember

This is not an attempt to recreate Alexa's entire feature set. It is a narrow workflow for a credible recurring problem: people cannot reliably act on obligations they have not noticed, do not understand, or have not followed through on. The MCP server turns the workflow into reusable tools; the web client makes the value and the tool calls observable; source evidence and completion states make the system accountable.

---

## 15. Reference

- **Build, Ship, Shape: Amazon Developer Hackathon (Devpost):** https://amazonappdev2026.devpost.com/
- Track requirements, deadline, mini-challenges, submission checklist, prizes, and judging criteria in this document were summarized from the supplied page capture dated October 13, 2026. Verify the live page before final submission.
