"""Test that all 6 cancer sources register correctly."""



def test_all_cancer_sources_registered():
    """All 6 cancer sources should be registered with correct weights."""
    # Trigger registration
    from openlab.contrib.cancer import register_all
    from openlab.registry import list_registered_sources
    register_all()

    sources = list_registered_sources()
    expected = {"clinvar", "cosmic", "oncokb", "cbioportal", "civic", "tcga_gdc"}
    registered_cancer = {name for name in sources if sources[name].group == "cancer"}
    assert registered_cancer == expected


def test_cancer_source_weights():
    """Cancer sources should have the planned convergence weights."""
    from openlab.services.convergence import CONVERGENCE_SOURCE_WEIGHTS

    expected_weights = {
        "clinvar": 1.8,
        "cosmic": 2.0,
        "oncokb": 2.0,
        "cbioportal": 1.5,
        "civic": 1.8,
        "tcga_gdc": 1.5,
    }
    for source, weight in expected_weights.items():
        assert CONVERGENCE_SOURCE_WEIGHTS[source] == weight, (
            f"{source} weight: expected {weight}, got {CONVERGENCE_SOURCE_WEIGHTS.get(source)}"
        )


def test_cancer_sources_have_group():
    """Each cancer source registration should have group='cancer'."""
    from openlab.contrib.cancer import register_all
    from openlab.registry import list_registered_sources
    register_all()

    sources = list_registered_sources()
    for name in ("clinvar", "cosmic", "oncokb", "cbioportal", "civic", "tcga_gdc"):
        assert sources[name].group == "cancer", f"{name} missing group='cancer'"


def test_idempotent_registration():
    """Calling register_all() twice should not raise or double-register."""
    from openlab.contrib.cancer import register_all
    register_all()
    register_all()  # second call should be no-op

    from openlab.registry import list_registered_sources
    sources = list_registered_sources()
    cancer_sources = [n for n in sources if sources[n].group == "cancer"]
    assert len(cancer_sources) == 6
