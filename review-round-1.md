# Review Round 1

Reviewed the working-tree diff against `HEAD` (`4380b52`) against the updated [issue #1](https://github.com/ric6121824/LightlessGroupExaminer/issues/1).

## Standards

No documented coding standards were found. No actionable standards violations or code smells were identified.

## Spec

The sort dropdown includes all requested criteria. Unique Online Players uses snapshot counts in either analysis scope and falls back to zero for ordering when online data is absent.

- [ ] **[P2] Sort direction clears the Leave Impact filter and hides every syncshell card.** In Grid or List view, start with visible cards and click either direction button. The dashboard shows “No syncshells match your search or filter criteria.” Both direction buttons share the `.btn-filter` styling class, so `filterBtns` in `public/app.js` registers the Leave Impact handler on them too. They lack `data-filter`, so their clicks set `currentFilter` to `null` and every group fails the filter check. The simulated click check reproduced this for both numeric and both alphabetical directions. Clicking **All** in the Leave Impact filter restored the cards.
  - **Suggested fix** — Select Leave Impact buttons with `.filter-buttons [data-filter]` in `public/app.js`. Keep sort direction clicks bound through `[data-sort-direction]`.
  - **Verify** — Use a fixture with at least two matching syncshells with different names and unique online counts. Apply a search and a Leave Impact filter that match both groups. In Grid and List views, toggle both directions for **Unique Online Players**, then select **Name** and toggle **A to Z** and **Z to A**. Check the order after each click and confirm the same cards, search text, and active filter are preserved. The empty state should stay hidden.

**Findings:** Standards 0; Spec 1.
