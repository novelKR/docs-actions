# 문서 사이트 운영

[English](site.md) | [한국어](site.ko.md)

사이트는 이 저장소에서 선택한 영문·한국어 Markdown을 VitePress로 빌드한다.
문서와 빌드 도구는 소비자인 이 저장소가 소유하며, 게시는 다른 저장소에도
제공하는 동일한 공통 배포 계약을 사용한다.

## 빌드와 미리보기

Node 24.21.0, npm 11.19.0, Python 3.11 이상을 사용한다. 빌드 중 커밋된 npm
lock과 웹 고지 원문을 검증한다. PATH에는 고정한 Node 실행 파일을 두고,
Python 실행 파일 이름이 다르면 DOCS_PYTHON을 설정한다.

```sh
python3.14 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-ci.txt
python -B -m unittest discover -s tests -v
python -B scripts/check_contract.py
npm ci --prefix docs-site --ignore-scripts
npm test --prefix docs-site
npm run build --prefix docs-site
python -B docs-site/scripts/site.py check
python -B docs-site/scripts/site.py preview
```

미리보기는 http://127.0.0.1:43141/docs-actions/ 에서 검증한 파일만 제공한다.
자동 재빌드나 hot reload는 없으므로 소스 수정 후 다시 빌드한다. 개발 서버를
공개 사이트로 노출하지 않는다. 생성 파일은 .local/ 아래에 둔다.

## 원본과 사용자 인터페이스

[pages.json](../docs-site/pages.json)이 다섯 가이드의 대응 언어판을 선택한다.
두 언어 모두 탐색, 로컬 검색, 소스 링크와 Markdown 원문 복사를 제공한다.
복사할 때 브라우저는 현재 페이지에 대응하는 선택된 Markdown을 가져오며,
클립보드 권한 실패는 화면에 표시한다. 검색은 브라우저의 로컬 색인을 사용한다.
사이트 경로는 /docs-actions/ 와 /docs-actions/ko/ 이다.

## 게시와 승인

Documentation site workflow는 PR에서 읽기 전용 권한으로 계약·사이트 검사를
실행하고 검토용 산출물을 보관한다. main push 또는 main 수동 실행에서는 정확한
소스 commit과 깨끗한 checkout을 추가 확인한 뒤 검증한 같은 디렉터리를 포장한다.
배포 작업은 pages: write와 id-token: write를 가지고 같은 commit의 로컬 공통
workflow를 호출한다. 공통 workflow가 문서 workflow를 다시 호출하지 않는다.

최초 배포 전에 이 저장소의 Pages 소스를 GitHub Actions로 설정한다.
github-pages 환경을 main 브랜치로 제한하고 필요한 검토자 정책을 선택한다.
검토자는 해당 배포 실행만 승인하며 미래 실행을 승인하지 않는다. 최초 성공 후
contracts와 docs-build를 PR 필수 검사로 유지한다. 이는 관리 설정이며 문서
빌드가 직접 수행하지 않는다.

승인 후 실제 URL, 두 언어 페이지와 build-manifest.json을 확인한다. source_commit을
배포 commit과 대조하고 파일 해시를 같은 CI 실행의 검토 산출물과 비교한다.
CI 성공만으로 실제 게시를 증명하지 않는다. 과거 main 실행을 다시 실행하면
이전 내용이 게시될 수 있다. [유지보수 안내](maintenance.md)를 참고한다.

## 소스와 의존성 고지

사이트 구현은 MIT로 독립 관리한다. 설계 참조와 빌드 버전은
[사이트 출처](../docs-site/PROVENANCE.json)에 기록한다.
[고지 정책](../docs-site/licensing/policy.json)은 실제 전달되는 클라이언트 패키지와
내장 아이콘의 고지 원문을 고정한다. 생성 사이트에는 LICENSE.txt,
web-notices.txt, web-dependencies.json을 포함한다. 대응 소스와 조건을 검토하지
않고 변경된 고지 해시를 기록하지 않는다. 저장소 전체에는 [라이선스 범위](licensing.md)의
과거 AGPL 예외 자료도 보존하며, 이를 사이트 구현으로 묶어 제공하지 않는다.

## 개발 의존성 보안 공지

고정된 VitePress 1.6.4 의존성에는 Vite와 esbuild 개발 서버에 대한 npm audit
경고가 있다. 지원하는 절차는 정적 파일을 빌드하고 검증된 Python 서버로
미리보며, Vite나 esbuild 개발 서버를 실행하지 않는다. 이 미리보기를 외부에
노출한 Vite 개발 서버로 대체하지 않는다. 이 제한은 의존성 패치가 아니므로
호환되는 도구 모음 업그레이드는 별도로 검토하고 의존성 검토에서 경고를
명시한다. [Vite 공지](https://github.com/vitejs/vite/security/advisories/GHSA-fx2h-pf6j-xcff)와
[esbuild 공지](https://github.com/evanw/esbuild/security/advisories/GHSA-67mh-4wv8-2f99)를 참고한다.
