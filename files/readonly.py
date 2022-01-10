#!/usr/bin/env python3

import argparse
import logging as log
from re import match
from os import environ as env
from github import Github

# urllib3 and github spew a lot of garbage
log.getLogger('urllib3').setLevel(log.WARN)
log.getLogger('github').setLevel(log.WARN)


def skip_repo(name, include_regex, exclude_regex):
    if include_regex and match(include_regex, name):
        return False
    if exclude_regex and match(exclude_regex, name):
        return True
    return False


def parse_args():
    parser = argparse.ArgumentParser(
        description='Grant ONLY read-only rights to all repos to given user.',
        epilog='Example: ./readonly.py -T all -u example-user my-org'
    )
    parser.add_argument('orgs', help='List of GitHub orgs separated by a commas.')
    parser.add_argument('-u', '--github-user', help='Name of user.', required=True)
    parser.add_argument('-l', '--log-level', help='Logging level', default='info')
    parser.add_argument('-T', '--repo-types', help='Types of repos.', default='public')
    parser.add_argument('-i', '--include-regex', help='Regex for including repos',
                        default=env.get('REPO_INCLUDE_REGEX'))
    parser.add_argument('-e', '--exclude-regex', help='Regex for excluding repos',
                        default=env.get('REPO_EXCLUDE_REGEX'))
    parser.add_argument('-g', '--github-token', help='GitHub API token.',
                        default=env.get('GITHUB_TOKEN'), required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    log.root.handlers=[]
    log.basicConfig(format='%(levelname)7s - %(message)s', level=args.log_level.upper())

    gh = Github(args.github_token)
    admin = gh.get_user()
    log.info('GitHub token user: %s (ID: %d)', admin.login, admin.id)

    user = gh.get_user(args.github_user)
    log.info('GitHub user to add: %s (ID: %d)', user.login, user.id)

    for org_name in args.orgs.split(','):
        org = gh.get_organization(org_name)
        log.info('Org: %s', org.login)
        try:
            bots = org.get_team_by_slug('bots')
        except:
            bots = None

        org.add_to_members(user)

        created, updated = 0, 0
        for repo in org.get_repos(type=args.repo_types):
            prefix = '[%s/%s]' % (org.login, repo.name)
            log.info('%s: ID=%d (%s)', prefix, repo.id,
                     ("private" if repo.private else "public"))

            if repo.archived:
                log.debug('%s: ARCHIVED', prefix)
                continue
            # Temporary private fork for security advisory.
            if repo.private and not repo.has_issues:
                log.debug('%s: TEMPORARY', prefix)
                continue
            if skip_repo(repo.name, args.include_regex, args.exclude_regex):
                log.warning('%s: SKIPPING', prefix)
                continue

            perms = repo.get_collaborator_permission(user)
            if perms == 'read':
                log.debug('%s: ALREADY READ', prefix)
                continue
            elif perms == 'write':
                bots_perms = bots.get_repo_permission(repo)
                if bots_perms and bots_perms.push:
                    log.info('%s: BOTS GROUP', prefix)
                    continue
            elif perms == 'write':
                log.info('%s: REMOVING WRITE', prefix)
                repo.remove_from_collaborators(user)
                perms = 'none'
            if perms == 'none':
                log.info('%s: ADDING READ', prefix)
                repo.add_to_collaborators(user, 'pull')


if __name__ == '__main__':
    main()
