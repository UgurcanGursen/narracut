# Target Directory Map

Bu belge roadmap hedefini gösterir; Faz 0'da hiçbir mevcut dosya taşınmamıştır.

```text
repo/
├─ docs/                         # roadmap, state, ADR, acceptance, limits
├─ baseline/                     # immutable/referenced baseline evidence
├─ shared-schemas/               # canonical JSON Schema + OpenAPI contracts
├─ domain-packs/
│  └─ business-tech/             # ilk production intelligence pack
│     ├─ policies/
│     ├─ prompts/
│     ├─ fixtures/
│     └─ benchmarks/
├─ studio-api/                   # thin FastAPI adapter/orchestration
├─ studio-ui/                    # React + TypeScript + Vite
├─ engine/                       # future domain-agnostic Python core boundary
│  ├─ workspace/
│  ├─ llm_gateway/
│  ├─ research/
│  ├─ story/
│  ├─ timing/
│  ├─ assets/
│  ├─ edl/
│  ├─ audio/
│  ├─ validation/
│  └─ artifacts/
├─ motion-renderer/              # Remotion + React compositions
├─ projects/                     # long-form project workspaces
├─ v2/                           # ACTIVE LEGACY PRODUCTION ENGINE (korunur)
├─ assets/
├─ cache/
├─ output/
└─ temp_assets/
```

## Migration sınırı

```text
v2/ active engine
→ explicit adapter boundary
→ küçük verified replacement modules
→ fixture + artifact parity validation
→ controlled migration
→ kullanıcı onaylı deprecation (gelecek karar)
```

Kurallar:

- `main.py → v2.main.process_timeline` delegation Faz 0'da değişmez.
- `v2/` topluca taşınmaz, rename edilmez veya silinmez.
- Yeni core modülü yalnızca parity kanıtı olan sorumluluğu devralır.
- `assets/`, `cache/`, `output/`, `temp_assets/` lifecycle/registry kurulmadan
  hedef yapıya zorla taşınmaz.
- Business-tech davranışı core servislerine dağılmış koşullar olarak değil,
  Domain Pack contract üzerinden ileride çözülür.
- FastAPI/React/Remotion dizinleri roadmap hedefidir; Faz 0 deliverable'ı
  yalnızca bu haritadır, implementation değildir.

