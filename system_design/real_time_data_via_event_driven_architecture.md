How MongoDB Enables Real-Time Data with Event-Driven Architecture...October 2019
=

>Event-Driven Architecture를 중심으로 요약

https://github.com/adhiambovivian/cs-papers/blob/master/system-design/Real-Time-Data-via-Event-Driven-Architecture.pdf

산업은 더욱 에자일한 방식으로 변화한다. 어플리케이션은 더욱 스케일 가능한 형태이기를 요구받는다. 기존의  request-driven data architecture는 이러한 환경에서는 안티 패턴이 된다. request-driven data architecture은 말 그대로 유저가 명령을 내리면 수행한다. 반면 event-driven architecture는 능동적으로 자신의 관심사를 찾아 수행한다. 맥락을 알고 시스템보다는 유저에 초점을 맞춘다.

> The most commonly agreed definition is that
real time is the ability to ingest and act on
data in 100-200 milliseconds

The Major Driver of Real Time
Today is Microservices
=
오늘날 리얼타임에 대해 가장 큰 요구를 하는 분야는 MSA이다. 독립적인 서비스들 사이의 빠른 데이터 이동이 중요하기 때문이다.

Core Building Block of Real Time is an Event
=
데이터 관리 관점에서 이벤트는 다음과 같은 정의를 가진다.

- Atomic: 이벤트는 특정 사건에 대한 원자적인 유닛이다.
- Related: 이벤트는 많은 경우 단독 사건이 아닌, 다른 이벤트의 시퀀셜한 성향이 있다.
- Behavioral: 이런 시퀀셜한 이벤트의 특징은 사건의 행동에대한 누적된 단서를 남긴다.


이러한 이벤트는 능동적으로 사건에 대응한다.

What Is Event-Driven Architecture?
=
request-driven architectures는 유저가 요청하고, 필요한 데이터를 유저에게서 받는다. 이는 강한 결합을 의미한다.

반면, 이벤트 드리븐 환경에서는 이벤트를 발행한다. 요청을 기다리는 대신, 비동기적으로 각자의 서비스가 발행된 이벤트에 따라 행동한다.

이벤트 드리븐 환경에서 가능해진 즉각적인 반응은 보다 나은 UX와 대응에 도움이 된다.

Microservices and EventDriven Architectures: Why MongoDB
=

레거시 데이터베이스의 스키마는 때로는 까다로운 요소가 된다. MongoDB는 이러한 점에서 도움이 된다.

... 이후 대략 몽고 DB에 관한 내용...