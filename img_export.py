import json
from dotenv import load_dotenv
from datetime import datetime
from mpluspy import MPlusClient
from abstract_exporter import AbstractExporter
from logger import Logger

load_dotenv()


class ImgExporter(AbstractExporter):

    TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
    LAST_RUN_KEY = "last-run.txt"
    PENDING_KEY = "pending.json"
    JSON_KEYS = {"size": "size", "state": "state"}

    def __init__(self):
        super().__init__()
        # set upload folder for s3 client
        self.s3.set_key_prefix("extra_large")

    def run_export(self):
        """Runs export of new/changed thumbnail images from MPlus and saves them to S3."""
        # setup export and get state of last run
        self._setup_export()

        # query new images and add them to pending list
        new = self._query_for_new_images(self.last)
        self._update_pending(new if new else {})

        # save pending and last run before downloading images
        self._save_pending()
        self._save_last_run()

        # download images and save them to s3
        self._process_pending()

        # save processed pending
        self._save_pending()

        # mirror deleted assets on s3
        self._mirror_deleted_images()
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
        """Load dict of pending images from json on S3. If the file is not found it will be initialized as empty"""
        key = self.PENDING_KEY
        if not self.s3.check_key(key):
            Logger.log(
                f"No pending file found ({key}) on S3. Initializing empty.",
                "WARNING",
            )
            return {}

        s = self.s3.get_object_string(key)
        return json.loads(s)

    def _save_pending(self):
        """Saves dict with img prcessing state as json to S3"""
        self.s3.put_object(
            key=self.PENDING_KEY, object=json.dumps(self.pending), content_type="text/json"
        )

    def _query_for_new_images(self, last_run):
        """Query Mplus for Digital Assets modifed after given date. Returns list dict of IDs with requested thumb size"""
        Logger.log(f"Get IDs of all digital assets in MPlus modified since {last_run}.")
        timestamp = MPlusClient.format_timestamp(last_run)
        result = {}

        # get medium images
        response_medium = self.mplus.request(
            "image-search-not-downloadable", xml_placeholders={"timestamp": timestamp}
        )
        for id_ in response_medium.parse_IDs() or {}:
            result[id_] = {self.JSON_KEYS["size"]: "medium", self.JSON_KEYS["state"]: "pending"}

        # get extra-large images
        response_extra_large = self.mplus.request(
            "image-search-downloadable", xml_placeholders={"timestamp": timestamp}
        )
        for id_ in response_extra_large.parse_IDs() or {}:
            result[id_] = {self.JSON_KEYS["size"]: "extra_large", self.JSON_KEYS["state"]: "pending"}

        return result

    def _update_pending(self, new):
        """Adds dict of new IDs to pending images. Skips if ID is already present and updates sizes where needed."""
        Logger.log(f"Checking and appending/updating {len(new)} entries for list of pending assets.")
        for id_ in new:
            if not id_ in self.pending:
                self.pending[id_] = new[id_]
            elif new[id_][self.JSON_KEYS["size"]] != self.pending[id_][self.JSON_KEYS["size"]]:
                self.pending[id_] = new[id_]
            else:
                Logger.log(f"{id_} already exists on S3. Skipping...")


    def _process_pending(self):
        """Iterates over each entry of currently pending images.
        If an entry is already marked as uploaded it is skipped and removed from pending.
        If not the image is downloaded from the MuseumPlus API and saved to S3.
        """
        Logger.log("Processing pending images")
        aborted = False

        for id_ in self.pending:
            try:
                key = self._id_to_key(id_)

                if self.pending[id_][self.JSON_KEYS["state"]] == "pending":
                    Logger.log(f"Downloading {key}")
                    self._download_and_save_image(id_, self.pending[id_][self.JSON_KEYS["size"]])
                    self.pending[id_][self.JSON_KEYS["state"]] = "uploaded"

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

        Logger.log(
            (
                "Some errors occurred. Pending images might still exist. Re-run the script to complete the process."
                if aborted
                else "Querying and downloading of all images finished successfully!"
            ),
            "WARNING" if aborted else "SUCCESS",
        )

    def _download_and_save_image(self, id_, size):
        self.s3.put_object(
            key=self._id_to_key(id_),
            object=self.mplus.request(
                "image-download", url_placeholders={"id": id_, "size": size}
            ).content,
            content_type="image/jpeg",
        )

    def _mirror_deleted_images(self):
        """Search and delete images that have been removed/set to private in M+"""
        Logger.log(f"Get IDs of all public digital assets in MPlus to check for deletions.")

        public_images = self.mplus.request("image-search").parse_IDs()
        for id_ in self.pending:
            if not id_ in public_images:
               self.s3.delete_object(self._id_to_key(id_))
               self.pending[id_][self.JSON_KEYS["state"]] = "deleted"

    def _id_to_key(self, id_):
        return f"{id_}.jpg"


def main():
    exporter = ImgExporter()
    exporter.run_export()


if __name__ == "__main__":
    main()
