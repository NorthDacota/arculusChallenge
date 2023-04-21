#!/usr/bin/python3
# Author: Andrei Egorov
# Email:  anegorov777@gmail.com

import re
import getopt
import sys
import gitlab
from pathlib import Path
import argparse

unic_pipelines = []

parser = argparse.ArgumentParser(description='\nUse arguments or default variables will be set\n'
          'The script shows statuses of the last pipelines in every branch of a project\n'
          'Don\'t forget specify a project name and a host of gitlab\n'
          'Please put your token in file ./token_file in the same directory or use the \"token\" key '
          '(The first option should safe if you set 600 on it)')

parser.add_argument('--gitlab_host', dest='gitlab_host', type=str, default="http://localhost/",
                    help='Specify your GitLab host. Default value - localhost')

parser.add_argument('--token', type=str, default='', help='Set token')

parser.add_argument('--project_name', type=str, default="gitlab-instance-831d1df5/mytestproject",
                    help='Specify your project name.')

parser.add_argument('--duration_limit', type=int, default=600,
                    help='Any running job will be considered slow if it exceeds this limit. '
                         'Default value - 600 seconds.')

parser.add_argument('--report-problems', dest="report_flag", action='store_true', default=False,
                    help='Send an issue about slow or failed jobs in the last pipelines')

parser.add_argument('--fetch-logs', dest="fetch_logs", action='store_true', default=False,
                    help='Get logs from all failed jobs in the last pipelines. '
                         'They will be stored in files of a current directory')

parser.add_argument('--trigger-failed', dest="trigger_failed", action='store_true', default=False,
                    help='Trigger all failed jobs in the last pipelines')

parser.add_argument('--token_file', dest="token_file", type=str, default="./token_file",
                    help='Specify a token file.')

args = parser.parse_args()

# check if a token exists
if args.token == '':
    try:
        args.token = Path(args.token_file).read_text().replace('\n', '').replace('b', '')
    except Exception as e:
        print(f'Unable to get token from file.. Use --token or create token_file. Error: {e}')
        exit(1)

# Connect to GitLab
try:
    gl = gitlab.Gitlab(args.gitlab_host, private_token=args.token)
    my_project = gl.projects.get(args.project_name)
except Exception as e:
    print(f"I can't connect to the gitlab or get access to the project. "
          f"Check \"--gitlab-host\", \"--project-name\" and \"--token\" params. Error:\n {e}")
    sys.exit(1)

# Check if the project is empty
pipelines = my_project.pipelines.list(get_all=True)
if len(pipelines) == 0:
    print("There are no pipelines in the project")
    exit(0)


# Send an issue in GitLab
def report_problem(message, description):
    if args.report_flag:
        title = 'Job ' + str(message)
        report_to_project = my_project.issues.create({'title': title, 'description': description})
        print("Problem has been reported with the title: \n" + title)

# Print description of a job
def print_job_stat(job):
    print('====================================================')
    print("    Job ID: ", job.id, "Job Name: ", job.name, "Stage:", job.stage)
    print("    JOB STATUS: ", job.status)
    print("    IMPACTED STAGE: ", job.stage)
    print(("URL: ", job.attributes['web_url']))


# Print description of a pipeline
def print_pipe_stat(pipeline):
    print("\nBRANCH: ", pipeline.attributes['ref'])
    print("Pipeline ID: ", pipeline.id)
    print("STATUS: ", pipeline.status)


# Gitlab returns a log with colors which should be deleted, or we get unreadable log
def escape_ansi(line):
    ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', line)


# Show the last five strings of a log. Save it in files if the fetch_logs flag was set.
def get_trace(id):
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
def slow_jobs_handler(job):
    print_job_stat(job)
    print("    The job is slow: ", job.attributes['duration'] + "sec")
    get_trace(job.id)
    message = str(job.name) + ' at ' \
              + str(job.stage) + " stage " + "is slow. Duration: " + str(job.attributes['duration'])
    description = str(job.id) + " " + job.attributes['web_url']
    report_problem(message, description)

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
for pipeline in pipelines:
    if pipeline.attributes['ref'] not in unic_pipelines:
        unic_pipelines.append(pipeline.attributes['ref'])
        print_pipe_stat(pipeline)
        # dive deeper if it's not successfully
        if pipeline.status != 'success':
            jobs = pipeline.jobs.list()
            for job in jobs:
                if job.status == "failed":
                    failed_jobs_handler(job)
                if job.status == "running" and job.attributes['duration'] >= args.duration_limit:
                    slow_jobs_handler(job)
                if job.status == "pending" and job.attributes['queued_duration'] >= args.duration_limit:
                    slow_jobs_handler(job, pending=True)
            if args.trigger_failed: pipeline.retry()

    else:
        continue
exit(0)
