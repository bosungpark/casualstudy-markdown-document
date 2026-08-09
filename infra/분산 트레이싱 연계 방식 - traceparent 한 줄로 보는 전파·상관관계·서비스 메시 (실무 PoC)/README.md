# 분산 트레이싱 전파 PoC

3-hop HTTP 체인에서 W3C `traceparent` 전파가 trace의 연결 관계를 어떻게 바꾸는지 직접 확인한다.

```text
propagation ON : gateway-on  -> orders-on  -> payments-on  = 요청당 1 trace, 5 spans
propagation OFF: gateway-off -> orders-off -> payments-off = 요청당 3 traces, 5 spans
```

전파를 꺼도 Flask 서버 span 3개와 Requests 클라이언트 span 2개는 그대로 생성된다. 달라지는 것은 span 수가 아니라 부모-자식 간선이다.

## 실행

필요한 것은 Docker Desktop과 Python 3뿐이다.

```bash
cd "infra/분산 트레이싱 연계 방식 - traceparent 한 줄로 보는 전파·상관관계·서비스 메시 (실무 PoC)"
./run.sh
```

기본값은 각 체인에 요청 3건이다. 요청 수를 바꾸려면:

```bash
./run.sh --requests 10
```

성공하면 응답에서 관찰한 hop별 trace ID와 Jaeger에서 집계한 결과가 함께 출력된다.

```text
[PASS] propagation ON: all hops keep one trace ID
[PASS] propagation OFF: every hop starts a new trace ID
[PASS] Jaeger
  ON : 3 requests -> 3 traces, 15 spans
  OFF: 3 requests -> 9 traces, 15 spans
```

Jaeger UI는 <http://localhost:16686>에서 볼 수 있다. 서비스 드롭다운에서 `gateway-on`과 `gateway-off`를 각각 조회하면 연결된 trace와 끊어진 trace를 비교할 수 있다.

## 직접 응답 비교

```bash
curl -s http://localhost:8001/work | python3 -m json.tool
curl -s http://localhost:8002/work | python3 -m json.tool
```

- `8001`(ON): 세 hop의 `trace_id`가 같고 다운스트림에 `received_traceparent`가 있다.
- `8002`(OFF): 세 hop의 `trace_id`가 모두 다르고 `received_traceparent`가 없다.

## 종료

```bash
docker compose down
```
