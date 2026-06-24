ARG ATEME_NEXUS_DOCKER_HUB_PRIVATE=nexus-rennes.ateme.net:10443
ARG BASE_IMAGE=environment/base-image:2.10.0

#=========================
FROM $ATEME_NEXUS_DOCKER_HUB_PRIVATE/$BASE_IMAGE
WORKDIR /opt
RUN mkdir /opt/input
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY generate_um_export_from_pms.py .
ENTRYPOINT ["python", "/opt/generate_um_export_from_pms.py"]
CMD ["--help"]