
import sys
import os
import shutil
import re
import time
import copy
import logging
import collections

import git as git
import svn as svn
import svn.remote
import svn.local
import requests
from ftplib import FTP

from urllib.parse import urlparse
from urllib.parse import ParseResult
from pkg_resources import parse_version
from bs4 import BeautifulSoup

from makefile_parser.makefile_parser import MakefileParser

_LOGGER = logging.getLogger(__name__)

class SearchUpdate(object):

    work_dir = 'work'

    delay_cache = 24 * 3600

    def __init__(self, package, path):
        self._use_cache = True
        self._package = package
        self._path = path
        self._work_dir = os.path.join(SearchUpdate.work_dir, package)
        self._urls_list = []

        _LOGGER.debug("__init__: path: %s" % (path,))
        self._parser = MakefileParser()
        self._parser.parse_file(path)

    def print(self, message):
        print("[" + self._package + "] " + message)


    def enable_cache(self):
        self._use_cache = True


    def disable_cache(self):
        self._use_cache = False


    def _generate_regex_version(self, version):

        tmp_parser = copy.copy(self._parser)
        tmp_parser.set_var_values('PKG_VERS', 'XXXVERXXX')
        tmp_parser.evaluate_var('PKG_DIST_NAME')
        filename = tmp_parser.get_var_values('PKG_DIST_NAME')

        regex_version = '([0-9]+((?P<sep>[._-])([0-9a-zA-Z]+))*(-\w+)*)'
        regex_filename = '(' + re.escape(filename[0]).replace('XXXVERXXX', regex_version) + ')'
        regex_filename = re.sub('(\\\.tar\\\.lz|\\\.tar\\\.bz2|\\\.tar\\\.gz|\\\.tar\\\.xz|\\\.tar\\\.bz2|\\\.zip|\\\.rar|\\\.tgz)', '\.(tar\.lz|tar\.bz2|tar\.gz|tar\.xz|tar\.bz2|zip|rar|tgz)', regex_filename)
        _LOGGER.debug("_generate_regex_version: regex_filename: %s" % (regex_filename,))

        return re.compile(regex_filename)


    def get_url(self):
        url = self._parser.get_var_values('PKG_DIST_SITE')
        if url is not None:
            url_file = self._parser.get_var_values('PKG_DIST_NAME')
            if url_file is not None:
                url[0] += '/' + url_file[0]

            return url[0]

        return None


    def get_version(self):
        version = self._parser.get_var_values('PKG_VERS')
        if version is None:
            version = self._parser.get_var_values('PKG_VERS_MAJOR')

            if version is not None:
                version_minor = self._parser.get_var_values('PKG_VERS_MINOR')
                if version_minor is not None:
                    version[0] += '.' + version_minor[0]
                    version_patch = self._parser.get_var_values('PKG_VERS_PATCH')
                    if version_patch is not None:
                        version[0] += '.' + version_patch[0]
                version = version[0]
        else:
            version = version[0]

        return version



    def _search_updates_git(self):
        url = self.get_url()

        git_path = os.path.join(self._work_dir, 'git')
        git_hash = self._parser.get_var_values('PKG_GIT_HASH', ['master'])[0]

        _LOGGER.info("Current git hash: %s" % (git_hash,))

        git_is_cloned = os.path.join(self._work_dir, '.git_clone')
        if not os.path.exists(git_is_cloned):
            if os.path.exists(git_path):
                shutil.rmtree(git_path)

            self.print("Clone repository: " + url)
            try:
                git.Repo.clone_from(url, git_path)
            except git.GitCommandError as exception:
                self.print("Error to clone git")
                return
            open(git_is_cloned, 'w').close()
            self.print("Repository cloned")


        self.print("Fetch and pull git")
        repo = git.Repo(git_path)
        for remote in repo.remotes:
            remote.fetch()
            remote.pull()

        new_versions = []

        tags = repo.tags
        if len(tags) > 0:
            # Has tag: List new tags
            self.print("Has tags: Get new versions from tags")
            tags.sort(key=lambda t: t.commit.committed_datetime)
            for c in repo.iter_commits(git_hash + '..HEAD'):
                tag = next((tag for tag in repo.tags if tag.commit == c), None)
                if tag is not None:
                    new_versions.append(str(tag))
        else:
            # No tags: list new commits
            self.print("No tags: Get new versions from commits")
            for c in repo.iter_commits(git_hash + '..HEAD'):
                new_versions.append(str(c))

        return new_versions


    def _search_updates_svn(self):
        url = self.get_url()

        svn_path = os.path.join(self._work_dir, 'svn')
        svn_rev = self._parser.get_var_values('PKG_SVN_REV')
        svn_rev_next = 'HEAD'
        if svn_rev is not None:
            svn_rev = svn_rev[0]
            svn_rev_next = int(svn_rev) + 1
        else:
            svn_rev = 'HEAD'

        self.print("Current svn revision: " + svn_rev)


        svn_is_checkout = os.path.join(self._work_dir, '.svn_checkout')
        if not os.path.exists(svn_is_checkout):
            if os.path.exists(svn_path):
                shutil.rmtree(svn_path)

            self.print("Checkout repository: " + url)
            try:
                repo = svn.remote.RemoteClient(url)
                repo.checkout(svn_path)
            except:
                self.print("Error to checkout svn")
                return
            open(svn_is_checkout, 'w').close()
            self.print("Repository checkout")


        repo = svn.local.LocalClient(svn_path)

        self.print("Update svn")
        repo.update()

        new_versions = []

        self.print("Get new revisions in /tags directory")
        tags_rev = repo.log_default(None, None, None, '^/tags', None, svn_rev_next, None)
        for rev in tags_rev:
            new_versions.insert(0, str(rev.revision))

        return new_versions


    def _search_updates_ftp(self):
        url = self.get_url()
        version = self.get_version()
        version_p = parse_version(version)

        self.print("Current version: " + version)

        url_splitted = url.split('/')
        filename = url_splitted[-1]
        url_to_request = '/'.join(url_splitted[:-1])

        self.print("Download ftp list from parent url: " + url_to_request)

        url_to_request_p = urlparse(url_to_request)
        self._urls_list.append(url_to_request)


        path_file_cached = os.path.join(self._work_dir, 'list.txt')

        download = True
        if self._use_cache == True and os.path.exists(path_file_cached):
            mtime = os.path.getmtime(path_file_cached)
            delay_cache = SearchUpdate.delay_cache
            if (mtime + delay_cache) > time.time():
                download = False

        files = []
        if download:
            try:
                ftp = FTP(url_to_request_p.netloc)
                ftp.login()
                ftp.cwd(url_to_request_p.path)
                files = ftp.nlst()
            except:
                self.print('Error to connect on FTP')
                return None

            file = open(path_file_cached, 'w')
            file.write('\n'.join(files))
            file.close()

        else:
            self.print("Use cached file: " + path_file_cached)
            file= open(path_file_cached, 'r')
            files = file.readlines()
            file.close()

        regex_filename = self._generate_regex_version(version)

        new_versions = {}
        for filename in files:
            match = regex_filename.search(filename.strip('\n'))
            if match:
                m = match.groups()
                version_curr_p = parse_version(m[1])
                if version_curr_p >= version_p:
                    if m[1] not in new_versions:
                        new_versions[ m[1] ] = {'version': m[1], 'extensions': [ m[-1] ], 'is_prerelease': version_curr_p.is_prerelease}
                    elif m[-1] not in new_versions[ m[1] ]['extensions']:
                        new_versions[ m[1] ]['extensions'].append(m[-1])

        new_versions = collections.OrderedDict(sorted(new_versions.items(), key=lambda x: parse_version(x[0]), reverse=True))

        return new_versions


    def _get_url_data(self, url, depth = 0):

        url_p = urlparse(url)

        path_splitted = url_p.path.split('/')
        url_to_request_base = url_p.scheme + '://' + url_p.netloc

        # Get URL to request before remove depth path
        url_to_request = None
        if url_p.netloc == 'github.com':

            direcotries = ['releases', 'tags']
            if depth >= len(direcotries):
                return None

            if path_splitted[1] == 'downloads':
                path_splitted.remove('downloads')
                url_to_request = url_to_request_base + '/'.join(path_splitted) + '/' + direcotries[depth]
            else:
                url_to_request = url_to_request_base + '/'.join(path_splitted[0:3]) + '/' + direcotries[depth]

        elif url_p.netloc == 'files.pythonhosted.org':
            if depth > 0:
                return None

            url_to_request = 'https://pypi.python.org/pypi/' + path_splitted[-1]

        elif url_p.netloc.endswith('.googlecode.com'):

            project = url_p.netloc[:-15]
            url_to_request = 'https://www.googleapis.com/storage/v1/b/google-code-archive/o/v2%2Fcode.google.com%2F' + project + '%2Fdownloads-page-' + str(depth + 1) + '.json?alt=media&stripTrailingSlashes=false'


        # Remove depth path
        if not url_to_request:
            if depth > 0:
                path_splitted = path_splitted[0:-depth]

        # Get URL after remove depth path
        if url_p.netloc == 'sourceforge.net':
            if len(path_splitted) < 4:
                return None

        elif url_p.netloc == 'code.google.com':
            if len(path_splitted) < 4:
                return None

        elif url_p.netloc == 'download.sourceforge.net':
            if len(path_splitted) < 2:
                return None

            url_to_request_base = url_p.scheme + '://sourceforge.net'
            path_splitted = ['', 'projects'] + path_splitted[1:2] + ['files'] + path_splitted[2:]

        elif url_p.netloc == 'downloads.sourceforge.net':
            if len(path_splitted) < 3:
                return None

            url_to_request_base = url_p.scheme + '://sourceforge.net'
            path_splitted = ['', 'projects'] + path_splitted[2:3] + ['files'] + path_splitted[3:]

        else:
            if len(path_splitted) < 2:
                return None

        if not url_to_request:
            url_to_request = url_to_request_base + '/'.join(path_splitted)


        url_to_request_p = urlparse(url_to_request.rstrip('/'))

        if url_to_request in self._urls_list:

            self.print("Url page already download: " + url_to_request)
            return None

        self.print("Download url page: " + url_to_request)
        req = requests.get(url_to_request, allow_redirects=True)

        text = ''
        if req.status_code == requests.codes.ok:
            text = req.text
        else:
            self.print('Error to download page: ' + str(req.status_code))
            return None

        # Text filter
        text_filtered = ''
        if url_to_request_p.netloc == 'sourceforge.net':
            soup = BeautifulSoup(text, "html5lib")
            soup_find = soup.find("div", {"id": "files"})
            if soup_find:
                text_filtered += str(soup_find)

            soup_find = soup.find("div", {"id": "download-bar"})
            if soup_find:
                text_filtered += str(soup_find)
        elif url_to_request_p.netloc == 'pypi.python.org':
            soup = BeautifulSoup(text, "html5lib")
            soup_find = soup.find("table", {"id": "list"})
            if soup_find:
                text_filtered += str(soup_find)

            soup_find = soup.find("ul", {"id": "nodot"})
            if soup_find:
                text_filtered += str(soup_find)
        else:
            text_filtered = text

        if len(text_filtered) > 0:
            text = text_filtered


        # Check for redirect
        # Ex: Google Code redirect to github
        req.url = req.url.rstrip('/')
        req_url_p = urlparse(req.url)
        if len(req.history) > 0 and (url_to_request_p.netloc != req_url_p.netloc or url_to_request_p.path != req_url_p.path):
            self.print("Check redirection to: "+req.url)
            text_full = ''
            depth = 0
            while True:
                text = self._get_url_data(req.url, depth)
                if not text:
                    break
                text_full += text
                depth += 1
            return text_full
        else:
            self._urls_list.append(url_to_request)

        return text


    def _search_updates_http(self):
        url = self.get_url()
        version = self.get_version()
        if not version:
            self.print('Error: No version found !')
            return None

        version_p = parse_version(version)

        self.print("Current version: " + version)

        url_splitted = url.split('/')
        filename = url_splitted[-1]
        url = '/'.join(url_splitted[0:-1])

        path_file_cached = os.path.join(self._work_dir, 'list.html')
        path_file_txt_cached = os.path.join(self._work_dir, 'list.txt')

        download = True
        if self._use_cache == True and os.path.exists(path_file_cached):
            mtime = os.path.getmtime(path_file_cached)
            delay_cache = SearchUpdate.delay_cache
            if (mtime + delay_cache) > time.time():
                download = False

        text_full = ''
        if download:
            text_full = ''
            depth = 0
            while True:
                text = self._get_url_data(url, depth)
                if not text:
                    break
                text_full += text
                depth += 1

            # If no data, check home page
            if len(text_full) == 0:
                home_page = self._parser.get_var_values('HOMEPAGE')
                if home_page:
                    home_page__p = urlparse(home_page[0])
                    home_page = home_page[0]
                    if len(home_page) == 1:
                        home_page += '/'
                    self.print("No result: Search in home page")
                    text = self._get_url_data(home_page, 0)
                    if text:
                        text_full += text



            if len(text_full) > 0:
                file = open(path_file_cached, 'w')
                file.write(text_full)
                file.close()
            else:
                return None

        else:
            self.print("Use cached file: " + path_file_cached)
            file= open(path_file_cached, 'r')
            text_full = ''.join(file.readlines())
            file.close()


        self.print("Check for filename in pages")

        regex_filename = self._generate_regex_version(version)

        matches = regex_filename.findall(text_full)

        new_versions = {}
        for m in matches:
            version_curr_p = parse_version(m[1])
            # Keep current version to avoid to search version
            if version_curr_p >= version_p:
                if m[1] not in new_versions:
                    new_versions[ m[1] ] = {'version': m[1], 'extensions': [ m[-1] ], 'is_prerelease': version_curr_p.is_prerelease}
                elif m[-1] not in new_versions[ m[1] ]['extensions']:
                    new_versions[ m[1] ]['extensions'].append(m[-1])

        # If none filename with version is found even the current version, search any version if the current version is present
        if len(new_versions) == 0 and version in text_full:

            def clean_html(html):
                soup = BeautifulSoup(html, "html5lib")
                for script in soup(["script", "style"]):
                    script.extract()
                text = soup.get_text()
                # break into lines and remove leading and trailing space on each
                lines = (line.strip() for line in text.splitlines())
                # break multi-headlines into a line each
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                # drop blank lines
                text = '\n'.join(chunk for chunk in chunks if chunk)
                return text

            plain_text = clean_html(text_full)

            self.print("Check for version in pages")

            regex_version = re.escape(version)
            regex_version = re.sub('\-\w+', '\-\w+', regex_version)
            regex_version = re.sub('[0-9]+', '[0-9]+', regex_version)
            regex_version = '(' + regex_version + ')'
            _LOGGER.debug("_search_updates_http: regex_version: %s" % (regex_version,))

            matches = re.findall(regex_version, plain_text)

            for m in matches:
                version_curr_p = parse_version(m)
                if m not in new_versions and version_curr_p >= version_p:
                    new_versions[ m ] = {'version': m, 'is_prerelease': version_curr_p.is_prerelease}

        new_versions = collections.OrderedDict(sorted(new_versions.items(), key=lambda x: parse_version(x[0]), reverse=True))

        # Remove current version
        #if version in new_versions.keys():
        #    del new_versions[ version ]

        return new_versions


    def _search_updates_common(self):
        url = self.get_url()

        url_p = urlparse(url)

        new_versions = []
        if url_p.scheme == 'ftp':
            new_versions = self._search_updates_ftp()
        else:
            new_versions = self._search_updates_http()

        return new_versions

    def search_updates(self):

        if not os.path.exists(self._work_dir):
            os.makedirs(self._work_dir)

        method = self._parser.get_var_values('PKG_DOWNLOAD_METHOD', ['common'])[0]
        func_name = '_search_updates_' + method

        try:
            func = getattr(self, func_name)
            return func()
        except Exception as e:
            print(e)
            print('Method ' + func_name + ' has not found')
            return None




