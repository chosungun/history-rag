from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    anthropic_api_key: str = ""
    public_data_api_key: str = ""
    gongu_api_key: str = ""
    independence_api_key: str = ""
    hgis_api_key: str = ""
    nl_api_key: str = ""
    chroma_path: str = "/chroma_data"
    data_path: str = "/data"
    embed_model: str = "paraphrase-multilingual-mpnet-base-v2"
    chroma_host: str = "chromadb"
    chroma_port: int = 8000

    class Config:
        env_file = ".env"

settings = Settings()
