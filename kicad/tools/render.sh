#!/bin/bash
# Render each figure to SVG + PDF + PNG preview and run KiCad's ERC.
#   bash render.sh [fig3-ram ...]     (default: every .kicad_sch)
CLI="$LOCALAPPDATA/Programs/KiCad/10.0/bin/kicad-cli.exe"
[ -x "$CLI" ] || CLI="/c/Users/david/AppData/Local/Programs/KiCad/10.0/bin/kicad-cli.exe"
D="$(cd "$(dirname "$0")/../sheets" && pwd)"
OUT="$D/export"; mkdir -p "$OUT"
names=("$@"); [ ${#names[@]} -eq 0 ] && names=($(cd "$D" && ls *.kicad_sch | sed 's/.kicad_sch$//'))
for n in "${names[@]}"; do
  "$CLI" sch export svg -o "$OUT" "$D/$n.kicad_sch" >/dev/null 2>&1 || echo "$n: svg FAILED"
  "$CLI" sch export pdf -o "$OUT/$n.pdf" "$D/$n.kicad_sch" >/dev/null 2>&1 || echo "$n: pdf FAILED"
  "$CLI" sch erc -o "$OUT/$n-erc.rpt" --severity-error --severity-warning "$D/$n.kicad_sch" >/dev/null 2>&1
  e=$(grep -c "^\[" "$OUT/$n-erc.rpt" 2>/dev/null)
  echo "$n: ERC items: ${e:-?}"
done
ls "$OUT"
