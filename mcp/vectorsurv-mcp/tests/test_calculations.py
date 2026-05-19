"""Unit tests for the surveillance calculations.

Synthetic data so we can verify the math without a live VectorSurv
account.
"""

from vectorsurv_mcp.calculations import (
    abundance,
    infection_rate,
    vector_index,
)


def _collection(date: str, count: int, trap_nights: int = 1, species="Culex tarsalis", trap="CDC-CO2") -> dict:
    return {
        "collection_date": date,
        "num_count": count,
        "trap_nights": trap_nights,
        "species_display_name": species,
        "trap_acronym": trap,
    }


def _pool(date: str, n: int, positive: bool, target="WNV", species="Culex tarsalis", trap="CDC-CO2") -> dict:
    return {
        "collection_date": date,
        "num_count": n,
        "test_status": "Positive" if positive else "Negative",
        "target_acronym": target,
        "species_display_name": species,
        "trap_acronym": trap,
    }


def test_abundance_basic_average():
    cols = [
        _collection("2025-07-01", 30, trap_nights=2),
        _collection("2025-07-02", 50, trap_nights=2),
    ]
    rows = abundance(cols, interval="Month")
    assert len(rows) == 1
    r = rows[0]
    assert r["count"] == 80
    assert r["trap_nights"] == 4
    assert r["abundance"] == 20.0  # 80 / 4


def test_abundance_species_filter():
    cols = [
        _collection("2025-07-01", 30, species="Culex tarsalis"),
        _collection("2025-07-02", 50, species="Aedes aegypti"),
    ]
    rows = abundance(cols, interval="Month", species="Aedes aegypti")
    assert rows[0]["count"] == 50


def test_mir_zero_when_no_positives():
    pools = [_pool("2025-08-01", 50, positive=False) for _ in range(5)]
    rows = infection_rate(pools, target_disease="WNV", interval="Month", method="mir")
    assert rows[0]["infection_rate"] == 0.0
    assert rows[0]["mosquitoes_tested"] == 250


def test_mir_two_positives_per_thousand():
    # 2 positive pools, 1000 mosquitoes tested -> MIR = 2 per 1000
    pools = [
        _pool("2025-08-01", 100, positive=(i < 2)) for i in range(10)
    ]
    rows = infection_rate(pools, target_disease="WNV", interval="Month", method="mir")
    assert rows[0]["positive_pools"] == 2
    assert rows[0]["mosquitoes_tested"] == 1000
    assert abs(rows[0]["infection_rate"] - 2.0) < 1e-9


def test_bc_mle_returns_nonzero_when_positives_present():
    pools = [_pool("2025-08-01", 100, positive=(i < 3)) for i in range(20)]
    rows = infection_rate(
        pools, target_disease="WNV", interval="Month", method="bc-mle"
    )
    assert rows[0]["infection_rate"] > 0


def test_vector_index_combines_abundance_and_ir():
    cols = [_collection("2025-08-01", 100, trap_nights=10)]  # abundance = 10
    pools = [_pool("2025-08-01", 100, positive=True)]        # MIR = 1000/100 = 10 per 1000
    rows = vector_index(
        cols, pools, target_disease="WNV", interval="Month", method="mir", scale=1000
    )
    assert rows[0]["abundance"] == 10.0
    # VI = abundance * IR / scale = 10 * 10 / 1000 = 0.1
    assert abs(rows[0]["vector_index"] - 0.1) < 1e-9
