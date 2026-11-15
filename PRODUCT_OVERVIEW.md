# VoiceDesk product overview

VoiceDesk is a prototype for multilingual customer-support intake. It converts spoken or typed complaints into structured tickets for agent review and prioritization.

## Intended workflow

1. Capture a complaint as audio or text.
2. Transcribe audio with Gnani Prisma when configured.
3. Classify the issue and extract available details using deterministic rules.
4. Ask for a missing delivery order ID when appropriate.
5. Flag recognized fraud and safety complaints for human review.
6. Provide a summary, suggested next step, example response target, and CSV/JSON export.
7. Speak a confirmation with Gnani Timbre when configured.

An optional OpenAI-compatible language model can review cases the rules are unsure about. It cannot provide order IDs or amounts, and cannot lower a rule-based Critical priority. If the LLM is unavailable, the rules-only workflow remains available.

## Design and scope

- The application supports agent review; it does not resolve complaints autonomously.
- Tickets are held in Streamlit session state and are not saved to a durable database.
- Phone and card numbers are masked in transcript text. This is limited masking, not a complete privacy or compliance control.
- There is no CRM integration, enterprise authentication, or role-based access.

## Evaluation status

Text evaluation uses small, developer-written datasets. On the blind stress set, the rules-only system scored 63% for category-and-urgency agreement and recognized 3 of 10 fraud/safety cases with unfamiliar wording.

Speech accuracy, live LLM accuracy, and operational impact have not been measured. The prototype has not been evaluated with real customer data.
