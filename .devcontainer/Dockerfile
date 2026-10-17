FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye

# Defects4J ve C/C++ AST araçları için gerekli sistem paketleri (Java, Perl, Git, GCC)
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
        openjdk-11-jdk \
        perl \
        cpanminus \
        build-essential \
        git \
        curl \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Hızlı Python paket yöneticisi 'uv' kurulumu
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Defects4J kurulumu (Proje bazlı testler için hazır gelir)
WORKDIR /opt
RUN git clone https://github.com/rjust/defects4j.git \
    && cd defects4j \
    && cpanm --installdeps . \
    && ./init.sh
ENV PATH="/opt/defects4j/framework/bin:${PATH}"

WORKDIR /workspace