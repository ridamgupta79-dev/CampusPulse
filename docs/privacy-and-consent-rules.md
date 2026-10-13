# CampusPulse — Privacy and Consent Rules

## 1. Purpose

CampusPulse uses synthetic student-success data to demonstrate responsible, human-reviewed intervention workflows.

These rules define how the prototype represents consent, limits data visibility, handles missing information, and decides when an action requires additional review.

The prototype's consent records and demo roles do not constitute a production-grade legal consent or authentication system.

## 2. Purpose-Specific Consent

Consent must be represented separately for each relevant purpose.

Initial purpose categories:
- Academic support
- Mentoring and student check-ins
- Counselling referral coordination
- Financial-support follow-up
- Placement-readiness support
- General student-success review, if enabled by the demo policy

These categories are a starting point for the prototype. The final implementation must not imply that recording one consent grants permission for every other purpose.

Possible consent statuses:
- granted
- declined
- unknown
- withdrawn

Each consent record should retain:
- Student reference
- Purpose category
- Status
- Recorded timestamp
- Source or concise note, where appropriate

Consent history should be preserved rather than silently overwritten.

## 3. Consent Handling Rules

### Granted
A granted status records permission for the specified demo purpose. The workflow must still check the user's role, permitted scope, data sensitivity, and other applicable restrictions.

### Declined
A declined status must not be silently treated as permission. A workflow requiring that consent must be blocked or sent for an authorized policy review, as appropriate.

### Unknown
An unknown status must be displayed as unknown. It must not be assumed to mean granted or declined.

If a workflow requires confirmed consent, the system must request review before proceeding with that workflow.

### Withdrawn
A withdrawn status records that previously granted consent is no longer active for the specified purpose.

The system must not treat the earlier grant as current permission. The relevant workflow must be stopped, restricted, or reviewed according to the demo policy.

## 4. Role and Purpose Are Separate Checks

Permission requires more than selecting a role.

Before returning protected information or performing a protected action, the backend must evaluate:
1. The current demo identity and role.
2. The resource and student scope the role may access.
3. The purpose of the requested action.
4. The sensitivity of the requested fields.
5. Relevant consent and review requirements.
6. Whether the requested operation is allowed for that role.

A permitted role does not automatically have access to every field or every student.

A frontend role switcher is only a demonstration mechanism. Backend checks remain mandatory.

## 5. Sensitive Data Rules

### General profile
Fictional name, synthetic student code, program, department, year, and cohort may be returned only within the viewer's permitted student scope.

### Attendance and academics
Attendance, marks, assignment completion, and academic trends may be available to faculty and relevant mentors within their assigned or authorized scope.

Leadership views should expose only the detail required for their permitted work.

### Participation
Participation information must be presented with its quality and freshness context. Missing information must not be interpreted as disengagement.

### Financial information
Detailed fee and financial-support information is restricted to finance-authorized workflows.

Faculty, mentors, placement staff, and general leadership views must not receive detailed fee values by default.

Where another role has an explicitly authorized support responsibility, it should receive only the minimum necessary information rather than unrestricted financial details.

### Skills and placement readiness
Detailed skills and placement-readiness information is available to the placement team and other explicitly authorized workflows.

It must not be used to infer academic risk without an appropriate, explainable rule.

### Counselling information
Sensitive counselling notes are restricted to the counsellor.

Other authorized staff may receive a minimal coordination status when needed for their permitted workflow, but not therapy notes or unnecessary personal details.

A referral indicator must never be presented as a psychological diagnosis.

### Consent information
Show the consent status and purpose information needed for a permitted decision. Do not expose unrelated personal notes or unnecessary consent history.

## 6. Missing, Stale, and Uncertain Data

Each relevant signal should distinguish:
- Available and current
- Missing or unavailable
- Stale
- Uncertain or quality-limited

Rules:
- Missing data is not equivalent to zero.
- Stale data must not be presented as current.
- Missing or stale signals must not add negative points to a risk score.
- The assessment must disclose relevant data-quality limitations.
- If evidence is insufficient, the system must communicate uncertainty rather than manufacture a conclusion.

## 7. Recommendation and Intervention Safeguards

Before recommending or routing an intervention:
- Identify the signal or evidence supporting it.
- Confirm that the proposed purpose is appropriate.
- Apply the relevant consent and authorization checks.
- Route the action to the appropriate stakeholder.
- Show uncertainty and missing context.
- Require human review before an intervention is approved or assigned when required by the workflow.

If a recommendation is overridden or declined, record the decision and its reason where required.

A risk score alone must never automatically trigger punishment, disciplinary action, or an irreversible decision.

## 8. Error Handling

The backend must not return protected information when access is denied.

Use a consistent response policy:
- Unauthenticated or invalid demo identity: reject the request when identity is required.
- Authenticated demo role without permission: return an appropriate authorization error.
- Missing resource: return a not-found response where appropriate.
- Consent or purpose requirement not satisfied: return a clear policy-related response without exposing restricted data.
- Invalid workflow transition: reject the transition and explain the validation error without leaking sensitive fields.

The exact HTTP status codes and response payloads will be finalized in the API contract.

## 9. Prototype Limitations

The prototype will demonstrate:
- Simulated roles and permissions
- Purpose-specific consent records
- Restricted response fields
- Human review and override
- Visible data-quality limitations

It will not claim to provide:
- Production authentication or institutional identity verification
- Complete legal consent management
- A comprehensive regulatory compliance implementation
- Psychological diagnosis or automated disciplinary decisions

## 10. Required Tests

- Declined consent is not treated as granted.
- Unknown consent is not treated as granted.
- Withdrawn consent is not treated as a current grant.
- Consent for one purpose does not automatically authorize another.
- Faculty cannot retrieve detailed fee information through a protected endpoint.
- Finance cannot retrieve restricted counselling notes.
- Placement access does not automatically grant financial access.
- A mentor cannot access every student without the required scope.
- Missing or stale signals do not create negative risk evidence.
- Unauthorized requests never return restricted fields.
- The frontend cannot bypass backend authorization by directly calling an API.
