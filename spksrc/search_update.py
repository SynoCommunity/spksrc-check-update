
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
        self._urls_downloaded = {}

        _LOGGER.debug("__init__: path: %s" % (path,))
        self._parser = MakefileParser()
        self._parser.parse_file(path)

    def print(self, message):
        print("[" + self._package + "] " + message)


    def enable_cache(self):
        self._use_cache = True


    def disable_cache(self):
        self._use_cache = False


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
        if version:
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
                    new_versions.append({'hash': str(tag)})
        else:
            # No tags: list new commits
            self.print("No tags: Get new versions from commits")
            for c in repo.iter_commits(git_hash + '..HEAD'):
                new_versions.append({'hash': str(c)})

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
            new_versions.insert(0, {'rev': str(rev.revision)})

        return new_versions


    def _download_content(self, url):
        url = url.rstrip('/')
        url_p = urlparse(url)

        content = None
        history = []
        if url_p.scheme == 'ftp':
            try:
                ftp = FTP(url_p.netloc)
                ftp.login()
                ftp.cwd(url_p.path)
                #files = ftp.nlst()
                #files = ftp.dir()
                files = []
                ftp.retrlines('LIST', files.append)
                files_new = []
                for f in files:
                    infos = f.split(' ')
                    file = infos[-1]
                    if infos[0][0] == 'd':
                        file += '/'
                    files_new.append(file)
                content = '\n'.join(files_new)
            except:
                self.print('Error to connect on FTP')
                return None
        else:
            req = requests.get(url, allow_redirects=True)

            if req.status_code == requests.codes.ok:
                content = req.text
                url = req.url.rstrip('/')
                history = req.history
            else:
                self.print('Error to download page: ' + url)
                return None

        return {'type': url_p.scheme, 'url': url, 'url_p': url_p, 'content': content, 'history': history}


    def _search_download_urls(self):

        # List domains to get download link for these domains
        schemes = ['', 'http', 'https', 'ftp']
        domains = ['']
        for url, data in self._urls_downloaded.items():
            if data['url_p'].netloc not in domains:
                domains.append(data['url_p'].netloc)

        urls = []
        for url, data in self._urls_downloaded.items():
            soup = BeautifulSoup(data['content'], "html5lib")
            for item in soup.find_all("a"):
                href = item.get('href')
                if href:
                    href_p = urlparse(href)
                    if href_p.scheme in schemes and href_p.netloc in domains:
                        content = href_p.path + ' ' + str(item.next)
                        match = re.search('download', content, re.IGNORECASE)
                        if match:
                            _LOGGER.warn("_search_download_urls: regex-search: %s" % (content,))
                            url = data['url_p'].scheme + '://' + data['url_p'].netloc + '/' + href_p.path.lstrip('/')
                            if url not in urls and url not in self._urls_downloaded:
                              urls.append(url)

        return urls



    def _search_version_urls(self):

        # List domains to get version directory link for these domains
        schemes = ['', 'http', 'https', 'ftp']
        domains = ['']
        for url, data in self._urls_downloaded.items():
            if data['url_p'].netloc not in domains:
                domains.append(data['url_p'].netloc)

        regex_version_href = re.compile('(([0-9]+)(\.([0-9]+))+(-[a-zA-Z0-9_]+)*)/(\w+.(html|php))?$')
        regex_version_content = re.compile('^(([0-9]+)(\.([0-9]+))+(-[a-zA-Z0-9_]+))*$')

        urls = []
        for url, data in self._urls_downloaded.items():

            hrefs = []
            if data['url_p'].scheme == 'ftp':
                hrefs = map(lambda x: [x, ''], data['content'].split('\n'))
            else:
                soup = BeautifulSoup(data['content'], "html5lib")
                for item in soup.find_all("a"):
                    hrefs.append([item.get('href'), str(item.next).strip()])
            for href_info in hrefs:
                version = None
                href = href_info[0]
                content = href_info[1]
                href_p = urlparse(href)

                if href_p.scheme in schemes and href_p.netloc in domains:
                    match_href = regex_version_href.search(str(href_p.path))
                    if match_href:
                        version = parse_version(match_href.group(1))
                    if not version:
                        if len(content) > 0:
                            match_content = regex_version_content.search(content)
                            if match_content:
                                version = parse_version(match_content.group(1))
                if version and version > self._version_p:
                    _LOGGER.debug("_search_version_urls: regex-search: %s, %s" % (str(href_p.path), content,))
                    url_found = ''
                    if len(href_p.netloc) > 0:
                        url_found = href_p.scheme + '://' + href_p.netloc
                    else:
                        if href_p.path[0] == '/':
                            url_found = data['url_p'].scheme + '://' + data['url_p'].netloc
                        else:
                            url_found = url
                    url_found += '/' + href_p.path.lstrip('/')
                    if url_found not in urls and url_found not in self._urls_downloaded:
                      urls.append(url_found)

        return urls


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

            url_to_request_base = 'https://sourceforge.net'
            path_splitted = ['', 'projects'] + path_splitted[1:2] + ['files'] + path_splitted[2:]

        elif url_p.netloc == 'downloads.sourceforge.net':
            if len(path_splitted) < 3:
                return None

            url_to_request_base = 'https://sourceforge.net'
            path_splitted = ['', 'projects'] + path_splitted[2:3] + ['files'] + path_splitted[3:]

        else:
            if len(path_splitted) < 2:
                return None

        if not url_to_request:
            url_to_request = url_to_request_base + '/'.join(path_splitted)


        if url_to_request in self._urls_downloaded:
            self.print("Url page already download: " + url_to_request)
            return None

        self.print("Download url page: " + url_to_request)
        content_request = self._download_content(url_to_request)

        if not content_request:
            return None


        # Text filter
        content = content_request['content']
        content_filtered = ''
        if content_request['url_p'].netloc == 'sourceforge.net':
            soup = BeautifulSoup(content, "html5lib")
            soup_find = soup.find("div", {"id": "files"})
            if soup_find:
                content_filtered += str(soup_find)

            soup_find = soup.find("div", {"id": "download-bar"})
            if soup_find:
                content_filtered += str(soup_find)
        elif content_request['url_p'].netloc == 'pypi.python.org':
            soup = BeautifulSoup(content, "html5lib")
            soup_find = soup.find("table", {"id": "list"})
            if soup_find:
                content_filtered += str(soup_find)

            soup_find = soup.find("ul", {"id": "nodot"})
            if soup_find:
                content_filtered += str(soup_find)

        if len(content_filtered) > 0:
            content = content_filtered


        self._urls_downloaded[ url_to_request ] = {'content': content, 'url_p': content_request['url_p']}


        # Check for redirect
        # Ex: Google Code redirect to github
        req_url_p = urlparse(content_request['url'])
        if len(content_request['history']) > 0 and (content_request['url_p'].netloc != req_url_p.netloc or content_request['url_p'].path != req_url_p.path):
            self.print("Check redirection to: "+content_request['url'])
            depth = 0
            while True:
                text = self._get_url_data(content_request['url'], depth)
                if not text:
                    break
                depth += 1

        return True


    def _generate_regex_filename(self):
        tmp_parser = copy.copy(self._parser)
        tmp_parser.set_var_values('PKG_VERS', 'XXXVERXXX')
        tmp_parser.evaluate_var('PKG_DIST_NAME')
        filename = tmp_parser.get_var_values('PKG_DIST_NAME')

        regex_version = '([0-9]+((?P<sep>[._-])([0-9a-zA-Z]+))*(-[a-zA-Z0-9_]+)*)'
        regex_filename = '(' + re.escape(filename[0]).replace('XXXVERXXX', regex_version) + ')($|/)'
        regex_filename = re.sub('(\\\.tar\\\.lz|\\\.tar\\\.bz2|\\\.tar\\\.gz|\\\.tar\\\.xz|\\\.tar\\\.bz2|\\\.zip|\\\.rar|\\\.tgz|\\\.7z)', '\.(tar\.lz|tar\.bz2|tar\.gz|tar\.xz|tar\.bz2|zip|rar|tgz|7z)', regex_filename)
        _LOGGER.debug("_generate_regex_filename: regex_filename: %s" % (regex_filename,))

        return re.compile(regex_filename)


    def _generate_regex_version(self):
        regex_version = re.escape(self._version)
        regex_version = re.sub('\-[a-zA-Z0-9_]+', '\-[a-zA-Z0-9_]+', regex_version)
        regex_version = re.sub('[0-9]+', '[0-9]+', regex_version)
        regex_version = '(' + regex_version + ')'
        _LOGGER.debug("_generate_regex_version: regex_version: %s" % (regex_version,))

        return re.compile(regex_version)


    def _search_updates_common(self):
        url = self.get_url()
        url_p = urlparse(url)

        self._version = self.get_version()

        if not self._version:
            self.print('Error: No version found in the package !')
            return None

        self.print("Current version: " + self._version)

        self._version_p = parse_version(self._version)

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

        if download:
            depth = 0
            while True:
                check = self._get_url_data(url, depth)
                if not check:
                    break
                depth += 1

            # Check home page
            home_page = self._parser.get_var_values('HOMEPAGE')
            if home_page:
                home_page_p = urlparse(home_page[0])
                home_page = home_page[0]
                if home_page_p.path == '':
                    home_page += '/'
                self.print("Search in home page")
                self._get_url_data(home_page, 0)


            # Check for download URL in the page
            #download_urls = self._search_download_urls()
            download_urls = []
            if len(download_urls) > 0:
                self.print("Found download link in page:")
                for url in download_urls:
                    self.print("Download link: " + url)
                    self._get_url_data(url)

            # Check for version URL in the page
            version_urls = self._search_version_urls()
            if len(version_urls) > 0:
                self.print("Found version link in page:")
                for url in version_urls:
                    self._get_url_data(url)

            content = ' '
            if len(content) > 0:
                file = open(path_file_cached, 'w')
                file.write(content)
                file.close()
            else:
                return None

        else:
            self.print("Use cached file: " + path_file_cached)
            file= open(path_file_cached, 'r')
            content = ''.join(file.readlines())
            file.close()


        self.print("Check for filename in pages")

        regex_filename = self._generate_regex_filename()

        # Get version from downloaded pages
        new_versions = {}
        for url, data in self._urls_downloaded.items():

            hrefs = []
            if data['url_p'].scheme == 'ftp':
                hrefs = data['content'].split('\n')
            else:
                soup = BeautifulSoup(data['content'], "html5lib")
                for item in soup.find_all("a"):
                    hrefs.append(str(item.get('href')))

            for href in hrefs:
                href_p = urlparse(href)
                match = regex_filename.search(href_p.path)
                if match:
                    m = match.groups()
                    version_curr = m[1].replace('_', '.')
                    version_curr_p = parse_version(version_curr)
                    # Keep current version to avoid to search version
                    if version_curr_p >= self._version_p:
                        scheme = ''
                        url_filename = '//'
                        if len(href_p.netloc) > 0:
                            scheme = href_p.scheme
                            url_filename += href_p.netloc
                        else:
                            scheme =  data['url_p'].scheme
                            url_filename += data['url_p'].netloc

                        url_filename = url_filename + '/'
                        if href_p.path[0] != '/':
                            url_filename += data['url_p'].path.strip('/') + '/'

                        url_filename += href_p.path[0:match.end()].strip('/')

                        if scheme == '':
                            scheme = 'https'

                        url_info = {'filename': m[0], 'extensions': m[-2], 'full': url_filename, 'schemes': [scheme]}
                        if version_curr not in new_versions:
                            new_versions[ version_curr ] = {'version': version_curr, 'is_prerelease': version_curr_p.is_prerelease, 'urls': [ url_info ]}
                        else:
                            urls = list(map(lambda x: x['full'], new_versions[ version_curr ]['urls']))
                            if url_filename not in urls:
                                new_versions[ version_curr ]['urls'].append(url_info)
                            elif scheme not in new_versions[ version_curr ]['urls'][ urls.index(url_filename) ]['schemes']:
                                new_versions[ version_curr ]['urls'][ urls.index(url_filename) ]['schemes'].append(scheme)

        new_versions = collections.OrderedDict(sorted(new_versions.items(), key=lambda x: parse_version(x[0]), reverse=True))

        # Remove current version
        #if self._version in new_versions.keys():
        #    del new_versions[ self._version ]

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



