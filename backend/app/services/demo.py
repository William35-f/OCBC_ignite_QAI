"""The five demo scenarios shown in the Employee chat's "Demo scenarios" dropdown."""

SCENARIOS = [
    {
        "id": "red",
        "label": "1. Red – Mr Tan's overseas transfer",
        "question": "What's the daily overseas transfer limit, and what do I need to check before processing?",
        "hint": "Pick “New” when asked about the payee.",
    },
    {
        "id": "amber",
        "label": "2. Amber – fixed by one retry",
        "question": "How long does an overseas transfer take, and is there a fee?",
        "hint": "",
    },
    {
        "id": "green",
        "label": "3. Green – straightforward question",
        "question": "What documents does a customer need to change their mailing address?",
        "hint": "",
    },
    {
        "id": "assumption",
        "label": "4. Wrong assumption in the question",
        "question": "Since the limit is S$10,000, can I send S$8,000 to a new payee?",
        "hint": "",
    },
    {
        "id": "no_evidence",
        "label": "5. No evidence – not covered by any procedure",
        "question": "Can I process a cryptocurrency transfer to a customer's crypto wallet?",
        "hint": "",
    },
    {
        "id": "amber_stays",
        "label": "6. Amber – still Amber after the retry",
        "question": "How long does a replacement debit card take to arrive, and is there a fee?",
        "hint": "OCBC AI's retry is better but still guesses a delivery time, so it goes to the reviewer.",
    },
]
