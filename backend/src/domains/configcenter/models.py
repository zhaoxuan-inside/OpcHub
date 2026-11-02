"""配置中心模型：命名空间 / 配置项 / 版本 / 灰度发布。"""
from typing import Dict, List, Optional

from pydantic import BaseModel


class ConfigNamespace(BaseModel):
    namespace_id: str  # ns_
    key: str
    name: str
    description: str = ""
    project_id: str = ""
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""


class GrayRelease(BaseModel):
    version: str
    content: str
    percent: int = 0  # 0-100，命中桶 %100 < percent 命中灰度
    whitelist: List[str] = []  # uid 白名单直通灰度
    published_by: str = ""
    published_at: str = ""


class ConfigVersion(BaseModel):
    version: str
    status: str = "DRAFT"  # DRAFT | PUBLISHED | SUPERSEDED
    content: str
    changelog: str = ""
    created_by: str = ""
    created_at: str = ""
    published_by: str = ""
    published_at: str = ""


class ConfigItem(BaseModel):
    item_id: str  # cfg_
    namespace: str  # 命名空间 key
    key: str
    name: str = ""
    value_type: str = "JSON"  # JSON | TEXT
    description: str = ""
    versions: List[ConfigVersion] = []
    # 按环境的生效态：stable_env[env_key]=版本；"" 为遗留/无环境上下文的默认桶
    stable_env: Dict[str, str] = {}
    gray_env: Dict[str, GrayRelease] = {}
    project_id: str = ""
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""
