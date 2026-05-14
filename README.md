# docker-python

## 実行環境のセットアップ

### メモリ設定（Demucs実行前に必須）

- `docker-compose.yml` で `python3` サービスに `mem_limit: 8g` を設定済みです。
- Docker Desktop を利用している場合、アプリ全体のメモリ上限が低いとコンテナ内で `rc=-9`（OOM Kill）が発生します。
- Docker Desktop -> Settings -> Resources -> Memory を `8GB以上（推奨12GB）` に設定してください。

1. コンテナの起動

    ```bash
    docker-compose up -d --build
    ```

    起動時に `uv run python -m opt.cli` が自動実行され、`opt/input/*.mp4` が処理されます。

1. 作られたイメージの確認

    ```bash
    docker image ls
    ```

    docker-compose.ymlで設定された名称のイメージが生成されていたら成功。

1. 作られたコンテナの確認

    ```bash
    docker container ls
    ```

    docker-compose.ymlで設定された名称のコンテナが生成されていたら成功。

1. コンテナへの接続

    ```bash
    docker-compose exec python3 bash
    ```

1. 実行環境の確認

    ```bash
    uv --version
    uv run python --version
    ```

1. 動作確認

    - ボイス除去ツール

        1) 入力動画を `opt/input/*.mp4` に配置する。
        1) 起動時に自動実行される（`docker-compose up -d --build`）。

        ```bash
        docker-compose up -d --build
        ```

        1) 手動で再実行する場合

        ```bash
        docker-compose exec python3 uv run python -m opt.cli
        ```

        `rc=-9` が出る場合は、次を実行してコンテナを再作成してから再実行してください。

        ```bash
        docker-compose down
        docker-compose up -d --build
        docker-compose exec python3 uv run python -m opt.cli
        ```

        補足:
        - 依存追加後（`pyproject.toml` 更新後）は `docker-compose up -d --build` で再ビルドが必須です。

        1) 動作確認（Demucs経由の出力ファイルを確認）

        ```bash
        ls -1 opt/output/*_demucs_no_vocals.mp4 opt/output/*_estimated_no_vocals.wav
        ```

        出力例:
        - `opt/output/<元ファイル名>_demucs_no_vocals.mp4`（Demucs推定の非ボイス音声で置換した動画）
        - `opt/output/<元ファイル名>_estimated_no_vocals.wav`（Demucs推定の非ボイス）

1. 実行環境から戻る

    ```bash
    exit
    ```

## 実行環境の削除

1. Dockerコンテナの終了と削除

    ```bash
    docker-compose down
    ```

    以下のコマンドを実行して表示されるコンテナがなければ成功。

    ```bash
    docker container ls
    ```

    - 再度コンテナを実行したい場合
    イメージは作成されている状態なので--buildオプションが不要

        ```bash
        docker-compose up -d
        ```

1. イメージの削除

    ```bash
    docker image rm hogehoge
    ```

    以下のコマンドを実行して表示されるイメージがなければ成功。

    ```bash
    docker image ls
    ```

## このリポジトリをベースに新しくリポジトリを作成する手順

1. 新しいリポジトリを作成する

1. 外部クローンURLを使用して、外部リポジトリの"ベア"クローンを作成する。 これはデータの完全なコピーだが、ファイル編集のためのワーキングディレクトリはコピーされず、古いデータすべてのクリーンな新しいエクスポートが作成される。bash

    ```bash
    git clone --bare https://github.com/Shadowball429/docker-python.git
    ```

1. "mirror"オプションを使用して、ローカルにクローンされたリポジトリを GitHub にプッシュする。インポートされたリポジトリには、ブランチやタグなどすべての参照がコピーされる。

    ```bash
    cd REPO.git
    git push --mirror https://github.com/***/~~~.git
    ```

1. 一時ローカルリポジトリを削除する。

    ```bash
    cd ..
    rm -r -Force docker-python.git
    ```

## 参考文献

1. DockerでPython実行環境を作ってみる: <https://qiita.com/jhorikawa_err/items/fb9c03c0982c29c5b6d5>

1. Markdown記法/書き方（見出し・表・リンク・画像・文字色など）: <https://notepm.jp/help/how-to-markdown>

1. コマンド ラインを使って外部の Git リポジトリをインポートする: <https://docs.github.com/ja/migrations/importing-source-code/using-the-command-line-to-import-source-code/bashimporting-an-external-git-repository-using-the-command-line>
