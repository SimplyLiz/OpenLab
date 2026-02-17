"""Merged configuration — GeneLife app config + DNASyn settings."""

import os

from pydantic import BaseModel


class NCBIConfig(BaseModel):
    base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    api_key: str = ""  # Set via env; gives 10 req/s instead of 3
    email: str = ""
    accession: str = "CP016816.2"  # default Syn3A accession
    requests_per_second: float = 3.0


class EnsemblConfig(BaseModel):
    base_url: str = "https://rest.ensembl.org"
    requests_per_second: float = 15.0


class UniProtConfig(BaseModel):
    base_url: str = "https://rest.uniprot.org"
    requests_per_second: float = 25.0


class LLMConfig(BaseModel):
    provider: str = "anthropic"  # "anthropic", "openai", "ollama"
    model: str = "claude-sonnet-4-5-20250929"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    ollama_url: str = "http://localhost:11434"
    max_synthesis_genes: int = 10


class SimulationConfig(BaseModel):
    total_duration: float = 72000.0    # seconds (20 hours)
    metabolism_dt: float = 0.5         # seconds
    expression_dt: float = 60.0        # seconds
    snapshot_interval: int = 10        # macro-steps between snapshots
    initial_volume: float = 0.05       # femtoliters
    temperature: float = 310.0         # Kelvin
    ph: float = 7.5


class ETLConfig(BaseModel):
    brenda_email: str = ""
    brenda_password: str = ""
    cache_dir: str = "data/etl_cache"
    brenda_rate: float = 0.5
    sabio_rate: float = 1.0
    datanator_rate: float = 1.0
    kegg_rate: float = 3.0
    enable_brenda: bool = True
    enable_sabio: bool = True
    enable_datanator: bool = True
    enable_kegg: bool = True
    enable_esm2: bool = False


class DatabaseConfig(BaseModel):
    url: str = "sqlite:///openlab.db"
    echo: bool = False


class PipelineConfig(BaseModel):
    evidence_max_age_days: int = 30
    graduation_confidence_threshold: float = 0.7


class ToolsConfig(BaseModel):
    hhblits_db_path: str = ""
    eggnog_db_path: str = ""
    prost_db_path: str = ""
    pfam_db_path: str = ""
    proteomes_dir: str = ""
    structure_dir: str = "data/structures"
    hf_token: str = ""


class CancerConfig(BaseModel):
    cosmic_token: str = ""
    oncokb_token: str = ""
    clinvar_rate: float = 3.0
    cosmic_rate: float = 1.0
    oncokb_rate: float = 5.0
    cbioportal_rate: float = 10.0
    civic_rate: float = 10.0
    gdc_rate: float = 10.0


class VariantConfig(BaseModel):
    max_concurrency: int = 10
    hgvs_mode: str = "genomic"  # "genomic" (g. only) or "full" (requires biocommons)
    default_genome_build: str = "hg38"


class AgentConfig(BaseModel):
    max_tool_calls: int = 50
    timeout_seconds: int = 600
    require_citations: bool = True
    auto_critic: bool = True
    pmid_validation: bool = True
    max_concurrent_tools: int = 5
    synthesis_temperature: float = 0.3


class AppConfig(BaseModel):
    ncbi: NCBIConfig = NCBIConfig()
    ensembl: EnsemblConfig = EnsemblConfig()
    uniprot: UniProtConfig = UniProtConfig()
    llm: LLMConfig = LLMConfig()
    simulation: SimulationConfig = SimulationConfig()
    etl: ETLConfig = ETLConfig()
    database: DatabaseConfig = DatabaseConfig()
    pipeline: PipelineConfig = PipelineConfig()
    tools: ToolsConfig = ToolsConfig()
    agent: AgentConfig = AgentConfig()
    cancer: CancerConfig = CancerConfig()
    variant: VariantConfig = VariantConfig()
    debug: bool = False
    cors_origins: list[str] = [
        "http://localhost:5173", "http://localhost:3000",
        "http://localhost:5174", "http://localhost:5175",
        "http://localhost:5176",
    ]


def _build_config() -> AppConfig:
    """Build config from environment variables."""
    return AppConfig(
        ncbi=NCBIConfig(
            api_key=os.environ.get("NCBI_API_KEY", ""),
            email=os.environ.get("NCBI_EMAIL", ""),
        ),
        llm=LLMConfig(
            provider=os.environ.get("LLM_PROVIDER", "anthropic"),
            model=os.environ.get("LLM_MODEL", "claude-sonnet-4-5-20250929"),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", "") or os.environ.get("CLAUDE_API_KEY", ""),
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            ollama_url=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
            max_synthesis_genes=int(os.environ.get("MAX_SYNTHESIS_GENES", "10")),
        ),
        simulation=SimulationConfig(
            total_duration=float(os.environ.get("SIM_DURATION", "72000")),
        ),
        etl=ETLConfig(
            brenda_email=os.environ.get("BRENDA_EMAIL", ""),
            brenda_password=os.environ.get("BRENDA_PASSWORD", ""),
            cache_dir=os.environ.get("ETL_CACHE_DIR", "data/etl_cache"),
            enable_esm2=os.environ.get("ENABLE_ESM2", "").lower() in ("1", "true", "yes"),
        ),
        database=DatabaseConfig(
            url=os.environ.get("DATABASE_URL", "sqlite:///openlab.db"),
            echo=os.environ.get("DB_ECHO", "").lower() in ("1", "true", "yes"),
        ),
        pipeline=PipelineConfig(
            evidence_max_age_days=int(os.environ.get("EVIDENCE_MAX_AGE_DAYS", "30")),
            graduation_confidence_threshold=float(os.environ.get("GRADUATION_THRESHOLD", "0.7")),
        ),
        tools=ToolsConfig(
            hhblits_db_path=os.environ.get("HHBLITS_DB_PATH", ""),
            eggnog_db_path=os.environ.get("EGGNOG_DB_PATH", ""),
            prost_db_path=os.environ.get("PROST_DB_PATH", ""),
            pfam_db_path=os.environ.get("PFAM_DB_PATH", ""),
            proteomes_dir=os.environ.get("PROTEOMES_DIR", ""),
            structure_dir=os.environ.get("STRUCTURE_DIR", "data/structures"),
            hf_token=os.environ.get("HF_TOKEN", ""),
        ),
        cancer=CancerConfig(
            cosmic_token=os.environ.get("COSMIC_TOKEN", ""),
            oncokb_token=os.environ.get("ONCOKB_TOKEN", ""),
        ),
        agent=AgentConfig(
            max_tool_calls=int(os.environ.get("AGENT_MAX_TOOL_CALLS", "50")),
            timeout_seconds=int(os.environ.get("AGENT_TIMEOUT_SECONDS", "600")),
            require_citations=os.environ.get("AGENT_REQUIRE_CITATIONS", "true").lower()
            not in ("0", "false", "no"),
            auto_critic=os.environ.get("AGENT_AUTO_CRITIC", "true").lower()
            not in ("0", "false", "no"),
            pmid_validation=os.environ.get("AGENT_PMID_VALIDATION", "true").lower()
            not in ("0", "false", "no"),
        ),
        debug=os.environ.get("DEBUG", "").lower() in ("1", "true", "yes"),
    )


config = _build_config()


# DNASyn-compatible settings adapter — for services that expect `settings.database_url`
class _SettingsCompat:
    """Thin adapter so DNASyn services can still use settings.database_url etc."""

    @property
    def database_url(self) -> str:
        return config.database.url

    @property
    def debug(self) -> bool:
        return config.debug

    @property
    def llm_provider(self) -> str:
        return config.llm.provider

    @property
    def llm_model(self) -> str:
        return config.llm.model

    @property
    def openai_api_key(self) -> str:
        return config.llm.openai_api_key

    @property
    def anthropic_api_key(self) -> str:
        return config.llm.anthropic_api_key

    @property
    def ollama_url(self) -> str:
        return config.llm.ollama_url

    @property
    def ncbi_email(self) -> str:
        return config.ncbi.email

    @property
    def ncbi_api_key(self) -> str:
        return config.ncbi.api_key

    @property
    def ncbi_accession(self) -> str:
        return config.ncbi.accession

    @property
    def evidence_max_age_days(self) -> int:
        return config.pipeline.evidence_max_age_days

    @property
    def graduation_confidence_threshold(self) -> float:
        return config.pipeline.graduation_confidence_threshold

    @property
    def hhblits_db_path(self) -> str:
        return config.tools.hhblits_db_path

    @property
    def eggnog_db_path(self) -> str:
        return config.tools.eggnog_db_path

    @property
    def prost_db_path(self) -> str:
        return config.tools.prost_db_path

    @property
    def structure_dir(self) -> str:
        return config.tools.structure_dir

    @property
    def hf_token(self) -> str:
        return config.tools.hf_token

    @property
    def pfam_db_path(self) -> str:
        return config.tools.pfam_db_path

    @property
    def proteomes_dir(self) -> str:
        return config.tools.proteomes_dir


settings = _SettingsCompat()
