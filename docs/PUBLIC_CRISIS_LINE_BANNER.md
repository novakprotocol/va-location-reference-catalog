# Public Veterans Crisis Line banner

Status: public-side only

This public GitHub Pages surface hard-codes a Veterans Crisis Line notice at the top of every root public HTML page.

Displayed public banner content:

`	ext
Veterans Crisis Line: Call 988 then press 1 | Text 838255 | Chat VeteransCrisisLine.net | TTY 1-800-799-4889
`

Reason:

- The public catalog is visible outside the internal environment.
- Public-facing VA-adjacent pages should keep the emergency-resource notice obvious and immediately reachable.
- The banner is intentionally marked with id="public-crisis-line-banner" and data-public-only="true".

Internal deployment rule:

- When this catalog is brought inside an internal VA/enterprise environment, this public-side banner can be removed or replaced by the approved internal help/crisis/safety pattern.
- Do not promote this public banner into internal policy unless separately approved.

Implementation note:

- The banner is injected directly into root *.html public pages.
- Raw public-source evidence files under data/raw/ are not modified.