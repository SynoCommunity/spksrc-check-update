import sys
import os
import shutil
import re
import time
import copy
import logging
import collections
import pickle

import git as git
import svn as svn
import svn.remote
import svn.local
import requests
from ftplib import FTP
import json

from urllib.parse import urlparse, ParseResult, unquote
from pkg_resources import parse_version
from bs4 import BeautifulSoup

from .config import Config
from .cache import Cache
# from .tools import Tools
from .makefile_parser.makefile_parser import MakefileParser

_LOGGER = logging.getLogger(__name__)


class PackageSearchUpdate(object):

    # Regex pattern to match version
    regex_version = '(?P<version>[0-9]+([._-][0-9][0-9a-zA-Z]*|[._-][0-9a-zA-Z]*[0-9])*(-[a-zA-Z0-9_]+)*)'

    # Extensions to match urls to download
    extensions_to_download = [
        'tar.lz',
        'tar.bz2',
        'tar.gz',
        'tar.xz',
        'zip',
        'rar',
        'tgz',
        '7z'
    ]
    regex_extensions_replace_from = "|".join([re.escape(re.escape("." + e)) for e in extensions_to_download])
    regex_extensions_replace_to = "|".join([re.escape("." + e) for e in extensions_to_download])

    def __init__(self, package, path):
        self._package = package
        self._path = path
        self._cache_dir = os.path.join(Config.get('cache_dir'), self._package)
        self._cache = Cache(dir=self._cache_dir, duration=Config.get("cache_duration_search_update_download"))
        self._urls_downloaded = {}
        self._parser = None
        self._versions = None
        self._current_version = None

        _LOGGER.debug("path: %s", path)

    def log(self, message):
        """ Print a message with a prefix
        """
        _LOGGER.info("[Package:%s]: %s", self._package, message)

    def set_parser(self, parser):
        """ Set parser instance
        """
        self._parser = parser

    def get_parser(self):
        """ Get parser instance
        """
        if not self._parser:
            self._parser = MakefileParser()

        if not self._parser.is_parsed():
            self._parser.parse_file(self._path)

        return self._parser

    def get_url(self):
        """ Return URL from Makefile package
        """
        url = self.get_parser().get_var_values('PKG_DIST_SITE')
        if url is not None:
            url_file = self.get_parser().get_var_values('PKG_DIST_NAME')
            if url_file is not None:
                url[0] += '/' + url_file[0]

            return url[0]

        return None

    def get_method(self):
        """ Return the method used in Makefile
        """
        return self.get_parser().get_var_values('PKG_DOWNLOAD_METHOD', ['common'])[0]

    def _get_version_git(self):
        """ Return version for a package using git
        """
        return self.get_parser().get_var_values('PKG_GIT_HASH', ['master'])[0]

    def _get_version_svn(self):
        """ Return version for a package using svn
        """
        return self.get_parser().get_var_values('PKG_SVN_REV', ['HEAD'])[0]

    def _get_version_wget(self):
        """ Return version for a common package
        """
        return self._get_version_common()

    def _get_version_common(self):
        """ Return version for a common package
        """
        return self.get_parser().get_var_values('PKG_VERS', [''])[0]

    def get_version(self):
        """ Return version for the package
        """

        if self._current_version:
            return self._current_version

        method = self.get_method()
        func_name = '_get_version_' + method

        try:
            func = getattr(self, func_name)
        except AttributeError as e:
            _LOGGER.warning('Method "%s" was not found or during call: %s', method, e)
            return None

        self._current_version = func()

        return self._current_version

    def _search_updates_git(self):
        """ Search new tags or commits in git repository
        """
        url = self.get_url()

        # Temp path to clone reository
        git_path = os.path.join(self._cache_dir, 'git')
        # Get current Hash of package
        git_hash = self.get_version()

        _LOGGER.info("Current git hash: %s", git_hash)

        # State file to determine when the repository is cloned
        git_is_cloned = os.path.join(self._cache_dir, '.git_clone')
        if not os.path.exists(git_is_cloned):
            # Remove partial cloned dir
            if os.path.exists(git_path):
                shutil.rmtree(git_path)

            # Clone repository
            self.log("Clone repository: " + url)
            try:
                git.Repo.clone_from(url, git_path)
            except git.GitCommandError as exception:
                self.log("Error to clone git")
                return

            # Touch the state file
            open(git_is_cloned, 'w').close()
            self.log("Repository cloned")

        # Fetch and pull
        self.log("Fetch and pull git")
        repo = git.Repo(git_path)
        for remote in repo.remotes:
            remote.fetch()
            remote.pull()

        new_versions = collections.OrderedDict()

        tags = repo.tags
        if len(tags) > 0:
            # Has tag: List new tags
            self.log("Has tags: Get new versions from tags")
            tags.sort(key=lambda t: t.commit.committed_datetime)
            for c in repo.iter_commits(git_hash + '..HEAD'):
                tag = next((tag for tag in repo.tags if tag.commit == c), None)
                if tag is not None:
                    new_versions[str(tag)] = {'hash': str(tag)}
        else:
            # No tags: list new commits
            self.log("No tags: Get new versions from commits")
            for c in repo.iter_commits(git_hash + '..HEAD'):
                new_versions[str(c)] = {'hash': str(c)}

        return new_versions

    def _search_updates_svn(self):
        """ Search new tags or revision in subversion repository
        """
        url = self.get_url()

        # Temp path to checkout reository
        svn_path = os.path.join(self._cache_dir, 'svn')
        # Get current Revision of package
        svn_rev = self.get_version()
        # Get next revision
        svn_rev_next = 'HEAD'
        if svn_rev != 'HEAD':
            svn_rev_next = int(svn_rev) + 1

        self.log("Current svn revision: " + svn_rev)

        # State file to determine when the repository is checkout
        svn_is_checkout = os.path.join(self._cache_dir, '.svn_checkout')
        if not os.path.exists(svn_is_checkout):
            # Delete partial checkout dir
            if os.path.exists(svn_path):
                shutil.rmtree(svn_path)

            # Checkout repository
            self.log("Checkout repository: " + url)
            try:
                repo = svn.remote.RemoteClient(url)
                repo.checkout(svn_path)
            except:
                self.log("Error to checkout svn")
                return

            # Touch the state file
            open(svn_is_checkout, 'w').close()
            self.log("Repository checkout")

        repo = svn.local.LocalClient(svn_path)

        # Update repository
        self.log("Update svn")
        repo.update()

        new_versions = collections.OrderedDict()

        # Get new revision in /tags repository
        self.log("Get new revisions in /tags directory")
        tags_rev = repo.log_default(
            None, None, None, '^/tags', None, svn_rev_next, None)
        for rev in tags_rev:
            new_versions[str(rev.revision)] = {'rev': str(rev.revision)}

        # Return in reversed order
        return collections.OrderedDict(reversed(list(new_versions.items())))

    def _download_content(self, url, old_url):
        """ Download the content of an url (HTTP or FTP)
        For FTP, return the list of directories and files.
        For HTTP, return the content and href attribute of 'a' tag
        Return a dict with scheme, url, url parsed and hrefs found
        """
        url_p = urlparse(url)

        content = ''
        hrefs = None
        history = []
        if url_p.scheme == 'ftp':
            # Get content page on FTP
            try:
                ftp = FTP(url_p.netloc)
                ftp.login()
                ftp.cwd(url_p.path)
                files = []
                ftp.retrlines('LIST', files.append)
                hrefs = []
                for f in files:
                    infos = f.split(' ')
                    file = infos[-1]
                    if infos[0][0] == 'd':
                        file += '/'
                    hrefs.append({'href': file, 'href_p': urlparse(file), 'content': ''})
            except:
                self.log('Error to connect on FTP')
                return None
        else:
            # Get content page on HTTP
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'
                }
                req = requests.get(url, allow_redirects=True, headers=headers)
            except:
                # Catch server not found
                self.log('Error to download page: ' + url)
                return None

            # If code 200
            if req.status_code == requests.codes.ok:
                hrefs = []
                # Get url after redirection
                url = req.url.rstrip('/')
                # Get history of redirection
                history = req.history

                # Text filter to avoid ads
                content = req.text
                content_filtered = ''
                if url_p.netloc == 'sourceforge.net':
                    # Case of sourceforge.net
                    soup = BeautifulSoup(content, "html5lib")
                    soup_find = soup.find("div", {"id": "files"})
                    if soup_find:
                        content_filtered += str(soup_find)

                    soup_find = soup.find("div", {"id": "download-bar"})
                    if soup_find:
                        content_filtered += str(soup_find)
                elif url_p.netloc == 'pypi.python.org':
                    # Case of pypi.python.org
                    soup = BeautifulSoup(content, "html5lib")
                    soup_find = soup.find("table", {"id": "list"})
                    if soup_find:
                        content_filtered += str(soup_find)

                    soup_find = soup.find("ul", {"id": "nodot"})
                    if soup_find:
                        content_filtered += str(soup_find)

                if content_filtered:
                    content = content_filtered

                # Get page extension
                parts = url_p.path.split('/')[-1].split('.')
                ext = ''
                if len(parts) > 1:
                    ext = parts[-1]

                # When this is a JSON file
                if ext == 'json':
                    j = json.loads(content)
                    if url_p.netloc == 'www.googleapis.com':
                        old_url_p = urlparse(old_url)
                        project = old_url_p.netloc[:-15]
                        base_url = 'http://' + project + '.googlecode.com/files/'
                        for info in j['downloads']:
                            href = base_url + info['filename']
                            hrefs.append({'href': href, 'href_p': urlparse(href), 'content': ''})
                else:
                    soup = BeautifulSoup(content, "html5lib")
                    for item in soup.find_all("a"):
                        href = item.get('href')
                        if href:
                            hrefs.append({'href': href, 'href_p': urlparse(href), 'content': str(item.next).strip()})
            else:
                # In case of code different to 200
                self.log('Error to download page: ' + url)
                return None

        return {'type': url_p.scheme, 'url': url, 'url_p': url_p, 'hrefs': hrefs, 'history': history, 'content': content}

    def _search_download_urls(self):
        """ Search link or content link which contains 'download'
        Return link found
        """
        # List of allowed schemes
        schemes = ['', 'http', 'https', 'ftp']
        # List of allowed domains
        domains = ['']
        for url, data in self._urls_downloaded.items():
            if data['url_p'].netloc not in domains:
                domains.append(data['url_p'].netloc)

        urls = []
        for url, data in self._urls_downloaded.items():
            for href in data['hrefs']:
                if href['href_p'].scheme in schemes and href['href_p'].netloc in domains:
                    content = href['href'].path + ' ' + href['content']
                    match = re.search('download', content, re.IGNORECASE)
                    if match:
                        _LOGGER.debug("regex-search match: %s", content)

                        # Create full link
                        url_found = ''
                        if len(href['href_p'].netloc) > 0:
                            url_found = href['href_p'].scheme + \
                                '://' + href['href_p'].netloc
                        else:
                            if href['href_p'].path[0] == '/':
                                url_found = data['url_p'].scheme + \
                                    '://' + data['url_p'].netloc
                            else:
                                url_found = url
                        url_found += '/' + href['href_p'].path.lstrip('/')

                        if url not in urls and url not in self._urls_downloaded:
                            urls.append(url)
        return urls

    def _search_version_urls(self):
        """ Search link or content link which terminates by a directory ending by a version number and may be a html or php file
        Return link found
        """
        # List domains to get version directory link for these domains
        # List of allowed schemes
        schemes = ['', 'http', 'https', 'ftp']
        # List of allowed domains
        domains = ['']
        for url, data in self._urls_downloaded.items():
            if data['url_p'].netloc not in domains:
                domains.append(data['url_p'].netloc)

        # Regex for href attribute
        regex_version_href = re.compile(
            '(([0-9]+)([._-]([0-9][0-9a-zA-Z]*|[0-9a-zA-Z]*[0-9]))+(-[a-zA-Z0-9_]+)*)(/(\w+.(html|php))?)?$')
        # Regex for tag content
        regex_version_content = re.compile(
            '^(([0-9]+)([._-]([0-9][0-9a-zA-Z]*|[0-9a-zA-Z]*[0-9]))+(-[a-zA-Z0-9_]+))*$')

        urls = []
        for url, data in self._urls_downloaded.items():
            for href in data['hrefs']:
                version = None

                if href['href_p'].scheme in schemes and href['href_p'].netloc in domains:
                    match_href = regex_version_href.search(
                        str(href['href_p'].path))
                    if match_href:
                        version = parse_version(match_href.group(1))
                    if not version:
                        if len(href['content']) > 0:
                            match_content = regex_version_content.search(
                                href['content'])
                            if match_content:
                                version = parse_version(match_content.group(1))
                if version and version >= self._version_p:
                    _LOGGER.debug("regex-search match: %s, %s",
                                  href['href_p'].path, href['content'])

                    # Create full link
                    url_found = ''
                    if len(href['href_p'].netloc) > 0:
                        url_found = href['href_p'].scheme + \
                            '://' + href['href_p'].netloc
                    else:
                        if href['href_p'].path[0] == '/':
                            url_found = data['url_p'].scheme + \
                                '://' + data['url_p'].netloc
                        else:
                            url_found = url
                    url_found += '/' + href['href_p'].path.lstrip('/')

                    if url_found not in urls and url_found not in self._urls_downloaded:
                        urls.append(url_found)
        return urls

    def _get_url_data(self, url, depth=0, can_remove_version=True):
        """ Get data for an url.
        Depth define the path to remove from the url
        """
        url_p = urlparse(url)

        path_splitted = url_p.path.split('/')
        url_to_request_base = url_p.scheme + '://' + url_p.netloc

        # Adapt URL to request before remove depth path
        url_to_request = None
        if url_p.netloc == 'github.com':
            # For Github, get releases and tags directories
            directories = ['', 'releases', 'tags']
            if depth >= len(directories):
                return None
            if path_splitted[1] == 'downloads':
                path_splitted.remove('downloads')
                url_to_request = url_to_request_base + \
                    '/'.join(path_splitted) + '/' + directories[depth]
            else:
                url_to_request = url_to_request_base + \
                    '/'.join(path_splitted[0:3]) + '/' + directories[depth]

        elif url_p.netloc == 'files.pythonhosted.org':
            if depth > 0:
                return None
            # For files.pythonhosted.org, get the package information
            url_to_request = 'https://pypi.python.org/pypi/' + \
                path_splitted[-1]

        elif url_p.netloc.endswith('.googlecode.com'):
            # For .googlecode.com, get JSON of files list
            project = url_p.netloc[:-15]
            url_to_request = 'https://www.googleapis.com/storage/v1/b/google-code-archive/o/v2%2Fcode.google.com%2F' + \
                project + '%2Fdownloads-page-' + \
                str(depth + 1) + '.json?alt=media&stripTrailingSlashes=false'

        elif url_p.netloc == 'launchpad.net':
            if '+download' in path_splitted:
                path_splitted.remove('+download')

        # If path contains version, increment depth
        if can_remove_version and self._version in path_splitted:
            depth += 1

        # Stop if depth > path len
        if depth >= len(path_splitted):
            return None

        # Remove depth path
        if not url_to_request:
            if depth > 0:
                path_splitted = path_splitted[0:-depth]

        # Limit depth for spefic domain
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
            path_splitted = ['', 'projects'] + \
                path_splitted[1:2] + ['files'] + path_splitted[2:]

        elif url_p.netloc == 'downloads.sourceforge.net':
            if len(path_splitted) > 2 and path_splitted[1] == 'project':
                if len(path_splitted) < 3:
                    return None

                url_to_request_base = 'https://sourceforge.net'
                path_splitted = ['', 'projects'] + \
                    path_splitted[2:3] + ['files'] + path_splitted[3:]
            else:
                if len(path_splitted) < 2:
                    return None

                url_to_request_base = 'https://sourceforge.net'
                path_splitted = ['', 'projects'] + \
                    path_splitted[1:2] + ['files'] + path_splitted[2:]

        # If url_to_request was not defined in specific case
        if not url_to_request:
            url_to_request = url_to_request_base + '/'.join(path_splitted)

        # Avoid to download page more than one time
        if url_to_request in self._urls_downloaded:
            self.log("Url page already download: " + url_to_request)
            return None

        # Download page content
        self.log("Download url page: " + url_to_request)
        content_request = self._download_content(url_to_request, url)

        # In case of empty result, return None
        if not content_request:
            return None

        self._urls_downloaded[url_to_request] = content_request

        # Check for redirect
        # And download page to catch specific case
        # Ex: Google Code redirect to github
        req_url_p = urlparse(content_request['url'])
        if len(content_request['history']) > 0 and (content_request['url_p'].netloc != req_url_p.netloc or content_request['url_p'].path != req_url_p.path):
            self.log("Check redirection to: " + content_request['url'])
            depth = 0
            while True:
                text = self._get_url_data(content_request['url'], depth)
                if not text:
                    break
                depth += 1

        return True

    def _generate_regex_filename_path(self):
        """ Return a regex to find the filename with version, extension and path
        """
        tmp_parser = copy.copy(self.get_parser())
        tmp_parser.set_var_values('PKG_VERS', 'XXXVERXXX')
        tmp_parser.evaluate_var('PKG_DIST_NAME')
        filename = tmp_parser.get_var_values('PKG_DIST_NAME')

        regex_path = '((([\w/:]*)))'
        if 'XXXVERXXX' not in filename[0]:
            tmp_parser.evaluate_var('PKG_DIST_SITE')
            pkg_site_p = urlparse(
                tmp_parser.get_var_values('PKG_DIST_SITE')[0])
            path = pkg_site_p.path.rstrip('/') + '/'
            regex_path = re.escape(path).replace(
                'XXXVERXXX', PackageSearchUpdate.regex_version)

        regex_filename_path = '(' + regex_path + '(?P<filename>' + re.escape(filename[0]).replace('XXXVERXXX', PackageSearchUpdate.regex_version) + '))'
        _LOGGER.debug("regex_filename_path_before: %s", regex_filename_path)
        regex_filename_path = re.sub('(' + PackageSearchUpdate.regex_extensions_replace_from + ')',
                                     '\.(?P<extension>' + PackageSearchUpdate.regex_extensions_replace_to + ')', regex_filename_path)
        _LOGGER.debug("regex_filename_path: %s", regex_filename_path)

        return re.compile(regex_filename_path)

    def _generate_regex_filename(self):
        """ Return a regex to find the filename with version and extension
        """
        tmp_parser = copy.copy(self.get_parser())
        tmp_parser.set_var_values('PKG_VERS', 'XXXVERXXX')
        tmp_parser.evaluate_var('PKG_DIST_NAME')
        filename = tmp_parser.get_var_values('PKG_DIST_NAME')

        regex_filename = '(?P<filename>' + re.escape(filename[0]).replace(
            'XXXVERXXX', PackageSearchUpdate.regex_version) + ')($|/)'
        regex_filename = re.sub('(' + PackageSearchUpdate.regex_extensions_replace_from + ')',
                                     '\.(?P<extension>' + PackageSearchUpdate.regex_extensions_replace_to + ')', regex_filename)
        _LOGGER.debug("regex_filename: %s", regex_filename)

        return re.compile(regex_filename)

    def _generate_regex_version(self):
        """ Return a regex to find the version based on the current version
        """
        tmp_parser = copy.copy(self.get_parser())
        regex_version = re.escape(self._version)
        regex_version = re.sub(
            '\-[a-zA-Z0-9_]+', '\-[a-zA-Z0-9_]+', regex_version)
        regex_version = re.sub('[0-9]+', '[0-9]+', regex_version)
        regex_version = '(' + regex_version + ')'
        _LOGGER.debug("regex_version: %s", regex_version)

        return re.compile(regex_version)

    def _search_updates_common(self):
        """ Search for update for FTP and HTTP link
        """
        url = self.get_url()
        url_p = urlparse(url)

        self._version = self.get_version()

        if not self._version:
            self.log('Error: No version found in the package !')
            return None

        self.log("Current version: " + self._version)

        self._version_p = parse_version(self._version)

        url_splitted = url.split('/')
        # filename = url_splitted[-1]
        url = '/'.join(url_splitted[0:-1])

        cache_filename = 'list.pkl'
        download = not self._cache.check(cache_filename)
        if download:
            depth = 0
            while True:
                check = self._get_url_data(url, depth)
                if not check:
                    break
                depth += 1

            # Check home page
            home_page = self.get_parser().get_var_values('HOMEPAGE')
            if home_page:
                self.log("Search in home page")
                depth = 0
                while True:
                    check = self._get_url_data(home_page[0], depth)
                    if not check:
                        break
                    depth += 1

            # Check download page
            download_page = self.get_parser().get_var_values('DOWNLOAD_PAGE')
            if download_page:
                self.log("Search in download page")
                depth = 0
                while True:
                    check = self._get_url_data(download_page[0], depth)
                    if not check:
                        break
                    depth += 1

            # Check for download URL in the page
            #download_urls = self._search_download_urls()
            download_urls = []
            if len(download_urls) > 0:
                self.log("Found download link in page:")
                for url in download_urls:
                    self.log("Download link: " + url)
                    self._get_url_data(url)

            # Check for version URL in the page
            version_urls = self._search_version_urls()
            if len(version_urls) > 0:
                self.log("Found version link in page:")
                for url in version_urls:
                    self._get_url_data(url, 0, False)

            self._cache.save(cache_filename, self._urls_downloaded)
        else:
            self._urls_downloaded = self._cache.load(cache_filename)

        self.log("Check for filename in pages")

        # Get regex for filename
        regex_filename = self._generate_regex_filename()

        new_versions = {}
        # Get version from downloaded pages
        for url, data in self._urls_downloaded.items():
            for href in data['hrefs']:
                match = regex_filename.search(unquote(href['href_p'].path))
                if match:
                    try:
                        version_curr = match.group('version').replace('_', '.')
                        version_curr_p = parse_version(version_curr)
                    except:
                        version_curr = None
                    # Keep current version to avoid to search in content
                    if version_curr and version_curr_p >= self._version_p:
                        scheme = ''
                        url_filename = '//'
                        if len(href['href_p'].netloc) > 0:
                            scheme = href['href_p'].scheme
                            url_filename += href['href_p'].netloc
                        else:
                            scheme = data['url_p'].scheme
                            url_filename += data['url_p'].netloc

                        url_filename = url_filename + '/'
                        if href['href_p'].path[0] != '/':
                            url_filename += data['url_p'].path.strip('/') + '/'

                        url_filename += href['href_p'].path[0:match.end()
                                                            ].strip('/')

                        if scheme == '':
                            scheme = 'https'

                        url_info = {'filename': unquote(match.group('filename')), 'extensions': match.group('extension'), 'full': unquote(url_filename), 'schemes': [scheme]}
                        if version_curr not in new_versions:
                            new_versions[version_curr] = {
                                'version': version_curr, 'is_prerelease': version_curr_p.is_prerelease, 'urls': [url_info]}
                        else:
                            urls = list(
                                map(lambda x: x['full'], new_versions[version_curr]['urls']))
                            if url_filename not in urls:
                                new_versions[version_curr]['urls'].append(url_info)
                            elif scheme not in new_versions[version_curr]['urls'][urls.index(url_filename)]['schemes']:
                                new_versions[version_curr]['urls'][urls.index(url_filename)]['schemes'].append(scheme)

        # If no result found : Try to find directly in content page (maybe javascript is used to display)
        if not new_versions:
            # Get regex for filename and path
            regex_filename_path = self._generate_regex_filename_path()
            for url, data in self._urls_downloaded.items():
                if len(data['content']) > 0:
                    for match in regex_filename_path.finditer(data['content']):
                        version_curr = match.group('version').replace('_', '.')
                        version_curr_p = parse_version(version_curr)
                        href = str(match.group(0))
                        href_p = urlparse(href)
                        if version_curr_p >= self._version_p:
                            scheme = ''
                            url_filename = '//'
                            if len(href_p.netloc) > 0:
                                scheme = href_p.scheme
                                url_filename += href_p.netloc
                            else:
                                scheme = data['url_p'].scheme
                                url_filename += data['url_p'].netloc

                            url_filename = url_filename + '/'
                            if href_p.path[0] != '/':
                                url_filename += data['url_p'].path.strip(
                                    '/') + '/'

                            url_filename += href_p.path

                            if scheme == '':
                                scheme = 'https'

                            url_info = {'filename': unquote(match.group('filename')), 'extensions': match.group(
                                'extension'), 'full': unquote(url_filename), 'schemes': [scheme]}
                            if version_curr not in new_versions:
                                new_versions[version_curr] = {
                                    'version': version_curr,
                                    'is_prerelease': version_curr_p.is_prerelease,
                                    'urls': [url_info]
                                }
                            else:
                                urls = list(
                                    map(lambda x: x['full'], new_versions[version_curr]['urls']))
                                if url_filename not in urls:
                                    new_versions[version_curr]['urls'].append(
                                        url_info)
                                elif scheme not in new_versions[version_curr]['urls'][urls.index(url_filename)]['schemes']:
                                    new_versions[version_curr]['urls'][urls.index(url_filename)]['schemes'].append(scheme)

        # Sort by version desc
        new_versions = collections.OrderedDict(
            sorted(new_versions.items(), key=lambda x: parse_version(x[0]), reverse=False))

        return new_versions

    def _search_updates_wget(self):
        """ Search wget method: Call common method
        """
        return self._search_updates_common()

    def search_updates(self):
        """ Search for all new versions
        """
        cache_filename = 'versions.pkl'
        # if self._cache.check(cache_filename):
            # return self._cache.load(cache_filename)

        method = self.get_method()
        func_name = '_search_updates_' + method

        self._versions = None
        try:
            func = getattr(self, func_name)
        except AttributeError as e:
            _LOGGER.warning("Method '%s' was not found or during call: %s", method, e)
            return None

        self._versions = func()

        self._cache.save(cache_filename, self._versions)

        return self._versions

    def get_informations(self):
        depends = self.get_parser().get_var_values('DEPENDS', [])
        build_depends = self.get_parser().get_var_values('BUILD_DEPENDS', [])

        def flatten(l): return [item for sublist in l for item in sublist]

        # Split by space and flat the list
        depends = set(flatten([depend.split() for depend in depends]))
        build_depends = set(flatten([depend.split() for depend in build_depends]))
        all_depends = depends.union(build_depends)

        result = {
            "version": self.get_version(),
            "versions": self._versions,
            "method": self.get_method(),
            "depends": depends,
            "build_depends": build_depends,
            "all_depends": all_depends
        }

        return result
