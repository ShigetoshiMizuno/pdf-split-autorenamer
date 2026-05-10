# 使用例

サンプル PDF はリポジトリに含めていません（個人文書なので）。
以下のような構成で使うことを想定しています：

```
my_scans/
  2026-05-10-11-59-42.pdf      # ScanSnap が連続スキャンしたPDF（複数書類が混在）
  2026-05-10-12-02-22.pdf
  ...
```

```sh
# 解析（HTMLレポート生成）
psar analyze ./my_scans

# ブラウザで my_scans/.psar/report.html を開いて境界・出力名を編集
# → 「groups.json を保存」 → my_scans/.psar/groups.json に上書き

# 分割（dry-run → 本番）
psar split ./my_scans --dry-run
psar split ./my_scans

# 自動リネーム
psar rename ./my_scans            # dry-run
psar rename ./my_scans --apply
```

GUI の場合：
```sh
psar gui
# または
psar gui --folder ./my_scans
```
