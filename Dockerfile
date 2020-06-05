FROM continuumio/miniconda3
ENV PYTHONDONTWRITEBYTECODE 1

MAINTAINER Victor Ng <vng@mozilla.com> 
# add a non-privileged user for installing and running
# the application
RUN groupadd --gid 10001 app && \
    useradd --uid 10001 --gid 10001 --home /app --create-home app 

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gettext curl \
                                               libopenblas-dev libatlas3-base gfortran && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# First copy requirements.txt so we can take advantage of docker
# caching.
COPY . /app

RUN make setup_conda

RUN . /opt/conda/etc/profile.d/conda.sh && \
    conda activate taar-37 && \
    python setup.py install

USER app

ENV TAAR_API_PLUGIN=taar.plugin
ENV TAAR_ITEM_MATRIX_BUCKET=telemetry-public-analysis-2
ENV TAAR_ITEM_MATRIX_KEY=telemetry-ml/addon_recommender/item_matrix.json
ENV TAAR_ADDON_MAPPING_BUCKET=telemetry-public-analysis-2
ENV TAAR_ADDON_MAPPING_KEY=telemetry-ml/addon_recommender/addon_mapping.json
ENV TAAR_ENSEMBLE_BUCKET=telemetry-parquet
ENV TAAR_ENSEMBLE_KEY=taar/ensemble/ensemble_weight.json
ENV TAAR_WHITELIST_BUCKET=telemetry-parquet
ENV TAAR_WHITELIST_KEY=telemetry-ml/addon_recommender/only_guids_top_200.json
ENV TAAR_LOCALE_BUCKET=telemetry-parquet
ENV TAAR_LOCALE_KEY=taar/locale/top10_dict.json
ENV TAAR_SIMILARITY_BUCKET=telemetry-parquet
ENV TAAR_SIMILARITY_DONOR_KEY=taar/similarity/donors.json
ENV TAAR_SIMILARITY_LRCURVES_KEY=taar/similarity/lr_curves.json
ENV TAAR_MAX_RESULTS=10
ENV AWS_SECRET_ACCESS_KEY=
ENV AWS_ACCESS_KEY_ID=
ENV BIGTABLE_PROJECT_ID=
ENV BIGTABLE_INSTANCE_ID=
ENV BIGTABLE_TABLE_ID=

# Using /bin/bash as the entrypoint works around some volume mount issues on Windows
# where volume-mounted files do not have execute bits set.
# https://github.com/docker/compose/issues/2301#issuecomment-154450785 has additional background.
ENTRYPOINT ["/bin/bash", "/app/bin/run"]

# bin/run supports web|web-dev|test options
CMD ["web"]
