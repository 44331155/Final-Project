from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    JWT_SECRET: str = "replace_me"
    # 可以继续添加数据库、Redis 等配置
    model_config = SettingsConfigDict(
        env_file=".env",          # 自动读取 .env
        env_file_encoding="utf-8",
        extra="ignore"            # 忽略未定义的额外变量
    )

settings = Settings()