#!/usr/bin/env python3

import argparse
import logging as log
from re import match
from os import environ as env

from github import Github
from urllib.parse import urljoin
from requests import request, exceptions

# urllib3 and github spew a lot of garbage
log.getLogger('urllib3').setLevel(log.WARN)
log.getLogger('github').setLevel(log.WARN)

class Gitea:

    def __init__(self, url, token, gh_token):
        self.url = url
        self.token = token
        self.gh_token = gh_token

    def _request(self, method, path, data=None):
        url = urljoin(self.url, path)
        headers = { 'Authorization': 'token ' + self.token }
        try:
            result = request(
                method=method,
                url=url,
                json=data,
                headers=headers,
            )
        except exceptions.ConnectionError as e:
            log.error('ConnectionError on url %s: %s', url, e)
            return None
        if result.status_code not in [200, 201, 404]:
            log.error('Request failed: %s %s (%d)', method, url, result.status_code)
            log.error('Error: %s', result.text)
            result.raise_for_status()
        return result

    def version(self):
        return self._request('GET', 'version').json()['version']

    def create_update_org(self, org):
        try:
            self.get_org(org)
        except exceptions.HTTPError as err:
            if err.response.status_code == 404:
                return self.create_org(org)
            else:
                raise
        else:
            return self.update_org(org)

    def _parse_gh_org(self, org):
        return {
          'description': org.description,
          'full_name': org.name,
          'location': org.location,
          'username': org.login,
          'website': org.blog,
          'repo_admin_change_team_access': True,
          'visibility': 'public',
        }

    def get_org(self, org):
        return self._request('GET', 'orgs/'+org.login)

    def create_org(self, org):
        return self._request('POST', 'orgs', self._parse_gh_org(org))

    def update_org(self, org):
        return self._request('PATCH', 'orgs/'+org.login, self._parse_gh_org(org))

    def create_update_repo(self, repo):
        try:
            self.get_repo(repo)
        except exceptions.HTTPError as err:
            if err.response.status_code == 404:
                return self.create_repo(repo)
            else:
                raise
        else:
            return self.update_repo(repo)

    def _parse_gh_repo(self, repo):
        data = {
          'service': 'git',
          'clone_addr': repo.clone_url,
          'description': repo.description,
          'repo_name': repo.name,
          'repo_owner': repo.owner.login,
          'private': repo.private,
          'issues': repo.has_issues,
          'wiki': repo.has_wiki,
          'website': repo.homepage,
          'labels': not list(repo.get_labels()),
          'releases': not list(repo.get_releases()),
          'mirror': True,
          'milestones': True,
          'pull_requests': True,
        }
        # Necessary to facilitate mirroring private repos
        if data['private']:
            data['auth_token'] = self.gh_token
        return data

    def get_repo(self, repo):
        return self._request('GET', 'repos/%s/%s' % (repo.owner.login, repo.name))

    def create_repo(self, repo):
        return self._request('POST', 'repos/migrate', self._parse_gh_repo(repo))

    def update_repo(self, repo):
        return self._request('PATCH', 'repos/%s/%s' % (repo.owner.login, repo.name),
                             self._parse_gh_repo(repo))


def skip_repo(name, include_regex, exclude_regex):
    if include_regex and match(include_regex, name):
        return False
    if exclude_regex and match(exclude_regex, name):
        return True
    return False


def parse_args():
    parser = argparse.ArgumentParser(
        description='Create and maintain mirrors of GitHub orgs and repos.',
        epilog='Example: ./gitea_mirror.py -T private my-org,other-org'
    )
    parser.add_argument('orgs', help='List of GitHub orgs separated by a commas.')
    parser.add_argument('-l', '--log-level', help='Logging level', default='info')
    parser.add_argument('-T', '--repo-types', help='Types of repos.', default='public')
    parser.add_argument('-i', '--include-regex', help='Regex for including repos',
                        default=env.get('REPO_INCLUDE_REGEX'))
    parser.add_argument('-e', '--exclude-regex', help='Regex for excluding repos',
                        default=env.get('REPO_EXCLUDE_REGEX'))
    parser.add_argument('-g', '--github-token', help='GitHub API token.',
                        default=env.get('GITHUB_TOKEN'))
    parser.add_argument('-t', '--gitea-token', help='Gitea API token.',
                        default=env.get('GITEA_TOKEN'))
    parser.add_argument('-u', '--gitea-url', help='Gitea API URL.',
                        default=env.get('GITEA_URL', 'http://127.0.0.1:3000/api/v1/'))
    return parser.parse_args()


def main():
    args = parse_args()
    log.root.handlers=[]
    log.basicConfig(format='%(levelname)s - %(message)s', level=args.log_level.upper())

    log.info('Gitea URL: %s', args.gitea_url)
    ga = Gitea(args.gitea_url, args.gitea_token, args.github_token)
    gh = Github(args.github_token)
    log.info('Gitea Version: %s', ga.version())

    for org_name in args.orgs.split(','):
        org = gh.get_organization(org_name)

        resp = ga.create_update_org(org)
        log.info('Org: %s', org.login)

        created, updated = 0, 0
        for repo in org.get_repos(type=args.repo_types):
            prefix = '[%s/%s]' % (org.login, repo.name)
            
            if skip_repo(repo.name, args.include_regex, args.exclude_regex):
                log.warning('%s: SKIPPING', prefix)
                continue

            log.debug('%s: GH ID: %s', prefix, repo.id)
            resp = ga.create_update_repo(repo)

            if resp.ok and resp.status_code == 201:
                created += 1
                log.debug('%s: CREATED - ID: %s', prefix, resp.json()['id'])
            elif resp.ok and resp.status_code == 200:
                updated += 1
                log.debug('%s: UPDATED - ID: %s', prefix, resp.json()['id'])
            else:
                log.error('%s: FAILURE - %s', prefix, resp.json()['error'])
                raise Exception(resp)

        log.info('Created: %s, Updated: %s', created, updated)

if __name__ == '__main__':
    main()
