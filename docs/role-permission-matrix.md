# CampusPulse — Role and Permission Matrix

## 1. Purpose

This document defines the prototype's role-aware data visibility and permitted actions.

The role switcher is for demonstration only. It does not provide production authentication or identity verification.

The backend must enforce permissions. Frontend visibility alone is not a security control.

## 2. Roles

- Faculty
- Mentor
- HOD / Leadership
- Counsellor
- Finance
- Placement
- Student (optional, restricted demo view)

## 3. Permission Matrix

| Capability | Faculty | Mentor | HOD | Counsellor | Finance | Placement | Student |
|---|---|---|---|---|---|---|---|
| View permitted student academic profile | Yes | Assigned students | Permitted scope | Referral context | Minimum necessary | Relevant scope | Own profile |
| View attendance and academic signals | Yes | Assigned students | Cohort/permitted scope | Minimum necessary | No by default | Relevant readiness context | Own permitted summary |
| View participation signals | Yes | Assigned students | Aggregated/permitted scope | Minimum necessary | No | Relevant scope | Own permitted summary |
| View detailed fee information | No by default | No | No by default | No | Yes | No | Own permitted status |
| View sensitive counselling notes | No | No | No | Restricted to counsellor | No | No | Not through staff notes |
| View skills/readiness information | Relevant scope | Assigned students | Aggregated/permitted scope | Minimum necessary | No | Yes | Own permitted summary |
| Review academic-support recommendations | Yes | Relevant assigned cases | Oversight | Referral-related only | Fee-support cases only | Placement cases only | No |
| Assign or manage interventions | Academic support | Mentoring | Permitted oversight/reassignment | Counselling referral workflow | Fee-support workflow | Placement workflow | No |
| Record follow-up evidence | Own actions | Own actions | Permitted oversight actions | Restricted coordination status | Own workflow | Own workflow | Optional support response |
| View cohort analytics | Limited/permitted | Limited/permitted | Yes, aggregated | Restricted scope | Finance-related aggregates only | Placement-related aggregates | No |
| Change consent/preferences | No general unrestricted access | No general unrestricted access | Only if explicitly authorized | No general unrestricted access | No | No | Own preferences, if implemented |

**Interpretation:** “Yes” is not blanket access to every student or every field. Access remains limited by assignment, purpose, consent/context, and the backend's authorization rules.

Where this matrix says “by default” or “permitted scope,” the exact prototype rules will be implemented centrally and tested. A production institution would need a formal authorization policy.

## 4. Data Classification

### General student profile
Examples: synthetic student code, program, department, year, cohort.

Access: only where needed for the role's permitted work.

### Academic and attendance signals
Examples: attendance percentage, assessment trend, assignment completion.

Access: faculty and relevant mentors; leadership only within its permitted scope; other roles receive only what their workflow requires.

### Financial information
Examples: fee-support status and financial-support follow-up.

Access: finance-authorized workflow. Other roles must not receive detailed fee values by default.

### Skills and placement readiness
Examples: skills assessments, workshop participation, readiness indicators.

Access: placement team and other explicitly permitted workflows.

### Counselling-related information
Examples: referral coordination status and sensitive counselling notes.

Access: sensitive notes are restricted to the counsellor. General staff may receive only the minimum coordination information needed for a permitted action, not therapy notes.

### Consent and data quality
Examples: consent status, purpose category, last-recorded date, freshness, missing-data flags.

Access: show the minimum information needed to make a permitted decision. Do not treat missing or stale data as evidence of poor performance.

## 5. Authorization Rules

1. Every protected backend endpoint must determine the current demo role and permitted scope.
2. The backend must filter records and sensitive fields before returning responses.
3. A hidden frontend button does not authorize or prevent an API action.
4. Fee and counselling information must be restricted at the response/service layer.
5. Consent for one purpose must not automatically imply consent for another.
6. Recommendations must respect relevant consent and purpose restrictions.
7. Manual overrides and rejected recommendations must record a reason where required.
8. Important actions must record an actor label, timestamp, and event.
9. Missing data must be represented as unknown or unavailable, not fabricated as zero.
10. The prototype must clearly identify demo roles as simulated identities.

## 6. Prototype Identity Model

For the hackathon, a request may use a demo-role header to simulate the current user.

This is a development-only mechanism. It is not secure production authentication and must not be presented as such.

The role and permitted scope must be validated centrally in the backend rather than independently implemented in each frontend screen.

## 7. Permission Tests

- Faculty cannot retrieve detailed fee information through a protected endpoint.
- Finance cannot retrieve unrelated sensitive counselling notes.
- Placement cannot access detailed financial records merely because a student has a placement case.
- A mentor cannot access every student simply because they have the mentor role.
- Leadership analytics do not expose sensitive counselling notes.
- Student view, if implemented, cannot retrieve another student's private information.
- Consent or purpose restrictions can block or require review of a proposed workflow.
- Unauthorized requests return an appropriate error rather than the restricted data.

## 8. Implementation Boundary

This document defines the intended prototype behavior. The authorization code and automated tests must enforce it.

The role switcher, synthetic records, and demo identity header are not substitutes for production authentication, institutional policy, or legal compliance review.
