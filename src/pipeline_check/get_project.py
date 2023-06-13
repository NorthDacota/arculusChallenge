from pathlib import Path
import gitlab
import sys
import time


def get_project(args, connection_gitlab_monitor=None):
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
            print("Using project name: ", args.project_name)
            my_project_data = gl.projects.get(args.project_name)
        except Exception as e:
            print(f"I can't connect to the gitlab or get access to the project. "
                  f"Check \"--gitlab-host\", \"--project-name\" and \"--token\" params. Error:\n {e}")
            sys.exit(1)
    else:
        while True:
            try:
                gl = gitlab.Gitlab(args.gitlab_host, private_token=args.token)
                print("Using project name: ", args.project_name)
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
    if len(my_project_data.items.list(get_all=True)) == 0:
        print("There are no pipelines in the project")
        exit(0)
    return my_project_data
