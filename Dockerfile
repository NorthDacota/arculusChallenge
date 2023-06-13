FROM python:3.10-alpine

WORKDIR /source
COPY . .
RUN pip install -e .

#CMD ["sleep", "600"]
CMD ["pipeline-check", "--gitlab-host=http://gitlab-ce", "--token=glpat-yp_AY6oJrf5N2zQ_yoXU"]