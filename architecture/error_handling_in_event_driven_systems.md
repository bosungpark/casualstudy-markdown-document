Error Handling in Event-Driven Systems...Aritra Das
=

HTTP response codes를 기반으로 best-practice가 어느정도 있는 REST based Architecture와 달리 Event-based Architecture에서의 에러 관리는 제법 까다롭다.

event-driven system에서 데이터는 producer에서 consumer로 단방향 이동을 할 뿐이다.

또  event-driven system에서 하나의 잘못된 메시지는 전체 시스템을 멈출 위험도 있다.

**Potential Failure points**

예:
- The consumer can’t parse the message because of invalid JSON structure.
- The message received is not supported for processing by our application.
- The processor can’t find data for this message in the data store, because of a delay introduced by some other service that was responsible for putting in that data.
- The HTTP connection to the Data Store is broken.
- The cache system is down and unable to accept requests.

**Error Classification**

1. Retryable exception: this is for those errors which can be solved by just retrying the operation once or more
2. Requeable exception: 무언가 모종의 이유로 큐에서 정체되는 현상(poison pill)이 발생할 때 다시 넣어주는 것
3. Droppable exception: 그냥 버림으로서 해결할 수 있는 에러
4. DLQable exception: The Unhandled Exceptions