# Character packs from Ping Island

GIF frames are exported from Ping Island's `MascotView` via:

```bash
./scripts/render-mascots.sh --status all --size 96 \
  --kind codex,pi,hermes,cursor,kimi
```

Island states → Stick states (unique files only):

| Stick state | Island GIF |
|-------------|------------|
| idle / sleep / heart | `*-idle.gif` |
| busy / completed / celebrate | `*-working.gif` |
| attention | `*-warning.gif` |
| dizzy | `*-dragging.gif` |

`dsh` has no Island mascot — Stick maps it to the **Kimi** pack.
Unknown agents fall back to Mao.
