추천 시스템 서비스 적용을 위한 Elastic Search 도입기
=

https://blog.dramancompany.com/2022/11/%EC%B6%94%EC%B2%9C-%EC%8B%9C%EC%8A%A4%ED%85%9C-%EC%84%9C%EB%B9%84%EC%8A%A4-%EC%A0%81%EC%9A%A9%EC%9D%84-%EC%9C%84%ED%95%9C-elastic-search-%EB%8F%84%EC%9E%85%EA%B8%B0/

- MongoDB에 임베딩을 저장 후 추출하는 경우 속도 이슈 존재
- ElasticSearch (OpenSearch) 도입
  - k-NN(k-nearest neighbors): k-NN을 사용하면 벡터 공간에서 포인트를 검색하고 해당 포인트에 대한 “가장 가까운 이웃”을 Euclidean 거리 또는 코사인 유사도로 찾을 수 있다.
    - Approximate k-NN(ANN): 여러 알고리즘 중 하나를 사용하여 대략적인 k-NN 결과를 쿼리 벡터로 반환. 짧은 대기 시간, 더 작은 메모리 공간 및 더 확장 가능한 검색. 인덱싱 속도와 검색 정확도의 성능은 일부 떨어질 수 있다.
    - Script Score k-NN: OpenSearch의 Script Score 기능을 확장하여 나타나는 “knn_vector”에 대하여 정확한 k-NN 검색을 수행. 존재하는 벡터에 대해서 사전 필터링이 필요할 경우 사용.
    - Painless extensions: Script Score k-NN에 비하여 쿼리 성능이 약간 느리다는 단점이 존재합니다. 그러나 거리함수를 더 복잡한 상황에서 적용할 수 있다.
  - HNSW (Hierarchical Navigable Small World Algorithm): k-NN 검색문제에 대해서 빠르고 정확한 솔루션을 제공하기위해서 HNSW 알고리즘을 기반으로 하여 검색엔진이 동작. 적은 거리를 계산하고, 거리 계산 비용을 더 저렴하게 하도록 하는 것에 목적. 입력 쿼리에 대한 가장 가까운 이웃을 찾기 위해 검색 프로세스는 최상위 계층의 그래프에서 가장 가까운 이웃을 찾고 이 점을 후속 계층에 대한 진입점으로 사용.
- 성능 향상 및 A/B 결과 유저 경험 개선
