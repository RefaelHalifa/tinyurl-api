from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mongo_url: str
    mongo_db_name: str
    redis_url: str
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    class Config:
        env_file = ".env"

settings = Settings()