
import sys
import os
import shutil
import git as git

from makefile_parser.makefile_parser import MakefileParser

class SearchUpdate(object):

    work_dir = 'work'

    def __init__(self, package, path):
        self._package = package
        self._path = path
        self._work_dir = os.path.join(SearchUpdate.work_dir, package)

        self._parser = MakefileParser()
        self._parser.parse_file(path)


    def _generate_regex_version(self, version):
        prefix_parts = version.split('-')
        #regex_version =
        #local regexVersionPackageVersion=$(echo $version | sed -e 's/\./\\./g' -e 's/[0-9]\+/(\\\\d+)/g' -e 's/-\w\+$/(-[\\\\w]+)?/')


    def get_url(self):
        url = self._parser.get_var('PKG_DIST_SITE')
        if url is not None:
            url_file = self._parser.get_var('PKG_DIST_NAME')
            if url_file is not None:
                url[0] += '/' + url_file[0]

            return url[0]

        return None


    def get_version(self):
        version = self._parser.get_var('PKG_VERS')
        if version is None:
            version = self._parser.get_var('PKG_VERS_MAJOR')

            if version is not None:
                version_minor = self._parser.get_var('PKG_VERS_MINOR')
                if version_minor is not None:
                    version[0] += '.' + version_minor[0]
                    version_patch = self._parser.get_var('PKG_VERS_PATCH')
                    if version_patch is not None:
                        version[0] += '.' + version_patch[0]
                version = version[0]
        else:
            version = version[0]

        return version


    def _search_updates_git(self):
        url = self.get_url()


        git_path = os.path.join(self._work_dir, 'git')
        git_hash = self._parser.get_var('PKG_GIT_HASH', ['master'])[0]

        git_is_cloned = os.path.join(self._work_dir, '.git_clone')
        if not os.path.exists(git_is_cloned):
            if os.path.exists(git_path):
                shutil.rmtree(git_path)

            try:
                git.Repo.clone_from(url, git_path)
            except git.GitCommandError as exception:
                print("[" + self._package + "] Error to clone git: " + url)
                pass
            open(git_is_cloned, 'w').close()

        repo = git.Repo(git_path)
        for remote in repo.remotes:
            remote.fetch()
            remote.pull()

        new_versions = []

        tags = repo.tags
        if len(tags) > 0:
            # Has tag: List new tags
            tags.sort(key=lambda t: t.commit.committed_datetime)
            for c in repo.iter_commits(git_hash + '..HEAD'):
                tag = next((tag for tag in repo.tags if tag.commit == c), None)
                if tag is not None:
                    new_versions.append(str(tag))
        else:
            # No tags: list new commits
            for c in repo.iter_commits(git_hash + '..HEAD'):
                new_versions.append(str(c))

        return new_versions


    def _search_updates_svn(self):
        url = self.get_url()

        svn_path = os.path.join(self._work_dir, 'svn')
        svn_rev = self._parser.get_var('PKG_SVN_REV', ['HEAD'])[0]

        if not os.path.exists(svn_path):
            os.mkdir(svn_path)


    def _search_updates_file(self):
        url = self.get_url()
        url = self.get_url()
        version = self.get_version()

        print('url')
        print(url)


    def search_updates(self):

        if not os.path.exists(self._work_dir):
            os.makedirs(self._work_dir)

        method = self._parser.get_var('PKG_DOWNLOAD_METHOD', ['file'])[0]
        func_name = '_search_updates_' + method
        try:
            func = getattr(self, func_name)
            print(func())
        except:
            print('Method ' + func_name + ' has not found')




