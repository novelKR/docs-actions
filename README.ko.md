# docs-actions

[English](README.md) | [한국어](README.ko.md)

독립된 저장소들이 자신의 GitHub Pages를 게시할 때 사용하는 배포 전용 workflow다.
각 소비 저장소가 사이트를 빌드·검증하며, 이 저장소는 마지막 배포 작업만 제공한다.
통합 문서 포털이나 자격 증명을 모으는 중앙 서버가 아니다.

유지보수 구현·문서·예제는 **MIT**다. 과거 AGPL 증거는 명시적으로 제외한다.
[라이선스 범위](docs/licensing.ko.md)를 확인한다. 이 변경은 gateway 프로젝트의
라이선스나 이미 고정된 소비 저장소의 SHA를 변경하지 않는다.

## 소비 저장소에서 사용

먼저 Pages의 게시 원본을 GitHub Actions로 설정하고, 게시 브랜치를 보호하며,
소비 저장소의 `github-pages` 환경을 해당 브랜치로 제한한다. 공개에 사용자 승인이
필요하면 환경의 필수 검토자를 지정한다. CODEOWNERS만으로 이 설정이 강제되지는
않는다. 소비 저장소의 Actions 정책에서 이 공개 reusable workflow를 허용한다.

다음 단계는 소비 저장소 자체 workflow에 둔다.

```text
PR -> read-only build and verification -> review artifact; no deployment
main -> build once -> verify source and file hashes -> Pages artifact
     -> required CI gate -> pinned central workflow -> consumer's Pages site
```

정확한 산출물 파일, 명세의 소스 SHA, 깨끗한 빌드 출처, 공개·라이선스 경계를 검증한
뒤 `actions/upload-pages-artifact`로 올린다. 업로드 Action도 검토한 전체 SHA로
고정한다. 실행 안에서 고유한 산출물 이름을 사용하고, 예상 승인 대기보다 긴 보존
기간을 정한다. 빌드·업로드에는 Pages 쓰기 권한이 필요 없다. 권한이 있는 배포
작업에서 재빌드하거나 신뢰하지 않는 PR 산출물을 승격하지 않는다.

다음 **작업 조각**을 기존 빌드와 필수 검사 작업 뒤, 호출자의 `jobs:` 아래에 넣는다.
표시자는 코드·라이선스 범위·중앙 CI를 검토한 실제 전체 commit SHA로 교체한다.
표시자는 존재하는 태그나 릴리스가 아니며, 이 조각은 독립된 전체 workflow가 아니다.

```yaml
# SPDX-License-Identifier: MIT
# Insert AFTER your repository-specific build and required gate jobs.
# Replace the explicit marker with a reviewed, real 40-character commit SHA.
# This is a job fragment, NOT a complete runnable workflow.
docs-pages:
  needs: ci-required
  if: >-
    (github.event_name == 'push' || github.event_name == 'workflow_dispatch') &&
    github.ref == 'refs/heads/main'
  permissions:
    pages: write
    id-token: write
  uses: novelKR/docs-actions/.github/workflows/reusable-pages-deploy.yml@<REVIEWED_FULL_COMMIT_SHA>
  with:
    artifact-name: github-pages
    publication-branch: main
```

`ci-required`는 빌드·공개 검사 성공을 요구해야 하며 검사 생략이나 실패가 배포를
차단해야 한다. 호출하는 배포 작업에만 `pages: write`와 `id-token: write`를 준다.
`secrets: inherit`는 사용하지 않는다. 소비 저장소마다 도구 버전, 기준 경로,
고지, 산출물 검사와 사이트 설정을 유지한다. 새 SHA 채택 전
[유지보수·고정 SHA 갱신](docs/maintenance.ko.md)을 확인한다.

## 계약 v1

[기계 판독 계약](contracts/pages-deploy-v1.json) ·
[Workflow](.github/workflows/reusable-pages-deploy.yml)

| 항목 | 값 |
| --- | --- |
| `artifact-name` | 선택 문자열, 기본 `github-pages`, 현재 호출자 실행의 산출물만 사용 |
| `publication-branch` | 선택 문자열, 기본 `main`, 환경의 브랜치 제한도 일치해야 함 |
| `page-url` | 공식 Pages 배포 성공 시 반환하는 출력 |
| 이벤트 | 게시 브랜치의 `push` 또는 `workflow_dispatch` |
| 환경 | 호출자 저장소의 고정된 `github-pages` |
| 권한 | 배포 작업의 `pages: write`, `id-token: write` |
| 실행 | 전체 SHA로 고정한 공식 `actions/deploy-pages` 단계 하나 |

checkout, 빌드 명령, 패키지 설치, PAT 입력, 애플리케이션 secret 상속, 다른 저장소
선택, 다른 실행의 산출물, preview와 환경 변경을 제공하지 않는다. 산출물 이름은
검토 증거가 아니다. 검증과 승인은 호출자의 책임이다. GitHub는 호출자 저장소
문맥으로 reusable workflow를 실행하며, 중앙 CI 자체는 읽기 전용이다.

배포는 저장소별 `github-pages` 동시 실행 그룹을 공유하며 진행 중인 배포를 취소하지
않는다. 이는 **최신 커밋 우선 게시 보장**이 아니다. 호출자의 main 실행 직렬화를
유지한다. 과거 main 실행을 의도적으로 재실행하면 과거 내용이 게시될 수 있다.
전체 호출자 workflow의 동시 실행 그룹을 배포 그룹과 같게 두지 않는다.
다른 실행의 산출물을 사용한 복구는 이 계약 범위 밖이다.

## 개발과 검증

테스트에는 Python 3.11+와 Git이 필요하다. 배포 작업은 Python이나 이 저장소의
의존성을 설치하지 않는다.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-ci.txt
python -B -m unittest discover -s tests -v
python -B scripts/check_contract.py
```

CI 전용 PyYAML은 버전 고정이며 해시 잠금은 아니다. 테스트는 YAML, 금지 기능,
전체 계약 일치, 과거 증거, 라이선스 표지와 두 언어 예제를 검사한다. 원격 SHA의
실존, 법적 권리, 사용자 승인, GitHub OIDC 동작이나 실제 배포를 증명하지 않는다.

일반 개발에서는 최초 게시 도구나 gateway 이관 도구를 실행하지 않는다. 이들은
특정 기준 버전의 과거 복구 도구로 보존한다. [최초 게시 이력](docs/history.ko.md)은
최초 중앙 CI와 소비자 배포를 기록하며 지속적인 정상 상태를 주장하지 않는다.

## 라이선스와 기여

유지보수 코드나 예제를 복사할 때 MIT 저작권·허가 고지를 보존한다. workflow 호출이
소비자의 독립된 코드·문서 라이선스를 바꾸지는 않는다. 저장소 전체를 복사하면
과거 예외 자료의 고지도 보존해야 한다. 제3자 Actions·의존성은 각자의 라이선스를
유지한다. [LICENSE](LICENSE), [라이선스 범위](docs/licensing.ko.md),
[PROVENANCE.json](PROVENANCE.json)을 확인한다.

해당 파일의 조건으로 제공할 권한이 있는 기여만 제출하고 외부 출처와 조건을 밝힌다.
CI 통과는 저작권 양도, 상용 예외, CLA 체결이나 법적 승인을 의미하지 않는다.
[저장소 지침](AGENTS.md)과 [보안 경계](SECURITY.md)를 확인한다.

## 공식 자료

[재사용 workflow 문맥·권한](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations) ·
[Pages 산출물·배포 요구사항](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) ·
[MIT 라이선스](https://opensource.org/license/mit)
