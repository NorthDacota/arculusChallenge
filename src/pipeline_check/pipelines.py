def get_stat(pipeline):
    single_stat = {
        'Type': 'pipeline',
        'Id': pipeline.id,
        'Brunch': pipeline.attributes['ref'],
        'Status': pipeline.status
    }
    return single_stat


class PipeLines:
    def __init__(self, my_project):
        self._project = my_project
        self.items = self.get_current_pipelines()

    # Get list of not closed\merged branches
    def _get_branches_list(self):
        actual_branches = []
        branches = self._project.branches.list(get_all=True)
        for branch in branches:
            if not branch.merged:
                actual_branches.append(branch.name)
        return actual_branches

    def get_current_pipelines(self):
        current_pipelines = []
        branch_list = self._get_branches_list()
        for branch in branch_list:
            if self._project.pipelines.list(ref=branch, get_all=True):
                current_pipelines.append(self._project.pipelines.list(ref=branch, get_all=True)[0])
        return current_pipelines
