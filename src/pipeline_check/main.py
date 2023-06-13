import argparse
from prometheus_client import start_http_server, Gauge
from .get_project import get_project
from .pipelines import PipeLines, get_stat
from .jobswithwarns import JobsWithWarns


parser = argparse.ArgumentParser(description='\nUse arguments or default variables will be set\n'
          'The script shows statuses of the last pipelines in every branch of a project\n'
          'Don\'t forget specify a project name and a host of gitlab\n'
          'Please put your token in file ./token_file in the same directory or use the \"token\" key '
          '(The first option should safe if you set 600 on it)')

parser.add_argument('--gitlab-host', dest='gitlab_host', type=str, default="http://localhost/",
                    help='Specify your GitLab host. Default value - localhost')

parser.add_argument('--token', type=str, default='', help='Set token')

parser.add_argument('--project-name', dest='project_name', type=str, default="gitlab-instance-e85cba46/justforfun",
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


'''# Print description of a job
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

'''
# Gitlab returns a log with colors which should be deleted, or we get unreadable log


'''def pipeline_handler(pipeline):
    if args.exporter_mode:
        pipeline_metrics.labels(id=pipeline.id, status=pipeline.status, branch=pipeline.attributes['ref'],
                                project=my_project.name).set(1)
    print_pipe_stat(pipeline)

'''

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
    general_statistics = []
    my_project = get_project(args)
    pipelines = PipeLines(my_project)

    for pipeline in pipelines.items:
        stat = get_stat(pipeline)
        jobs = JobsWithWarns(pipeline, args)
        if jobs.warns:
            stat["Jobs"] = jobs.warns
        general_statistics.append(stat)

    print(general_statistics)
    if not args.exporter_mode:
        exit(0)