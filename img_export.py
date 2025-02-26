import csv
import io
from dotenv import load_dotenv
from datetime import datetime
from mpluspy import MPlusClient
from abstract_exporter import AbstractExporter
from logger import Logger

load_dotenv()


class ImgExporter(AbstractExporter):

    TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
    LAST_RUN_KEY = "last-run.txt"
    PENDING_KEY = "pending.csv"
    CSV_HEADER = ["ID", "time-added"]

    def __init__(self):
        super().__init__()
        # set upload folder for s3 client
        self.s3.set_key_prefix("extra-large")

    def run_export(self):
        """Runs export of new/changed thumbnail images from MPlus and saves them to S3."""
        # setup export and get state of last run
        self._setup_export()

        # query new images and add them to pending list
        new = self._query_for_new_images(self.last)
        self._append_new_images(new if new else [])

        # save pending and last run before downloading images
        self._save_pending()
        self._save_last_run()

        # download images and save them to s3
        self._process_pending()

        # save processed pending
        self._save_pending()

    def _setup_export(self):
        """Gets and sets up state of last export."""
        self.NOW = datetime.now()
        self.last = self._get_last_run()
        self.pending = self._load_pending()

    def _get_last_run(self):
        """Retreive and parse last run from file on S3. If none is found current time will be set as last run."""
        key = self.LAST_RUN_KEY
        if not self.s3.check_key(key):
            Logger.log(
                f"No last run file was found ({key}) on S3. Current time will be set as Last run and saved to S3 now. Edit {key} afterwards to set te correct timestamp!",
                "WARNING",
            )
            return self.NOW

        s = self.s3.get_object_string(key)
        return datetime.strptime(s, self.TIMESTAMP_FORMAT)

    def _save_last_run(self):
        """Saves timestamp of last successfull query as txt to S3"""
        self.s3.put_object(
            key=self.LAST_RUN_KEY,
            object=self.NOW.strftime(self.TIMESTAMP_FORMAT),
            content_type="text/plain",
        )

    def _load_pending(self):
        """Load list of pending images from csv on S3. If the file is not found the list will be initialized as empty"""
        key = self.PENDING_KEY
        if not self.s3.check_key(key):
            Logger.log(
                f"No pending file found ({key}) on S3. Initializing empty list.",
                "WARNING",
            )
            return []

        s = self.s3.get_object_string(key)
        return list(csv.DictReader(io.StringIO(s)))

    def _save_pending(self):
        """Saves list of pending images as csv to S3"""
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=self.CSV_HEADER)
        writer.writeheader()
        writer.writerows(self.pending)
        self.s3.put_object(
            key=self.PENDING_KEY, object=csv_buffer.getvalue(), content_type="text/csv"
        )

    def _query_for_new_images(self, last_run):
        """Query Mplus for Digital Assets modifed after given date. Returns list of IDs"""
        Logger.log(f"Get IDs of all digital assets in MPlus modified since {last_run}.")
        timestamp = MPlusClient.format_timestamp(last_run)
        response = self.mplus.request(
            "image-search", xml_placeholders={"timestamp": timestamp}
        )
        return response.parse_IDs()

    def _append_new_images(self, ids):
        """Adds list of IDs to pending images"""
        Logger.log(f"Adding {len(ids)} new entries to list of pending assets.")
        self.pending.extend(
            dict(zip(self.CSV_HEADER, [item, self.NOW])) for item in ids
        )

    def _process_pending(self):
        """Iterates over each entry of list of currently pending images.
        If an entry already exists on S3 it is skipped and removed from pending.
        If not the image is downloaded from the MuseumPlus API and saved to S3.
        """
        Logger.log("Processing pending images")
        aborted = False
        done = []

        for item in self.pending:
            try:
                id_ = item["ID"]
                key = self._id_to_key(id_)

                if self.s3.check_key(key):
                    Logger.log(
                        f"{key} already exists on S3. Removing it from pending..."
                    )

                else:
                    Logger.log(f"Downloading {key}")
                    self._download_and_save_image(id_)

                done.append(item)

            except KeyboardInterrupt:
                # Terminate downloading if user sends keyboard interrupt
                Logger.log("KeyboardInterrupt: Execution was halted", "ERROR")
                aborted = True
                break

            except Exception as e:
                # Skip image if error occurs
                Logger.log(
                    f"Processing of {key} failed: {type(e).__name__}\nError Message: {e}",
                    "ERROR",
                )
                aborted = True

        self.pending = [item for item in self.pending if item not in done]

        Logger.log(
            (
                "Some errors occurred. Pending images might still exist. Re-run the script to complete the process."
                if aborted
                else "Querying and downloading of all images finished successfully!"
            ),
            "WARNING" if aborted else "SUCCESS",
        )

    def _download_and_save_image(self, id_):
        self.s3.put_object(
            key=self._id_to_key(id_),
            object=self.mplus.request(
                "image-download", url_placeholders={"id": id_}
            ).content,
            content_type="image/jpeg",
        )

    def _id_to_key(self, id_):
        return f"{id_}.jpg"


def main():
    exporter = ImgExporter()
    exporter.run_export()


if __name__ == "__main__":
    main()
