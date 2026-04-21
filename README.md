# barkingpuppy

## Rich list preview UI

Generate JSON data from the script:

`python3 /workspace/algorand_rich_list.py --asset-id 0 --basis network-total --output-file /workspace/ui/data/algo-rich-list.json`

Then open the UI file in a browser:

`/workspace/ui/rich-list-preview.html`

The page lets you load the generated JSON and renders:

- Holder distribution by minimum supply threshold
- "Percentage # Accounts Balance equals (or greater than)" table