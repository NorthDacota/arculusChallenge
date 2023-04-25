#!/usr/bin/python3
# Author: Andrei Egorov
# Email:  anegorov777@gmail.com

import re
import sys
import gitlab
from pathlib import Path
import argparse
import time
from prometheus_client import start_http_server, Gauge

parser = argparse.ArgumentParser(description='\nUse arguments or default variables will be set\n'
          'The script shows statuses of the last pipelines in every branch of a project\n'
          'Don\'t forget specify a project name and a host of gitlab\n'
          'Please put your token in file ./token_file in the same directory or use the \"token\" key '
          '(The first option should safe if you set 600 on it)')

parser.add_argument('--gitlab-host', dest='gitlab_host', type=str, default="http://localhost/",
                    help='Specify your GitLab host. Default value - localhost')

parser.add_argument('--token', type=str, default='', help='Set token')

parser.add_argument('--project-name', dest='project_name', type=str, default="gitlab-instance-831d1df5/mytestproject",
                    help='Specify your project name.')

parser.add_argument('--duration-limit', dest='duration_limit', type=int, default=600,
                    help='Any running job will be considered slow if it exceeds this limit. '
                         'Default value - 600 seconds.')

parser.add_argument('--report-problems', dest="report_flag", action='store_true', default=False,
                    help='Send an issue about slow or failed jobs in the last pipelines')

parser.add_argument('--fetch-logs', dest="fetch_logs", action='store_true', default=False,
                    help='Get logs from all failed jobs in the last pipelines. '
                         'They will be stored in files of a current directory')

parser.add_argument('--trigger-failed', dest="trigger_failed", action='store_true', default=False,
                    help='Trigger all failed jobs in the last pipelines')

parser.add_argument('--token-file', dest="token_file", type=str, default="./token_file",
                    help='Specify a token file.')

parser.add_argument('--exporter-mode', dest="exporter_mode", action='store_true', default=False,
                    help='export Prometheus metrics at 9000 port')

args = parser.parse_args()


def get_project():
    # check if a token exists
    if args.token == '':
        try:
            args.token = Path(args.token_file).read_text().replace('\n', '').replace('b', '')
        except Exception as e:
            print(f'Unable to get token from file.. Use --token or create token_file. Error: {e}')
            exit(1)
    # Connect to GitLab
    if not args.exporter_mode:
        try:
            gl = gitlab.Gitlab(args.gitlab_host, private_token=args.token)
            my_project_data = gl.projects.get(args.project_name)
        except Exception as e:
            print(f"I can't connect to the gitlab or get access to the project. "
                  f"Check \"--gitlab-host\", \"--project-name\" and \"--token\" params. Error:\n {e}")
            sys.exit(1)
    else:
        while True:
            try:
                gl = gitlab.Gitlab(args.gitlab_host, private_token=args.token)
                my_project_data = gl.projects.get(args.project_name)
            except Exception as e:
                print(f"I can't connect to the gitlab or get access to the project. "
                      f"Check \"--gitlab-host\", \"--project-name\" and \"--token\" params. Error:\n {e}"
                      f"Keep trying...\n")
                connection_gitlab_monitor.labels(host=args.gitlab_host).set(0)
                time.sleep(10)
            else:
                connection_gitlab_monitor.labels(host=args.gitlab_host).set(1)
                break
    # Check if the project is empty
    if len(my_project_data.pipelines.list(get_all=True)) == 0:
        print("There are no pipelines in the project")
        exit(0)
    return my_project_data


# Send an issue in GitLab
# Next step - the func can duplicate issues. I need to fix it.
def report_problem(message, description):
    if args.report_flag:
        title = 'Job ' + str(message)
        report_to_project = my_project.issues.create({'title': title, 'description': description})
        print("Problem has been reported with the title: \n" + title)


# Print description of a job
def print_job_stat(job):
    if not args.exporter_mode:
        print('====================================================')
        print("    Job ID: ", job.id, "Job Name: ", job.name)
        print("    JOB STATUS: ", job.status)
        print("    STAGE: ", job.stage)
        print(("URL: ", job.attributes['web_url']))


# Print description of a pipeline
def print_pipe_stat(pipeline):
    if not args.exporter_mode:
        print("\nBRANCH: ", pipeline.attributes['ref'])
        print("Pipeline ID: ", pipeline.id)
        print("STATUS: ", pipeline.status)


# Gitlab returns a log with colors which should be deleted, or we get unreadable log
def escape_ansi(line):
    ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', line)


# Show the last five strings of a log. Save it in files if the fetch_logs flag was set.
def get_trace(id):
    if not args.exporter_mode:
        thejob = my_project.jobs.get(id)
        log_data = escape_ansi(thejob.trace().decode("ascii"))
        last_log = log_data.split('\n')
        separator = "\n    "
        print("    TRACE:\n    ", separator.join(last_log[-5:]))
        if args.fetch_logs:
            filename = str(thejob.id) + '.log'
            logfile = open(filename, "w")
            logfile.write(log_data)


# Print details about a failed job and send an issue about it.
def failed_jobs_handler(job):
    print_job_stat(job)
    get_trace(job.id)
    message = str(job.name) + ' at ' + str(job.stage) + " stage " + "failed. "
    description = str(job.id) + " " + job.attributes['web_url']
    report_problem(message, description)


# Print details about a slow job and send an issue about it. A job is considered slow if its time exceeds the set limit.
def slow_jobs_handler(job, pending=False):
    print_job_stat(job)
    if pending:
        duration_attribute = 'queued_duration'
        job_status_for_message = " pending too long"
    else:
        duration_attribute = 'duration'
        job_status_for_message = " too slow"
    print("    The job is",job_status_for_message,': ', str(job.attributes[duration_attribute]) + "sec")
    get_trace(job.id)
    message = str(job.name) + ' at ' + str(job.stage) + " stage is" +\
              job_status_for_message + ". Duration: " + str(job.attributes[duration_attribute])
    description = str(job.id) + " " + job.attributes['web_url']
    report_problem(message, description)


# It takes only the last pipeline in each branch and if the pipeline has a problem makes a report
def check_pipelines(pipelines):
    last_pipelines = []
    for pipeline in pipelines:
        if pipeline.attributes['ref'] not in last_pipelines:
            last_pipelines.append(pipeline.attributes['ref'])
            if args.exporter_mode:
                pipeline_metrics.labels(id=pipeline.id, status=pipeline.status, branch=pipeline.attributes['ref'],
                                        project=my_project.name).set(1)
            print_pipe_stat(pipeline)

            jobs = pipeline.jobs.list()
            for job in jobs:
                if job.status == "failed":
                    failed_jobs_handler(job)
                if job.status == "running" and job.attributes['duration'] <= args.duration_limit:
                    print_job_stat(job)
                if job.status == "running" and job.attributes['duration'] >= args.duration_limit:
                    slow_jobs_handler(job)
                if job.status == "pending" and job.attributes['queued_duration'] >= args.duration_limit:
                    slow_jobs_handler(job, pending=True)
                if args.exporter_mode:
                    job_metric.labels(name=job.name, id=job.id, status=job.status, duration=job.attributes['duration'],
                                      stage=job.stage, pipeline=job.pipeline["id"]).set(1)
                    job_duration.labels(name=job.name, id=job.id, status=job.status, stage=job.stage,
                                        pipeline=job.pipeline["id"]).set(( job.attributes['duration'] or 0))


            if args.trigger_failed:
                pipeline.retry()
    if args.exporter_mode:
        time.sleep(3)


if args.exporter_mode:
    pipeline_metrics = Gauge('gitlab_last_pipeline_in_branch', 'show last pipeline in each brunch',
                             ["id", "status", "branch", "project"])
    job_metric = Gauge('gitlab_job_of_last_pipelines', 'shows only last jobs. Gaps are possible',
                             ["name", "id", "status", "duration", "stage", "pipeline"])
    job_duration = Gauge('gitlab_job_of_last_pipelines_duration', 'duration is seconds',
                             ["name", "id", "status", "stage", "pipeline"])
    connection_gitlab_monitor = Gauge('gitlab_connection_established',
                                      'equal to 1 if the connection is established successfully', ["host"])

    start_http_server(9000)
    print("Metrics are available at 9000 port...")

    while True:
        my_project = get_project()
        pipelines_data = get_project().pipelines.list(get_all=True)
        pipeline_metrics.clear()
        check_pipelines(pipelines_data)
else:
    my_project = get_project()
    pipelines_data = get_project().pipelines.list(get_all=True)
    check_pipelines(pipelines_data)
    exit(0)