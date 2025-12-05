Document Database
=
JSON과 비슷한 field : value 형식의 자료구조를 가진 Document Database.
field의 값은 다른 도큐먼트, array 등을 포함할 수 있다.

장점
=
- native data types과의 호환
- 내장된 도큐먼트와 array가 불필요한 조인을 줄여준다
- 유연한 다형성에 도움을 주는 다이나믹 스키마

Collections/Views/On-Demand Materialized Views
=
MongoDB는 도큐먼트를 컬렉션에 저장한다.
컬렉션은 관계형 DB와 유사하다.

MongoDB는 Read-only Views, On-Demand Materialized Views 역시 지원한다.

Key Features
=

**High Performance**
- io를 줄여주는 내장 데이터모델을 지원한다.
- 인덱스 지원, 도큐먼트와 array에서 key를 포함할 수 있다.

**Query API**
- Data Aggregation
- Text Search and Geospatial Queries.

등등...

High Availability
=
replica set은 automatic failover, 중복 데이터 유지로 인한 가용성 향상.

Horizontal Scalability
=
MongoDB provides horizontal scalability as part of its core functionality

Starting in 3.4, MongoDB supports creating zones of data based on the shard key. In a balanced cluster, MongoDB directs reads and writes covered by a zone only to those shards inside the zone. 

