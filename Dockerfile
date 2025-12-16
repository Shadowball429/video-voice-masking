# uv+pythonの公式イメージ
FROM ghcr.io/astral-sh/uv:0.9.2-python3.12-bookworm-slim

# ルートユーザーに切り替える
USER root

# ロケールの設定
# ロケールの設定に関するステップです。日本語のUTF-8エンコーディングとタイムゾーンを設定します。
RUN apt-get update
RUN apt-get -y install locales ffmpeg build-essential libsndfile1 && \
    localedef -f UTF-8 -i ja_JP ja_JP.UTF-8
ENV LANG=ja_JP.UTF-8
ENV LANGUAGE=ja_JP:ja
ENV LC_ALL=ja_JP.UTF-8
ENV TZ=JST-9
ENV TERM=xterm

# コードのディレクトリを作成し、作業ディレクトリを設定
# /codeディレクトリを作成し、そのディレクトリを作業ディレクトリに設定します。
RUN mkdir /code
WORKDIR /code

# プロジェクト設定とロックファイルを先に配置し、依存解決だけ先行させる
COPY pyproject.toml uv.lock ./
# パッケージ実体も置いて uv がプロジェクトを認識できるようにする
COPY docker_python ./docker_python
# pyproject からロックを生成（ローカルの uv.lock を使いつつ不整合を防ぐ）
RUN uv lock
# ロックに従って依存を同期（アプリ本体のインストールは行わない）
RUN uv sync --no-install-project
ENV PATH="/code/.venv/bin:${PATH}"

# コードのコピー
# ホストマシン上のコードをコンテナ内の/codeディレクトリにコピーします。
COPY . /code/
