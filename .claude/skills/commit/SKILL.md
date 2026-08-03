---
name: commit
description: このリポジトリの規約に沿って、作業内容をステージし、日本語のコミットメッセージで commit して push する。検証（lint・テスト・マイグレーション整合）を先に通してからコミットする。
when_to_use: 「コミットして」「commit」「커밋해줘」「push して」「作業を保存して」と言われたとき。PR の作成は別スキル `pr` を使う。
argument-hint: "[任意: コミットメッセージの方向性]"
---

# コミットと push

## 前提

- **`main` はブランチ保護されている。** 直接 push できない。
- コミットメッセージの本文は**日本語**で書く。接頭辞（`feat:` など）だけ英語。
- 検証を通してからコミットする。CI で落ちるものをローカルで先に落とす。

## 手順

### 1. ブランチを確認する

```bash
git branch --show-current
```

`main` にいる場合は**そのままコミットしない**。作業ブランチを切るかユーザーに確認する。

```bash
git checkout -b feat/<機能名>   # feat / fix / docs / chore / refactor
```

### 2. 変更内容を把握する

```bash
git status --short
git diff
git diff --cached
```

**何が変わったかを自分で読む。** 差分を読まずにメッセージを書かない。

### 3. 検証を通す

サービスが起動している前提（起動していなければ `docker compose up -d`）。

```bash
# backend
docker compose exec -T api ruff format .
docker compose exec -T api ruff check .
docker compose exec -T api python manage.py makemigrations --check --dry-run
docker compose exec -T api pytest -q

# frontend（フロントを触った場合）
docker compose exec -T web npm run lint
docker compose exec -T web npm run build
```

**落ちたら直してから進む。** 特に `makemigrations --check` は、モデルを変えたのに
マイグレーションを作り忘れた変更を止めるためにある。

> `ruff format` はファイルを書き換える。実行後に差分が増えるので、
> **ステージはフォーマットの後**に行う。

### 4. ステージする

```bash
git add -A
```

ステージ後、**入ってはいけないものが含まれていないか必ず確認する**。

```bash
git diff --cached --name-only | grep -E '\.env$|node_modules|\.venv|\.sqlite3|staticfiles/' \
  && echo "!! 除外すべきファイルが含まれている !!" \
  || echo "OK"
```

引っかかった場合は `.gitignore` を直し、`git restore --staged <path>` で外す。
**`.env` や API キーを含んだままコミットしない。**

### 5. メッセージを組み立てる

**形式**

```
<type>(<scope>): <日本語の要約 50 字以内>

<なぜそうしたかを日本語で。何をしたかは差分を見れば分かるので、
 差分から読み取れないことを書く>

<設計上の判断を変えた場合は、変える前の案と変えた理由を残す>
```

**type**

| type | 使う場面 |
|---|---|
| `feat` | 機能追加 |
| `fix` | バグ修正 |
| `docs` | ドキュメントのみ |
| `refactor` | 挙動を変えないコード整理 |
| `test` | テストのみ |
| `chore` | 依存更新、設定、雑務 |

**書き方の指針**

- **「なぜ」を書く。** 「何を」は差分に書いてある。
- **設計の判断を変えたら、変える前の案と理由を残す。** 後から「なぜこうなっているのか」を
  git log で追えるようにする。
- **落とし穴を踏んだら書く。** 同じ罠を次に踏まないため。
- 関連するドキュメントがあれば参照する（`docs/04-data-model.md` など）。
- 箇条書きを使ってよい。長くなってもよい。**説明を削るより長いほうがまし。**

**良い例**

```
fix(deploy): ヘルスチェックのパスを HTTPS リダイレクトから除外する

本番で「プロセスは生きているのにリクエストの約半分が 404 になる」症状が出ていた。

原因は SECURE_SSL_REDIRECT とヘルスチェックの衝突。Render の内部チェックは
X-Forwarded-Proto を付けずに叩くことがあり、Django が 301 を返す。Render は
2xx でないため失敗と見なしインスタンスをルーティングから外し、次の試行では
通るのでまた投入する —— これを繰り返していた。

アプリケーションログにはクラッシュもヘルスチェック失敗も出ないため気付きにくい。
切り分けには x-render-origin-server ヘッダを見るとよい。
```

**避けること**

- `update files`、`fix bug`、`修正` のような中身のない要約
- 差分をそのまま日本語にしただけの本文
- 無関係な変更を 1 コミットに混ぜる（分けられるなら分ける）

### 6. コミットする

**必ず HEREDOC を使う。** 複数行と日本語を安全に渡すため。

末尾に、実際に動かしている AI の trailer を付ける。

| 実行しているツール | trailer |
|---|---|
| Claude | `Co-Authored-By: Claude <noreply@anthropic.com>` |
| Codex | `Co-authored-by: Codex <noreply@openai.com>` |

```bash
git commit -m "$(cat <<'EOF'
feat(libraries): 図書館の検索 API を追加

（本文）

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### 7. push する

```bash
git push -u origin HEAD
```

失敗したときの対処:

| 症状 | 対処 |
|---|---|
| `protected branch` | `main` にいる。ブランチを切り直す |
| `rejected (non-fast-forward)` | `git pull --rebase origin <branch>` してから再度 push |
| 認証エラー | ユーザーに `gh auth login` を依頼する |

### 8. 報告する

- コミットハッシュ
- ブランチ名
- 変更ファイル数
- **検証結果**（テスト何件通過、lint の結果）

PR を作るかどうかを尋ねる。作るなら `pr` スキルを使う。

## やらないこと

- **`git push --force` を使わない。** 必要だと判断した場合は必ずユーザーに確認する。
- **`main` に直接コミットしない。**
- ユーザーに確認せず `git reset --hard` などの破壊的操作をしない。
- 検証を飛ばしてコミットしない。急ぎの場合はその旨を報告に明記する。
