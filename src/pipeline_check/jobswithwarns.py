import re


class JobsWithWarns:
    def __init__(self, pipeline, args):
        self._all_jobs = pipeline.jobs.list(get_all=True)
        self._args = args
        self.items = self.all_jobs_handler()
        self.warns = self.get_jobs_stat()

    def get_jobs_stat(self):
        all_jobs_with_warns_stat = []
        for job in self.items:
            stat = {
                'Name': job.name,
                'Stage': job.stage,
                'ID': job.id,
                'Status': job.status,
                'Duration': job.attributes['duration'],
                'URL': job.attributes['web_url']
                #'Issue:'
                #'Log':

            }
            all_jobs_with_warns_stat.append(stat)
        return all_jobs_with_warns_stat

    def all_jobs_handler(self):
        jobs_with_warnings = []
        for job in self._all_jobs:
            if job.status == "failed":
                jobs_with_warnings.append(job)
            if job.status == "running" and job.attributes['duration'] <= self._args.duration_limit:
                jobs_with_warnings.append(job)
            if job.status == "running" and job.attributes['duration'] >= self._args.duration_limit:
                jobs_with_warnings.append(job)
            if job.status == "pending" and job.attributes['queued_duration'] >= self._args.duration_limit:
                jobs_with_warnings.append(job)
        return jobs_with_warnings
        #if args.trigger_failed:
        #    pipeline.retry()


'''
    def _escape_ansi(line):
        ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
        return ansi_escape.sub('', line)

    # Show the last five strings of a log. Save it in files if the fetch_logs flag was set.
    def _get_trace(self, id):
        if not self._args.exporter_mod:
            the_job = self._my_project.jobs.get(id)
            log_data = _escape_ansi(the_job.trace().decode("ascii"))
            last_log = log_data.split('\n')
            separator = "\n    "
            print("    TRACE:\n    ", separator.join(last_log[-5:]))
            if self._args.fetch_logs:
                filename = str(the_job.id) + '.log'
                logfile = open(filename, "w")
                logfile.write(log_data)

    def failed_jobs_handler(self, job):
        get_trace(job.id)
        message = str(job.name) + ' at ' + str(job.stage) + " stage " + "failed. "
        description = str(job.id) + " " + job.attributes['web_url']
        report_problem(message, description)
        return get_job_stat(self, job)

    # Print details about a slow job and send an issue about it. A job is considered slow if its time exceeds the set limit.
    def slow_jobs_handler(job, pending=False):
        print_job_stat(job)
        if pending:
            duration_attribute = 'queued_duration'
            job_status_for_message = " pending too long"
        else:
            duration_attribute = 'duration'
            job_status_for_message = " too slow"
        print("    The job is", job_status_for_message, ': ', str(job.attributes[duration_attribute]) + "sec")
        get_trace(job.id)
        message = str(job.name) + ' at ' + str(job.stage) + " stage is" + job_status_for_message
        description = str(job.id) + " " + job.attributes['web_url'] + ". Duration: " + str(job.attributes[duration_attribute])
        report_problem(message, description)
'''
'''            if args.exporter_mode:
                job_metric.labels(name=job.name, id=job.id, status=job.status, duration=job.attributes['duration'],
                                  stage=job.stage, pipeline=job.pipeline["id"]).set(1)
                job_duration.labels(name=job.name, id=job.id, status=job.status, stage=job.stage,
                                    pipeline=job.pipeline["id"]).set((job.attributes['duration'] or 0))'''