# 최초 게시와 과거 도구

[English](history.md) | [한국어](history.ko.md)

## 최초 연동 기록

다음은 특정 시점의 관측 기록이며 실시간 상태 화면이 아니다. 한국 시간 2026-09-10,
중앙 commit `1191cea41d88f07497be04407b3c949ca8361733`의
[중앙 CI](https://github.com/novelKR/docs-actions/actions/runs/34385729100)가 성공했다.
[Gateway PR #52](https://github.com/novelKR/agent-response-gateway/pull/52)는
`653ce577c6a82280a88829d9bc55aa2058b36891`로 병합되었고, 해당 중앙 SHA를 사용한
[배포 작업](https://github.com/novelKR/agent-response-gateway/actions/runs/34432954753/job/102732854728)이
성공했다. 이는 Actions 결과 기록이며 모든 페이지의 브라우저 검수 완료를 뜻하지
않는다. 해당 중앙 판본의 라이선스는 AGPL-3.0-only였다.

[최초 출처 기록](../licensing/historical/PROVENANCE-v1.json)과
[원본 fixture](../tests/fixtures/gateway-reusable.yml)는 gateway commit
`41e1417a84ae7785e1450d2d35240fe0797c96bf`에서의 추출을 이력 복사 없이 보존한다.
운영 상태는 의도적으로 범용 재사용 계약에서 제외한다.

## 현재 연결 절차가 아닌 과거 명령

일반 소비자는 [README](../README.ko.md), SHA 갱신은 [유지보수](maintenance.ko.md)를
사용한다. 아래는 과거 도구의 기록이므로 이미 존재하는 저장소를 대상으로 명령 전체를
터미널에 복사해서 실행하지 않는다.

```text
python -B bootstrap/publish.py
python -B bootstrap/publish.py --apply
python -B bootstrap/publish.py --apply --existing-empty
python -B scripts/migrate_gateway.py --gateway /path/to/agent-response-gateway --central-commit <REVIEWED_FULL_COMMIT_SHA>
python -B scripts/migrate_gateway.py --gateway /path/to/agent-response-gateway --central-commit <REVIEWED_FULL_COMMIT_SHA> --apply
```

게시 도구의 기본 동작은 오프라인 dry run이다. `--apply`에서만 쓰기를 수행하며
novelKR로 인증한 사용자 GitHub CLI와 설정된 Git 작성자 정보를 사용한다. 새 공개
저장소 docs-actions를 독립된 최초 commit으로 만드는 데만 사용한다.
`--existing-empty`는 ref가 없는 공개 저장소를 요구한다. 공개 범위 변경, force push,
저장소 삭제, Pages 활성화나 보호 규칙 변경은 하지 않는다. 부분 실패 시 로컬
`.local/initial-repository`를 보존하고 상태를 조사한다. 증거를 지우고 무작정
재시도하지 않는다. 현재 중앙 저장소를 갱신하는 방법이 아니다.

Gateway 도구는 깨끗한 로컬 `codex/docs-pages-deployment` 브랜치와 정확한 과거
파일 blob 해시를 요구한다. 원격 workflow 바이트와 해당 중앙 main-push/`contracts`
CI 성공을 확인한 뒤 기본적으로 패치를 출력한다. `--apply`는 로컬 checkout만
수정하고 관련 테스트를 실행하며 commit, push, 병합이나 배포는 하지 않는다.
과거 브랜치 기준은 현재의 일반 운영 상태가 아니다. 변경·병합된 소스에 대한 거부는
의도한 동작이므로 해시 검사를 우회하지 않는다.

이 버전에서 도구와 오프라인 테스트는 MIT로 유지보수하지만 원본 과거 fixture와
라이선스 증거는 예외 조건을 유지한다. [선택 파일 목록](../bootstrap/source-files.json)은
그 고지를 포함한다. 자격 증명, 생성 사이트와 비공개 이력은 포함하지 않는다.
