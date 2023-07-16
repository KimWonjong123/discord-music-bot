# discord-music-bot
마음에 드는 음악 봇이 없어서 내가 직접 만드는 음악 봇


## before start
requirements.txt 설치 후 youtube_dl/extractor/youtube.py의 1794번 라인을 다음 코드로 교체
```python
uploader_id': self._search_regex(r'/(?:channel/|user/|@)([^/?&#]+)', owner_profile_url, 'uploader id', default=None),
```
