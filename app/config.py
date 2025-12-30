from datetime import date, time
from typing import Dict, List, Tuple, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

TermPeriods = List[Tuple[time, time]]

class Settings(BaseSettings):
    DB_PATH: str = "data/schedule.db"
    JWT_SECRET: str = "a_very_secret_key_change_it_in_production"
    ENCRYPTION_KEY: str = "5ZNNJxlB_leSfnTvWTWZp5dqc1-6gvW97_3CeYl43PE="

    WECHAT_APPID: str = "wx4ff8014b152a5815"
    WECHAT_APPSECRET: str = "2531306416eb95f63fd3602964e20d8e"

    # 默认学期标识（用于未显式传入学期的场景）
    CURRENT_TERM: str = "2025-2026-1"

    # 默认作息时间表（当某个学期未指定 periods 时使用）
    DEFAULT_PERIODS: TermPeriods = [
        (time(8, 0), time(8, 45)),    # 第1节
        (time(8, 50),time(9, 35)),   # 第2节
        (time(10, 0), time(10, 45)),  # 第3节
        (time(10, 50), time(11, 35)), # 第4节
        (time(11, 45), time(12, 25)),  # 第5节
        (time(13, 25), time(14, 10)), # 第6节
        (time(14, 15), time(15, 0)),  # 第7节
        (time(15, 5), time(15, 50)), # 第8节
        (time(16, 15), time(17, 0)), # 第9节
        (time(17, 5), time(17, 50)), # 第10节
        (time(18, 50), time(19, 35)),  # 第11节
        (time(19, 40), time(20, 25)), # 第12节
        (time(20, 30), time(21, 15)),# 第13节
    ]

    # 多学期配置：每个学期至少设置 start_monday，可选 periods（不填则使用 DEFAULT_PERIODS）
    TERM_CONFIGS: Dict[str, Dict[str, object]] = {
        "2023-2024-1": {
            "start_monday": date(2023, 9, 18),
        },
        "2023-2024-2": {
            "start_monday": date(2024, 2, 26),
        },
        "2024-2025-1": {
            "start_monday": date(2024, 9, 9),
        },
        "2024-2025-2": {
            "start_monday": date(2025, 2, 17),
        },
        "2025-2026-1": {
            "start_monday": date(2025, 9, 15),
        },
        "2025-2026-2": {
            "start_monday": date(2026, 3, 2),
        },
    }

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("DEFAULT_PERIODS")
    @classmethod
    def validate_default_periods(cls, v: TermPeriods):
        if not v:
            raise ValueError("DEFAULT_PERIODS cannot be empty")
        for i, pair in enumerate(v, start=1):
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise ValueError(f"DEFAULT_PERIODS item #{i} must be a tuple (start_time, end_time)")
            start, end = pair
            if start >= end:
                raise ValueError(f"DEFAULT_PERIODS item #{i} start_time must be earlier than end_time")
        return v

    @field_validator("TERM_CONFIGS")
    @classmethod
    def validate_term_configs(cls, v: Dict[str, Dict[str, object]]):
        if not isinstance(v, dict) or not v:
            raise ValueError("TERM_CONFIGS must be a non-empty dict")
        for term_id, cfg in v.items():
            if "start_monday" not in cfg or not isinstance(cfg["start_monday"], date):
                raise ValueError(f"TERM_CONFIGS[{term_id}] must include 'start_monday' as a date")
            periods = cfg.get("periods")
            if periods is not None:
                # 校验 periods 格式
                for i, pair in enumerate(periods, start=1):
                    if not isinstance(pair, tuple) or len(pair) != 2:
                        raise ValueError(f"TERM_CONFIGS[{term_id}].periods item #{i} must be a tuple (start_time, end_time)")
                    start, end = pair
                    if start >= end:
                        raise ValueError(f"TERM_CONFIGS[{term_id}].periods item #{i} start_time must be earlier than end_time")
        return v

    # 帮助方法：获取某学期起始日与作息表
    def get_term_start_monday(self, term_id: Optional[str]) -> date:
        t = term_id or self.CURRENT_TERM
        cfg = self.TERM_CONFIGS.get(t)
        if not cfg:
            raise ValueError(f"Unknown term_id: {t}")
        return cfg["start_monday"]  # type: ignore

    def get_term_periods(self, term_id: Optional[str]) -> TermPeriods:
        t = term_id or self.CURRENT_TERM
        cfg = self.TERM_CONFIGS.get(t)
        if not cfg:
            raise ValueError(f"Unknown term_id: {t}")
        return cfg.get("periods") or self.DEFAULT_PERIODS  # type: ignore

settings = Settings()