# CampusPulse — Intervention Workflow Contract

## 1. Purpose

Coordinate supportive interventions for students through explainable signals, human decisions, accountable assignments, follow-up evidence, and recorded outcomes.

## 2. Workflow stages

1. **Assessment:** Record explainable indicators, observed values, thresholds or rationale, timestamps, and data-quality limitations.
2. **Recommendation:** Propose a relevant support action with its rationale, contributing signals, intended staff role, and priority.
3. **Human review:** An authorized staff member approves, edits, overrides, or declines the recommendation.
4. **Assignment:** An approved support action becomes an intervention with a responsible role, owner, due date, and status.
5. **Follow-up:** Record progress, contact attempts, completed activities, and supporting evidence.
6. **Outcome:** Record baseline and follow-up measurements, evidence quality, and an appropriately qualified outcome classification.

## 3. Human-review rules

- Recommendations are proposals, not automatic decisions.
- Declined recommendations must not create active interventions.
- Overrides must record a reason.
- Edited recommendations must retain a record of the decision.
- No risk score alone may trigger punishment or an adverse academic decision.
- Counselling-related information must not be exposed to unauthorized roles.

## 4. Intervention statuses

Use these workflow statuses:

- `approved`
- `assigned`
- `in_progress`
- `follow_up_recorded`
- `measured`
- `completed`
- `cancelled`

Overdue status should be derived from the due date and the current workflow status rather than inferred from a student's risk level.

## 5. Event history

Record each important workflow action with:

- Intervention ID
- Event type
- Actor role and label
- Timestamp
- Action note
- Relevant metadata, when appropriate

Events must not be silently overwritten when an intervention changes status.

## 6. Follow-up and outcomes

A follow-up record should describe what happened and when. An outcome should distinguish observed change from causal attribution.

- Missing evidence must remain missing.
- Stale measurements must be identified.
- A change after an intervention does not prove that the intervention caused it.
- Use `insufficient_evidence` when the available information does not support a reliable conclusion.

## 7. Authorization and privacy

- Validate the viewer's role and permission for every protected action.
- Apply purpose-specific consent checks before exposing sensitive student signals.
- Restrict fee and counselling information to authorized purposes and roles.
- Record the actor and reason for consequential workflow decisions.
- The current demo-role header is not production authentication.

## 8. Acceptance criteria

The workflow is acceptable when a demo user can:

1. View a permitted recommendation and its rationale.
2. Make and record a human decision.
3. Create and assign an intervention following approval.
4. Record follow-up activity and evidence.
5. Record an outcome with baseline, follow-up, and evidence quality.
6. Review the intervention's event history.
7. See overdue work without interpreting it as additional student-risk evidence.
8. Verify that unauthorized roles cannot access restricted information.
