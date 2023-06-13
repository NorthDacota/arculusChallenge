def issue_existed_id(project, title):
    issues = project.issues.list(state='opened', get_all=True)
    for issue in issues:
        if issue.title == title:
            return issue.id
        else:
            continue


# Send an issue in GitLab
# Next step - the func can duplicate issues. I need to fix it.
def report_problem(project, args, message, description):
    if args.report_flag:
        title = 'Job ' + str(message)
        if issue_existed_id(title) == '':
            project.issues.create({'title': title, 'description': description})
            print("Problem has been reported with the title: \n" + title)
        else:
            if not args.exporter_mode:
                print("The issue already exists")
