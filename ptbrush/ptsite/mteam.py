#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   mteam.py
@Time    :   2024/11/02 14:37:48
@Author  :   huihuidehui 
@Desc    :   None
"""


import json
from datetime import datetime, timedelta
from time import sleep
from typing import Generator

from loguru import logger

from model import Torrent
from ptsite import BaseSiteSpider


class MTeamSpider(BaseSiteSpider):
    NAME = "M-Team"
    HOST = "api.m-team.cc"
    API = "api/torrent/search"
    TORRENT_API = "api/torrent/genDlToken"
    PAGE_SIZE = 200
    BODYS = [
        # 成人最新
        {
            "categories": [],
            "mode": "adult",
            "visible": 1,
            "pageNumber": 1,
            "pageSize": 100,
            "sortDirection": "DESC",
            "sortField": "CREATED_DATE",
        },
        # 排行榜 下载数最多
        {
            "categories": [],
            "mode": "rankings",
            "visible": 1,
            "pageNumber": 1,
            "pageSize": 100,
            "sortDirection": "DESC",
            "sortField": "LEECHERS",
        },
    ]

    # MODES = ["adult", "", "normal", "movie", "music", "tvshow", "rankings"]
    # SORT_FIELDS = [
    #     "CREATED_DATE",
    #     "LEECHERS",
    # ]
    # DISCOUNTS = ["FREE"]

    def free_torrents(self) -> Generator[Torrent, Torrent, Torrent]:
        for body in self.BODYS:
            logger.debug(
                f"searching mt body:{json.dumps(body, separators=(',', ':'), ensure_ascii=False)}"
            )
            text = self.fetch(
                url=f"https://{self.HOST}/{self.API}",
                method="POST",
                data=json.dumps(body),
            ).text
            data = json.loads(text).get("data", {}).get("data")
            if data:
                for item in data:
                    if self._is_free_torrent(item):
                        yield self._parse_torrent(item)
            sleep(3)

    def _is_free_torrent(self, item: dict) -> bool:
        """
        规则如下：
        1. discount = FREE or _2X_FREE
        2. toppingLevel != 0
        """
        if item.get("status").get("discount") in ["FREE", "_2X_FREE"]:
            return True
        if (
            not self.options.free_only
            and not item.get("status").get("toppingLevel") == "0"
        ):
            return True
        return False

    def _parse_torrent(self, item: dict) -> Torrent:
        free_end_time = datetime.now() + timedelta(days=1)
        if item.get("status").get("discount") in ["FREE", "_2X_FREE"]:
            if item.get("status").get("discountEndTime"):
                free_end_time = datetime.strptime(
                    item.get("status").get("discountEndTime"), "%Y-%m-%d %H:%M:%S"
                )
        if not item.get("status").get("toppingLevel") == "0":
            if item.get("status").get("toppingEndTime"):
                free_end_time = datetime.strptime(
                    item.get("status").get("toppingEndTime"), "%Y-%m-%d %H:%M:%S"
                )

        torrent = Torrent(
            name=item.get("name"),
            id=item.get("id"),
            seeders=item.get("status").get("seeders"),
            leechers=item.get("status").get("leechers"),
            size=int(item.get("size")),
            created_time=datetime.strptime(
                item.get("createdDate"), "%Y-%m-%d %H:%M:%S"
            ),
            free_end_time=free_end_time,
            site=self.NAME,
        )

        return torrent

    def parse_torrent_link(self, torrent_id: str) -> str:
        """
        获取种子下载链接
        """
        response = self.fetch(
            url=f"https://{self.HOST}/{self.TORRENT_API}",
            method="POST",
            data={"id": str(torrent_id)},
        )
        torrent_url = json.loads(response.text).get("data")
        return torrent_url

    pass
