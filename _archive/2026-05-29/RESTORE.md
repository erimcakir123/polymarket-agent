# Restore from 2026-05-29 snapshot

Rollback git:
```
git reset --hard pre-unified-2026-05-29
```

Restore data + audit:
```
cp -r _archive/2026-05-29/data/* data/
rm -rf logs/audit && cp -r _archive/2026-05-29/logs/audit logs/
```

Verify:
```
python -c "import json; d=json.load(open('data/positions.json',encoding='utf-8')); print('open=', len(d.get('positions',{})))"
```

Snapshot taken: 2026-05-29.
HEAD at snapshot: `pre-unified-2026-05-29` tag.
Phase 1 starts immediately after this snapshot.
