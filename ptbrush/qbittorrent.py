#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   qbittorrent.py
@Time    :   2024/11/03 09:18:15
@Author  :   huihuidehui 
@Desc    :   None
"""
from datetime import datetime
from pathlib import Path
import re
import traceback
from typing import List
import uuid
import qbittorrentapi
import requests
from loguru import logger
from pydantic import BaseModel


class QBitorrentTorrent(BaseModel):
    site: str
    name: str
    torrent_id: str
    completed: bool = False  # 是否下载完成
    free_end_time: datetime
    upspeed: int  # 上传速度 字节
    up_total_size: int
    dl_total_size: int
    dlspeed: int
    hash: str = ""
    size: int = 0


class QBittorrentStatus(BaseModel):
    dl_total_size: int
    up_total_size: int
    upspeed: int
    dlspeed: int
    free_space_size: int


class QBittorrent:

    def close(self):
        self.qb.auth_log_out()

    def __init__(self, qb_url: str, username: str, password: str):
        self.qb_url = qb_url
        self.qb = qbittorrentapi.Client(
            host=qb_url, username=username, password=password
        )
        self.qb.auth_log_in()

        # 受此项目管理的种子所带有的分类名
        self.category = "ptbrush"
        self._create_category(self.category)

    @property
    def status(self) -> QBittorrentStatus:
        result = self.qb.sync_maindata().server_state

        return QBittorrentStatus(
            dl_total_size=result.alltime_dl,
            up_total_size=result.alltime_ul,
            free_space_size=result.free_space_on_disk,
            upspeed=result.up_info_speed,
            dlspeed=result.dl_info_speed,
        )

    @property
    def torrents(self) -> List[QBitorrentTorrent]:
        # return []
        result = []
        for i in self.qb.torrents_info(category=self.category).data:
            torrent_name = i.get("name")
            site, torrent_id, end_time = re.search(
                r"__meta\.(.*?)\.(\d+)\.endTime\.(.*)", torrent_name
            ).groups()
            end_time = datetime.strptime(end_time, "%Y-%m-%d-%H:%M:%S")
            up_total_size = i.get("uploaded") if i.get("uploaded") else 0
            upspeed = i.get("upspeed") if i.get("upspeed") else 0
            dl_total_size = i.get("downloaded") if i.get("downloaded") else 0
            dlspeed = i.get("dlspeed") if i.get("dlspeed") else 0
            completed = i.get("completion_on") > 0
            torrent_hash = i.get("hash")
            size = i.get("size", 0)
            result.append(
                QBitorrentTorrent(
                    hash=torrent_hash,
                    name=torrent_name,
                    site=site,
                    torrent_id=torrent_id,
                    upspeed=upspeed,
                    up_total_size=up_total_size,
                    dl_total_size=dl_total_size,
                    dlspeed=dlspeed,
                    free_end_time=end_time,
                    completed=completed,
                    size=size,
                )
            )
        return result

    def _create_category(self, category):
        """
        编辑分类的保存路径, 分类不存在时则会创建
        :param category:
        :param save_path:
        :return:
        """
        try:
            save_path = str(Path(self.qb.app_default_save_path()) / "_ptbrush")
            self.qb.torrents_create_category(name=category, save_path=save_path)
        except qbittorrentapi.exceptions.Conflict409Error:
            # 已经存在
            pass
        # try:
        #     self.qb.torrents_edit_category(name=category, save_path=save_path)
        # except qbittorrentapi.exceptions.Conflict409Error:
        #     # 路径冲突或不可访问
        #     pass
        # return None

    def download_torrent_url(
        self,
        torrent_url: str,
        torrent_name: str,
    ) -> bool:
        torrent_download_res = requests.get(torrent_url, timeout=30, verify=False)
        res = self.qb.torrents_add(
            torrent_files=torrent_download_res.content,
            category=self.category,
            rename=torrent_name,
            use_auto_torrent_management=True,
        )
        return res == "Ok."

    def cancel_download(self, torrent_hash: str):
        """
        根据种子hash值，取消种子下载，但已下载的文件继续做种
        """
        files = self.get_torrent_files(torrent_hash)
        file_ids = [file["index"] for file in files]
        self.set_no_download_files(torrent_hash, file_ids)
        # self.qb.torrents_delete(delete_files=True, torrent_hashes=[torrent_hash])

    def get_torrent_files(self, hash: str) -> List[dict]:
        """
        检索单个种子的所有文件
        """
        files = self.qb.torrents_files(torrent_hash=hash)
        return files

    def set_no_download_files(self, hash: str, file_ids: List[int]) -> bool:
        """
        设置种子的某个文件不下载
        """
        self.qb.torrents_file_priority(hash, file_ids=file_ids, priority=0)
        return True

    # def clean_torrent(self, hash: str) -> bool:
    #     """
    #     将种子的所有文件大小小于500M的文件，全部设为不下载, 并把不需要下载文件打上需要删除标签

    #     """
    #     files = self._get_torrent_files(hash)
    #     no_download_file_ids = [
    #         file["index"] for file in files if file["size"] < 1024 * 1024 * 1024 * 0.5
    #     ]
    #     if not no_download_file_ids:
    #         return True
    #     self._set_no_download_files(hash, no_download_file_ids)
    #     for fid in no_download_file_ids:
    #         # 本来想的是先重命名，然后再开个线程去删，但貌似重命名后文件就没了，应该是被删除了
    #         try:
    #             self.qb.torrents_rename_file(
    #                 hash, fid, new_file_name=f"need_delete_{uuid.uuid1().hex}"
    #             )
    #         except qbittorrentapi.exceptions.Conflict409Error:
    #             pass
    #     return True

    # def _extract_torrent_task(self, torrent) -> TorrentTask:
    #     download_speed = 0
    #     if torrent.get("state") == "downloading":
    #         status = 0
    #         download_speed = torrent.dlspeed
    #     elif torrent.get("progress") == 1:
    #         status = 2
    #     else:
    #         status = 1
    #     content_path = str(Path(torrent.save_path))
    #     files = [
    #         TorrentTaskFile(
    #             size=file.size / 1024 / 1024 / 1024,
    #             path=content_path + "/" + file.name,
    #         )
    #         for file in torrent.files
    #     ]
    #     return TorrentTask(
    #         # size: float
    #         # files: Optional[List[TorrentTaskFile]]=[]
    #         download_speed=download_speed,
    #         files=files,
    #         status=status,
    #         name=torrent.name,
    #         created_time=datetime.fromtimestamp(torrent.added_on),
    #         progress=torrent.progress,
    #         hash=torrent.hash,
    #         completed_time=datetime.fromtimestamp(torrent.completion_on),
    #         size=torrent.size / 1024 / 1024 / 1024,
    #     )

    # def get_torrent_by_hash(self, hash: str) -> TorrentTask:
    #     e = self.qb.torrents_info(torrent_hashes=[hash])
    #     if e:
    #         i = e[0]
    #         return self._extract_torrent_task(i)
