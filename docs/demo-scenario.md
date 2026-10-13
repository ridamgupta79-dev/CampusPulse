# CampusPulse — Hero Student Demo Scenario

## 1. Purpose

This scenario demonstrates how CampusPulse converts early student-success signals into explainable, human-reviewed support, assigns responsibility, records follow-up evidence, and measures the observed outcome.

**All student identities and records in this scenario are fictional.**

## 2. Student Profile

- Synthetic student ID: CP-DEMO-0042
- Name: Aarav Mehta
- Program: B.Tech Information Technology
- Year: Second year
- Cohort: IT-Year-2
- Assigned mentor: Demo Mentor 01
- Academic advisor: Demo Faculty 01
- Data classification: Synthetic demonstration data

## 3. Initial Student Signals

### Attendance
- Previous attendance: 78%
- Current attendance: 61%
- Interpretation: Attendance has declined and merits a contextual check-in.
- Data status: Available for the demonstration.

### Academic Performance
- Previous assessment average: 68%
- Current assessment average: 52%
- Assignment completion: 5 of 8 assignments completed.
- Interpretation: Recent academic performance and assignment completion indicate that academic support may be useful.
- Data status: Available for the demonstration.

### Participation
- Recent participation record: Incomplete.
- Interpretation: Insufficient information to conclude that participation has declined.
- Risk treatment: Do not treat the missing information as a negative signal.

### Fees
- Financial-support status: Restricted demonstration field.
- Visibility: Finance-authorized role only.
- Risk treatment: Do not expose financial details to general faculty or leadership views, and do not use this field to justify the primary academic-support recommendation.

### Skills and Placement Readiness
- Skills assessment: Available as a separate support domain.
- Interpretation: Placement readiness should be assessed independently of academic review priority.
- Risk treatment: Route placement support only if the available skills evidence justifies it.

### Faculty Feedback
- Structured observation: Two lab submissions are pending; the student may benefit from a faculty check-in.
- Interpretation: This is contextual information, not a diagnosis or disciplinary finding.

## 4. Consent and Data Quality

- Academic-support purpose: Consent recorded as granted for this synthetic scenario.
- Other purposes: Must be evaluated separately rather than assuming blanket consent.
- Missing participation data: Display as unavailable.
- Data freshness: Show the last-recorded date for each signal.
- Sensitive fields: Restrict access by role and purpose.

This scenario represents a prototype consent record, not a production-grade legal consent system.

## 5. Explainable Review Priority

The system evaluates the available attendance and academic indicators using transparent prototype rules.

Potential contributing factors:
- Attendance declined from 78% to 61%.
- Assessment average declined from 68% to 52%.
- Only 5 of 8 assignments are recorded as completed.

The assessment must display the observed values, applicable thresholds, contributing factors, rule version, and data-quality limitations.

Missing participation data must not increase the score.

Any resulting score is a prototype review-priority aid, not a validated prediction, diagnosis, or judgment of the student.

An authorized staff member must review the context before deciding what action to take.

## 6. Recommended Intervention

Suggested intervention: Academic support and mentor check-in.

Rationale:
- Attendance has declined.
- Assessment performance has declined.
- Some assignments remain incomplete.
- A faculty check-in can help establish what support is appropriate.

Suggested responsible stakeholders:
- Primary owner: Demo Faculty 01.
- Supporting stakeholder: Demo Mentor 01.

Suggested follow-up:
- Arrange an academic check-in.
- Discuss pending assignments and possible remedial support.
- Record the action taken and any agreed next steps.

Suggested deadline: Three days after assignment.

The recommendation is not automatically approved or assigned. An authorized human must review, edit, approve, override, or decline it, recording a reason when required.

## 7. Intervention Lifecycle

The demonstration follows these stages:

1. Proposed: The recommendation is generated and its evidence is displayed.
2. Reviewed: Authorized faculty reviews the evidence and context.
3. Approved: Faculty accepts or edits the proposed support.
4. Assigned: An owner and due date are recorded.
5. In progress: The responsible stakeholder begins the action.
6. Follow-up recorded: The stakeholder records a timestamped contact or support event.
7. Outcome measured: Baseline and follow-up information are recorded when available.
8. Closed: The case is closed according to the workflow rules.

Overdue and escalation states must be derived from the deadline, status, and configured policy. They must not be fabricated as completed actions.

## 8. Follow-up Evidence

Example demonstration event:

- Event type: Academic check-in completed.
- Actor: Demo Faculty 01.
- Evidence note: Student and faculty reviewed pending lab submissions and agreed on a remedial-support plan.
- Timestamp: Generated when the demonstration event is recorded.

The event is an example of the evidence we intend to capture. The application must record it through the actual workflow rather than pretending the action occurred before it was entered.

## 9. Outcome Measurement

Record a baseline and a later measurement only when the follow-up data is available.

Potential measures:
- Attendance percentage.
- Assessment average.
- Assignment completion.
- Completion of the agreed support plan.

Example outcome:
- Baseline assessment average: 52%.
- Follow-up assessment average: 60%.
- Observed change: +8 percentage points.

This outcome is illustrative until the application records an actual synthetic follow-up event and corresponding measurement.

Outcome classification must consider the metric, measurement dates, data quality, and evidence available. Do not claim that the intervention caused the change.

If no reliable follow-up measurement exists, classify the outcome as insufficient evidence rather than inventing improvement.

## 10. Leadership Dashboard

After the workflow has been recorded, the cohort dashboard should summarize:

- Students by review-priority band.
- Open interventions and their responsible teams.
- Due, overdue, and escalated interventions.
- Follow-up completion.
- Recorded outcome categories and their denominators.
- Missing or stale data.
- Cohort and intervention-type breakdowns.

The dashboard must distinguish illustrative seed data from outcomes actually recorded during the demonstration.

## 11. End-to-End Acceptance Test

The evaluator must be able to follow this sequence:

1. Open the Command Center.
2. Select CP-DEMO-0042.
3. Inspect the Student 360 view.
4. Understand why academic support was suggested.
5. Review and approve or edit the recommendation.
6. Assign the responsible stakeholder and deadline.
7. Record follow-up evidence.
8. Record a baseline/follow-up outcome when supported by data.
9. Verify that cohort analytics reflect the persisted records.
10. Confirm that restricted information remains hidden from unauthorized roles.

## 12. Responsible-Use Boundaries

CampusPulse must not:
- Automatically punish or discipline a student based on a score.
- Diagnose a psychological or medical condition.
- Treat missing data as evidence of poor performance.
- Reveal sensitive financial or counselling details to unauthorized roles.
- Claim causal impact from a simple before-and-after comparison.
- Present fictional records or illustrative outcomes as real institutional evidence.
