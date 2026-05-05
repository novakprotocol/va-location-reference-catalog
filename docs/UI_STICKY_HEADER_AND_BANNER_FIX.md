# Public UI Sticky Header and Safety Banner Fix

## What this fixes

- The Veterans Crisis Line banner is fixed to the top of the viewport.
- Page content is offset so it is not covered by the fixed banner.
- Table column headings are sticky below the fixed banner.
- Table headings receive an opaque background and higher z-index so they do not visually collide with row text.
- Contact/hours review text receives day-of-week boxes where candidate language can be interpreted.
- 24/7 language receives a clear 24/7 badge.

## Scope

This is public UI behavior only.

It does not promote phone or hours candidates into approved facility records.

## Files

- `catalog-ui-public-fixes.css`
- `catalog-ui-public-fixes.js`
- `index.html`
- `addresses.html`
- `aliases-hours.html`
- `contact-hours-candidates.html`