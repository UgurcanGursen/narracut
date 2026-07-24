# Domain Packs

Kaynak karar: `docs/MASTER_ROADMAP.md` ADR-015.

Ürün modeli:

```text
multi-domain-ready core
+
domain-specific intelligence pack
```

İlk ve tek production hedefi `business-tech` olacaktır. Faz 0'da herhangi bir
Domain Pack implementation oluşturulmamıştır.

## Core adayları

Workspace/stable ID, source ve claim persistence, chronology, story hierarchy,
asset catalog, timeline/EDL, renderer, audio, review, artifact lifecycle,
validation orchestration ve export.

## Pack sorumlulukları

Research/source priority, claim taxonomy, entity roles, narrative/visual
grammar, safety/wording, prompt bundle, validation extension ve benchmark
fixture'ları.

## Faz 0 bulgusu

Mevcut engine domain-pack aware değildir. IBM acceptance fixture path'leri,
iş/finans örnek metinleri ve generic “technology data center” fallback'i
mevcuttur. Ayrıntılı dosya/satır envanteri
`baseline/domain_assumption_inventory.md` içindedir. Bu görevde taşınmamış veya
yeniden tasarlanmamıştır.

`true-crime-legal`, `history-geopolitics` ve `science-explainer` yalnızca
roadmap hedefidir; implementation yoktur ve Faz 0'da eklenmemiştir.

