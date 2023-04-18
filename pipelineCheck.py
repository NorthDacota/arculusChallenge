#!/usr/bin/python3
# Author: Andrei Egorov
# Email:  anegorov777@gmail.com

import re
import getopt
import sys
import gitlab
from pathlib import Path

token_file = "./token"
default_gitlab_host = 'http://localhost/'
gitlab_host = ''
duration_limit = 600
default_project_name = 'gitlab-instance-831d1df5/mytestproject'
project_name = ''
fetch_logs = False
token = ''
unic_pipelines = []
report_flag = False
verbose = False
trigger_failed = False


###
# Print help for CLI
def usage():
    print("\nUse arguments or default variables will be set\n"
          "The script shows statuses of the last pipelines in every branch of a project\n"
          "Don't forget specify a project name and a host of gitlab\n"
          "Please put your token in file ./token_file in the same directory or use the \"token\" key "
          "(The first option should safe if you set 600 on it)\n")
    print("--gitlab_host=\n"
          "    Specify your GitLab host. Default value - localhost\n"
          "--project_name=\n"
          "    Specify your project name.\n"
          "--token=\n"
          "    Set token\n"
          "--report-problems\n"
          "    Send an issue about slow or failed jobs in the last pipelines\n"
          "--trigger-failed\n"
          "    Trigger all failed jobs in the last pipelines\n"
          "--duration_limit=\n"
          "    Any running job will be considered slow if it exceeds this limit. Default value - 600 seconds.\n"
          "--fetch-logs\n"
          "    Get logs from all failed jobs in the last pipelines. They will be stored in files of a current director"
          "y")

    print("\n")


###
# CLI options
try:
    opts, args = getopt.getopt(sys.argv[1:], "ho:v", ["help", "token=", "trigger-failed",
                                                      "duration_limit=", "fetch-logs", "gitlab_host=", "project_name=",
                                                      "report-problems"])
except getopt.GetoptError as err:
    print(err)
    usage()
    sys.exit(2)

for o, a in opts:
    if o in ("-h", "--help"):
        usage()
        sys.exit()
    elif o in "--token":
        token = str(a)
    elif o in "--fetch-logs":
        fetch_logs = True
    elif o in "--gitlab_host":
        gitlab_host = str(a)
    elif o in "--project_name":
        project_name = str(a)
    elif o in "--report-problems":
        report_flag = True
    elif o in ("-v", "--verbose"):
        verbose = True
    elif o in "--trigger-failed":
        trigger_failed = True
    elif o in "--duration_limit":
        duration_limit = int(a)

# check if a token exists
if token == '':
    try:
        token = Path('./token_file').read_text().replace('\n', '').replace('b', '')
    except Exception as e:
        print(f'Unable to get token from file.. Use --token or create token_file. Error: {e}')
        exit(1)

# Use default value if a host wasn't set
if gitlab_host == '':
    gitlab_host = default_gitlab_host
    print("Using default host: ", gitlab_host)

# Check if a project was set
if project_name == '':
    project_name = default_project_name
    print('Using default project name: ', project_name)

# Connect to GitLab
try:
    gl = gitlab.Gitlab(gitlab_host, private_token=token)
    my_project = gl.projects.get(project_name)
except Exception as e:
    print(f"I can't connect to the gitlab or get access to the project. "
          f"Check \"gitlab_host\", \"project_name\" and \"token\" params. Error:\n {e}")
    sys.exit(1)

# Check if the project is empty
pipelines = my_project.pipelines.list()
if len(pipelines) == 0:
    print("There are no pipelines in the project")
    exit(0)


# Send an issue in GitLab
def report_problem(message, description):
    if report_flag:
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
    if fetch_logs:
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
                if job.status == "running" and job.attributes['duration'] >= duration_limit:
                    slow_jobs_handler(job)
            if trigger_failed: pipeline.retry()

    else:
        continue
exit(0)
