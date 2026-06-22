from time import perf_counter

import pytest


@pytest.mark.nonfunctional
def test_home_route_response_time_smoke(client):
    started = perf_counter()
    response = client.get("/")
    elapsed = perf_counter() - started

    assert response.status_code == 200
    assert elapsed < 1.0


@pytest.mark.nonfunctional
def test_home_route_repeated_requests_stability(client):
    started = perf_counter()

    for _ in range(20):
        response = client.get("/")
        assert response.status_code == 200

    elapsed = perf_counter() - started
    assert elapsed < 3.0
