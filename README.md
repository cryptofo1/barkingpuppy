# barkingpuppy

## Rich list preview UI

Generate JSON data from the script:

`python3 /workspace/algorand_rich_list.py --asset-id 0 --basis network-total --output-file /workspace/ui/data/algo-rich-list.json`

Then open the UI file in a browser:

`/workspace/ui/rich-list-preview.html`

The page lets you load the generated JSON and renders:

- Holder distribution by minimum supply threshold
- "Percentage # Accounts Balance equals (or greater than)" table
- Balance range summary with average holdings and top-percentile cutoff

Useful options for the script:

- `--balance-ranges` to customize range bands (whole-token units), e.g. `10000-50000`.
- `--output-file` to write JSON consumed by the preview UI.

Notes:

- `ui/sample-rich-list.json` now defaults to an ALGO sample preview.
- `ui/sample-yldy-rich-list.json` is included as an alternate token sample.