from yt_dlp import YoutubeDL, PlaylistEntries
from yt_dlp.extractor.lazy_extractors import YoutubeSearchIE
from yt_dlp.utils import UserNotLive, bug_reports_message, orderedSet


class YTDL(YoutubeDL):
    def extract_urls(
        self,
        url,
        download=True,
        ie_key=None,
        extra_info=None,
        process=True,
        force_generic_extractor=False,
    ):
        ie = self.get_info_extractor("YoutubeSearch")
        self._apply_header_cookies(url)
        try:
            ie_result = ie.extract(url)
        except UserNotLive as e:
            if process:
                if self.params.get("wait_for_video"):
                    self.report_warning(e)
                self._wait_for_video()
            raise
        if ie_result is None:
            self.report_warning(
                f"Extractor {ie.IE_NAME} returned nothing{bug_reports_message()}"
            )
            return
        self.add_default_extra_info(ie_result, ie, url)
        common_info = self._playlist_infodict(ie_result, strict=True)
        title = common_info.get("playlist") or "<Untitled>"
        self.to_screen(f'[download] Downloading {ie_result["_type"]}: {title}')
        all_entries = PlaylistEntries(self, ie_result)
        # urls = list(map(lambda entry: entry[1]['url'],
        #                 list(orderedSet(all_entries.get_requested_items()))))
        entries = tuple(zip(*list(orderedSet(all_entries.get_requested_items(), lazy=True))))[1]
        ie_result["entries"] = entries
        return ie_result
