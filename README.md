# Description

This role deploys a timer and script for mirroring repositories from [GitHub](https://github.com/) in [Gitea](https://gitea.io/).

# Configuration

```yaml
# Timer service
gitea_mirrors_log_level: 'debug'
gitea_mirrors_timer_frequency: 'weekly'
gitea_mirrors_timer_timeout_sec: 6000
# API Access
gitea_mirror_api_endpoint: 'http://10.1.2.3:4444/api/v1'
gitea_mirror_api_token: 'super-secret-gitea-api-token'
gitea_mirror_gh_api_token: 'super-secret-github-api-token'
```

# Scripts

The main python script does the work of querying GitHub API and mirroring or updating organizations and repositories via Gitea API.

```txt
usage: mirror.py [-h] [-l LOG_LEVEL] [-T REPO_TYPES] [-i INCLUDE_REGEX] [-e EXCLUDE_REGEX] [-g GITHUB_TOKEN] [-t GITEA_TOKEN] [-u GITEA_URL] orgs

Create and maintain mirrors of GitHub orgs and repos.

positional arguments:
  orgs                  List of GitHub orgs separated by a commas.

optional arguments:
  -h, --help            show this help message and exit
  -l LOG_LEVEL, --log-level LOG_LEVEL
                        Logging level
  -T REPO_TYPES, --repo-types REPO_TYPES
                        Types of repos.
  -i INCLUDE_REGEX, --include-regex INCLUDE_REGEX
                        Regex for including repos
  -e EXCLUDE_REGEX, --exclude-regex EXCLUDE_REGEX
                        Regex for excluding repos
  -g GITHUB_TOKEN, --github-token GITHUB_TOKEN
                        GitHub API token.
  -t GITEA_TOKEN, --gitea-token GITEA_TOKEN
                        Gitea API token.
  -u GITEA_URL, --gitea-url GITEA_URL
                        Gitea API URL.

Example: ./gitea_mirror.py -T private my-org,other-or
```

There is also a [`files/readonly.py`](./files/readonly.py) script which allows you to easilly add the user who's token will be used to run the mirroring script to all organization repositories with read-only permissions exclusively.
