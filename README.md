# LifeCanvas

Windows向けライフプランシミュレーター。

住宅ローン・教育費・資産運用・税金・社会保険・年金・ライフイベントを統合し、将来の資産・キャッシュフロー・老後資金をシミュレーションする。

## 技術スタック

| 領域 | 技術 |
|------|------|
| 言語 | Python 3.12+ |
| UI | PySide6 |
| ORM | SQLAlchemy |
| バリデーション | Pydantic |
| DB | SQLite |
| グラフ | matplotlib |
| PDF出力 | ReportLab |
| Excel出力 | openpyxl |
| テスト | pytest |

## ディレクトリ構成

```
LifeCanvas/
├── README.md
├── requirements.txt
├── main.py
├── docs/
│   ├── 00_PRD.md
│   ├── 01_REQUIREMENTS.md
│   ├── 02_SAMPLE_PROJECT.md
│   ├── 03_PROMPTS.md
│   └── 04_ROADMAP.md
├── sample/
│   └── genki_family.json
├── core/
│   ├── models/          # Pydantic データモデル
│   ├── calculator/      # 税金・ローン・投資計算
│   ├── engine.py        # シミュレーションエンジン
│   ├── database.py      # SQLAlchemy ORM
│   ├── project.py       # プロジェクト管理
│   └── report_generator.py
├── ui/
│   ├── styles.py        # QSSテーマ
│   ├── viewmodels/      # MVVM ViewModel層
│   └── views/           # PySide6 View層
└── tests/
```

## セットアップ

```powershell
python -m venv venv
.\venv\Scripts\pip.exe install -r requirements.txt
```

## 起動

```powershell
.\venv\Scripts\python.exe main.py
```

## ドキュメント

- [PRD](docs/00_PRD.md)
- [要件定義書](docs/01_REQUIREMENTS.md)
- [サンプルプロジェクト](docs/02_SAMPLE_PROJECT.md)
- [AI実装用プロンプト集](docs/03_PROMPTS.md)
- [ロードマップ](docs/04_ROADMAP.md)
