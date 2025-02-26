from abstract_exporter import AbstractExporter
from logger import Logger
from datetime import datetime, time
import time as t


class JsonExporter(AbstractExporter):

    MIN_TIME = time(18)
    MAX_TIME = time(8)
    PAGE = 10000

    def __init__(self):
        super().__init__()
        # set upload folder for s3 client
        self.s3.set_key_prefix("test")

    def run_export(self):
        """
        Exports all public objects from MPlus as JSON-files (each containing 10000 Objects) and saves the output to S3.
        The export waits if it is running outside the predefined time window
        """
        count = self.mplus.request("object-count").parse_size()
        Logger.log(f"{count} Objects to be downloaded found.")

        for offset in range(0, count, self.PAGE):
            self._wait_for_time_window()
            self._export_page(self.PAGE, offset)

        Logger.log("All pages successfully exported", "SUCCESS")

    def _wait_for_time_window(self):
        """Waits until exectution time window."""
        waiting = False
        while not self._check_time_window(datetime.now().time()):
            if not waiting:
                waiting = True
                Logger.log("Waiting for execution time window", "WARNING")

            t.sleep(60)

    def _check_time_window(self, time):
        """Returns True if given time is inside the exectution time window"""
        if self.MIN_TIME <= self.MAX_TIME:
            return self.MIN_TIME <= time < self.MAX_TIME
        else:  # over midnight e.g., 23:30-04:15
            return self.MIN_TIME <= time or time < self.MAX_TIME

    def _export_page(self, limit, offset):
        """Exports a page of objects from MPlus and saves the json to s3"""
        Logger.log(f"Starting Export of {limit} objects from {offset}.")
        response = self.mplus.request(
            "object-export", xml_placeholders={"limit": limit, "offset": offset}
        )
        filename = f"emp2-export-{offset:06d}.json"

        Logger.log(f"Saving {filename}")
        self.s3.put_object(
            key=filename,
            object=response.content,
            content_type="application/json",
        )


def main():
    exporter = JsonExporter()
    exporter.run_export()


if __name__ == "__main__":
    main()
