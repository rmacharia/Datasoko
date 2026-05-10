# ACCESSIBILITY.md

## Internal Admin UI (MVP) - New Section

### Implemented Baseline
- Keyboard reachable navigation and controls.
- Semantic headings, form labels, and inline error messages.
- Focus-visible outline for interactive elements.
- Text-first status rendering (no color-only signaling).
- Upload page includes ARIA-labeled progress indicator and copyable text errors.
- Setup, login, admin, reports, schedules, and settings forms use associated labels and visible validation states.

### Motion and Reduced Motion
- Motion is progressive enhancement only.
- Overview animations are disabled when `prefers-reduced-motion` is active.
- No 3D dependency in baseline workflow.

### Ongoing Requirements
- Maintain WCAG AA contrast minimum.
- Keep API errors human-readable and actionable.
- Do not render sensitive values (phones, names, raw transaction details).

## Settings Accessibility - New Section

### Theme and Motion Preferences
- Theme switch supports keyboard navigation and is persisted (`system`, `dark`, `light`).
- Reduced-motion users keep full functionality; Enhanced Mode effects are automatically limited.
- Theme is applied before hydration to avoid visual flicker/disorientation.

### Forms
- All settings controls are label-associated and keyboard reachable.
- Secret inputs use password fields and never prefill saved secret values.
- Save/test outcomes are surfaced through non-blocking toast alerts and visible inline error text.

## Admin and Tenant Context

- Organization/business selectors must be keyboard reachable and expose the selected context through text, not color alone.
- Role-denied and cross-tenant errors should preserve focus and provide a clear route back to an allowed page.
- Data visualizations must keep numeric summaries available as text so charts are not the only way to read analytics.
