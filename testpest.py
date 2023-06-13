import gitlab
from src.pipeline_check.pipelines import PipeLines, get_stat
from src.pipeline_check.jobswithwarns import JobsWithWarns
import json


# create a GitLab connection object
gl = gitlab.Gitlab('http://localhost:8080', private_token='glpat-yp_AY6oJrf5N2zQ_yoXU')

# get the project you want to monitor
project = gl.projects.get('gitlab-instance-e85cba46/justforfun')
#x= PipeLines(project)
#print(x.items)
#x = PipeLines(project).get_stat()
#print(json.dumps(x, indent=1))

general_statistics = []
pipelines = PipeLines(project)
args = None
for pipeline in pipelines.items:
    stat = get_stat(pipeline)
    jobs = JobsWithWarns(pipeline, args)
    if jobs.warns:
        stat["Jobs"] = jobs.warns
    general_statistics.append(stat)

print(json.dumps(general_statistics, indent=1))

'''branch_name = 'master'
# get the most recent pipeline for the project
pipelines = project.pipelines.list()
branches = project.branches.list()
for i in branches:
    if i.merged :print(i.name)
p = project.branches.get('master')
exit(0)
'''

'''
docker run \
    -p 9090:9090 \
    -v /home/alterego/pipelineMonitor/prometheus:/etc/prometheus/ \
    prom/prometheus
'''