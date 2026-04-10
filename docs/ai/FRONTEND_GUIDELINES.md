# FRONTEND GUIDELINES

This project has no web frontend. The only user-facing surface is the CLI and generated report artifacts.

## Visual Direction

- Use clean terminal output with concise section headings.
- Prefer tables for summaries and small textual dashboards for status.
- Report charts should be restrained and publication-friendly rather than decorative.

## Design Tokens

- Use one accent color for chart highlights.
- Use neutral backgrounds and high-contrast text.
- Keep figure sizes consistent across generated reports.

## Typography

- Use the default monospace terminal font for CLI output.
- Use a readable sans-serif or default Matplotlib font stack for charts.

## Spacing and Layout

- Keep CLI output compact with blank lines only between logical sections.
- Align summary columns to make payoff comparisons easy to scan.
- Export figures with enough padding to survive PDF embedding.

## Components

- Simulation status banner.
- Agent summary table.
- Round-by-round metrics table.
- Cumulative payoff chart.
- Reputation and demand line charts.

## Responsive Breakpoints

- Not applicable to a web UI.
- Generated figures should remain legible at report-page width and A4/letter scale.

## Motion and Interaction

- Not applicable.

## Accessibility Rules

- Avoid color-only distinctions in charts.
- Label every axis and legend.
- Include units in titles where useful.
- Ensure CLI messages are explicit about file paths and saved artifacts.
