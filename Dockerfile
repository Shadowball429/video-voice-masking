# ベースイメージをPython 3から選択
FROM python:3

# ルートユーザーに切り替える
USER root

# ロケールの設定
# ロケールの設定に関するステップです。日本語のUTF-8エンコーディングとタイムゾーンを設定します。
RUN apt-get update
RUN apt-get -y install locales && \
    localedef -f UTF-8 -i ja_JP ja_JP.UTF-8
ENV LANG ja_JP.UTF-8
ENV LANGUAGE ja_JP:ja
ENV LC_ALL ja_JP.UTF-8
ENV TZ JST-9
ENV TERM xterm

# 便利なツールのインストール
# vimとlessをインストールするためのステップです。
RUN apt-get install -y vim less

# Pipのアップグレード
# pipとsetuptoolsのバージョンをアップグレードします。
RUN pip install --upgrade pip
RUN pip install --upgrade setuptools

# コードのディレクトリを作成し、作業ディレクトリを設定
# /codeディレクトリを作成し、そのディレクトリを作業ディレクトリに設定します。
RUN mkdir /code
WORKDIR /code

# 依存関係のインストール
# requirements.txtファイルに記載されたPythonパッケージをインストールします。
COPY requirements.txt /code/
RUN pip install -r /code/requirements.txt

# コードのコピー
# ホストマシン上のコードをコンテナ内の/codeディレクトリにコピーします。
COPY . /code/
