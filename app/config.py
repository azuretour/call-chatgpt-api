from pydantic import BaseSettings


class AppSettings(BaseSettings):
    ProjectName: str = "Demo"


settings = AppSettings()
