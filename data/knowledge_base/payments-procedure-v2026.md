---
id: payments-procedure-v2026
title: Payments Procedure
topic: overseas_transfers
version: v2026
effective_date: 2026-03-01
status: current
superseded_by: null
owner: Payments Operations
required_details:
  - name: payee_type
    question: "Is this payee new or existing?"
    options: ["New", "Existing"]
    # Only ask when the question is about limits or processing a transfer
    needed_when: ["limit", "check", "process", "send", "how much"]
fields:
  overseas_limit_new_payee: "S$5,000"
  overseas_limit_existing_payee: "S$10,000"
  overseas_fee_threshold: "S$1,000"
---
# Payments Procedure v2026

## §1 Purpose
This procedure explains how branch staff process outward overseas transfers for retail customers. It replaces Payments Procedure v2024.

## §2 Scope
It applies to telegraphic transfers sent from a customer's savings or current account at a branch counter.

## §3 Limits

### §3.1 Overseas transfer limit
Overseas transfer limit: S$10,000 per day for existing payees; S$5,000 per day for new payees.

### §3.2 Payee status
A payee is new if the customer has never sent a successful transfer to that payee before.

## §4 Before processing

### §4.1 Identity verification
Verify the customer's ID against the account record before processing.

### §4.2 Scam-risk check
A scam-risk check is required before processing any transfer to a first-time overseas payee. Ask the customer how they know the payee and record the answer.

## §5 Fees
No fee for overseas transfers below S$1,000.

## Conditions and exceptions
- [C1] (when: payee_type=new) A **scam-risk check** is required before processing any transfer to a first-time overseas payee (see §4.2).
- [C2] (when: mentions=sanction|sanctioned|embargo) Transfers to **sanctioned countries** must not be processed; refer them to Compliance.
- [C3] (when: mentions=exceed|above the limit|over the limit|increase the limit) Requests above the daily limit need **Branch Manager approval**.
