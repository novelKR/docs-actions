# 라이선스 범위와 전환

[English](licensing.md) | [한국어](licensing.ko.md)

## 유지보수 구현

이 버전의 docs-actions workflow, Python 도구, 테스트, 문서와 예제는 아래 과거 자료를
제외하고 [MIT 라이선스](../LICENSE)로 제공한다. 이 저장소만의 라이선스 전환이며
agent-response-gateway나 GitHub Actions의 라이선스를 바꾸는 작업은 아니다.
작은 배포 구성 요소와 호출 예제를 쉽게 재사용하면서 저작권·허가·무보증 고지를
유지할 수 있도록 MIT를 선택한다.

유지보수 구현이나 예제의 상당 부분을 복사할 때 MIT 저작권·허가 고지를 포함한다.
MIT에 따른 상업적 이용이 가능하며 이 저장소가 별도 유료 허가를 요구하지 않는다.
배포 workflow를 호출한다고 독립적으로 작성한 소비자 코드·문서·정적 산출물에 MIT가
강제되지 않는다. 사이트에 포함한 제3자 코드와 자산의 조건은 별도로 유지된다.

## 과거 자료 예외

| 자료 | 유지하는 조건과 목적 |
| --- | --- |
| [원본 workflow fixture](../tests/fixtures/gateway-reusable.yml) | AGPL-3.0-only, 실행용 workflow가 아닌 출처 증거 |
| [Fixture 고지](../tests/fixtures/gateway-reusable.yml.license) | 원본 fixture를 복사할 때 함께 유지 |
| [최초 출처 기록](../licensing/historical/PROVENANCE-v1.json) | 변경하지 않은 과거 AGPL-3.0-only 기록 |
| [원본 AGPL 본문](../licensing/historical/AGPL-3.0.txt) | 변경하지 않은 라이선스 문서, 자체의 원문 복제 허가 고지 유지 |

저장소 전체 압축파일에는 예외 자료가 있으므로 **MIT만 포함한 배포물은 아니다**.
해당 자료와 고지를 함께 보존한다. 유지보수 workflow만 호출하는 소비자는 이 과거
fixture를 실행하거나 배포하지 않는다. fixture를 직접 복사하는 소비자는 복사한
특정 판본의 조건을 유지해야 한다. 유지보수 구현이 MIT여도 과거 fixture는 AGPL이다.

[PROVENANCE.json](../PROVENANCE.json)은 현재 라이선스와 추출 이력을 구분하고 과거
Git blob 해시를 기록한다. 검사는 과거 바이트 보존과 현재 배포 정책을 분리한다.
소스 해시는 무결성 증거이지 저작권이나 재라이선스 권한의 증명이 아니다.

## 과거 판본과 권리 검토

중앙 최초 commit `1191cea41d88f07497be04407b3c949ca8361733`은 AGPL-3.0-only로
게시되었다. 이 전환은 이력을 다시 쓰거나 기존 AGPL 허가를 철회하지 않으며,
기존 SHA에 고정된 소비자의 라이선스를 자동 변경하지 않는다. 유지보수 MIT 판본을
채택하려면 실제 병합 SHA, 범위와 CI를 검토하고 소비자 자신의 pin, lock과 복사한
현재 snapshot을 갱신한다. 과거 SHA를 MIT 릴리스라고 표시하지 않는다.

이번 전환은 유지보수자의 요청으로 준비한다. 병합 전에 추출 부분을 포함한
유지보수 코드를 MIT로 제공할 권한과 제3자 기여 조건을 확인한다. 저장소 관리 권한,
작성자 메타데이터와 테스트 성공은 법적 권리 검토를 대신하지 않는다. 이 저장소는
서명된 양도 계약, CLA나 제3자 동의의 완료를 주장하지 않는다. 과거 증거와 제3자
라이선스 원문은 MIT로 다시 표시하지 않고 적용 범위에서 제외한다. AGPL gateway
프로젝트는 독립적인 라이선스를 유지한다.

## 제3자 도구와 기여

공식 GitHub Actions는 코드를 복제하지 않고 전체 SHA로 참조한다. 예를 들어
[현재 deploy-pages 라이선스](https://github.com/actions/deploy-pages/blob/d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e/LICENSE)는
MIT이며, 참조하는 소프트웨어는 자체 저작권·고지를 유지한다. CI 전용 PyYAML과
배포물도 자체 라이선스를 유지한다. 갱신 시 소스·라이선스 검토가 필요하며 이 문서는
외부 소프트웨어에 대한 허가를 부여하지 않는다.

대상 파일의 조건으로 제공할 권한이 있는 코드만 기여하고, 복사한 자료의 출처와
필수 고지를 유지한다. 저작권 양도를 요구하거나 CLA 체결을 주장하지 않는다.
실제 허가 본문은 [LICENSE](../LICENSE)를 따른다. 이 안내는 추가 제한을 부과하지
않으며 임의의 결합 제품에 대한 법적 판단을 제공하지 않는다.

자료: [MIT](https://opensource.org/license/mit) ·
[AGPL v3](https://www.gnu.org/licenses/agpl-3.0.html).
