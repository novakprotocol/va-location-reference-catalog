# Full Top Freeze and Table Header Lock

Current purpose:

- The Veterans Crisis Line banner is fixed at the top of the viewport.
- The page chrome above the result table remains visible.
- The result rows scroll inside the table panel instead of scrolling the whole browser page.
- The table column headers remain sticky inside the table panel.
- The header cells use an opaque background and high z-index so row text does not bleed through.

Why this exists:

The earlier sticky-header fix still depended on browser-page scrolling and table-header stacking behavior. That can cause column headings to overlap row text or appear visually inline with the first records.

This fix changes the layout model:

```text
viewport
â”œâ”€ fixed VCL banner
â”œâ”€ fixed visible page top/chrome because body no longer scrolls
â””â”€ table panel scrolls internally
   â”œâ”€ sticky real table header
   â””â”€ scrolling data rows
```

Public/internal boundary:

- This is a public UI behavior fix.
- It does not promote candidate phone or hour fields.
- It does not add restricted/internal VA operational data.
- Internal overlays should remain separate from the public catalog contract.