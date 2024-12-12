import shutil
from dataclasses import field
from pathlib import Path
from typing import List, Optional, Tuple, Type

from loguru import logger
from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

CONFIG_FILE_PATH = Path(__file__).parent.parent / "data" / "config.toml"


class HeaderParam(BaseModel):
    key: str
    value: str


class OptionParam(BaseModel):
    free_only: Optional[bool] = False  # 是否只获取免费种子


class SiteModel(BaseModel):
    name: str
    cookie: Optional[str] = ""
    options: Optional[OptionParam] = OptionParam()
    headers: Optional[List[HeaderParam]] = []


class QBConfig(BaseModel):
    url: str
    username: str
    password: str


class BrushConfig(BaseModel):
    min_disk_space: int = 1099511627776
    max_downloading_torrents: int = 6
    upload_cycle: int = 600
    download_cycle: int = 600
    expect_upload_speed: int = 1966080
    expect_download_speed: int = 13107200
    torrent_max_size: int = 53687091200


class PTBrushConfig(BaseSettings):
    downloader: Optional[QBConfig] = None
    sites: Optional[List[SiteModel]] = field(default_factory=list)
    brush: Optional[BrushConfig] = BrushConfig()

    model_config = SettingsConfigDict(toml_file=str(CONFIG_FILE_PATH))

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            TomlConfigSettingsSource(settings_cls, toml_file=str(CONFIG_FILE_PATH)),
        )

    @classmethod
    def init_config(cls):
        if not CONFIG_FILE_PATH.exists():
            example_config_path = Path(__file__).parent / "config.example.toml"
            shutil.copy(example_config_path, CONFIG_FILE_PATH)
            logger.info(
                f"配置文件不存在已为您创建新的配置文件：{CONFIG_FILE_PATH.absolute()}"
            )
            logger.info(f"请编辑配置文件添加站点信息以及下载器信息后，开始刷流~")
        else:
            logger.info(
                f"配置文件已存在：{CONFIG_FILE_PATH.absolute()}，跳过初始化配置文件"
            )

    @classmethod
    def override_config(cls, **kwargs):
        example_config_path = Path(__file__).parent / "config.example.toml"
        shutil.copy(example_config_path, CONFIG_FILE_PATH)
        logger.info(f"已覆盖配置文件：{CONFIG_FILE_PATH.absolute()}")


# PTBrushConfig.init_config()
# print(PTBrushConfig().model_dump_json())
