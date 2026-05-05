# Page-Scoped Public Top Freeze

This supersedes the earlier broad sticky-header behavior.

## Reason

The public catalog table pages and the contact/hours candidate review page do not have the same layout.

The catalog pages have true table columns and can safely use:

```text
fixed VCL banner
fixed page chrome
internal table-row scroll
sticky real table header
```

The contact/hours candidate review page is not a simple catalog table. Applying the same generic table-scroll lock can select the wrong container and visually create blank columns or displaced content.

## Current behavior

- The Veterans Crisis Line banner remains fixed at the top.
- Main catalog table pages keep sticky real table headers.
- Contact/hours candidate review keeps natural page scrolling and does not receive the generic table-pane lock.
- Older `catalog-ui-public-fixes.css/js` are removed from the HTML load path to prevent competing sticky behavior.
- No candidate phone or hours data is promoted into approved catalog records.