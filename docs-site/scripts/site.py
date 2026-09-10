#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Allowlisted Markdown -> site inputs; exact output verification and static preview."""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
from urllib.parse import quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
BASE = '/docs-actions/'
REPOSITORY = 'https://github.com/novelKR/docs-actions'
SCHEMA = 'docs-actions-site/v1'
BLOCKED = {'.git', '.private', '.local', '.env', 'node_modules', '__pycache__'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique)


def safe_file(root, relative):
    require(isinstance(relative, str) and bool(relative), 'Missing source path')
    parts = PurePosixPath(relative).parts
    require(not relative.startswith('/') and '\\' not in relative and '..' not in parts,
            'Unsafe source path')
    require(not set(parts) & BLOCKED, 'Reserved source path')
    file = root.joinpath(*parts)
    for parent in (file, *file.parents):
        if parent == root:
            break
        require(not parent.is_symlink(), 'Source links are forbidden')
    require(file.resolve().is_relative_to(root.resolve()) and file.is_file(), 'Missing regular source file')
    require(file.stat().st_size <= 1024 * 1024, 'Source is too large')
    return file


def pages(root):
    registry = read_json(safe_file(root, 'docs-site/pages.json'))
    require(set(registry) == {'schema', 'pages'} and registry['schema'] == 'docs-actions-pages/v1', 'Invalid page registry')
    require(isinstance(registry['pages'], list) and 0 < len(registry['pages']) <= 100, 'Invalid page count')
    result, ids, paths = [], set(), set()
    for entry in registry['pages']:
        require(set(entry) == {'id', 'en', 'ko'}, 'Invalid registry entry')
        ident = entry['id']
        require(isinstance(ident, str) and re.fullmatch(r'[a-z][a-z0-9-]*', ident) and ident not in ids, 'Duplicate or invalid page ID')
        ids.add(ident)
        for locale in ('en', 'ko'):
            source = entry[locale]
            require(isinstance(source, str) and source.endswith('.md') and source not in paths, 'Invalid or duplicate Markdown source')
            require(source in {'README.md', 'README.ko.md'} or source.startswith('docs/'), 'Not a maintained document')
            paths.add(source)
            raw = safe_file(root, source).read_bytes()
            text = raw.decode('utf-8')
            heading = re.search(r'^# (.+)$', text, re.M)
            require(heading is not None, 'Missing document title')
            prefix = '/ko' if locale == 'ko' else ''
            result.append({'id': ident, 'locale': locale, 'source': source,
                           'title': heading[1], 'route': prefix + '/guide/' + ident,
                           'copy': 'sources/' + locale + '/' + ident + '.md', 'sha256': digest(raw)})
    return result


def remap(text, source, routes, root, commit):
    """Rewrite prose links, not code examples. Keep the original file for copying."""
    def link(match):
        label, target = match.groups()
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc:
            require(parsed.scheme in {'https', 'http', 'mailto'} and not target.startswith('//'), 'Unsupported link scheme')
            return match[0]
        if not parsed.path:
            return match[0]
        path = (root / source).parent / unquote(parsed.path)
        # Resolve '..' in legitimate documentation links but never follow symlinks.
        normalized = Path(__import__('os').path.normpath(path))
        require(normalized.is_relative_to(root) and not set(normalized.relative_to(root).parts) & BLOCKED, 'Link escapes public sources')
        relative = normalized.relative_to(root).as_posix()
        safe_file(root, relative)
        suffix = ('?' + parsed.query if parsed.query else '') + ('#' + parsed.fragment if parsed.fragment else '')
        url = routes[relative] if relative in routes else REPOSITORY + '/blob/' + commit + '/' + quote(relative, safe='/')
        return '[' + label + '](' + url + suffix + ')'

    def prose(value):
        require('<<<' not in value and '{{' not in value, 'Includes and Vue expressions are not allowed in documents')
        # Explicit id-only anchors are the sole supported raw HTML form.
        sanitized = re.sub(r'<a id="[\w-]+"></a>', '', value)
        require(not re.search(r'<\s*/?\s*[A-Za-z!]', sanitized), 'Raw HTML or components are not allowed')
        require('![' not in value, 'Unreviewed page resources are not allowed')
        require(not re.search(r'^\s*\[[^]]+\]:', value), 'Use inline Markdown links, not reference definitions')
        return re.sub(r'\[([^]\n]+)\]\(([^)\s]+)\)', link, value)

    lines, fence = [], None
    for line in text.splitlines(keepends=True):
        marker = re.match(r'^\s*(`{3,}|~{3,})(.*)$', line)
        if marker and fence is None:
            fence = marker[1]
            lines.append(line)
            continue
        if fence:
            lines.append(line)
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            continue
        # Inline code is kept byte-for-byte, including placeholder angle brackets.
        pieces = re.split(r'(`+[^`\n]+`+)', line)
        lines.append(''.join(part if part.startswith('`') else prose(part) for part in pieces))
    require(fence is None, 'Unclosed fenced code block')
    return ''.join(lines)


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()


def prepare(root=ROOT):
    root = root.resolve()
    commit = git(root, 'rev-parse', 'HEAD')
    require(re.fullmatch('[0-9a-f]{40}', commit), 'Expected committed source')
    dirty = bool(git(root, 'status', '--porcelain', '--untracked-files=normal'))
    inventory = pages(root)
    work = root / '.local/docs-site'
    require(not (root / '.local').is_symlink() and not work.is_symlink(), 'Build directories cannot be symlinks')
    source = work / 'source'
    require(not source.is_symlink(), 'Build source cannot be a symlink')
    if source.exists():
        shutil.rmtree(source)
    source.mkdir(parents=True)
    routes = {p['source']: p['route'] for p in inventory}
    for p in inventory:
        raw = safe_file(root, p['source']).read_bytes()
        body = remap(raw.decode('utf-8'), p['source'], routes, root, commit)
        dest = source / (p['route'].lstrip('/') + '.md')
        dest.parent.mkdir(parents=True, exist_ok=True)
        front = {'title': p['title'], 'docLocale': p['locale'], 'copyPath': '/' + p['copy'], 'sourceCommit': commit}
        dest.write_text('---\n' + '\n'.join(k + ': ' + json.dumps(v, ensure_ascii=False) for k, v in front.items()) + '\n---\n\n' + body, encoding='utf-8')
        copy = source / 'public' / p['copy']
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_bytes(raw)
    for locale, tagline, labels in (
        ('en', 'Build once. Verify. Publish with your own permissions.', ['Start here', 'Deployment contract', 'Maintain your pin', 'Small by design']),
        ('ko', '한 번 빌드하고 검증한 뒤, 자신의 권한으로 게시합니다.', ['시작하기', '배포 계약', '버전 관리', '작은 책임 범위'])):
        prefix = '/ko' if locale == 'ko' else ''
        data = {'layout': 'home', 'docLocale': locale,
                'hero': {'name': 'docs-actions', 'text': 'Caller-owned Pages' if locale == 'en' else '저장소가 소유하는 배포', 'tagline': tagline,
                         'actions': [{'theme': 'brand', 'text': labels[0], 'link': prefix + '/guide/getting-started'},
                                     {'theme': 'alt', 'text': 'GitHub', 'link': REPOSITORY}]},
                'features': [{'title': labels[1], 'details': 'PR → Build → Verify → Artifact → Pages', 'link': prefix + '/guide/site'},
                             {'title': labels[2], 'details': 'SHA · CI · Review', 'link': prefix + '/guide/maintenance'},
                             {'title': labels[3], 'details': 'No checkout · No rebuild · No shared PAT', 'link': prefix + '/guide/licensing'}]}
        # JSON is valid YAML and avoids interpolating document text as executable code.
        home = source / (prefix.lstrip('/') + '/' if prefix else '') / 'index.md'
        home.parent.mkdir(parents=True, exist_ok=True)
        home.write_text('---\n' + json.dumps(data, ensure_ascii=False, indent=2) + '\n---\n', encoding='utf-8')
    (source / 'public').mkdir(exist_ok=True)
    shutil.copyfile(root / 'LICENSE', source / 'public/LICENSE.txt')
    record = {'schema': SCHEMA, 'source_commit': commit, 'working_tree': dirty, 'pages': inventory}
    (work / 'catalogue.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return record


class HTML(HTMLParser):
    def __init__(self, raw):
        super().__init__(convert_charrefs=True)
        self.ids, self.links, self.resources = set(), [], []
        self.feed(raw.decode('utf-8'))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        if tag == 'a' and 'href' in attrs:
            self.links.append(attrs['href'])
        if tag in {'script', 'img', 'source', 'iframe', 'video', 'audio'} and 'src' in attrs:
            self.resources.append(attrs['src'])
        if tag == 'link' and set(attrs.get('rel', '').split()) & {'stylesheet', 'modulepreload', 'preload', 'icon'}:
            self.resources.append(attrs.get('href', ''))


def inventory(directory, catalog, root=ROOT):
    require(directory.is_dir() and not directory.is_symlink(), 'Missing regular site directory')
    expected = {'index.html', 'ko/index.html', '404.html'} | {p['route'].lstrip('/') + '.html' for p in catalog['pages']}
    required = expected | {p['copy'] for p in catalog['pages']} | {'LICENSE.txt', 'web-notices.txt', 'web-dependencies.json'}
    allowed = required | {'hashmap.json', 'vp-icons.css', 'build-manifest.json'}
    files, html = {}, {}
    for path in sorted(directory.rglob('*')):
        require(not path.is_symlink(), 'Symlink in published output')
        if path.is_dir():
            continue
        require(path.is_file() and path.stat().st_nlink == 1, 'Only regular non-linked files may be published')
        name = path.relative_to(directory).as_posix()
        require(name in allowed or re.fullmatch(r'assets/(?:chunks/)?[@A-Za-z0-9_.-]+\.(?:js|css)', name), 'Unexpected publication file: ' + name)
        raw = path.read_bytes()
        require(len(raw) <= 16 * 1024 * 1024, 'Published file too large')
        require(str(root.resolve()).encode() not in raw, 'Local build path leaked')
        if name != 'build-manifest.json':
            files[name] = digest(raw)
        if name.endswith('.html'):
            html[name] = HTML(raw)
    require(set(html) == expected and required <= set(files), 'Missing or unexpected pages/notices')
    for p in catalog['pages']:
        require(files[p['copy']] == p['sha256'], 'Copied Markdown differs from selected source')
    for name, page in html.items():
        for resource in page.resources:
            require(resource.startswith(BASE) and not urlsplit(resource).netloc, 'Nonlocal page resource')
            require(unquote(urlsplit(resource).path[len(BASE):]) in files, 'Missing local resource')
        for link in page.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                require(url.scheme in {'https', 'http', 'mailto'}, 'Invalid link scheme')
                continue
            target = name
            if url.path:
                require(url.path.startswith(BASE), 'Link escapes the site base')
                target = unquote(url.path[len(BASE):])
                if not target or target.endswith('/'):
                    target += 'index.html'
                elif target not in files and not Path(target).suffix:
                    target += '.html'
            require(target in files, 'Broken local link: ' + target)
            if url.fragment and target in html:
                require(unquote(url.fragment) in html[target].ids, 'Broken local anchor: ' + target)
    return dict(sorted(files.items()))


def verify(root=ROOT, record=False, commit=None):
    catalog = read_json(root / '.local/docs-site/catalogue.json')
    directory = root / '.local/docs-site/dist'
    require(catalog['schema'] == SCHEMA, 'Unknown catalogue schema')
    files = inventory(directory, catalog, root)
    manifest = {key: catalog[key] for key in ('schema', 'source_commit', 'working_tree')}
    manifest['sources'] = {p['source']: p['sha256'] for p in catalog['pages']}
    manifest['files'] = files
    for source, sha in manifest['sources'].items():
        require(digest(safe_file(root, source).read_bytes()) == sha, 'Sources changed after preparation')
    if commit is not None:
        require(not record, 'Publication verification cannot rewrite its evidence')
        require(re.fullmatch(r'[0-9a-f]{40}', commit) and manifest['source_commit'] == commit, 'Publication commit mismatch')
        require(git(root, 'rev-parse', 'HEAD') == commit, 'Checkout does not match publishing commit')
        require(manifest['working_tree'] is False and not git(root, 'status', '--porcelain', '--untracked-files=normal'), 'Publication source is dirty')
    path = directory / 'build-manifest.json'
    if record:
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    else:
        require(read_json(path) == manifest, 'Build manifest differs from verified output')
    print(f'Site verified: {len(files)} hashed files, {sum(n.endswith(".html") for n in files)} HTML pages')
    return manifest


def handler(directory, manifest):
    class Static(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urlsplit(self.path)
            path = unquote(url.path)
            if not path.startswith(BASE) or '\\' in path or '..' in PurePosixPath(path).parts:
                self.send_error(404)
                return
            relative = path[len(BASE):]
            relative = relative + 'index.html' if not relative or relative.endswith('/') else relative
            if relative not in manifest['files'] and not Path(relative).suffix:
                relative += '.html'
            if relative not in manifest['files']:
                self.send_error(404)
                return
            file = directory / relative
            try:
                require(not any(p.is_symlink() for p in (file, *file.parents)), 'Linked preview file')
                raw = file.read_bytes()
                require(digest(raw) == manifest['files'][relative], 'Modified preview file')
            except (OSError, ValueError):
                self.send_error(409)
                return
            mime = {'.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json'}.get(file.suffix, 'text/plain')
            self.send_response(200)
            self.send_header('Content-Type', mime + '; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *_args):
            pass
    return Static


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'check', 'record', 'preview'])
    parser.add_argument('--commit')
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            prepare()
        elif args.command == 'preview':
            manifest = verify()
            print('Verified preview: http://127.0.0.1:43141' + BASE, flush=True)
            ThreadingHTTPServer(('127.0.0.1', 43141), handler(ROOT / '.local/docs-site/dist', manifest)).serve_forever()
        else:
            verify(record=args.command == 'record', commit=args.commit)
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print('Site check failed: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
