# docs-actions

[English](README.md) | [한국어](README.ko.md)

각 소비 저장소가 자신의 GitHub Pages를 배포하도록 하는 공통 인프라다.
예정된 공개 저장소 이름은 `novelKR/docs-actions`다. 이 소스 패키지가 있다는
사실만으로 원격 저장소·릴리스·실제 Pages 배포가 존재한다고 볼 수는 없다.

## 책임 경계

문서 원본, 프레임워크, 빌드, 무결성·공개 경계 검사, Pages 산출물,
실제 사이트와 `github-pages` 환경은 각각의 소비 저장소가 소유한다.
중앙 저장소는 **배포 구현과 그 검증**만 담당한다. 문서를 모으는 포털이나
다른 저장소를 대신 관리하는 서버가 아니며, 소비자 인증정보도 보관하지 않는다.

```text
소비 저장소 PR -> 읽기 전용 빌드·검사 -> 검토 산출물 보관; 배포 없음
소비 저장소 main -> 한 번 빌드 -> 검증 -> Pages 산출물 -> 필수 CI 통과
                                                    -> 중앙 workflow 호출
                                                    -> 소비 저장소의 Pages
```

공통 workflow는 소스를 checkout하거나, 빌드 명령·패키지 설치를 실행하거나,
애플리케이션 secret·PAT를 받지 않는다. 다른 저장소, 다른 실행의 산출물,
다른 배포 환경도 선택할 수 없다. 호출자의 토큰과 저장소 문맥을 사용한다.
중앙 자체 CI는 `contents: read`만 가지며, 실제 게시 권한은 소비 저장소의
배포 작업에만 부여한다.

## 배포 계약 v1

[공통 workflow](.github/workflows/reusable-pages-deploy.yml)와
[기계 판독용 계약](contracts/pages-deploy-v1.json)을 함께 관리한다.

| 항목 | 계약 |
| --- | --- |
| `artifact-name` | 문자열, 기본 `github-pages`; 호출자의 같은 실행에서 이미 업로드된 산출물 |
| `publication-branch` | 문자열, 기본 `main`; 소비 저장소 환경의 허용 브랜치도 별도로 제한 |
| `page-url` | 공식 Pages 배포 성공 시 반환하는 주소 |
| 권한 | 호출자의 배포 작업에만 `pages: write`, `id-token: write` |
| 허용 이벤트 | 게시 브랜치의 `push` 또는 `workflow_dispatch` |
| 환경 | 호출자 저장소의 고정 `github-pages` |
| 빌드·검사 | 호출자 책임; 공통 workflow 호출 전에 완료 |
| 실행 | 전체 SHA로 고정한 `actions/deploy-pages` 단계 하나, GitHub-hosted runner |

산출물 이름만으로 검토 여부를 증명할 수는 없다. 소비 저장소에서 빌드 명세를
대상 commit과 연결하고, 파일 해시·공개 경계를 검증한 뒤 필수 검사 통과 후
호출해야 한다. 사람의 공개 승인이 필요하면 해당 소비 저장소의 배포 환경에서
강제한다. `pull_request_target`이나 신뢰되지 않은 PR 산출물 승격에 사용하지 않는다.

저장소별 배포 동시 실행 그룹은 동시에 게시하는 것을 막지만, 최신 commit이
항상 마지막에 게시된다는 순서 보장까지 제공하지 않는다. 소비 저장소의 main
실행 직렬화를 유지한다. 과거 main 실행을 의도적으로 재실행하면 오래된 내용이
게시될 수 있다. 다른 실행의 산출물을 가져오는 롤백 기능은 포함하지 않는다.

## 중앙 저장소 최초 게시

Python 3.11 이상, Git, 전역 Git 작성자 이름·이메일 설정, `github.com`에
`novelKR`로 인증된 GitHub CLI가 필요하다. 해당 인증에는 저장소 생성과
workflow 파일 push 권한이 있어야 한다. 토큰을 소스나 대화에 붙여 넣지 않는다.
이 초기 게시용 인증은 실제 공통 배포 workflow에는 필요하지 않다.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-ci.txt
python -B -m unittest discover -s tests -v
python -B scripts/check_contract.py
python -B bootstrap/publish.py
```

마지막 명령은 **로컬 사전 검사**다. GitHub 조회나 원격 변경을 하지 않는다.
선택된 소스를 검토한 뒤 다음 명령으로 명시적으로 게시한다.

```sh
python -B bootstrap/publish.py --apply
```

새 **공개** 저장소 `novelKR/docs-actions`를 생성하고, 선택된 소스만으로 독립된
최초 commit을 만든 뒤 강제 push 없이 `main`에 올린다. gateway 이력은 복사하지
않는다. 작성자 정보는 사용자의 Git 설정을 사용하며 이름·이메일을 만들어 내거나
전역 Git 설정을 변경하지 않는다. 파일 목록에는 `.git`, `.local`, 비공개 파일,
설치 패키지가 포함되지 않는다. symlink와 안전하지 않은 경로도 거부한다.

이미 직접 생성했지만 완전히 비워 둔 공개 저장소를 사용할 때는 다음과 같다.

```sh
python -B bootstrap/publish.py --apply --existing-empty
```

비공개이거나 기존 ref가 있는 저장소는 거부한다. 공개 범위를 바꾸지 않는다.
부분 실패 시 `.local/initial-repository`를 보존하여 점검·수동 복구할 수 있게 한다.
생성한 원격 저장소를 삭제하거나 변경을 무조건 재시도하지 않는다. 원격 상태를
이해하기 전에 보존된 디렉터리를 지우지 않는다.

생성된 중앙 저장소의 `CI`와 `contracts` 작업 결과를 확인한다. 소스 push는
CI 성공, 태그·릴리스 생성 또는 실제 사이트 배포를 의미하지 않는다.
실제 소스 SHA는 `.local/published.json`에 기록하며 존재하지 않는 SHA를 쓰지 않는다.

## 첫 소비 저장소 연결

준비한 이관 도구는 commit `41e1417a84ae7785e1450d2d35240fe0797c96bf`에서 확인한
`agent-response-gateway`의 기존 PR #52, `codex/docs-pages-deployment` 브랜치를
대상으로 한다. 다른 저장소는 등록하지 않는다.

중앙 CI가 성공한 뒤, 기존 PR 브랜치를 로컬에 checkout하고 변경 사항이 없는
상태에서 다음을 실행한다.

```sh
python -B scripts/migrate_gateway.py --gateway /path/to/agent-response-gateway
```

초기 게시 기록에서 실제 중앙 SHA를 읽고, 공개 원격 workflow의 바이트,
그 commit의 main push CI 및 `contracts` 성공 여부, gateway origin·브랜치와
알려진 소스 blob 해시를 확인한 뒤 패치를 출력한다. `--apply` 없이는 로컬·원격
gateway를 수정하지 않는다.

```sh
python -B scripts/migrate_gateway.py --gateway /path/to/agent-response-gateway --apply
```

패치는 호출부를 중앙 전체 SHA로 고정하고 로컬 실행용 workflow 사본을 제거한다.
소비자 lock, 검증된 비실행용 snapshot을 기록하고 기존 계약 테스트를 그 구조에
맞춘다. snapshot은 오프라인 검사 fixture이지 두 번째 실행 workflow가 아니다.
로컬 적용 후 해당 gateway 테스트를 실행한다. commit·push·병합은 자동 수행하지
않는다. diff를 검토하고 전체 gateway 검사를 실행한 뒤 PR #52를 갱신한다.
알려진 소스 blob이 달라졌으면 새 작업을 덮어쓰지 않고 명시적으로 중단한다.
PR #52가 이미 병합되었거나 변경되었다면 이관 내용을 새로 검토해야 한다.

`--central-commit <REVIEWED_FULL_COMMIT_SHA>`로 검토한 실제 SHA를 직접 지정할
수도 있다. 브랜치나 태그와 같은 변경 가능한 ref는 거부한다. 중앙 저장소가 없거나
중앙 CI가 진행 중·실패 상태이면 이관을 허용하지 않는다. PR에서 배포 작업을
건너뛴다는 이유로 존재하지 않는 공통 workflow를 참조하지 않는다.

## 다른 저장소와 업데이트

각 저장소의 빌더가 검증한 Pages 산출물을 업로드하고 필수 검사에 통과한 뒤
[호출 작업 예시](examples/caller-job.yml.example)를 사용한다. 예시는 완전한
workflow가 아니며 SHA 자리는 실제로 없는 commit을 만들어 넣지 않은 표시자다.

소비 저장소는 VitePress·MkDocs 등 기존 빌드 방식, base path, 고지와 무결성
검사를 유지한다. 배포를 위해 PAT나 중앙 저장소 쓰기 권한을 가질 필요는 없다.
공개 소비 저장소에서는 Actions 정책이 이 공개 workflow 사용을 허용해야 한다.

중앙 workflow는 검토한 전체 commit SHA로 고정한다. 따라서 중앙 변경이
모든 소비 저장소에 **몰래 일괄 전파되지 않는다**. 소비 저장소 PR과 검사로
새 SHA를 채택하며, 필요하면 PR로 pin을 되돌린다. `v1`은 인터페이스 계약의
버전이지 실제 Git 태그가 존재한다는 뜻이 아니다. Dependabot은 중앙 저장소의
Actions·CI 전용 파서 갱신 PR을 제안할 뿐, 자동 병합·승인이나 소비자 자동
업그레이드를 하지 않는다.

실제 게시 전에 각 소비 저장소에서 Pages의 Source를 GitHub Actions로 설정하고,
`github-pages` 환경의 허용 브랜치를 게시 브랜치로 제한한다. 필요하면 필수
검토자를 설정한다. 중앙 `main`에는 `contracts` 필수 검사와 코드 소유자 검토를
설정한다. [CODEOWNERS](.github/CODEOWNERS)만 추가한다고 보호 규칙이 켜지지는
않는다. 이 패키지의 도구는 해당 관리 설정을 변경하지 않는다.

## 검증과 출처

중앙 테스트는 YAML을 파싱하고 권한·이벤트·산출물·pinning·초기 게시·이관의
실패 경계를 확인한다. **오프라인 소스 계약 검사**이며 GitHub의 전체 workflow
스키마 검증, 저장소 간 OIDC 검사, 실제 Pages 배포를 대체하지 않는다.
기본 테스트는 실제 외부 호출을 하지 않는다. `PyYAML==6.0.3`은 버전을 고정한
개발 의존성이며, 배포 runtime 의존성이나 해시까지 잠근 의존성 집합은 아니다.

추출한 workflow의 실행 YAML은 기존 gateway 버전과 동일하다.
[PROVENANCE.json](PROVENANCE.json)에 원본 commit과 blob을 기록했다.
[LICENSE](LICENSE)는 원본 AGPL-3.0 전문과 바이트 단위로 동일하고 코드는
AGPL-3.0-only를 유지한다. 별도 상용 권한이나 법적 승인을 뜻하지 않는다.
GitHub Actions는 참조만 하며 소스를 vendor하지 않는다. 글꼴 파일과 생성된
문서 사이트는 포함하지 않는다.

[저장소 지침](AGENTS.md)과 [보안 경계](SECURITY.md)를 함께 참조한다.

## 공식 참고 자료

- [재사용 workflow 접근·문맥·권한](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations)
- [GitHub Pages 산출물·배포 요구](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [GitHub CLI API 호출](https://cli.github.com/manual/gh_api)
- [저장소 생성 API](https://docs.github.com/en/rest/repos/repos#create-a-repository-for-the-authenticated-user)
- [고정한 CI 파서](https://pypi.org/project/PyYAML/6.0.3/)
