# docker-python

## 実行環境のセットアップ

1. コンテナの起動

    ```bash
    docker-compose up -d --build
    ```

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
    python --version
    ```

1. 動作確認

    ```bash
    python opt/sample.py 180.0
    ```

    結果として3.141592653589793のように円周率の値が出てきたら成功。

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
