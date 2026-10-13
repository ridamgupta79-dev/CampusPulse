# CampusPulse frontend style pass

This pass adapts the CampusPulse desktop workspace to the clean, light SaaS dashboard style used by the supplied LeadFlow reference, without migrating the app from Vite/React to Next.js or changing backend API contracts.

## Updated

- `frontend/src/App.tsx`
  - Added a global student search field in the top bar, connected to the existing student filter.
  - Added a privacy-first sidebar note.
  - Reworked Command Center into a KPI row, risk-distribution panel, data-quality panel, student directory, intervention workload, and quick actions.
  - All new dashboard figures come from existing API responses; no sales-style or fabricated demo metrics were introduced.
- `frontend/src/App.css`
  - Added a LeadFlow-inspired light sidebar, blue active navigation, compact metric cards, thin borders, lighter canvas, and tighter panel/table spacing.
  - Added restrained CSS entrance/hover/bar animations and a `prefers-reduced-motion` fallback.
  - Kept the responsive navigation and mobile layouts, although desktop remains the primary presentation target.

## Validation notes

- `node node_modules/typescript/bin/tsc -b` passed in the extracted workspace.
- The Vite production build could not complete in this extracted environment because the archive's existing `node_modules` is missing the platform-specific Rolldown native binding. Reinstall dependencies on the target machine (`npm ci` in `frontend`) before running `npm run build`.
- ESLint reports four `react-hooks/set-state-in-effect` errors in pre-existing data-loading effects in `App.tsx`; these are not caused by the visual stylesheet changes and were not silently suppressed.

## Run locally

```powershell
cd frontend
npm ci
npm run dev
```
