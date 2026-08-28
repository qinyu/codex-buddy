# Character packs from Ping Island

GIF frames are exported from Ping Island's `MascotView` via:

```bash
./scripts/render-mascots.sh --status all --size 96 \
  --kind codex,pi,hermes,cursor
```

Island states → Stick states (unique files only):

| Stick state | Island GIF |
|-------------|------------|
| idle / sleep / heart | `*-idle.gif` |
| busy / completed / celebrate | `*-working.gif` |
| attention | `*-warning.gif` |
| dizzy | `*-dragging.gif` |

`dsh` and unknown agents fall back to the Mao pack.
